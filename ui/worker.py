"""
Hilos de trabajo asíncronos (QThread) con emisión de telemetría de alta resolución.
Permiten alimentar el HUD en tiempo real con la ruta actual, velocidad en MB/s,
volumen procesado, contadores por categoría y soporte para múltiples directorios seleccionados.
"""

import os
import time
from typing import Any, List
from PyQt5.QtCore import QThread, pyqtSignal
from core.recycle_bin import RecycleBinScanner
from core.temp_scanner import TempScanner
from core.thumbcache_extractor import ThumbcacheExtractor
from core.file_carver import FileCarver, FORENSIC_CONTAINER_EXTS
from core.mft_scanner import MFTScanner
from core.shadow_explorer import ShadowExplorer
from core.exporter import RecoveryExporter
from core.software_filter import SoftwareFilter
from core.session_manager import SessionManager
from core.integrity_analyzer import IntegrityAnalyzer

class ScanWorker(QThread):
    """Hilo asíncrono para ejecutar los protocolos de escaneo con telemetría en vivo."""

    progress_changed = pyqtSignal(str, int)  # Compatibilidad básica
    telemetry_updated = pyqtSignal(str, int, str, int, int, dict)  # (msg, pct, path, bytes, count, cats)
    finished_scan = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, 
                 scan_mode: str, 
                 target_paths: Any = None,
                 selected_categories: list = None,
                 skip_software: bool = True,
                 is_incremental: bool = True,
                 selected_doc_extensions: list = None,
                 selected_extensions: list = None):
        super().__init__()
        self.scan_mode = scan_mode
        if isinstance(target_paths, str):
            self.target_paths = [target_paths] if target_paths else []
        elif isinstance(target_paths, list):
            self.target_paths = target_paths
        else:
            self.target_paths = []

        self.selected_categories = selected_categories or []
        self.skip_software = skip_software
        self.is_incremental = is_incremental
        self.selected_doc_extensions = selected_doc_extensions
        self.selected_extensions = selected_extensions
        self.is_cancelled = False
        self.carver = None

        self.last_emit_time = 0
        self.category_counts = {
            "Imágenes": 0,
            "Documentos": 0,
            "Audio": 0,
            "Video": 0,
            "Comprimidos": 0,
            "Otros": 0
        }

    def _filter_items(self, items: list) -> list:
        """Aplica filtros de categoría y extensiones seleccionadas de cualquier tipo."""
        if not items:
            return []
        
        doc_exts = {e.lower() for e in self.selected_doc_extensions} if self.selected_doc_extensions is not None else None
        all_exts = {e.lower() for e in self.selected_extensions} if self.selected_extensions is not None else None
        
        filtered = []
        for it in items:
            cat = it.get("category", "Otros")
            
            # Si hay categorías seleccionadas y no coincide
            if self.selected_categories:
                matched_cat = False
                for sc in self.selected_categories:
                    if sc in cat or (sc == "Documentos" and "Documento" in cat):
                        matched_cat = True
                        break
                if not matched_cat:
                    continue

            name = it.get("name", "")
            orig = it.get("original_path", "")
            ext = os.path.splitext(name)[1].lower()
            if not ext and orig:
                ext = os.path.splitext(orig)[1].lower()

            # Si se proporcionó el filtro global de extensiones (todos los formatos activos)
            if all_exts is not None:
                if ext and ext not in all_exts:
                    continue
            else:
                # Compatibilidad hacia atrás si solo se definió selected_doc_extensions
                is_doc = (cat == "Documentos" or "Documento" in cat)
                if is_doc and doc_exts is not None:
                    if ext not in doc_exts:
                        continue

            filtered.append(it)
        return filtered

    def _filter_out_existing_data(self, items: list) -> list:
        """
        Filtro estricto forense:
        Omite todos los datos que actualmente existen y están activos en las unidades.
        Solo preserva información que se encuentre genuinamente en estado de recuperación
        (Papelera, MFT inactivo, borradores huérfanos, tallado en imágenes/sectores, o instantáneas VSS).
        No indexa nada de lo existente.
        """
        if not items:
            return []

        # Obtener letras de unidad seleccionadas en el alcance (ej. {"H:", "C:"})
        target_drives = set()
        for p in self.target_paths:
            if len(p) >= 2 and p[1] == ":":
                target_drives.add(p[:2].upper())

        # Recopilar firmas de archivos activos en las rutas objetivo seleccionadas
        existing_signatures = set()
        for t_path in self.target_paths:
            if os.path.isdir(t_path):
                try:
                    for entry in os.scandir(t_path):
                        if entry.is_file(follow_symlinks=False):
                            try:
                                sz = entry.stat().st_size
                                existing_signatures.add((entry.name.lower(), sz))
                            except Exception:
                                pass
                except Exception:
                    pass

        filtered = []
        for it in items:
            method = it.get("source_method", "")
            orig_path = it.get("original_path", "")
            orig_name = it.get("name", "")
            item_size = it.get("size", 0)

            # 0. AISLAMIENTO ESTRICTO DE ALCANCE Y UNIDAD:
            # Si el usuario seleccionó unidades específicas, NINGÚN archivo de otra unidad
            # distinta puede ingresar a los resultados bajo ninguna circunstancia.
            if target_drives:
                item_drive = it.get("drive", "").upper().rstrip("\\/")
                orig = it.get("original_path", "")
                data_src = it.get("data_source_path", "")
                container = it.get("container_file", "")

                item_drv_letter = None
                if len(item_drive) >= 2 and item_drive[1] == ":":
                    item_drv_letter = item_drive[:2].upper()
                elif len(item_drive) == 1:
                    item_drv_letter = f"{item_drive}:".upper()
                elif len(orig) >= 2 and orig[1] == ":":
                    item_drv_letter = orig[:2].upper()
                elif len(data_src) >= 2 and data_src[1] == ":":
                    item_drv_letter = data_src[:2].upper()
                elif len(container) >= 2 and container[1] == ":":
                    item_drv_letter = container[:2].upper()

                if item_drv_letter and item_drv_letter not in target_drives:
                    # El archivo pertenece a OTRA unidad diferente a la seleccionada -> OMITIR
                    continue

            # 1. Si el elemento apunta a un archivo que existe físicamente en el disco y es accesible:
            # En la papelera o MFT, orig_path es la ruta antes del borrado. Si esa ruta existe actualmente
            # en el disco como un archivo regular con datos, el archivo ya está presente (no está perdido).
            if orig_path and os.path.isabs(orig_path) and not orig_path.startswith(("\\\\.\\", "/dev/")):
                if os.path.isfile(orig_path):
                    data_src = it.get("data_source_path", "")
                    if not data_src or os.path.abspath(data_src).lower() == os.path.abspath(orig_path).lower():
                        # El archivo existe directamente en esa ubicación; omitirlo
                        continue
                    else:
                        # Si data_src es de la papelera ($Recycle.Bin), pero en orig_path YA EXISTE otro archivo
                        # idéntico en nombre y tamaño, el usuario ya lo tiene activo.
                        try:
                            if os.path.getsize(orig_path) == item_size:
                                continue
                        except Exception:
                            pass

            # 2. Si el elemento fue tallado (carved) y el contenedor es un archivo regular de usuario existente:
            container = it.get("container_file")
            if container and os.path.isfile(container):
                cont_ext = os.path.splitext(container)[1].lower()
                if cont_ext not in FORENSIC_CONTAINER_EXTS and not container.startswith(("\\\\.\\", "/dev/")):
                    continue

            # 3. Si coincide exactamente en nombre y tamaño con un archivo activo en el directorio analizado:
            # (a menos que provenga de una Copia de Sombra VSS o registro MFT con datos residentes)
            if "Copia de Sombra" not in method and (orig_name.lower(), item_size) in existing_signatures:
                continue

            # 4. Excluir archivos con tamaño 0 o corruptos sin contenido
            if item_size == 0 and not it.get("is_folder", False):
                continue

            filtered.append(it)

        return filtered


    def cancel(self):
        """Cancela la ejecución del escaneo."""
        self.is_cancelled = True
        if self.carver:
            self.carver.cancel()

    def _emit_telemetry(self, msg: str, pct: int, current_path: str = "", bytes_scanned: int = 0, items_count: int = 0, force: bool = False):
        """Emite telemetría controlando la tasa de refresco (máximo 25 Hz) para máxima fluidez."""
        now = time.time()
        if force or (now - self.last_emit_time >= 0.04):
            self.last_emit_time = now
            self.progress_changed.emit(msg, pct)
            self.telemetry_updated.emit(
                msg, 
                pct, 
                current_path, 
                bytes_scanned, 
                items_count, 
                self.category_counts
            )

    def _register_items(self, items: list):
        """Actualiza los contadores de categoría."""
        for item in items:
            cat = item.get("category", "Otros")
            if cat in self.category_counts:
                self.category_counts[cat] += 1
            elif "Documento" in cat:
                self.category_counts["Documentos"] += 1
            else:
                self.category_counts["Otros"] += 1

    def run(self):
        try:
            results = []
            self.is_cancelled = False
            self.category_counts = {k: 0 for k in self.category_counts}

            matched_session = None
            fingerprints = {}

            # Comprobación de Escaneo Incremental previo
            if self.is_incremental and self.target_paths:
                matched_session = SessionManager.find_matching_session(self.target_paths, self.selected_categories)
                if matched_session:
                    fingerprints = matched_session.get("fingerprints", {})
                    prev_count = len(matched_session.get("items", []))
                    self._emit_telemetry(
                        f"⚡ [Incremental] Sesión previa '{matched_session.get('name')}' detectada ({prev_count} archivos). Analizando solo novedades...",
                        3,
                        "Sesión previa guardada",
                        0,
                        prev_count,
                        force=True
                    )

            # FASE PRELIMINAR: Catalogación inteligente de software y juegos para exclusión
            if self.skip_software:
                self._emit_telemetry("[Fase Inicial] Analizando catálogo de software y juegos instalados...", 4, "Registro de Windows y Bibliotecas de Juegos", 0, 0, force=True)
                catalog = SoftwareFilter.build_catalog()
                self._emit_telemetry(f"Filtro Inteligente: {catalog['total_prefixes']} rutas de programas/juegos catalogadas.", 6, force=True)

            # Extraer letras de unidades del alcance seleccionado
            target_drives = set()
            for p in self.target_paths:
                if len(p) >= 2 and p[1] == ":":
                    target_drives.add(p[:2].upper())

            # MODO 1: PROTOCOLO FORENSE PROFUNDO MULTICAPA (El más exhaustivo)
            if self.scan_mode == "deep_forensic":
                # Fase 1/5: Papelera Forense y Huérfanos $R (Exclusivo para las unidades seleccionadas)
                self._emit_telemetry("[Fase 1/5] Análisis Forense de Papelera ($Recycle.Bin y Huérfanos)", 5, force=True)
                def cb_rb(msg, pct, path):
                    if not self.is_cancelled:
                        self._emit_telemetry(f"[Fase 1/5] {msg}", int(pct * 0.20), path, 0, len(results))

                drives_for_rb = [f"{d}\\" for d in target_drives] if target_drives else None
                rb_items = RecycleBinScanner.scan_drives(drives=drives_for_rb, progress_callback=cb_rb)
                rb_items = self._filter_out_existing_data(self._filter_items(rb_items))
                results.extend(rb_items)
                self._register_items(rb_items)

                # Fase 2/5: Extracción de Caché Gráfica (Solo si la unidad C: del sistema está en el alcance)
                if not self.is_cancelled and (not target_drives or "C:" in target_drives):
                    self._emit_telemetry("[Fase 2/5] Rescate de Fotos en Caché Gráfica de Windows...", 21, force=True)
                    def cb_tc(msg, pct, path):
                        if not self.is_cancelled:
                            self._emit_telemetry(f"[Fase 2/5] {msg}", 20 + int(pct * 0.20), path, 0, len(results))

                    tc_items = ThumbcacheExtractor.scan_thumbnails(max_images=200, progress_callback=cb_tc)
                    tc_items = self._filter_out_existing_data(self._filter_items(tc_items))
                    results.extend(tc_items)
                    self._register_items(tc_items)

                # Fase 3/5: Temporales, Borradores de Office y Copias de Seguridad (Solo si la unidad C: está en el alcance)
                if not self.is_cancelled and (not target_drives or "C:" in target_drives):
                    self._emit_telemetry("[Fase 3/5] Rastreando Borradores de Office y Auto-Recuperación...", 41, force=True)
                    def cb_temp(msg, pct):
                        if not self.is_cancelled:
                            self._emit_telemetry(f"[Fase 3/5] {msg}", 40 + int(pct * 0.20), "Borradores de Office y %TEMP%", 0, len(results))

                    temp_items = TempScanner.scan_temp_and_drafts(progress_callback=cb_temp)
                    temp_items = self._filter_out_existing_data(self._filter_items(temp_items))
                    results.extend(temp_items)
                    self._register_items(temp_items)

                # Fase 4/5: Análisis Forense de Registros Eliminados en NTFS ($MFT)
                if not self.is_cancelled:
                    self._emit_telemetry("[Fase 4/5] Análisis de Registros NTFS MFT (Archivos Eliminados)...", 61, force=True)
                    drives_to_scan = target_drives if target_drives else {"C:"}

                    mft_items = []
                    for drv in sorted(drives_to_scan):
                        if self.is_cancelled:
                            break
                        def cb_mft(msg, pct, count, path):
                            if not self.is_cancelled:
                                self._emit_telemetry(f"[Fase 4/5] {msg}", 60 + int(pct * 0.15), path, 0, len(results) + count)
                        m_items = MFTScanner.scan_drive_mft(drv, progress_callback=cb_mft)
                        mft_items.extend(m_items)

                    mft_items = self._filter_out_existing_data(self._filter_items(mft_items))
                    results.extend(mft_items)
                    self._register_items(mft_items)

                # Fase 5/5: File Carving Estructural en Imágenes Forenses y Sectores
                if not self.is_cancelled and self.target_paths:
                    self.carver = FileCarver()
                    tot_paths = len(self.target_paths)
                    for idx, t_path in enumerate(self.target_paths):
                        if self.is_cancelled:
                            break
                        t_name = os.path.basename(t_path) or t_path
                        base_pct = 75 + int((idx / tot_paths) * 25)
                        self._emit_telemetry(f"[Fase 5/5] ({idx+1}/{tot_paths}) Carving en {t_name}...", base_pct, t_path, force=True)

                        def cb_carve(msg, pct, count, bytes_s, cur_target):
                            if not self.is_cancelled:
                                calc_pct = base_pct + int((pct / 100) * (25 / tot_paths))
                                self._emit_telemetry(f"[Fase 5/5] ({idx+1}/{tot_paths}) {msg}", calc_pct, cur_target, bytes_s, len(results) + count)

                        carved_items = self.carver.scan_path(
                            t_path, 
                            selected_categories=self.selected_categories, 
                            progress_callback=cb_carve,
                            skip_software=self.skip_software,
                            fingerprints=fingerprints,
                            selected_doc_extensions=self.selected_doc_extensions,
                            selected_extensions=self.selected_extensions
                        )
                        carved_items = self._filter_out_existing_data(self._filter_items(carved_items))
                        results.extend(carved_items)
                        self._register_items(carved_items)

            # MODO 2: SOLO PAPELERA FORENSE
            elif self.scan_mode == "recycle":
                drives = [f"{d}\\" for d in target_drives] if target_drives else None
                def cb_rb(msg, pct, path):
                    if not self.is_cancelled:
                        self._emit_telemetry(msg, pct, path, 0, len(results))

                results = RecycleBinScanner.scan_drives(drives=drives, progress_callback=cb_rb)
                results = self._filter_out_existing_data(self._filter_items(results))
                self._register_items(results)

            # MODO 3: SOLO CACHÉ GRÁFICA (THUMBCACHE)
            elif self.scan_mode == "thumbcache":
                def cb_tc(msg, pct, path):
                    if not self.is_cancelled:
                        self._emit_telemetry(msg, pct, path, 0, len(results))

                results = ThumbcacheExtractor.scan_thumbnails(max_images=300, progress_callback=cb_tc)
                results = self._filter_out_existing_data(self._filter_items(results))
                self._register_items(results)

            # MODO 4: TEMPORALES Y OFFICE
            elif self.scan_mode == "temp":
                def cb_temp(msg, pct):
                    if not self.is_cancelled:
                        self._emit_telemetry(msg, pct, "Carpetas de AutoRecuperación y %TEMP%", 0, len(results))

                results = TempScanner.scan_temp_and_drafts(progress_callback=cb_temp)
                results = self._filter_out_existing_data(self._filter_items(results))
                self._register_items(results)

            # MODO 5: FILE CARVING ESTRUCTURAL
            elif self.scan_mode == "carve":
                self.carver = FileCarver()
                tot_paths = len(self.target_paths)
                for idx, t_path in enumerate(self.target_paths):
                    if self.is_cancelled:
                        break
                    t_name = os.path.basename(t_path) or t_path
                    base_pct = int((idx / max(tot_paths, 1)) * 100)
                    self._emit_telemetry(f"({idx+1}/{tot_paths}) Carving en {t_name}...", base_pct, t_path, force=True)

                    def cb_carve(msg, pct, count, bytes_s, cur_target):
                        if not self.is_cancelled:
                            calc_pct = base_pct + int((pct / 100) * (100 / max(tot_paths, 1)))
                            self._emit_telemetry(f"({idx+1}/{tot_paths}) {msg}", calc_pct, cur_target, bytes_s, len(results) + count)

                    carved_items = self.carver.scan_path(
                        t_path, 
                        selected_categories=self.selected_categories,
                        progress_callback=cb_carve,
                        skip_software=self.skip_software,
                        fingerprints=fingerprints,
                        selected_doc_extensions=self.selected_doc_extensions,
                        selected_extensions=self.selected_extensions
                    )
                    carved_items = self._filter_out_existing_data(self._filter_items(carved_items))
                    results.extend(carved_items)
                    self._register_items(carved_items)

            # MODO 6: COPIAS DE SOMBRA (VSS)
            elif self.scan_mode == "vss":
                self._emit_telemetry("Consultando Servicio de Instantáneas de Volumen (VSS)...", 50, force=True)
                vss_res = ShadowExplorer.get_shadow_copies()
                if vss_res.get("shadows"):
                    for sh in vss_res["shadows"]:
                        results.append({
                            "id": f"vss_{sh.get('id', '')}",
                            "name": f"Punto de Restauración - {sh.get('creation_time', '')}",
                            "original_path": sh.get("device_object", ""),
                            "original_dir": sh.get("original_volume", ""),
                            "size": 0,
                            "date": sh.get("creation_time", "-"),
                            "category": "Copia de Sombra (VSS)",
                            "source_method": "Volume Shadow Copy",
                            "recoverable": True,
                            "is_folder": True
                        })
                results = self._filter_out_existing_data(self._filter_items(results))
                self._register_items(results)

            # Doble barrera de verificación: garantizar 0 archivos activos existentes en resultados finales
            results = self._filter_out_existing_data(results)
            self.category_counts = {k: 0 for k in self.category_counts}
            self._register_items(results)

            # Evaluación Forense de Integridad y Usabilidad
            if not self.is_cancelled and results:
                self._emit_telemetry("Evaluando integridad y usabilidad forense de los archivos...", 98, "Analizador de Usabilidad", 0, len(results), force=True)
                IntegrityAnalyzer.analyze_batch(results)

            # Finalización y Fusión Incremental / Auto-Guardado de Sesión
            if matched_session and not self.is_cancelled:
                merged_results, n_new, n_upd = SessionManager.filter_and_merge_incremental(matched_session, results)
                results = merged_results
                # Actualizar sesión persistente con protección de excepción
                try:
                    SessionManager.save_session(
                        name=matched_session.get("name"),
                        items=results,
                        targets=self.target_paths,
                        categories=self.selected_categories,
                        mode=self.scan_mode,
                        session_id=matched_session.get("session_id")
                    )
                except Exception as save_err:
                    print(f"Advertencia: No se pudo auto-guardar la sesión incremental: {save_err}")

                final_msg = f"Escaneo incremental finalizado: {n_new} nuevos, {n_upd} actualizados ({len(results)} totales en sesión)."
            elif not self.is_cancelled and results:
                # Auto-guardar sesión para futuras comparaciones con protección de excepción
                targets_label = ", ".join(os.path.basename(p) or p for p in self.target_paths[:2]) or "General"
                try:
                    SessionManager.save_session(
                        name=f"Escaneo {targets_label}",
                        items=results,
                        targets=self.target_paths,
                        categories=self.selected_categories,
                        mode=self.scan_mode
                    )
                except Exception as save_err:
                    print(f"Advertencia: No se pudo auto-guardar la sesión: {save_err}")

                final_msg = f"Escaneo finalizado. {len(results)} archivos encontrados (Sesión guardada)."
            elif self.is_cancelled:
                final_msg = "Cancelado por el usuario."
            else:
                final_msg = "Escaneo finalizado. No se encontraron archivos."

            self._emit_telemetry(final_msg, 100, "", 0, len(results), force=True)
            self.finished_scan.emit(results)

        except Exception as e:
            self.error_occurred.emit(str(e))


class ExportWorker(QThread):
    """Hilo asíncrono para exportar de forma segura archivos seleccionados con resolución de nombres y árbol."""

    progress_changed = pyqtSignal(str, int)
    finished_export = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, 
                 items: list, 
                 destination_dir: str, 
                 preserve_original_names: bool = True, 
                 restore_folder_tree: bool = True):
        super().__init__()
        self.items = items
        self.destination_dir = destination_dir
        self.preserve_original_names = preserve_original_names
        self.restore_folder_tree = restore_folder_tree

    def run(self):
        try:
            def cb(msg, pct):
                self.progress_changed.emit(msg, pct)

            summary = RecoveryExporter.export_batch(
                self.items, 
                self.destination_dir, 
                preserve_original_names=self.preserve_original_names,
                restore_folder_tree=self.restore_folder_tree,
                progress_callback=cb
            )
            self.finished_export.emit(summary)
        except Exception as e:
            self.error_occurred.emit(str(e))
