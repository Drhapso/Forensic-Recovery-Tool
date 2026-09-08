"""
Ventana Principal de la Suite de Recuperación de Datos Forense.
Integra la Barra de Información y Telemetría en Vivo (HUD), el panel de escaneo,
la tabla de resultados, el visor de previsualización y el exportador seguro.
"""

import os
import sys
import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QSplitter, QMessageBox,
    QStatusBar, QFrame, QProgressDialog, QInputDialog, QCheckBox
)
from PyQt5.QtCore import Qt

from core.disk_utils import is_admin, format_size
from core.exporter import RecoveryExporter
from core.session_manager import SessionManager
from ui.info_bar import InfoBar
from ui.scan_panel import ScanPanel
from ui.results_table import ResultsTable
from ui.preview_widget import PreviewWidget
from ui.session_dialog import SessionDialog
from ui.worker import ScanWorker, ExportWorker
from ui.theme import DARK_THEME_QSS
from ui.demo_banner import DemoBanner

class MainWindow(QMainWindow):
    """Ventana principal del Recuperador de Datos."""

    def __init__(self, is_demo: bool = False):
        super().__init__()
        self.is_demo = is_demo
        if self.is_demo:
            self.setWindowTitle("🛡️ Forensic Recovery Suite [DEMO DE EVALUACIÓN - 24 HORAS]")
        else:
            self.setWindowTitle("Recuperador de Datos Forense - Forensic Data Recovery Suite")
        self.resize(1360, 840)
        self.setMinimumSize(1024, 650)

        self.scan_worker = None
        self.export_worker = None
        self.last_results = []
        self.demo_banner = None

        self.setStyleSheet(DARK_THEME_QSS)
        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. Encabezado Superior (Header)
        header_frame = QFrame()
        header_frame.setObjectName("Card")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title_box = QVBoxLayout()
        lbl_app_title = QLabel("🛡️ RECUPERADOR DE DATOS FORENSE | DEEP RECOVERY SUITE")
        lbl_app_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        title_box.addWidget(lbl_app_title)

        lbl_app_sub = QLabel("Análisis Multicapa: Papelera Forense ($Recycle.Bin), Huérfanos $R, Thumbcache 1080p/4K, Office Drafts, VSS y File Carving Estructural")
        lbl_app_sub.setStyleSheet("font-size: 11px; color: #8b949e;")
        title_box.addWidget(lbl_app_sub)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Botones de Gestión de Sesiones Persistentes
        self.btn_new_session = QPushButton("➕ Nueva Sesión")
        self.btn_new_session.setToolTip("Cerrar el escaneo actual, limpiar los resultados y comenzar una nueva sesión limpia (Ctrl+N).")
        self.btn_new_session.setShortcut("Ctrl+N")
        self.btn_new_session.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                border: 1px solid #388bfd;
                color: #58a6ff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #ffffff;
                border-color: #58a6ff;
            }
        """)
        self.btn_new_session.clicked.connect(self._start_new_session)
        header_layout.addWidget(self.btn_new_session)

        self.btn_open_sessions = QPushButton("📂 Sesiones Guardadas...")
        self.btn_open_sessions.setToolTip("Explorar, restaurar, renombrar o eliminar sesiones de recuperación previas sin reescanear.")
        self.btn_open_sessions.clicked.connect(self._open_session_manager)
        header_layout.addWidget(self.btn_open_sessions)

        self.btn_save_session = QPushButton("💾 Guardar Sesión...")
        self.btn_save_session.setToolTip("Guardar la lista actual de archivos recuperables como una sesión persistente.")
        self.btn_save_session.setEnabled(False)
        self.btn_save_session.clicked.connect(self._save_current_session)
        header_layout.addWidget(self.btn_save_session)

        # Insignia de Privilegios
        admin_badge = QLabel("🛡️ ADMINISTRADOR" if is_admin() else "👤 MODO ESTÁNDAR")
        badge_style = "padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;"
        if is_admin():
            badge_style += " background-color: #238636; color: white;"
        else:
            badge_style += " background-color: #30363d; color: #e3b341;"
        admin_badge.setStyleSheet(badge_style)
        header_layout.addWidget(admin_badge)

        main_layout.addWidget(header_frame)

        # Si se ejecuta en modo demostración comercial, integrar banner de cuenta regresiva
        if self.is_demo:
            self.demo_banner = DemoBanner(self)
            self.demo_banner.trial_expired.connect(self._on_trial_expired)
            main_layout.addWidget(self.demo_banner)

        # 2. BARRA DE INFORMACIÓN Y TELEMETRÍA EN VIVO (HUD)
        self.info_bar = InfoBar()
        main_layout.addWidget(self.info_bar)

        # 3. Área Central Dividida (Splitter)
        main_splitter = QSplitter(Qt.Horizontal)

        # Panel Izquierdo: Configuración de Escaneo
        self.scan_panel = ScanPanel()
        self.scan_panel.start_scan_requested.connect(self._start_scan)
        self.scan_panel.cancel_scan_requested.connect(self._cancel_scan)
        main_splitter.addWidget(self.scan_panel)

        # Panel Central/Derecho: Splitter de Resultados + Vista Previa
        content_splitter = QSplitter(Qt.Horizontal)

        # Tabla de resultados
        self.results_table = ResultsTable()
        self.results_table.item_selected.connect(self._on_item_selected)
        self.results_table.selection_changed.connect(self._update_export_button_state)
        content_splitter.addWidget(self.results_table)

        # Panel de previsualización
        self.preview_panel = PreviewWidget()
        content_splitter.addWidget(self.preview_panel)

        content_splitter.setStretchFactor(0, 6)
        content_splitter.setStretchFactor(1, 4)

        main_splitter.addWidget(content_splitter)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 7)

        main_layout.addWidget(main_splitter, stretch=1)

        # 4. Barra Inferior de Recuperación y Exportación
        footer_frame = QFrame()
        footer_frame.setObjectName("Card")
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(14, 10, 14, 10)
        footer_layout.setSpacing(8)

        # Fila 1: Selector de Carpeta de Destino
        dest_row = QHBoxLayout()
        dest_row.setSpacing(10)

        lbl_dest = QLabel("📁 Carpeta de Guardado:")
        lbl_dest.setStyleSheet("font-weight: bold;")
        dest_row.addWidget(lbl_dest)

        self.txt_dest = QLabel(self._get_default_recovery_dir())
        self.txt_dest.setStyleSheet("background-color: #0d1117; padding: 6px 12px; border-radius: 4px; border: 1px solid #30363d; color: #58a6ff;")
        dest_row.addWidget(self.txt_dest, stretch=1)

        self.btn_change_dest = QPushButton("Cambiar Destino...")
        self.btn_change_dest.clicked.connect(self._browse_destination)
        dest_row.addWidget(self.btn_change_dest)

        footer_layout.addLayout(dest_row)

        # Fila 2: Opciones Forenses de Restauración y Botón Principal
        opts_row = QHBoxLayout()
        opts_row.setSpacing(16)

        self.chk_preserve_names = QCheckBox("Restaurar con Nombres Originales")
        self.chk_preserve_names.setChecked(True)
        self.chk_preserve_names.setToolTip(
            "Restaura los archivos con su nombre real original, limpiando nombres temporales\n"
            "y recuperando títulos de documentos Office, metadatos y registros del sistema."
        )
        self.chk_preserve_names.setStyleSheet("font-weight: bold; color: #58a6ff;")
        opts_row.addWidget(self.chk_preserve_names)

        self.chk_restore_tree = QCheckBox("Reconstruir Árbol de Carpetas y Subcarpetas Original")
        self.chk_restore_tree.setChecked(True)
        self.chk_restore_tree.setToolTip(
            "Recrea en la carpeta destino la estructura de directorios exacta (Disco C\\Users\\...)\n"
            "donde residían los archivos antes de eliminarse para mantenerlos perfectamente organizados."
        )
        self.chk_restore_tree.setStyleSheet("font-weight: bold; color: #3fb950;")
        opts_row.addWidget(self.chk_restore_tree)

        opts_row.addStretch(1)

        self.btn_export = QPushButton("💾 RECUPERAR SELECCIONADOS")
        self.btn_export.setObjectName("PrimaryButton")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_selected_files)
        opts_row.addWidget(self.btn_export)

        footer_layout.addLayout(opts_row)

        main_layout.addWidget(footer_frame)

        # Barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo para iniciar escaneo.")

    def _get_default_recovery_dir(self) -> str:
        """Determina una carpeta de destino predeterminada segura."""
        user_home = os.path.expanduser("~")
        rec_dir = os.path.join(user_home, "Desktop", "Archivos_Recuperados")
        return rec_dir

    def _browse_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccione la carpeta donde guardar los archivos recuperados")
        if folder:
            self.txt_dest.setText(folder)

    def _start_scan(self, mode: str, target_paths: list, categories: list, skip_software: bool = True, is_incremental: bool = True, selected_doc_extensions: list = None):
        """Inicia el hilo de escaneo conectando la telemetría al HUD."""
        if self.is_demo:
            from core.trial_manager import TrialManager
            TrialManager.heartbeat()
            st = TrialManager.check_or_init_trial()
            if st.get("is_expired"):
                self._on_trial_expired()
                return

        self.results_table.clear()
        self.preview_panel.load_item(None)
        self.btn_export.setEnabled(False)
        self.btn_save_session.setEnabled(False)

        mode_labels = {
            "deep_forensic": "PROTOCOLO FORENSE PROFUNDO",
            "recycle": "PAPELERA FORENSE Y HUÉRFANOS",
            "thumbcache": "RESCATE DE FOTOS EN THUMBCACHE",
            "temp": "BORRADORES DE OFFICE Y TEMPORALES",
            "carve": "FILE CARVING ESTRUCTURAL",
            "vss": "COPIAS DE SOMBRA (VSS)"
        }
        phase_label = mode_labels.get(mode, "ESCANEO EN CURSO")
        if is_incremental:
            phase_label += " (INCREMENTAL)"
        self.info_bar.start(phase_label)
        self.status_bar.showMessage(f"Iniciando {phase_label}...")

        all_selected_exts = None
        if hasattr(self.scan_panel, "get_all_selected_extensions"):
            all_selected_exts = self.scan_panel.get_all_selected_extensions()

        self.scan_worker = ScanWorker(
            scan_mode=mode,
            target_paths=target_paths,
            selected_categories=categories,
            skip_software=skip_software,
            is_incremental=is_incremental,
            selected_doc_extensions=selected_doc_extensions,
            selected_extensions=all_selected_exts
        )
        self.scan_worker.telemetry_updated.connect(self.info_bar.update_status)
        self.scan_worker.finished_scan.connect(self._on_scan_finished)
        self.scan_worker.error_occurred.connect(self._on_scan_error)
        self.scan_worker.start()

    def _cancel_scan(self):
        """Cancela el escaneo en progreso."""
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.info_bar.finish(success=False, final_msg="Cancelando escaneo a petición del usuario...")
            self.status_bar.showMessage("Cancelando escaneo...")

    def _on_scan_finished(self, items: list):
        """Se ejecuta cuando el escáner finaliza."""
        self.last_results = items
        self.scan_panel.set_scanning_state(False)
        self.results_table.set_items(items)
        self._update_export_button_state()
        self.btn_save_session.setEnabled(len(items) > 0)
        self.scan_panel._check_matching_session()

        msg = f"Escaneo completado. Se encontraron {len(items)} archivo(s) recuperables."
        self.info_bar.finish(success=True, final_msg=msg)
        self.status_bar.showMessage(msg)

        if not items:
            QMessageBox.information(
                self,
                "Escaneo Completado",
                "No se encontraron archivos con el protocolo seleccionado en la ubicación especificada."
            )

    def _open_session_manager(self):
        """Abre el diálogo de gestión y carga de sesiones guardadas."""
        dlg = SessionDialog(self)
        dlg.session_loaded.connect(self._load_session_into_ui)
        dlg.new_session_requested.connect(lambda: self._start_new_session(prompt_user=True))
        dlg.exec_()

    def _start_new_session(self, prompt_user: bool = True):
        """
        Cierra el escaneo actual y limpia todos los resultados previos para comenzar desde cero.
        """
        # 1. Si hay un escaneo activo en ejecución
        if self.scan_worker and self.scan_worker.isRunning():
            if prompt_user:
                reply = QMessageBox.question(
                    self,
                    "Escaneo en Ejecución",
                    "Hay un escaneo en curso actualmente.\n\n¿Desea detenerlo y comenzar una nueva sesión limpia?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            self._cancel_scan()
            self.scan_worker.wait(2000)

        # 2. Si hay resultados en la tabla
        elif prompt_user and self.last_results:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Nueva Sesión")
            msg_box.setText(
                f"La sesión actual contiene {len(self.last_results)} archivo(s) recuperables.\n\n"
                f"¿Desea guardar estos resultados antes de iniciar la nueva sesión?"
            )
            msg_box.setIcon(QMessageBox.Question)
            btn_save = msg_box.addButton("💾 Guardar y Continuar", QMessageBox.AcceptRole)
            btn_discard = msg_box.addButton("🗑️ Descartar y Limpiar", QMessageBox.DestructiveRole)
            btn_cancel = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
            msg_box.setDefaultButton(btn_save)
            msg_box.exec_()

            clicked = msg_box.clickedButton()
            if clicked == btn_cancel:
                return
            elif clicked == btn_save:
                self._save_current_session()

        # 3. Limpieza de memoria y controles
        self.last_results = []
        self.results_table.clear()
        self.results_table._clear_filters()
        self.preview_panel.load_item(None)
        self.info_bar.reset()
        self.scan_panel.reset_session_state()
        self.btn_save_session.setEnabled(False)
        self.btn_export.setEnabled(False)

        msg = "Nueva sesión iniciada. Se han cerrado los escaneos previos y limpiado la tabla de resultados."
        self.status_bar.showMessage(msg, 5000)

    def _save_current_session(self):
        """Permite al usuario guardar manualmente los resultados actuales con un nombre personalizado."""
        if not self.last_results:
            QMessageBox.warning(self, "Sin Resultados", "No hay elementos encontrados para guardar en una sesión.")
            return

        default_name = f"Sesión {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
        name, ok = QInputDialog.getText(
            self,
            "Guardar Sesión de Exploración",
            "Ingrese un nombre para identificar esta sesión:",
            text=default_name
        )
        if ok and name.strip():
            targets = self.scan_panel.dir_selector.get_target_paths()
            cats = self.scan_panel._get_active_categories()
            filepath = SessionManager.save_session(
                name=name.strip(),
                items=self.last_results,
                targets=targets,
                categories=cats,
                mode="manual_saved"
            )
            self.scan_panel._check_matching_session()
            QMessageBox.information(
                self,
                "Sesión Guardada",
                f"La sesión '{name.strip()}' se ha guardado exitosamente.\n\n"
                f"Archivo: {os.path.basename(filepath)}"
            )

    def _load_session_into_ui(self, session_data: dict):
        """Restaura los resultados y estado de una sesión guardada previa en la interfaz."""
        items = session_data.get("items", [])
        self.last_results = items
        self.results_table.set_items(items)
        self._update_export_button_state()
        self.btn_save_session.setEnabled(len(items) > 0)

        session_name = session_data.get("name", "Sesión Guardada")
        total_size = sum(it.get("size", 0) for it in items)

        # Desglose de categorías para el HUD
        cat_counts = {}
        for it in items:
            c = it.get("category", "Otros")
            cat_counts[c] = cat_counts.get(c, 0) + 1

        self.info_bar.start(f"SESIÓN RESTAURADA: {session_name.upper()}")
        self.info_bar.update_status(
            message=f"Sesión cargada: {session_name} ({len(items)} archivos, {format_size(total_size)})",
            percentage=100,
            current_item_path=f"ID: {session_data.get('session_id', 'N/A')} | Fecha: {session_data.get('updated_at', '-')}",
            bytes_scanned=total_size,
            items_count=len(items),
            category_counts=cat_counts
        )
        self.info_bar.finish(success=True, final_msg=f"Sesión '{session_name}' restaurada ({len(items)} archivos disponibles).")
        self.status_bar.showMessage(f"Sesión '{session_name}' cargada con {len(items)} archivo(s).")
        self.scan_panel._check_matching_session()

    def _on_scan_error(self, error_msg: str):
        self.scan_panel.set_scanning_state(False)
        self.info_bar.finish(success=False, final_msg=f"Error: {error_msg}")
        self.status_bar.showMessage(f"Error durante el escaneo: {error_msg}")
        QMessageBox.critical(self, "Error de Escaneo", f"Ocurrió un error al ejecutar el escaneo:\n{error_msg}")

    def _on_item_selected(self, item: dict):
        self.preview_panel.load_item(item)

    def _update_export_button_state(self):
        selected = self.results_table.get_selected_items()
        count = len(selected)
        vis_selected = self.results_table.get_selected_items(only_visible=True)
        vis_count = len(vis_selected)

        has_filter = len(self.results_table.filtered_items) < len(self.results_table.all_items)
        if has_filter and count != vis_count:
            self.btn_export.setText(f"💾 RECUPERAR ({vis_count} visibles / {count} tot.)" if count > 0 else "💾 RECUPERAR SELECCIONADOS")
        else:
            self.btn_export.setText(f"💾 RECUPERAR ({count}) SELECCIONADOS" if count > 0 else "💾 RECUPERAR SELECCIONADOS")
        self.btn_export.setEnabled(count > 0)

    def _export_selected_files(self):
        selected_items = self.results_table.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "Sin Selección", "Marque al menos un archivo en la tabla para recuperarlo.")
            return

        # Si el usuario tiene filtros activos y hay archivos ocultos marcados en otras categorías
        vis_items = self.results_table.get_selected_items(only_visible=True)
        has_filter = len(self.results_table.filtered_items) < len(self.results_table.all_items)
        if has_filter and len(vis_items) < len(selected_items):
            total_sz = sum(it.get("size", 0) for it in selected_items)
            vis_sz = sum(it.get("size", 0) for it in vis_items)
            hidden_count = len(selected_items) - len(vis_items)
            hidden_sz = total_sz - vis_sz

            filter_prompt = (
                f"Tiene activos filtros de visualización en la tabla:\n\n"
                f"• Archivos visibles que está viendo: {len(vis_items)} ({format_size(vis_sz)})\n"
                f"• Archivos marcados de otras categorías/ocultos: {hidden_count} ({format_size(hidden_sz)})\n"
                f"• Total del lote marcado: {len(selected_items)} ({format_size(total_sz)})\n\n"
                f"¿Desea recuperar únicamente los {len(vis_items)} archivos visibles que está consultando, "
                f"o restaurar todo el lote incluyendo los {hidden_count} archivos ocultos?"
            )
            dlg_box = QMessageBox(self)
            dlg_box.setWindowTitle("Confirmación de Alcance de Recuperación")
            dlg_box.setText(filter_prompt)
            dlg_box.setIcon(QMessageBox.Question)
            btn_only_vis = dlg_box.addButton(f"✔ Solo Visibles ({format_size(vis_sz)})", QMessageBox.AcceptRole)
            btn_all_batch = dlg_box.addButton(f"Restaurar Todo el Lote ({format_size(total_sz)})", QMessageBox.ActionRole)
            btn_cancel_batch = dlg_box.addButton("Cancelar", QMessageBox.RejectRole)
            dlg_box.setDefaultButton(btn_only_vis)
            dlg_box.exec_()

            if dlg_box.clickedButton() == btn_cancel_batch:
                return
            elif dlg_box.clickedButton() == btn_only_vis:
                selected_items = vis_items
                if not selected_items:
                    QMessageBox.warning(self, "Sin Selección Visible", "No hay archivos visibles marcados para recuperar.")
                    return

        dest_dir = self.txt_dest.text().strip()
        if not dest_dir:
            self._browse_destination()
            dest_dir = self.txt_dest.text().strip()
            if not dest_dir:
                return

        # Verificación inteligente de usabilidad y calidad forense
        high_quality_items = [
            it for it in selected_items
            if it.get("is_high_quality") or it.get("usability_score", 0) >= 80 or it.get("usability_tier") == "high"
        ]
        low_quality_count = len(selected_items) - len(high_quality_items)

        if low_quality_count > 0 and len(high_quality_items) > 0:
            qual_msg = (
                f"Ha seleccionado {len(selected_items)} archivo(s) para recuperar:\n\n"
                f"• 🌟 Archivos de Alta Calidad e Íntegros: {len(high_quality_items)}\n"
                f"• ⚠️ Archivos de Baja Calidad, Truncados o Dudosos: {low_quality_count}\n\n"
                f"¿Desea restaurar ÚNICAMENTE los {len(high_quality_items)} archivos de Alta Calidad para evitar recuperar datos inservibles o dañados?"
            )
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Filtro de Usabilidad y Calidad Forense")
            msg_box.setText(qual_msg)
            msg_box.setIcon(QMessageBox.Question)
            btn_only_high = msg_box.addButton("🌟 Solo Alta Calidad", QMessageBox.AcceptRole)
            btn_all = msg_box.addButton("Restaurar Todos", QMessageBox.ActionRole)
            btn_cancel = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
            msg_box.setDefaultButton(btn_only_high)

            msg_box.exec_()
            clicked_btn = msg_box.clickedButton()
            if clicked_btn == btn_cancel:
                return
            elif clicked_btn == btn_only_high:
                selected_items = high_quality_items

        # Advertencia de seguridad: ¿Está en el mismo disco?
        first_item = selected_items[0]
        src_path = first_item.get("data_source_path") or first_item.get("original_path", "")
        if RecoveryExporter.is_same_drive(src_path, dest_dir):
            warn_reply = QMessageBox.warning(
                self,
                "⚠️ Advertencia de Seguridad de Recuperación",
                f"La carpeta de destino seleccionada se encuentra en la misma unidad ({os.path.splitdrive(dest_dir)[0]}).\n\n"
                "Guardar datos en el mismo disco de origen podría sobreescribir sectores libres donde "
                "residen otros archivos eliminados pendientes de recuperación.\n\n"
                "¿Desea continuar de todos modos con esta ubicación?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if warn_reply != QMessageBox.Yes:
                return

        preserve_names = self.chk_preserve_names.isChecked()
        restore_tree = self.chk_restore_tree.isChecked()

        # Diálogo de progreso de exportación
        progress_dlg = QProgressDialog("Exportando y verificando archivos...", "Cancelar", 0, 100, self)
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setMinimumDuration(0)
        progress_dlg.setValue(0)

        self.export_worker = ExportWorker(
            selected_items, 
            dest_dir,
            preserve_original_names=preserve_names,
            restore_folder_tree=restore_tree
        )

        def on_export_progress(msg, pct):
            progress_dlg.setLabelText(msg)
            progress_dlg.setValue(pct)

        def on_export_finished(summary: dict):
            progress_dlg.close()
            success = summary.get("success_count", 0)
            total = summary.get("total", 0)
            report_p = summary.get("report_path", "")
            folders_cnt = summary.get("folders_count", 0)

            names_info = "Activado (Nombres Originales Preservados)" if preserve_names else "Desactivado (Nombres de Escaneo)"
            tree_info = f"Reconstruido con Éxito ({folders_cnt} subcarpetas recreadas)" if restore_tree else "Modo Plano (Guardado Directo en Raíz)"

            msg = (
                f"🎉 ¡Proceso de recuperación completado con éxito!\n\n"
                f"• Archivos recuperados: {success} de {total}\n"
                f"• Nombres originales: {names_info}\n"
                f"• Estructura jerárquica: {tree_info}\n"
                f"• Carpeta de guardado: {dest_dir}\n"
                f"• Reporte de auditoría generado en: {os.path.basename(report_p)}"
            )

            reply = QMessageBox.information(
                self,
                "Recuperación Exitosa",
                msg,
                QMessageBox.Open | QMessageBox.Ok,
                QMessageBox.Open
            )

            if reply == QMessageBox.Open:
                try:
                    os.startfile(dest_dir)
                except Exception:
                    pass

        def on_export_error(err):
            progress_dlg.close()
            QMessageBox.critical(self, "Error al Exportar", f"Ocurrió un error guardando los archivos:\n{err}")

        self.export_worker.progress_changed.connect(on_export_progress)
        self.export_worker.finished_export.connect(on_export_finished)
        self.export_worker.error_occurred.connect(on_export_error)
        progress_dlg.canceled.connect(self.export_worker.terminate)

        self.export_worker.start()

    def _on_trial_expired(self):
        """Maneja el vencimiento definitivo de la versión de prueba de 24 horas."""
        if self.scan_worker and self.scan_worker.isRunning():
            try:
                self.scan_worker.cancel()
                self.scan_worker.wait(1000)
            except Exception:
                pass

        QMessageBox.critical(
            self,
            "⏰ Período de Demostración Expirado",
            "El período de evaluación de 24 horas para este equipo ha finalizado.\n\n"
            "Esta versión de prueba ha quedado permanentemente bloqueada e inutilizable.\n"
            "El archivo ejecutable procederá a autodestruirse de forma segura.\n\n"
            "Para continuar utilizando la herramienta sin limitaciones, adquiera la versión comercial completa."
        )
        from core.trial_manager import TrialManager
        TrialManager.trigger_self_destruction()
        self.close()
        sys.exit(0)

    def closeEvent(self, event):
        """Al cerrar, si la prueba expiró, asegurar autodestrucción."""
        if self.is_demo:
            from core.trial_manager import TrialManager
            status = TrialManager.check_or_init_trial()
            if status.get("is_expired"):
                TrialManager.trigger_self_destruction()
        super().closeEvent(event)
