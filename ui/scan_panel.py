"""
Panel de configuración y lanzamiento de escaneo minimalista y limpio.
Convierte las opciones principales (Protocolo de Recuperación, Tipos de Archivo y Alcance)
en controles desplegables (QComboBox) y ventanas modales emergentes (Pop-ups).
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QCheckBox, QMessageBox, QFrame,
    QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from core.disk_utils import is_admin, restart_as_admin
from ui.directory_selector import DirectorySelector
from ui.popups import (
    FileTypesDialog, 
    IMAGE_FORMAT_CATALOG, 
    DOCUMENT_FORMAT_CATALOG, 
    MEDIA_FORMAT_CATALOG, 
    COMPRESSED_FORMAT_CATALOG
)
from core.session_manager import SessionManager


class ModeRadioProxy:
    """Proxy para compatibilidad hacia atrás con código o tests que consulten rb_deep_forensic, etc."""
    def __init__(self, combo: QComboBox, mode_key: str):
        self._combo = combo
        self._mode_key = mode_key

    def isChecked(self) -> bool:
        return self._combo.currentData() == self._mode_key

    def setChecked(self, value: bool):
        if value:
            for idx in range(self._combo.count()):
                if self._combo.itemData(idx) == self._mode_key:
                    self._combo.setCurrentIndex(idx)
                    break


class ScanPanel(QWidget):
    """Panel de configuración de escaneo con diseño limpio basado en menús desplegables y ventanas flotantes."""

    start_scan_requested = pyqtSignal(str, list, list, bool, bool, list)
    # (mode, target_paths, categories, skip_software, is_incremental, selected_doc_extensions)
    cancel_scan_requested = pyqtSignal()

    PROTOCOL_DESCRIPTIONS = {
        "deep_forensic": "💡 Todo-en-Uno: Inspecciona MFT, Papelera de reciclaje, VSS, Thumbcache, Borradores de Office y Carving en una sola pasada profunda.",
        "recycle": "💡 Papelera Forense: Rastrea carpetas $Recycle.Bin y encabezados $I/$R en todas las particiones NTFS.",
        "thumbcache": "💡 Caché Gráfica: Rescata imágenes y miniaturas de alta resolución (1080p/4K) de las bases de Windows Thumbcache.",
        "temp": "💡 Borradores Office: Recupera borradores no guardados de Word (.asd), Excel (.xar), PowerPoint y temporales %TEMP%.",
        "carve": "💡 Carving por Firmas: Búsqueda a bajo nivel de cabeceras y pies de archivo (Magic Bytes) en sectores libres del disco.",
        "vss": "💡 Copias de Sombra: Monta instantáneas VSS y puntos de restauración de Windows para extraer versiones previas."
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialog_types = FileTypesDialog(self)
        self.dialog_types.categories_changed.connect(self._on_categories_changed)
        self._init_ui()

        # Proxies para compatibilidad
        self.rb_deep_forensic = ModeRadioProxy(self.combo_protocol, "deep_forensic")
        self.rb_recycle = ModeRadioProxy(self.combo_protocol, "recycle")
        self.rb_thumb = ModeRadioProxy(self.combo_protocol, "thumbcache")
        self.rb_temp = ModeRadioProxy(self.combo_protocol, "temp")
        self.rb_carve = ModeRadioProxy(self.combo_protocol, "carve")
        self.rb_vss = ModeRadioProxy(self.combo_protocol, "vss")

    @property
    def chk_docs(self):
        return self.dialog_types.chk_docs

    @property
    def chk_images(self):
        return self.dialog_types.chk_images

    @property
    def chk_media(self):
        return self.dialog_types.chk_media

    @property
    def chk_zips(self):
        return self.dialog_types.chk_zips

    @property
    def docs_subframe(self):
        return self.dialog_types.docs_subframe

    @property
    def doc_checkboxes(self):
        return self.dialog_types.doc_checkboxes

    @property
    def image_checkboxes(self):
        return self.dialog_types.image_checkboxes

    @property
    def media_checkboxes(self):
        return self.dialog_types.media_checkboxes

    @property
    def zip_checkboxes(self):
        return self.dialog_types.zip_checkboxes

    def _apply_doc_preset(self, preset: str):
        self.dialog_types._apply_doc_preset(preset)
        self._update_types_summary()

    def _apply_image_preset(self, preset: str):
        self.dialog_types._apply_image_preset(preset)
        self._update_types_summary()

    def _apply_media_preset(self, preset: str):
        self.dialog_types._apply_media_preset(preset)
        self._update_types_summary()

    def _apply_zip_preset(self, preset: str):
        self.dialog_types._apply_zip_preset(preset)
        self._update_types_summary()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #0d1117;
                width: 7px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #58a6ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        container = QWidget()
        container.setObjectName("ScanPanelContainer")
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # 1. Menú Desplegable: Protocolo de Recuperación
        group_protocol = QGroupBox("1. PROTOCOLO DE RECUPERACIÓN")
        proto_layout = QVBoxLayout(group_protocol)
        proto_layout.setContentsMargins(12, 12, 12, 10)
        proto_layout.setSpacing(6)

        self.combo_protocol = QComboBox()
        self.combo_protocol.addItem("🛡️ Protocolo Forense Profundo (Multicapa - Máxima Recuperación)", "deep_forensic")
        self.combo_protocol.addItem("🗑️ Papelera Forense ($Recycle.Bin y Huérfanos $R)", "recycle")
        self.combo_protocol.addItem("🖼️ Rescate de Fotos en Caché Gráfica (Thumbcache 1080p/4K)", "thumbcache")
        self.combo_protocol.addItem("💾 Borradores de Office y Temporales (Word .asd, Excel, %TEMP%)", "temp")
        self.combo_protocol.addItem("🔍 Escaneo de Sectores por Firmas (File Carving Estructural)", "carve")
        self.combo_protocol.addItem("🕒 Copias de Sombra de Windows (Puntos de Restauración VSS)", "vss")
        self.combo_protocol.currentIndexChanged.connect(self._on_protocol_changed)
        proto_layout.addWidget(self.combo_protocol)

        self.lbl_protocol_desc = QLabel(self.PROTOCOL_DESCRIPTIONS["deep_forensic"])
        self.lbl_protocol_desc.setWordWrap(True)
        self.lbl_protocol_desc.setStyleSheet("font-size: 11px; color: #8b949e; line-height: 1.3;")
        proto_layout.addWidget(self.lbl_protocol_desc)

        layout.addWidget(group_protocol)

        # 2. Selector Emergente: Tipos de Archivo a Recuperar
        group_types = QGroupBox("2. TIPOS DE ARCHIVO A RECUPERAR")
        types_layout = QVBoxLayout(group_types)
        types_layout.setContentsMargins(12, 12, 12, 10)
        types_layout.setSpacing(6)

        row_types = QHBoxLayout()
        row_types.setSpacing(8)

        self.lbl_types_summary = QLabel(self.dialog_types.get_summary_text())
        self.lbl_types_summary.setStyleSheet("""
            QLabel {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 5px;
                padding: 6px 10px;
                color: #7ee787;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        row_types.addWidget(self.lbl_types_summary, stretch=1)

        self.btn_configure_types = QPushButton("⚙️ Configurar Tipos y Formatos ▾")
        self.btn_configure_types.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                border: 1px solid #388bfd;
                border-radius: 5px;
                padding: 6px 12px;
                color: #58a6ff;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #ffffff;
            }
        """)
        self.btn_configure_types.clicked.connect(self._open_types_dialog)
        row_types.addWidget(self.btn_configure_types)

        types_layout.addLayout(row_types)
        layout.addWidget(group_types)

        # 3. Listado de Alcance: Carpetas y Ubicaciones para Recuperación
        group_scope = QGroupBox("3. ALCANCE: CARPETAS Y UBICACIONES PARA RECUPERACIÓN")
        scope_layout = QVBoxLayout(group_scope)
        scope_layout.setContentsMargins(12, 12, 12, 10)
        scope_layout.setSpacing(6)

        self.dir_selector = DirectorySelector(self)
        self.dir_selector.selection_changed.connect(self._check_matching_session)
        scope_layout.addWidget(self.dir_selector)

        layout.addWidget(group_scope)

        # 4. Filtro Inteligente de Exclusión de Software y Juegos
        self.chk_skip_software = QCheckBox("⚡ Filtro Inteligente: Omitir juegos y programas instalados (Ahorra tiempo)")
        self.chk_skip_software.setChecked(True)
        self.chk_skip_software.setToolTip("Escanea el Registro de Windows y bibliotecas de juegos para omitir carpetas de binarios y texturas sin tocar tus documentos.")
        self.chk_skip_software.setStyleSheet("color: #58a6ff; font-weight: bold;")
        layout.addWidget(self.chk_skip_software)

        # 5. Escaneo Incremental / Diferencial
        self.chk_incremental = QCheckBox("⚡ Escaneo Incremental: Reutilizar sesión previa y buscar solo cambios")
        self.chk_incremental.setChecked(True)
        self.chk_incremental.setToolTip("Compara tamaños y marcas de tiempo con sesiones guardadas para no re-procesar archivos ya conocidos.")
        self.chk_incremental.setStyleSheet("color: #3fb950; font-weight: bold;")
        layout.addWidget(self.chk_incremental)

        self.lbl_matched_session = QLabel("")
        self.lbl_matched_session.setStyleSheet("color: #7ee787; font-size: 11px; background-color: #0d1117; padding: 4px; border-radius: 4px; border: 1px solid #238636;")
        self.lbl_matched_session.setVisible(False)
        layout.addWidget(self.lbl_matched_session)

        # Banner de privilegios de Administrador
        if not is_admin():
            admin_banner = QHBoxLayout()
            self.lbl_admin = QLabel("Modo Estándar.")
            self.lbl_admin.setStyleSheet("color: #e3b341;")
            admin_banner.addWidget(self.lbl_admin)

            self.btn_admin = QPushButton("🛡️ Ejecutar como Administrador")
            self.btn_admin.setObjectName("AdminButton")
            self.btn_admin.setToolTip("Reinicia el programa solicitando permisos UAC para acceder a VSS y sectores protegidos.")
            self.btn_admin.clicked.connect(self._request_admin_restart)
            admin_banner.addWidget(self.btn_admin)
            layout.addLayout(admin_banner)

        # Botones de Acción
        actions_row = QHBoxLayout()
        self.btn_start = QPushButton("🚀 INICIAR ESCANEO PROFUNDO")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_start.clicked.connect(self._on_start_clicked)
        actions_row.addWidget(self.btn_start, stretch=3)

        self.btn_cancel = QPushButton("⏹ Cancelar")
        self.btn_cancel.setObjectName("DangerButton")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        actions_row.addWidget(self.btn_cancel, stretch=1)

        layout.addLayout(actions_row)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Actualizar recomendaciones iniciales
        self._on_categories_changed()

    def _open_types_dialog(self):
        """Abre la ventana modal para configurar categorías y formatos específicos."""
        if self.dialog_types.exec_() == FileTypesDialog.Accepted:
            self._update_types_summary()
            self._on_categories_changed()

    def _update_types_summary(self):
        self.lbl_types_summary.setText(self.dialog_types.get_summary_text())

    def _on_protocol_changed(self):
        mode = self.combo_protocol.currentData()
        desc = self.PROTOCOL_DESCRIPTIONS.get(mode, "")
        self.lbl_protocol_desc.setText(desc)

        if mode == "vss" and not is_admin():
            QMessageBox.information(
                self,
                "Permisos de Administrador Requeridos",
                "El Servicio de Instantáneas de Volumen (VSS) de Windows requiere permisos de Administrador.\n\n"
                "Haga clic en el botón 'Ejecutar como Administrador' para habilitar esta función."
            )

    def _on_categories_changed(self):
        cats = self._get_active_categories()
        self._update_types_summary()
        self.dir_selector.update_categories(cats)
        self._check_matching_session()

    def _check_matching_session(self):
        """Verifica si ya existe una sesión guardada previa para los destinos seleccionados."""
        targets = self.dir_selector.get_target_paths()
        cats = self._get_active_categories()
        matched = SessionManager.find_matching_session(targets, cats)
        if matched:
            self.lbl_matched_session.setText(
                f"📌 Sesión previa detectada: '{matched['name']}' ({matched.get('total_items', 0)} archivos). Modo incremental activo."
            )
            self.lbl_matched_session.setVisible(True)
        else:
            self.lbl_matched_session.setVisible(False)

    def _get_active_categories(self) -> list:
        """Devuelve las categorías principales seleccionadas en el diálogo emergente."""
        return self.dialog_types.get_selected_categories()

    def get_selected_doc_extensions(self) -> list:
        """Devuelve las extensiones de documentos seleccionadas."""
        return self.dialog_types.get_selected_doc_extensions()

    def get_selected_image_extensions(self) -> list:
        """Devuelve las extensiones de imágenes seleccionadas."""
        return self.dialog_types.get_selected_image_extensions()

    def get_selected_media_extensions(self) -> list:
        """Devuelve las extensiones de audio y video seleccionadas."""
        return self.dialog_types.get_selected_media_extensions()

    def get_selected_zip_extensions(self) -> list:
        """Devuelve las extensiones de comprimidos seleccionadas."""
        return self.dialog_types.get_selected_zip_extensions()

    def get_all_selected_extensions(self) -> list:
        """Devuelve el conjunto unificado de todas las extensiones seleccionadas de categorías activas."""
        return self.dialog_types.get_all_selected_extensions()

    def _on_start_clicked(self):
        target_paths = self.dir_selector.get_target_paths()
        cats = self._get_active_categories()
        doc_exts = self.get_selected_doc_extensions()
        mode = self.combo_protocol.currentData()

        if mode == "carve" and not target_paths:
            QMessageBox.warning(
                self,
                "Selección Requerida",
                "Para el escaneo de firmas seleccione al menos una carpeta o unidad."
            )
            return

        skip_software = self.chk_skip_software.isChecked()
        is_incremental = self.chk_incremental.isChecked()
        self.set_scanning_state(True)
        self.start_scan_requested.emit(mode, target_paths, cats, skip_software, is_incremental, doc_exts)

    def _on_cancel_clicked(self):
        self.btn_cancel.setEnabled(False)
        self.cancel_scan_requested.emit()

    def set_scanning_state(self, scanning: bool):
        """Alterna el estado de la UI durante el escaneo."""
        self.btn_start.setEnabled(not scanning)
        self.btn_cancel.setEnabled(scanning)

    def reset_session_state(self):
        """Restablece los controles del panel de escaneo al estado inicial limpio."""
        self.set_scanning_state(False)
        self.lbl_matched_session.setVisible(False)
        self.lbl_matched_session.setText("")
        self.combo_protocol.setCurrentIndex(0)
        self.dir_selector.select_recommended_only()

    def _request_admin_restart(self):
        reply = QMessageBox.question(
            self,
            "Reiniciar con Permisos Elevados",
            "¿Desea reiniciar la aplicación solicitando permisos de Administrador de Windows (UAC)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            restart_as_admin()
