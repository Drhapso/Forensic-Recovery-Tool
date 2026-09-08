"""
Módulo de exportación forense, resolución de nombres originales y reconstrucción jerárquica de carpetas.
Garantiza que la recuperación no destruya ni sobreescriba datos en el disco de origen,
restaura los nombres auténticos de los archivos mediante metadatos y registros forenses,
recrea la jerarquía completa de directorios y subdirectorios, calcula hashes SHA-256 y audita reportes.
"""

import os
import re
import io
import shutil
import hashlib
import json
import zipfile
import datetime
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Optional

class RecoveryExporter:
    """Gestiona la exportación segura, resolución de nombres originales y reconstrucción de directorios."""

    INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    RESERVED_NAMES = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }

    @staticmethod
    def sanitize_filename(name: str, max_length: int = 240) -> str:
        """Sanitiza una cadena para que sea un nombre de archivo 100% válido en Windows."""
        if not name:
            return "archivo_recuperado.bin"
        
        # Reemplazar caracteres inválidos
        clean = RecoveryExporter.INVALID_FS_CHARS.sub("_", name)
        # Eliminar espacios y puntos iniciales/finales
        clean = clean.strip(" .")
        
        if not clean:
            clean = "archivo_recuperado.bin"

        base, ext = os.path.splitext(clean)
        # Proteger nombres de dispositivo reservados en Windows
        if base.upper() in RecoveryExporter.RESERVED_NAMES:
            base = f"rec_{base}"
            clean = f"{base}{ext}"

        # Truncar respetando la extensión
        if len(clean) > max_length:
            base = base[:max_length - len(ext) - 4]
            clean = f"{base}{ext}"

        return clean

    @staticmethod
    def sanitize_folder_name(name: str, max_length: int = 240) -> str:
        """Sanitiza una cadena para ser un nombre de subdirectorio válido en Windows."""
        if not name:
            return "Carpeta_Sin_Nombre"
        clean = RecoveryExporter.INVALID_FS_CHARS.sub("_", name).strip(" .")
        if not clean:
            clean = "Carpeta_Recuperada"
        if clean.upper() in RecoveryExporter.RESERVED_NAMES:
            clean = f"dir_{clean}"
        return clean[:max_length]

    @staticmethod
    def extract_embedded_title(data_or_path: Any, extension: str) -> Optional[str]:
        """
        Intenta extraer el título interno o nombre descriptivo original incrustado
        en los metadatos de documentos (Office OOXML, PDF), imágenes (EXIF) y multimedia (MP4).
        """
        ext = extension.lower().strip()
        data = None

        try:
            if isinstance(data_or_path, (bytes, bytearray)):
                data = bytes(data_or_path)
            elif isinstance(data_or_path, str) and os.path.exists(data_or_path):
                # Leer muestra suficiente para metadatos (hasta 4MB)
                with open(data_or_path, "rb") as f:
                    data = f.read(4 * 1024 * 1024)
        except Exception:
            return None

        if not data:
            return None

        # 1. Documentos Office OpenXML (DOCX, XLSX, PPTX)
        if ext in {".docx", ".xlsx", ".pptx", ".zip"}:
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    if "docProps/core.xml" in zf.namelist():
                        core_xml = zf.read("docProps/core.xml")
                        root = ET.fromstring(core_xml)
                        for elem in root.iter():
                            if elem.tag.endswith("}title") and elem.text and elem.text.strip():
                                title = elem.text.strip()
                                if len(title) >= 3 and not title.startswith("Microsoft Word"):
                                    return title
            except Exception:
                pass

        # 2. Documentos PDF
        elif ext == ".pdf":
            try:
                # Buscar /Title (Texto del título)
                m = re.search(rb'/Title\s*\(([^)]+)\)', data[:65536])
                if m:
                    raw_title = m.group(1).decode("latin-1", errors="ignore").strip()
                    if len(raw_title) >= 3:
                        return raw_title
            except Exception:
                pass

        # 3. Archivos MP4 / MOV (Metadatos atom 'moov.udta.meta.ilst.\xa9nam')
        elif ext in {".mp4", ".mov", ".m4a"}:
            try:
                idx = data.find(b"\xa9nam")
                if idx != -1 and idx + 16 < len(data):
                    # El átomo 'data' usualmente sigue después
                    data_tag = data.find(b"data", idx)
                    if data_tag != -1 and data_tag + 12 < len(data):
                        val_len = int.from_bytes(data[data_tag - 4 : data_tag], byteorder="big") - 16
                        if 3 <= val_len <= 120:
                            title_bytes = data[data_tag + 8 : data_tag + 8 + val_len]
                            title_str = title_bytes.decode("utf-8", errors="ignore").strip()
                            if len(title_str) >= 3:
                                return title_str
            except Exception:
                pass

        return None

    @staticmethod
    def clean_autorecover_filename(raw_name: str, item: Optional[Dict[str, Any]] = None) -> str:
        """
        Normaliza nombres de archivos de auto-recuperación de Microsoft Office.
        Ejemplo: 'AutoRecovery save of Presupuesto.asd' -> 'Presupuesto.docx'
        """
        if not raw_name:
            return raw_name

        m = re.match(r"(?:AutoRecovery save of |Autoguardado de |Copia de seguridad de )(.*)\.(?:asd|wbk|xar)$", raw_name, re.IGNORECASE)
        if m:
            base = m.group(1).strip()
            ext = os.path.splitext(raw_name)[1].lower()
            orig_ext = ".docx" if ext in {".asd", ".wbk"} else (".xlsx" if ext == ".xar" else ".docx")
            return f"{base}{orig_ext}"

        # Caso ~WRLXXXX.tmp de Word
        if re.match(r"~WRL\d{4}\.tmp", raw_name, re.IGNORECASE):
            return "Documento_Word_Autoguardado.docx"

        return raw_name

    @classmethod
    def resolve_item_filename(cls, item: Dict[str, Any], preserve_original_name: bool = True) -> Tuple[str, bool]:
        """
        Determina el nombre de archivo final a usar en la restauración.
        Retorna: (nombre_sanitizado, fue_restaurado_nombre_original)
        """
        if not preserve_original_name:
            return cls.sanitize_filename(item.get("name", "archivo_recuperado.bin")), False

        # 1. Si el ítem ya posee un 'original_name' explícito
        if item.get("original_name"):
            return cls.sanitize_filename(item["original_name"]), True

        # 2. Si tiene una ruta original real en disco (ej. desde Papelera $I o MFT)
        orig_path = item.get("original_path", "")
        if orig_path and not orig_path.startswith("[") and not orig_path.startswith("Papelera Huérfana"):
            base_from_path = os.path.basename(orig_path.replace("/", "\\"))
            if base_from_path and not base_from_path.startswith("$R"):
                return cls.sanitize_filename(base_from_path), True

        # 3. Detección de auto-recuperación de Office
        cur_name = item.get("name", "")
        cleaned_auto = cls.clean_autorecover_filename(cur_name, item)
        if cleaned_auto != cur_name:
            return cls.sanitize_filename(cleaned_auto), True

        # 4. Extracción de título incrustado en metadatos (para huérfanos $R o tallados)
        sample = item.get("data_source_path") or item.get("preview_bytes")
        ext = os.path.splitext(cur_name)[1]
        title = cls.extract_embedded_title(sample, ext)
        if title:
            candidate = f"{title}{ext}"
            return cls.sanitize_filename(candidate), True

        # 5. Fallback al nombre catalogado en el escaneo
        return cls.sanitize_filename(cur_name or "archivo_recuperado.bin"), False

    @classmethod
    def resolve_item_destination_path(cls, 
                                     item: Dict[str, Any], 
                                     base_dest_dir: str, 
                                     restore_folder_tree: bool = True, 
                                     preserve_original_name: bool = True) -> Tuple[str, str, str]:
        """
        Calcula la ruta completa final y la carpeta destino dentro del árbol recreado.
        Retorna: (ruta_completa_segura, subcarpeta_relativa, nombre_archivo_final)
        """
        final_filename, _ = cls.resolve_item_filename(item, preserve_original_name=preserve_original_name)

        if not restore_folder_tree:
            # Modo Plano: Todos los archivos se guardan directamente en la raíz de destino
            os.makedirs(base_dest_dir, exist_ok=True)
            target_path = cls.get_safe_filepath(base_dest_dir, final_filename)
            return target_path, "", final_filename

        # Modo Árbol Jerárquico: Reconstruir la estructura original
        orig_path = item.get("original_path", "")
        orig_dir = item.get("original_dir", "")

        # Caso A: Ruta original real con unidad de Windows (ej. C:\Users\User\Documents\Reportes)
        path_to_inspect = orig_dir if (orig_dir and not orig_dir.startswith("[")) else orig_path
        drive, tail = os.path.splitdrive(path_to_inspect.replace("/", "\\"))

        if drive:
            drive_letter = drive.replace(":", "").upper()
            drive_folder = f"Disco {drive_letter}"
            # Dividir subdirectorios evitando partes vacías
            subdirs = [cls.sanitize_folder_name(p) for p in tail.strip("\\/").split("\\") if p]
            # Si el último componente es el nombre del archivo, removerlo del árbol de carpetas
            if subdirs and (subdirs[-1].lower() == item.get("name", "").lower() or subdirs[-1].lower() == final_filename.lower()):
                subdirs.pop()
            
            target_folder = os.path.join(base_dest_dir, drive_folder, *subdirs)
            rel_folder = os.path.join(drive_folder, *subdirs)

        # Caso B: Ubicaciones relativas identificadas (Papelera Huérfana, Temporales, VSS, etc.)
        elif orig_dir and not orig_dir.startswith("[") and not orig_dir.startswith("Sectores en Crudo") and not item.get("is_carved"):
            clean_dir = cls.sanitize_folder_name(orig_dir)
            target_folder = os.path.join(base_dest_dir, "Estructura_Detectada", clean_dir)
            rel_folder = os.path.join("Estructura_Detectada", clean_dir)

        # Caso C: Archivos tallados en crudo por sectores
        else:
            cat = cls.sanitize_folder_name(item.get("category", "Otros"))
            target_folder = os.path.join(base_dest_dir, "Archivos_Tallados_Sin_Ruta", cat)
            rel_folder = os.path.join("Archivos_Tallados_Sin_Ruta", cat)

        os.makedirs(target_folder, exist_ok=True)
        target_path = cls.get_safe_filepath(target_folder, final_filename)
        return target_path, rel_folder, final_filename

    @staticmethod
    def is_same_drive(src_path: str, dest_dir: str) -> bool:
        """Verifica si la ruta de origen y la de destino comparten la misma unidad."""
        try:
            src_drive = os.path.splitdrive(os.path.abspath(src_path))[0].upper()
            dest_drive = os.path.splitdrive(os.path.abspath(dest_dir))[0].upper()
            return src_drive == dest_drive and src_drive != ""
        except Exception:
            return False

    @staticmethod
    def get_safe_filepath(dest_dir: str, filename: str) -> str:
        """Genera una ruta única sin sobreescribir archivos existentes en el destino."""
        base, ext = os.path.splitext(filename)
        candidate = os.path.join(dest_dir, filename)
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(dest_dir, f"{base}_{counter}{ext}")
            counter += 1
        return candidate

    @staticmethod
    def compute_sha256(filepath: str) -> str:
        """Calcula el hash SHA-256 para verificar la integridad del archivo exportado."""
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    @classmethod
    def export_item(cls, 
                    item: Dict[str, Any], 
                    dest_dir: str,
                    preserve_original_names: bool = True,
                    restore_folder_tree: bool = True) -> Tuple[bool, str, str, str, str]:
        """
        Exporta un elemento individual resolviendo su nombre original y árbol de carpetas.
        Retorna: (éxito, ruta_final, mensaje_o_hash, nombre_final, carpeta_relativa)
        """
        target_path, rel_folder, final_name = cls.resolve_item_destination_path(
            item, 
            dest_dir, 
            restore_folder_tree=restore_folder_tree, 
            preserve_original_name=preserve_original_names
        )

        try:
            # Caso 1: Archivo con ruta de datos existente (Papelera o Temp)
            data_source = item.get("data_source_path")
            if data_source and os.path.exists(data_source):
                if item.get("is_folder"):
                    shutil.copytree(data_source, target_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(data_source, target_path)
                
                checksum = cls.compute_sha256(target_path)
                return True, target_path, checksum, final_name, rel_folder

            # Caso 2: Archivo reconstruido por Carving desde un contenedor o muestra
            if item.get("is_carved"):
                container = item.get("container_file")
                offset = item.get("stream_offset", 0)
                size = item.get("size", 0)

                if container and os.path.exists(container):
                    with open(container, "rb") as fsrc:
                        fsrc.seek(offset)
                        data = fsrc.read(size)
                    with open(target_path, "wb") as fdest:
                        fdest.write(data)
                elif "preview_bytes" in item and item["preview_bytes"]:
                    # Guardar los bytes disponibles en memoria
                    with open(target_path, "wb") as fdest:
                        fdest.write(item["preview_bytes"])
                else:
                    return False, "", "No se encontraron datos binarios asociados para el archivo tallado.", final_name, rel_folder

                checksum = cls.compute_sha256(target_path)
                return True, target_path, checksum, final_name, rel_folder

            # Caso 3: Archivo con muestra en memoria
            if "preview_bytes" in item and item["preview_bytes"]:
                with open(target_path, "wb") as fdest:
                    fdest.write(item["preview_bytes"])
                checksum = cls.compute_sha256(target_path)
                return True, target_path, checksum, final_name, rel_folder

            return False, "", "Tipo de origen no soportado o archivo sin datos.", final_name, rel_folder

        except Exception as e:
            return False, "", f"Error exportando: {e}", final_name, rel_folder

    @classmethod
    def export_batch(cls, 
                     items: List[Dict[str, Any]], 
                     dest_dir: str,
                     preserve_original_names: bool = True,
                     restore_folder_tree: bool = True,
                     progress_callback: Optional[Any] = None) -> Dict[str, Any]:
        """
        Exporta un lote de archivos seleccionados aplicando la reconstrucción del árbol
        y la preservación de nombres originales, generando un informe de auditoría forense.
        """
        results = []
        success_count = 0
        failed_count = 0
        total = len(items)
        reconstructed_dirs = set()
        total_bytes_exported = 0

        for i, item in enumerate(items):
            success, path, info, final_name, rel_folder = cls.export_item(
                item, 
                dest_dir,
                preserve_original_names=preserve_original_names,
                restore_folder_tree=restore_folder_tree
            )
            
            orig_name = item.get("original_name") or item.get("name")
            orig_path = item.get("original_path", "-")

            if success:
                success_count += 1
                f_size = item.get("size", 0)
                total_bytes_exported += f_size
                if rel_folder:
                    reconstructed_dirs.add(rel_folder)

                results.append({
                    "name": final_name,
                    "original_name": orig_name,
                    "original_path": orig_path,
                    "restored_path": path,
                    "rel_folder": rel_folder,
                    "status": "Recuperado con éxito",
                    "sha256": info,
                    "size": f_size,
                    "source_method": item.get("source_method", "")
                })
            else:
                failed_count += 1
                results.append({
                    "name": final_name,
                    "original_name": orig_name,
                    "original_path": orig_path,
                    "restored_path": "",
                    "rel_folder": rel_folder,
                    "status": "Fallido",
                    "error": info,
                    "size": item.get("size", 0),
                    "source_method": item.get("source_method", "")
                })

            if progress_callback:
                pct = int(((i + 1) / max(total, 1)) * 100)
                progress_callback(f"Restaurando {final_name}...", pct)

        # Generar reporte de auditoría forense en la carpeta destino
        report_path = os.path.join(dest_dir, "reporte_recuperacion.txt")
        try:
            with open(report_path, "w", encoding="utf-8") as rf:
                rf.write("=" * 70 + "\n")
                rf.write(" REPORTE DE RECUPERACIÓN FORENSE DE DATOS - LOCAL RECOVERY SUITE\n")
                rf.write("=" * 70 + "\n")
                rf.write(f" Fecha y Hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                rf.write(f" Carpeta Destino: {dest_dir}\n")
                rf.write(f" Preservar Nombres Originales: {'SÍ' if preserve_original_names else 'NO'}\n")
                rf.write(f" Reconstruir Árbol de Carpetas: {'SÍ' if restore_folder_tree else 'NO (Modo Plano)'}\n")
                rf.write(f" Carpetas Jerárquicas Recreadas: {len(reconstructed_dirs)}\n")
                rf.write(f" Total de archivos procesados: {total}\n")
                rf.write(f" Recuperados exitosamente: {success_count}\n")
                rf.write(f" Errores de exportación: {failed_count}\n")
                rf.write("=" * 70 + "\n\n")

                for res in results:
                    rf.write(f"• Archivo: {res['name']}\n")
                    if res.get("original_name") and res['original_name'] != res['name']:
                        rf.write(f"  Nombre Original Detectado: {res['original_name']}\n")
                    rf.write(f"  Ruta Original: {res['original_path']}\n")
                    rf.write(f"  Estado: {res['status']}\n")
                    rf.write(f"  Método de Recuperación: {res['source_method']}\n")
                    if res.get("restored_path"):
                        rf.write(f"  Ubicación Restaurada: {res['restored_path']}\n")
                        rf.write(f"  Firma Criptográfica SHA-256: {res.get('sha256')}\n")
                    if res.get("error"):
                        rf.write(f"  Causa del Error: {res.get('error')}\n")
                    rf.write("\n")
        except Exception:
            pass

        # Registrar exportación en la base de datos local SQLite si está disponible
        try:
            from core.local_db import LocalDatabase
            LocalDatabase.log_recovery_export(
                destination=dest_dir,
                file_count=success_count,
                byte_count=total_bytes_exported,
                report_path=report_path,
                details={
                    "preserve_original_names": preserve_original_names,
                    "restore_folder_tree": restore_folder_tree,
                    "folders_created": len(reconstructed_dirs),
                    "total_requested": total
                }
            )
        except Exception:
            pass

        return {
            "total": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "report_path": report_path,
            "preserve_original_names": preserve_original_names,
            "restore_folder_tree": restore_folder_tree,
            "folders_count": len(reconstructed_dirs),
            "results": results
        }
