"""
Diálogos y componentes emergentes (Pop-ups) para una interfaz limpia y minimalista.
Provee:
- FileTypesDialog: Selector modal con catálogos exhaustivos de extensiones para TODAS las categorías
  (Imágenes, Documentos, Audio/Video y Comprimidos), con presets de 1 clic y buscadores individuales.
- FolderChecklistDialog: Selector modal con checklist de carpetas sugeridas, buscador y adición de carpetas personalizadas.
"""

import os
from typing import List, Set, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QScrollArea, QFrame, QGridLayout,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFileDialog, QMessageBox, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.theme import DARK_THEME_QSS
from core.context_router import ContextRouter

# ==============================================================================
# 1. CATÁLOGO DE IMÁGENES (16 Formatos)
# ==============================================================================
IMAGE_FORMAT_CATALOG = [
    # Fotografía y Cámaras Digitales (RAW)
    {"ext": ".jpg", "name": ".JPG", "desc": "JPEG Estándar", "icon": "🖼️", "sub": "photo"},
    {"ext": ".jpeg", "name": ".JPEG", "desc": "JPEG Fotografía HD", "icon": "🖼️", "sub": "photo"},
    {"ext": ".raw", "name": ".RAW", "desc": "Foto Digital RAW en Crudo", "icon": "📸", "sub": "photo"},
    {"ext": ".cr2", "name": ".CR2", "desc": "Canon Digital RAW", "icon": "📸", "sub": "photo"},
    {"ext": ".nef", "name": ".NEF", "desc": "Nikon Digital RAW", "icon": "📸", "sub": "photo"},
    {"ext": ".arw", "name": ".ARW", "desc": "Sony Digital RAW", "icon": "📸", "sub": "photo"},
    {"ext": ".heic", "name": ".HEIC", "desc": "High Efficiency Image (Apple)", "icon": "📱", "sub": "photo"},

    # Web y Gráficos
    {"ext": ".png", "name": ".PNG", "desc": "Portable Network Graphics", "icon": "🖼️", "sub": "web"},
    {"ext": ".webp", "name": ".WEBP", "desc": "WebP Imagen Google", "icon": "🌐", "sub": "web"},
    {"ext": ".gif", "name": ".GIF", "desc": "Gráficos Animados GIF", "icon": "🎞️", "sub": "web"},
    {"ext": ".svg", "name": ".SVG", "desc": "Gráfico Vectorial SVG", "icon": "📐", "sub": "web"},
    {"ext": ".ico", "name": ".ICO", "desc": "Icono de Sistema", "icon": "⭐", "sub": "web"},

    # Diseño y Formatos Profesionales
    {"ext": ".psd", "name": ".PSD", "desc": "Adobe Photoshop", "icon": "🎨", "sub": "design"},
    {"ext": ".bmp", "name": ".BMP", "desc": "Mapa de Bits Windows", "icon": "🎨", "sub": "design"},
    {"ext": ".tiff", "name": ".TIFF", "desc": "Tag Image File Format", "icon": "🖨️", "sub": "design"},
    {"ext": ".tif", "name": ".TIF", "desc": "Imagen TIFF Clásica", "icon": "🖨️", "sub": "design"}
]

# ==============================================================================
# 2. CATÁLOGO DE DOCUMENTOS (40 Formatos)
# ==============================================================================
DOCUMENT_FORMAT_CATALOG = [
    # Microsoft Word & Texto Enriquecido
    {"ext": ".docx", "name": ".DOCX", "desc": "Word OpenXML", "icon": "📘", "suite": "office"},
    {"ext": ".doc", "name": ".DOC", "desc": "Word 97-2003", "icon": "📘", "suite": "office"},
    {"ext": ".docm", "name": ".DOCM", "desc": "Word con Macros", "icon": "📘", "suite": "office"},
    {"ext": ".dotx", "name": ".DOTX", "desc": "Plantilla Word", "icon": "📘", "suite": "office"},
    {"ext": ".dot", "name": ".DOT", "desc": "Plantilla Word Clásica", "icon": "📘", "suite": "office"},
    {"ext": ".rtf", "name": ".RTF", "desc": "Texto Enriquecido", "icon": "📝", "suite": "office"},
    {"ext": ".asd", "name": ".ASD", "desc": "AutoRecuperación Word", "icon": "💾", "suite": "office"},
    {"ext": ".wbk", "name": ".WBK", "desc": "Respaldo Word", "icon": "💾", "suite": "office"},

    # Microsoft Excel & Tablas
    {"ext": ".xlsx", "name": ".XLSX", "desc": "Excel OpenXML", "icon": "📊", "suite": "office"},
    {"ext": ".xls", "name": ".XLS", "desc": "Excel 97-2003", "icon": "📊", "suite": "office"},
    {"ext": ".xlsm", "name": ".XLSM", "desc": "Excel con Macros", "icon": "📊", "suite": "office"},
    {"ext": ".xlsb", "name": ".XLSB", "desc": "Excel Binario", "icon": "📊", "suite": "office"},
    {"ext": ".xltx", "name": ".XLTX", "desc": "Plantilla Excel", "icon": "📊", "suite": "office"},
    {"ext": ".csv", "name": ".CSV", "desc": "Valores por Comas", "icon": "📊", "suite": "text"},
    {"ext": ".tsv", "name": ".TSV", "desc": "Valores Tabulados", "icon": "📊", "suite": "text"},
    {"ext": ".xar", "name": ".XAR", "desc": "AutoRecuperación Excel", "icon": "💾", "suite": "office"},

    # Microsoft PowerPoint
    {"ext": ".pptx", "name": ".PPTX", "desc": "PowerPoint OpenXML", "icon": "📽️", "suite": "office"},
    {"ext": ".ppt", "name": ".PPT", "desc": "PowerPoint 97-2003", "icon": "📽️", "suite": "office"},
    {"ext": ".pptm", "name": ".PPTM", "desc": "PowerPoint con Macros", "icon": "📽️", "suite": "office"},
    {"ext": ".ppsx", "name": ".PPSX", "desc": "Presentación Directa", "icon": "📽️", "suite": "office"},
    {"ext": ".pps", "name": ".PPS", "desc": "Diapositivas 97-2003", "icon": "📽️", "suite": "office"},

    # Adobe PDF & Publicaciones Digitales
    {"ext": ".pdf", "name": ".PDF", "desc": "Adobe Acrobat PDF", "icon": "📕", "suite": "pdf"},
    {"ext": ".epub", "name": ".EPUB", "desc": "Libro Electrónico EPUB", "icon": "📚", "suite": "pdf"},
    {"ext": ".mobi", "name": ".MOBI", "desc": "Libro Mobipocket", "icon": "📚", "suite": "pdf"},
    {"ext": ".xps", "name": ".XPS", "desc": "XML Paper Spec", "icon": "📑", "suite": "pdf"},

    # LibreOffice / OpenOffice
    {"ext": ".odt", "name": ".ODT", "desc": "Writer Documento", "icon": "📑", "suite": "odf"},
    {"ext": ".ods", "name": ".ODS", "desc": "Calc Hoja Cálculo", "icon": "📑", "suite": "odf"},
    {"ext": ".odp", "name": ".ODP", "desc": "Impress Diapositivas", "icon": "📑", "suite": "odf"},
    {"ext": ".odg", "name": ".ODG", "desc": "Draw Dibujo Gráfico", "icon": "📑", "suite": "odf"},

    # Texto Plano & Formatos Web
    {"ext": ".txt", "name": ".TXT", "desc": "Texto Plano", "icon": "📄", "suite": "text"},
    {"ext": ".md", "name": ".MD", "desc": "Markdown Texto", "icon": "📄", "suite": "text"},
    {"ext": ".log", "name": ".LOG", "desc": "Registro de Texto", "icon": "📄", "suite": "text"},
    {"ext": ".xml", "name": ".XML", "desc": "Datos XML", "icon": "🌐", "suite": "text"},
    {"ext": ".html", "name": ".HTML", "desc": "Documento HTML", "icon": "🌐", "suite": "text"},
    {"ext": ".htm", "name": ".HTM", "desc": "Página Web HTM", "icon": "🌐", "suite": "text"},

    # Herramientas de Oficina & Bases
    {"ext": ".msg", "name": ".MSG", "desc": "Mensaje Outlook", "icon": "✉️", "suite": "office"},
    {"ext": ".pub", "name": ".PUB", "desc": "Microsoft Publisher", "icon": "📰", "suite": "office"},
    {"ext": ".one", "name": ".ONE", "desc": "Notas OneNote", "icon": "📓", "suite": "office"},
    {"ext": ".accdb", "name": ".ACCDB", "desc": "Base Datos Access", "icon": "🗄️", "suite": "office"},
    {"ext": ".mdb", "name": ".MDB", "desc": "Access 97-2003", "icon": "🗄️", "suite": "office"}
]

# ==============================================================================
# 3. CATÁLOGO DE AUDIO Y VIDEO (18 Formatos)
# ==============================================================================
MEDIA_FORMAT_CATALOG = [
    # Video
    {"ext": ".mp4", "name": ".MP4", "desc": "Video MPEG-4 HD/4K", "icon": "🎬", "sub": "video"},
    {"ext": ".mkv", "name": ".MKV", "desc": "Matroska Video HD/4K", "icon": "🎬", "sub": "video"},
    {"ext": ".mov", "name": ".MOV", "desc": "Apple QuickTime Video", "icon": "🍏", "sub": "video"},
    {"ext": ".avi", "name": ".AVI", "desc": "Audio Video Interleave", "icon": "📽️", "sub": "video"},
    {"ext": ".wmv", "name": ".WMV", "desc": "Windows Media Video", "icon": "🪟", "sub": "video"},
    {"ext": ".webm", "name": ".WEBM", "desc": "WebM Video HTML5", "icon": "🌐", "sub": "video"},
    {"ext": ".flv", "name": ".FLV", "desc": "Flash Video", "icon": "⚡", "sub": "video"},
    {"ext": ".m4v", "name": ".M4V", "desc": "Apple iTunes Video", "icon": "📱", "sub": "video"},
    {"ext": ".3gp", "name": ".3GP", "desc": "Video Móvil 3GPP", "icon": "📞", "sub": "video"},
    {"ext": ".ts", "name": ".TS", "desc": "Transport Stream HD", "icon": "📡", "sub": "video"},

    # Audio
    {"ext": ".mp3", "name": ".MP3", "desc": "Audio Comprimido MP3", "icon": "🎵", "sub": "audio"},
    {"ext": ".wav", "name": ".WAV", "desc": "Audio PCM Sin Pérdidas", "icon": "🔊", "sub": "audio"},
    {"ext": ".flac", "name": ".FLAC", "desc": "Free Lossless Audio Codec", "icon": "🎧", "sub": "audio"},
    {"ext": ".aac", "name": ".AAC", "desc": "Advanced Audio Coding", "icon": "🎵", "sub": "audio"},
    {"ext": ".m4a", "name": ".M4A", "desc": "Apple MPEG-4 Audio", "icon": "🍏", "sub": "audio"},
    {"ext": ".ogg", "name": ".OGG", "desc": "Ogg Vorbis Audio", "icon": "🎵", "sub": "audio"},
    {"ext": ".wma", "name": ".WMA", "desc": "Windows Media Audio", "icon": "🪟", "sub": "audio"},
    {"ext": ".mid", "name": ".MID", "desc": "Música MIDI", "icon": "🎹", "sub": "audio"}
]

# ==============================================================================
# 4. CATÁLOGO DE COMPRIMIDOS (8 Formatos)
# ==============================================================================
COMPRESSED_FORMAT_CATALOG = [
    {"ext": ".zip", "name": ".ZIP", "desc": "Archivo Comprimido ZIP", "icon": "📦", "sub": "archive"},
    {"ext": ".rar", "name": ".RAR", "desc": "Archivo WinRAR", "icon": "📦", "sub": "archive"},
    {"ext": ".7z", "name": ".7Z", "desc": "Archivo 7-Zip LZMA", "icon": "📦", "sub": "archive"},
    {"ext": ".iso", "name": ".ISO", "desc": "Imagen de Disco Óptico", "icon": "💿", "sub": "iso"},
    {"ext": ".tar", "name": ".TAR", "desc": "Empaquetado Unix TAR", "icon": "🐧", "sub": "tar"},
    {"ext": ".gz", "name": ".GZ", "desc": "Comprimido GZip", "icon": "🐧", "sub": "tar"},
    {"ext": ".bz2", "name": ".BZ2", "desc": "Comprimido BZip2", "icon": "🐧", "sub": "tar"},
    {"ext": ".xz", "name": ".XZ", "desc": "Comprimido XZ", "icon": "🐧", "sub": "tar"}
]


class _DocsSubframeProxy:
    """Proxy para mantener compatibilidad hacia atrás con tests que consultan isHidden() de docs_subframe."""
    def __init__(self, tab_docs, chk_docs):
        self._tab_docs = tab_docs
        self._chk_docs = chk_docs

    def isHidden(self) -> bool:
        return not self._chk_docs.isChecked()

    def isVisible(self) -> bool:
        return self._chk_docs.isChecked()

    def setVisible(self, visible: bool):
        self._chk_docs.setChecked(visible)

    def __getattr__(self, name):
        return getattr(self._tab_docs, name)


class FileTypesDialog(QDialog):
    """Diálogo emergente modal para selección exhaustiva de extensiones y formatos de archivo."""

    categories_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏷️ Tipos de Archivo y Formatos a Recuperar")
        self.setMinimumSize(700, 560)
        self.setStyleSheet(DARK_THEME_QSS)

        # Diccionarios de checkboxes por formato
        self.image_checkboxes: Dict[str, QCheckBox] = {}
        self.doc_checkboxes: Dict[str, QCheckBox] = {}
        self.media_checkboxes: Dict[str, QCheckBox] = {}
        self.zip_checkboxes: Dict[str, QCheckBox] = {}

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Encabezado
        lbl_title = QLabel("🏷️ Configuración de Tipos de Archivo y Formatos")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #58a6ff;")
        main_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Seleccione las categorías principales y afine los formatos exactos de cada tipo. "
            "Al hacer clic en cualquier categoría podrá personalizar sus extensiones con presets rápidos."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        main_layout.addWidget(lbl_desc)

        # 1. Selector Superior de Categorías Principales
        card_cats = QFrame()
        card_cats.setObjectName("Card")
        layout_cats = QVBoxLayout(card_cats)
        layout_cats.setContentsMargins(10, 8, 10, 8)
        layout_cats.setSpacing(6)

        lbl_cats_header = QLabel("CATEGORÍAS ACTIVAS (Haga clic en una categoría para configurar sus extensiones):")
        lbl_cats_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #7ee787;")
        layout_cats.addWidget(lbl_cats_header)

        cats_row = QHBoxLayout()
        cats_row.setSpacing(12)

        self.chk_images = QCheckBox("🖼️ Imágenes")
        self.chk_images.setChecked(True)
        self.chk_images.stateChanged.connect(lambda: self._on_master_cat_toggled(0, self.chk_images.isChecked()))
        cats_row.addWidget(self.chk_images)

        self.chk_docs = QCheckBox("📄 Documentos")
        self.chk_docs.setChecked(True)
        self.chk_docs.stateChanged.connect(lambda: self._on_master_cat_toggled(1, self.chk_docs.isChecked()))
        cats_row.addWidget(self.chk_docs)

        self.chk_media = QCheckBox("🎵 Audio / Video")
        self.chk_media.setChecked(True)
        self.chk_media.stateChanged.connect(lambda: self._on_master_cat_toggled(2, self.chk_media.isChecked()))
        cats_row.addWidget(self.chk_media)

        self.chk_zips = QCheckBox("📦 Comprimidos")
        self.chk_zips.setChecked(True)
        self.chk_zips.stateChanged.connect(lambda: self._on_master_cat_toggled(3, self.chk_zips.isChecked()))
        cats_row.addWidget(self.chk_zips)

        layout_cats.addLayout(cats_row)
        main_layout.addWidget(card_cats)

        # 2. Pestañas de Formatos Específicos para CADA Categoría
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                border-radius: 6px;
                background-color: #161b22;
                padding: 6px;
            }
            QTabBar::tab {
                background-color: #0d1117;
                color: #8b949e;
                padding: 7px 16px;
                margin-right: 4px;
                border: 1px solid #30363d;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #161b22;
                color: #58a6ff;
                border-bottom: 2px solid #58a6ff;
            }
            QTabBar::tab:hover {
                color: #ffffff;
            }
        """)

        # Pestaña 0: Imágenes
        self.tab_images = self._create_image_tab()
        self.tab_widget.addTab(self.tab_images, "🖼️ Imágenes")

        # Pestaña 1: Documentos
        self.tab_docs = self._create_docs_tab()
        self.tab_widget.addTab(self.tab_docs, "📄 Documentos")

        # Pestaña 2: Audio / Video
        self.tab_media = self._create_media_tab()
        self.tab_widget.addTab(self.tab_media, "🎵 Audio / Video")

        # Pestaña 3: Comprimidos
        self.tab_zips = self._create_zips_tab()
        self.tab_widget.addTab(self.tab_zips, "📦 Comprimidos")

        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tab_widget, stretch=1)

        # 3. Barra Inferior con Resumen y Botones
        footer_row = QHBoxLayout()
        footer_row.setSpacing(10)

        self.lbl_footer_count = QLabel("")
        self.lbl_footer_count.setStyleSheet("font-size: 11px; color: #7ee787; font-weight: bold;")
        footer_row.addWidget(self.lbl_footer_count)
        footer_row.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        footer_row.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("✔ Aplicar Selección")
        self.btn_apply.setObjectName("PrimaryButton")
        self.btn_apply.clicked.connect(self.accept)
        footer_row.addWidget(self.btn_apply)

        main_layout.addLayout(footer_row)

        self._update_all_counters()

    # Compatibilidad con propiedad docs_subframe en FileTypesDialog
    @property
    def docs_subframe(self):
        return _DocsSubframeProxy(self.tab_docs, self.chk_docs)

    # ==========================================================================
    # CREADORES DE PESTAÑAS
    # ==========================================================================
    def _create_image_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        lbl = QLabel("🖼️ FORMATOS DE IMAGEN Y FOTOGRAFÍA:")
        lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #58a6ff;")
        header.addWidget(lbl)
        header.addStretch()

        self.lbl_images_count = QLabel("")
        self.lbl_images_count.setStyleSheet("font-size: 11px; color: #7ee787; font-weight: bold;")
        header.addWidget(self.lbl_images_count)
        layout.addLayout(header)

        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)
        btn_preset_style = "font-size: 11px; padding: 4px 8px; border-radius: 4px; background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9;"

        btn_all = QPushButton("✔ Todas")
        btn_all.setStyleSheet(btn_preset_style)
        btn_all.clicked.connect(lambda: self._apply_image_preset("all"))
        presets_layout.addWidget(btn_all)

        btn_photos = QPushButton("📸 Solo Fotos (JPG/RAW)")
        btn_photos.setStyleSheet(btn_preset_style)
        btn_photos.setToolTip("JPG, JPEG, RAW, CR2, NEF, ARW, HEIC")
        btn_photos.clicked.connect(lambda: self._apply_image_preset("photo"))
        presets_layout.addWidget(btn_photos)

        btn_web = QPushButton("🌐 Solo Web (PNG/WEBP/GIF)")
        btn_web.setStyleSheet(btn_preset_style)
        btn_web.setToolTip("PNG, WEBP, GIF, SVG, ICO")
        btn_web.clicked.connect(lambda: self._apply_image_preset("web"))
        presets_layout.addWidget(btn_web)

        btn_design = QPushButton("🎨 Solo Diseño (PSD/TIFF)")
        btn_design.setStyleSheet(btn_preset_style)
        btn_design.setToolTip("PSD, BMP, TIFF, TIF")
        btn_design.clicked.connect(lambda: self._apply_image_preset("design"))
        presets_layout.addWidget(btn_design)

        btn_none = QPushButton("✖ Ninguna")
        btn_none.setStyleSheet(btn_preset_style)
        btn_none.clicked.connect(lambda: self._apply_image_preset("none"))
        presets_layout.addWidget(btn_none)

        layout.addLayout(presets_layout)

        # Buscador
        filter_row = QHBoxLayout()
        lbl_f = QLabel("🔍 Buscar formato:")
        lbl_f.setStyleSheet("font-size: 11px; color: #8b949e;")
        filter_row.addWidget(lbl_f)
        self.txt_filter_img = QLineEdit()
        self.txt_filter_img.setPlaceholderText("Filtrar (ej: jpg, png, raw, psd)...")
        self.txt_filter_img.setStyleSheet("padding: 3px 8px; font-size: 11px; background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px;")
        self.txt_filter_img.textChanged.connect(lambda t: self._filter_catalog(self.image_checkboxes, t))
        filter_row.addWidget(self.txt_filter_img)
        layout.addLayout(filter_row)

        # Grid
        layout.addWidget(self._build_grid_scroll(IMAGE_FORMAT_CATALOG, self.image_checkboxes, self._on_image_checkbox_changed))
        return widget

    def _create_docs_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        lbl = QLabel("📄 FORMATOS DE DOCUMENTOS Y OFIMÁTICA:")
        lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #58a6ff;")
        header.addWidget(lbl)
        header.addStretch()

        self.lbl_docs_count = QLabel("")
        self.lbl_docs_count.setStyleSheet("font-size: 11px; color: #7ee787; font-weight: bold;")
        header.addWidget(self.lbl_docs_count)
        layout.addLayout(header)

        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)
        btn_preset_style = "font-size: 11px; padding: 4px 8px; border-radius: 4px; background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9;"

        self.btn_preset_all = QPushButton("✔ Todos")
        self.btn_preset_all.setStyleSheet(btn_preset_style)
        self.btn_preset_all.clicked.connect(lambda: self._apply_doc_preset("all"))
        presets_layout.addWidget(self.btn_preset_all)

        self.btn_preset_office = QPushButton("📘 Solo Office")
        self.btn_preset_office.setStyleSheet(btn_preset_style)
        self.btn_preset_office.setToolTip("Word, Excel, PowerPoint, OneNote, Access y Publisher")
        self.btn_preset_office.clicked.connect(lambda: self._apply_doc_preset("office"))
        presets_layout.addWidget(self.btn_preset_office)

        self.btn_preset_pdf = QPushButton("📕 Solo PDF")
        self.btn_preset_pdf.setStyleSheet(btn_preset_style)
        self.btn_preset_pdf.setToolTip("PDF, EPUB, MOBI y XPS")
        self.btn_preset_pdf.clicked.connect(lambda: self._apply_doc_preset("pdf"))
        presets_layout.addWidget(self.btn_preset_pdf)

        self.btn_preset_text = QPushButton("📄 Solo Texto")
        self.btn_preset_text.setStyleSheet(btn_preset_style)
        self.btn_preset_text.setToolTip("TXT, MD, LOG, CSV, TSV, XML y HTML")
        self.btn_preset_text.clicked.connect(lambda: self._apply_doc_preset("text"))
        presets_layout.addWidget(self.btn_preset_text)

        self.btn_preset_odf = QPushButton("📑 Solo LibreOffice")
        self.btn_preset_odf.setStyleSheet(btn_preset_style)
        self.btn_preset_odf.setToolTip("ODT, ODS, ODP y ODG (OpenDocument)")
        self.btn_preset_odf.clicked.connect(lambda: self._apply_doc_preset("odf"))
        presets_layout.addWidget(self.btn_preset_odf)

        self.btn_preset_none = QPushButton("✖ Ninguno")
        self.btn_preset_none.setStyleSheet(btn_preset_style)
        self.btn_preset_none.clicked.connect(lambda: self._apply_doc_preset("none"))
        presets_layout.addWidget(self.btn_preset_none)

        layout.addLayout(presets_layout)

        # Buscador
        filter_row = QHBoxLayout()
        lbl_f = QLabel("🔍 Buscar formato:")
        lbl_f.setStyleSheet("font-size: 11px; color: #8b949e;")
        filter_row.addWidget(lbl_f)
        self.txt_filter_doc = QLineEdit()
        self.txt_filter_doc.setPlaceholderText("Filtrar (ej: docx, excel, pdf, odt)...")
        self.txt_filter_doc.setStyleSheet("padding: 3px 8px; font-size: 11px; background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px;")
        self.txt_filter_doc.textChanged.connect(lambda t: self._filter_catalog(self.doc_checkboxes, t))
        filter_row.addWidget(self.txt_filter_doc)
        layout.addLayout(filter_row)

        # Grid
        layout.addWidget(self._build_grid_scroll(DOCUMENT_FORMAT_CATALOG, self.doc_checkboxes, self._on_doc_checkbox_changed))
        return widget

    def _create_media_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        lbl = QLabel("🎵 FORMATOS DE AUDIO Y VIDEO:")
        lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #58a6ff;")
        header.addWidget(lbl)
        header.addStretch()

        self.lbl_media_count = QLabel("")
        self.lbl_media_count.setStyleSheet("font-size: 11px; color: #7ee787; font-weight: bold;")
        header.addWidget(self.lbl_media_count)
        layout.addLayout(header)

        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)
        btn_preset_style = "font-size: 11px; padding: 4px 8px; border-radius: 4px; background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9;"

        btn_all = QPushButton("✔ Todos")
        btn_all.setStyleSheet(btn_preset_style)
        btn_all.clicked.connect(lambda: self._apply_media_preset("all"))
        presets_layout.addWidget(btn_all)

        btn_video = QPushButton("🎬 Solo Video")
        btn_video.setStyleSheet(btn_preset_style)
        btn_video.setToolTip("MP4, MKV, MOV, AVI, WMV, WEBM, FLV, M4V, 3GP, TS")
        btn_video.clicked.connect(lambda: self._apply_media_preset("video"))
        presets_layout.addWidget(btn_video)

        btn_audio = QPushButton("🎵 Solo Audio")
        btn_audio.setStyleSheet(btn_preset_style)
        btn_audio.setToolTip("MP3, WAV, FLAC, AAC, M4A, OGG, WMA, MID")
        btn_audio.clicked.connect(lambda: self._apply_media_preset("audio"))
        presets_layout.addWidget(btn_audio)

        btn_hd = QPushButton("⚡ Video HD/4K")
        btn_hd.setStyleSheet(btn_preset_style)
        btn_hd.setToolTip("MP4, MKV, MOV")
        btn_hd.clicked.connect(lambda: self._apply_media_preset("hd"))
        presets_layout.addWidget(btn_hd)

        btn_lossless = QPushButton("🎧 Audio Lossless")
        btn_lossless.setStyleSheet(btn_preset_style)
        btn_lossless.setToolTip("FLAC, WAV")
        btn_lossless.clicked.connect(lambda: self._apply_media_preset("lossless"))
        presets_layout.addWidget(btn_lossless)

        btn_none = QPushButton("✖ Ninguno")
        btn_none.setStyleSheet(btn_preset_style)
        btn_none.clicked.connect(lambda: self._apply_media_preset("none"))
        presets_layout.addWidget(btn_none)

        layout.addLayout(presets_layout)

        # Buscador
        filter_row = QHBoxLayout()
        lbl_f = QLabel("🔍 Buscar formato:")
        lbl_f.setStyleSheet("font-size: 11px; color: #8b949e;")
        filter_row.addWidget(lbl_f)
        self.txt_filter_media = QLineEdit()
        self.txt_filter_media.setPlaceholderText("Filtrar (ej: mp4, mkv, mp3, flac)...")
        self.txt_filter_media.setStyleSheet("padding: 3px 8px; font-size: 11px; background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px;")
        self.txt_filter_media.textChanged.connect(lambda t: self._filter_catalog(self.media_checkboxes, t))
        filter_row.addWidget(self.txt_filter_media)
        layout.addLayout(filter_row)

        # Grid
        layout.addWidget(self._build_grid_scroll(MEDIA_FORMAT_CATALOG, self.media_checkboxes, self._on_media_checkbox_changed))
        return widget

    def _create_zips_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        lbl = QLabel("📦 FORMATOS COMPRIMIDOS Y ARCHIVOS:")
        lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #58a6ff;")
        header.addWidget(lbl)
        header.addStretch()

        self.lbl_zips_count = QLabel("")
        self.lbl_zips_count.setStyleSheet("font-size: 11px; color: #7ee787; font-weight: bold;")
        header.addWidget(self.lbl_zips_count)
        layout.addLayout(header)

        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)
        btn_preset_style = "font-size: 11px; padding: 4px 8px; border-radius: 4px; background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9;"

        btn_all = QPushButton("✔ Todos")
        btn_all.setStyleSheet(btn_preset_style)
        btn_all.clicked.connect(lambda: self._apply_zip_preset("all"))
        presets_layout.addWidget(btn_all)

        btn_std = QPushButton("📦 Solo ZIP / 7Z / RAR")
        btn_std.setStyleSheet(btn_preset_style)
        btn_std.setToolTip("ZIP, 7Z, RAR")
        btn_std.clicked.connect(lambda: self._apply_zip_preset("standard"))
        presets_layout.addWidget(btn_std)

        btn_iso = QPushButton("💿 Solo Disco ISO")
        btn_iso.setStyleSheet(btn_preset_style)
        btn_iso.setToolTip("ISO")
        btn_iso.clicked.connect(lambda: self._apply_zip_preset("iso"))
        presets_layout.addWidget(btn_iso)

        btn_tar = QPushButton("🐧 Solo Linux / TAR")
        btn_tar.setStyleSheet(btn_preset_style)
        btn_tar.setToolTip("TAR, GZ, BZ2, XZ")
        btn_tar.clicked.connect(lambda: self._apply_zip_preset("tar"))
        presets_layout.addWidget(btn_tar)

        btn_none = QPushButton("✖ Ninguno")
        btn_none.setStyleSheet(btn_preset_style)
        btn_none.clicked.connect(lambda: self._apply_zip_preset("none"))
        presets_layout.addWidget(btn_none)

        layout.addLayout(presets_layout)

        # Buscador
        filter_row = QHBoxLayout()
        lbl_f = QLabel("🔍 Buscar formato:")
        lbl_f.setStyleSheet("font-size: 11px; color: #8b949e;")
        filter_row.addWidget(lbl_f)
        self.txt_filter_zip = QLineEdit()
        self.txt_filter_zip.setPlaceholderText("Filtrar (ej: zip, rar, 7z, iso)...")
        self.txt_filter_zip.setStyleSheet("padding: 3px 8px; font-size: 11px; background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px;")
        self.txt_filter_zip.textChanged.connect(lambda t: self._filter_catalog(self.zip_checkboxes, t))
        filter_row.addWidget(self.txt_filter_zip)
        layout.addLayout(filter_row)

        # Grid
        layout.addWidget(self._build_grid_scroll(COMPRESSED_FORMAT_CATALOG, self.zip_checkboxes, self._on_zip_checkbox_changed))
        return widget

    def _build_grid_scroll(self, catalog: List[Dict[str, Any]], storage_dict: Dict[str, QCheckBox], callback) -> QScrollArea:
        """Construye un área de scroll con cuadrícula de 4 columnas para un catálogo de formatos."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #21262d; background-color: #0d1117; border-radius: 6px; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        grid = QGridLayout(scroll_content)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setSpacing(6)

        cols = 4
        for idx, fmt in enumerate(catalog):
            chk = QCheckBox(f"{fmt['icon']} {fmt['name']}")
            chk.setToolTip(f"{fmt['name']} ({fmt['desc']})")
            chk.setChecked(True)
            chk.setStyleSheet("font-size: 11px; color: #c9d1d9;")
            chk.stateChanged.connect(callback)
            chk.setProperty("format_info", fmt)
            storage_dict[fmt["ext"]] = chk
            row = idx // cols
            col = idx % cols
            grid.addWidget(chk, row, col)

        scroll.setWidget(scroll_content)
        return scroll

    # ==========================================================================
    # MANEJADORES DE ESTADO Y FILTRADO
    # ==========================================================================
    def _on_master_cat_toggled(self, tab_idx: int, is_checked: bool):
        """Al marcar o desmarcar una categoría principal, navega a su pestaña y actualiza."""
        if is_checked:
            self.tab_widget.setCurrentIndex(tab_idx)
        self._update_all_counters()
        self.categories_changed.emit()

    def _on_tab_changed(self, idx: int):
        pass

    def _filter_formats(self, text: str):
        """Compatibilidad hacia atrás con tests: filtra en el catálogo de documentos."""
        self._filter_catalog(self.doc_checkboxes, text)

    def _filter_catalog(self, checkboxes: Dict[str, QCheckBox], text: str):
        """Filtra en tiempo real los checkboxes visibles en la cuadrícula."""
        query = text.strip().lower()
        for chk in checkboxes.values():
            fmt = chk.property("format_info")
            if not fmt:
                continue
            matches = (
                not query or
                query in fmt["ext"].lower() or
                query in fmt["name"].lower() or
                query in fmt["desc"].lower() or
                query in fmt.get("sub", "").lower() or
                query in fmt.get("suite", "").lower()
            )
            chk.setVisible(matches)

    # Presets de Imágenes
    def _apply_image_preset(self, preset: str):
        for fmt in IMAGE_FORMAT_CATALOG:
            chk = self.image_checkboxes.get(fmt["ext"])
            if not chk:
                continue
            chk.blockSignals(True)
            if preset == "all":
                chk.setChecked(True)
            elif preset == "none":
                chk.setChecked(False)
            elif preset == "photo":
                chk.setChecked(fmt["sub"] == "photo")
            elif preset == "web":
                chk.setChecked(fmt["sub"] == "web")
            elif preset == "design":
                chk.setChecked(fmt["sub"] == "design")
            chk.blockSignals(False)
        self._on_image_checkbox_changed()

    def _on_image_checkbox_changed(self):
        active = sum(1 for chk in self.image_checkboxes.values() if chk.isChecked())
        total = len(self.image_checkboxes)
        self.lbl_images_count.setText(f"({active} de {total} activos)")
        self.lbl_images_count.setStyleSheet(f"font-size: 11px; color: {'#7ee787' if active > 0 else '#f85149'}; font-weight: bold;")
        self._update_footer_count()

    # Presets de Documentos
    def _apply_doc_preset(self, preset: str):
        for fmt in DOCUMENT_FORMAT_CATALOG:
            chk = self.doc_checkboxes.get(fmt["ext"])
            if not chk:
                continue
            chk.blockSignals(True)
            if preset == "all":
                chk.setChecked(True)
            elif preset == "none":
                chk.setChecked(False)
            elif preset == "office":
                chk.setChecked(fmt["suite"] == "office")
            elif preset == "pdf":
                chk.setChecked(fmt["suite"] == "pdf")
            elif preset == "text":
                chk.setChecked(fmt["suite"] == "text")
            elif preset == "odf":
                chk.setChecked(fmt["suite"] == "odf")
            chk.blockSignals(False)
        self._on_doc_checkbox_changed()

    def _on_doc_checkbox_changed(self):
        active = sum(1 for chk in self.doc_checkboxes.values() if chk.isChecked())
        total = len(self.doc_checkboxes)
        self.lbl_docs_count.setText(f"({active} de {total} activos)")
        self.lbl_docs_count.setStyleSheet(f"font-size: 11px; color: {'#7ee787' if active > 0 else '#f85149'}; font-weight: bold;")
        self._update_footer_count()

    # Presets de Audio / Video
    def _apply_media_preset(self, preset: str):
        for fmt in MEDIA_FORMAT_CATALOG:
            chk = self.media_checkboxes.get(fmt["ext"])
            if not chk:
                continue
            chk.blockSignals(True)
            if preset == "all":
                chk.setChecked(True)
            elif preset == "none":
                chk.setChecked(False)
            elif preset == "video":
                chk.setChecked(fmt["sub"] == "video")
            elif preset == "audio":
                chk.setChecked(fmt["sub"] == "audio")
            elif preset == "hd":
                chk.setChecked(fmt["ext"] in [".mp4", ".mkv", ".mov"])
            elif preset == "lossless":
                chk.setChecked(fmt["ext"] in [".flac", ".wav"])
            chk.blockSignals(False)
        self._on_media_checkbox_changed()

    def _on_media_checkbox_changed(self):
        active = sum(1 for chk in self.media_checkboxes.values() if chk.isChecked())
        total = len(self.media_checkboxes)
        self.lbl_media_count.setText(f"({active} de {total} activos)")
        self.lbl_media_count.setStyleSheet(f"font-size: 11px; color: {'#7ee787' if active > 0 else '#f85149'}; font-weight: bold;")
        self._update_footer_count()

    # Presets de Comprimidos
    def _apply_zip_preset(self, preset: str):
        for fmt in COMPRESSED_FORMAT_CATALOG:
            chk = self.zip_checkboxes.get(fmt["ext"])
            if not chk:
                continue
            chk.blockSignals(True)
            if preset == "all":
                chk.setChecked(True)
            elif preset == "none":
                chk.setChecked(False)
            elif preset == "standard":
                chk.setChecked(fmt["ext"] in [".zip", ".rar", ".7z"])
            elif preset == "iso":
                chk.setChecked(fmt["ext"] == ".iso")
            elif preset == "tar":
                chk.setChecked(fmt["sub"] == "tar")
            chk.blockSignals(False)
        self._on_zip_checkbox_changed()

    def _on_zip_checkbox_changed(self):
        active = sum(1 for chk in self.zip_checkboxes.values() if chk.isChecked())
        total = len(self.zip_checkboxes)
        self.lbl_zips_count.setText(f"({active} de {total} activos)")
        self.lbl_zips_count.setStyleSheet(f"font-size: 11px; color: {'#7ee787' if active > 0 else '#f85149'}; font-weight: bold;")
        self._update_footer_count()

    def _update_all_counters(self):
        self._on_image_checkbox_changed()
        self._on_doc_checkbox_changed()
        self._on_media_checkbox_changed()
        self._on_zip_checkbox_changed()

    def _update_footer_count(self):
        total_active = len(self.get_all_selected_extensions())
        total_possible = len(IMAGE_FORMAT_CATALOG) + len(DOCUMENT_FORMAT_CATALOG) + len(MEDIA_FORMAT_CATALOG) + len(COMPRESSED_FORMAT_CATALOG)
        self.lbl_footer_count.setText(f"Total: {total_active} de {total_possible} formatos activos seleccionados")

    # ==========================================================================
    # MÉTODOS PÚBLICOS DE CONSULTA
    # ==========================================================================
    def get_selected_categories(self) -> List[str]:
        """Devuelve las categorías principales seleccionadas."""
        cats = []
        if self.chk_images.isChecked():
            cats.append("Imágenes")
        if self.chk_docs.isChecked():
            cats.append("Documentos")
        if self.chk_media.isChecked():
            cats.extend(["Audio", "Video"])
        if self.chk_zips.isChecked():
            cats.append("Comprimidos")
        return cats

    def get_selected_image_extensions(self) -> List[str]:
        """Devuelve las extensiones de imágenes seleccionadas."""
        if not self.chk_images.isChecked():
            return []
        return [ext for ext, chk in self.image_checkboxes.items() if chk.isChecked()]

    def get_selected_doc_extensions(self) -> List[str]:
        """Devuelve las extensiones de documentos seleccionadas."""
        if not self.chk_docs.isChecked():
            return []
        return [ext for ext, chk in self.doc_checkboxes.items() if chk.isChecked()]

    def get_selected_media_extensions(self) -> List[str]:
        """Devuelve las extensiones de audio/video seleccionadas."""
        if not self.chk_media.isChecked():
            return []
        return [ext for ext, chk in self.media_checkboxes.items() if chk.isChecked()]

    def get_selected_zip_extensions(self) -> List[str]:
        """Devuelve las extensiones de comprimidos seleccionadas."""
        if not self.chk_zips.isChecked():
            return []
        return [ext for ext, chk in self.zip_checkboxes.items() if chk.isChecked()]

    def get_all_selected_extensions(self) -> List[str]:
        """Devuelve la lista unificada de todas las extensiones activas de categorías marcadas."""
        res = []
        res.extend(self.get_selected_image_extensions())
        res.extend(self.get_selected_doc_extensions())
        res.extend(self.get_selected_media_extensions())
        res.extend(self.get_selected_zip_extensions())
        return res

    def get_summary_text(self) -> str:
        """Devuelve una cadena descriptiva compacta con el estado actual."""
        cats = self.get_selected_categories()
        if not cats:
            return "Ninguna categoría seleccionada"

        img_exts = self.get_selected_image_extensions()
        doc_exts = self.get_selected_doc_extensions()
        med_exts = self.get_selected_media_extensions()
        zip_exts = self.get_selected_zip_extensions()

        total_exts = len(img_exts) + len(doc_exts) + len(med_exts) + len(zip_exts)
        total_possible = len(IMAGE_FORMAT_CATALOG) + len(DOCUMENT_FORMAT_CATALOG) + len(MEDIA_FORMAT_CATALOG) + len(COMPRESSED_FORMAT_CATALOG)

        has_img = self.chk_images.isChecked()
        has_doc = self.chk_docs.isChecked()
        has_med = self.chk_media.isChecked()
        has_zip = self.chk_zips.isChecked()

        # Si todas las 4 categorías están activas
        if has_img and has_doc and has_med and has_zip:
            if total_exts == total_possible:
                return f"🏷️ Todas las Categorías ({total_possible} Formatos)"
            else:
                return f"🏷️ Todas las Categorías ({total_exts} Formatos Activos)"

        # Si solo está activa una categoría
        if has_doc and not (has_img or has_med or has_zip):
            office_exts = {f["ext"] for f in DOCUMENT_FORMAT_CATALOG if f["suite"] == "office"}
            pdf_exts = {f["ext"] for f in DOCUMENT_FORMAT_CATALOG if f["suite"] == "pdf"}
            text_exts = {f["ext"] for f in DOCUMENT_FORMAT_CATALOG if f["suite"] == "text"}
            odf_exts = {f["ext"] for f in DOCUMENT_FORMAT_CATALOG if f["suite"] == "odf"}
            c_set = set(doc_exts)
            if c_set == office_exts:
                return f"📘 Solo Office ({len(doc_exts)} Formatos)"
            elif c_set == pdf_exts:
                return f"📕 Solo PDF ({len(doc_exts)} Formatos)"
            elif c_set == text_exts:
                return f"📄 Solo Texto ({len(doc_exts)} Formatos)"
            elif c_set == odf_exts:
                return f"📑 Solo LibreOffice ({len(doc_exts)} Formatos)"
            return f"📄 Solo Documentos ({len(doc_exts)} Formatos)"

        if has_img and not (has_doc or has_med or has_zip):
            photos = {f["ext"] for f in IMAGE_FORMAT_CATALOG if f["sub"] == "photo"}
            if set(img_exts) == photos:
                return f"📸 Solo Fotos ({len(img_exts)} Formatos)"
            return f"🖼️ Solo Imágenes ({len(img_exts)} Formatos)"

        if has_med and not (has_img or has_doc or has_zip):
            videos = {f["ext"] for f in MEDIA_FORMAT_CATALOG if f["sub"] == "video"}
            audios = {f["ext"] for f in MEDIA_FORMAT_CATALOG if f["sub"] == "audio"}
            if set(med_exts) == videos:
                return f"🎬 Solo Video ({len(med_exts)} Formatos)"
            elif set(med_exts) == audios:
                return f"🎵 Solo Audio ({len(med_exts)} Formatos)"
            return f"🎵 Audio / Video ({len(med_exts)} Formatos)"

        if has_zip and not (has_img or has_doc or has_med):
            return f"📦 Solo Comprimidos ({len(zip_exts)} Formatos)"

        # Combinación de categorías
        names = []
        if has_img:
            names.append(f"Img ({len(img_exts)})")
        if has_doc:
            names.append(f"Docs ({len(doc_exts)})")
        if has_med:
            names.append(f"Media ({len(med_exts)})")
        if has_zip:
            names.append(f"Zips ({len(zip_exts)})")

        return f"🏷️ {', '.join(names)}"


class FolderChecklistDialog(QDialog):
    """Diálogo emergente modal con checklist de carpetas recomendadas y personalizadas."""

    def __init__(self, active_categories: List[str] = None, custom_folders: List[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🖐️ Selección de Ubicaciones y Carpetas a Indexar")
        self.setMinimumSize(720, 520)
        self.setStyleSheet(DARK_THEME_QSS)

        self.active_categories = active_categories or ["Imágenes", "Documentos", "Audio", "Video", "Comprimidos"]
        self.custom_folders = list(custom_folders or [])
        self._init_ui()
        self.rebuild_table()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Encabezado
        lbl_title = QLabel("🖐️ Selector Manual de Carpetas y Ubicaciones")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #58a6ff;")
        main_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Marque las carpetas que desea incluir en el análisis. Puede filtrar por nombre, "
            "añadir cualquier carpeta del equipo o restablecer las recomendadas."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        main_layout.addWidget(lbl_desc)

        # Barra de Búsqueda y Filtro
        search_row = QHBoxLayout()
        lbl_search = QLabel("🔍 Buscar:")
        lbl_search.setStyleSheet("color: #8b949e; font-weight: bold;")
        search_row.addWidget(lbl_search)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Filtrar carpetas por nombre o ruta en disco...")
        self.txt_search.setStyleSheet("padding: 4px 8px; background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px;")
        self.txt_search.textChanged.connect(self._filter_table_rows)
        search_row.addWidget(self.txt_search)
        main_layout.addLayout(search_row)

        # Tabla de Carpetas
        self.table_folders = QTableWidget(0, 4)
        self.table_folders.setHorizontalHeaderLabels(["✔", "Ubicación", "Tipo / Relevancia", "Ruta en Disco"])
        self.table_folders.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_folders.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_folders.verticalHeader().setVisible(False)
        self.table_folders.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #21262d;
            }
            QTableWidget::item:selected {
                background-color: #1f6feb;
                color: white;
            }
        """)

        header = self.table_folders.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table_folders.setColumnWidth(0, 40)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.table_folders.setColumnWidth(1, 200)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.table_folders.setColumnWidth(2, 140)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.table_folders.itemClicked.connect(self._on_table_item_clicked)
        main_layout.addWidget(self.table_folders, stretch=1)

        # Barra de Acciones sobre la Lista
        btn_toolbar = QHBoxLayout()
        btn_toolbar.setSpacing(6)

        btn_style = "font-size: 11px; padding: 4px 10px; border-radius: 4px; background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9;"

        self.btn_add_folder = QPushButton("➕ Añadir Carpeta Personalizada...")
        self.btn_add_folder.setStyleSheet(btn_style)
        self.btn_add_folder.clicked.connect(self._browse_custom_folder)
        btn_toolbar.addWidget(self.btn_add_folder)

        self.btn_remove_custom = QPushButton("➖ Quitar Carpeta")
        self.btn_remove_custom.setStyleSheet(btn_style)
        self.btn_remove_custom.clicked.connect(self._remove_selected_custom)
        btn_toolbar.addWidget(self.btn_remove_custom)

        btn_toolbar.addStretch()

        self.btn_apply_recommended = QPushButton("🎯 Solo Recomendadas")
        self.btn_apply_recommended.setStyleSheet(btn_style)
        self.btn_apply_recommended.clicked.connect(self._check_recommended_only)
        btn_toolbar.addWidget(self.btn_apply_recommended)

        self.btn_select_all = QPushButton("Marcar Todas")
        self.btn_select_all.setStyleSheet(btn_style)
        self.btn_select_all.clicked.connect(lambda: self._set_all_checks(True))
        btn_toolbar.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Desmarcar")
        self.btn_deselect_all.setStyleSheet(btn_style)
        self.btn_deselect_all.clicked.connect(lambda: self._set_all_checks(False))
        btn_toolbar.addWidget(self.btn_deselect_all)

        main_layout.addLayout(btn_toolbar)

        # Barra Inferior con Conteo y Confirmación
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)

        self.lbl_counter = QLabel("0 carpetas seleccionadas")
        self.lbl_counter.setStyleSheet("font-size: 11px; font-weight: bold; color: #7ee787;")
        footer_layout.addWidget(self.lbl_counter)
        footer_layout.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("✔ Aplicar Ubicaciones")
        self.btn_apply.setObjectName("PrimaryButton")
        self.btn_apply.clicked.connect(self.accept)
        footer_layout.addWidget(self.btn_apply)

        main_layout.addLayout(footer_layout)

    def set_categories(self, active_categories: List[str]):
        """Actualiza las categorías activas y reconstruye las carpetas sugeridas."""
        self.active_categories = active_categories
        self.rebuild_table()

    def rebuild_table(self, previously_checked: List[str] = None):
        """Rellena la tabla con carpetas sugeridas por ContextRouter y personalizadas."""
        suggested = ContextRouter.get_suggested_folders(self.active_categories)
        self.table_folders.setRowCount(0)

        # 1. Carpetas sugeridas por el sistema
        for folder in suggested:
            row = self.table_folders.rowCount()
            self.table_folders.insertRow(row)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if previously_checked is not None:
                is_checked = folder["path"] in previously_checked
            else:
                is_checked = folder["recommended"]
            chk.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)
            chk.setData(Qt.UserRole, folder["path"])
            chk.setData(Qt.UserRole + 1, False) # is_custom = False
            self.table_folders.setItem(row, 0, chk)

            name_item = QTableWidgetItem(f"{folder['icon']} {folder['name']}")
            name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
            self.table_folders.setItem(row, 1, name_item)

            rel_str = "🎯 Recomendada" if folder["recommended"] else f"📁 {folder['category_tag']}"
            rel_item = QTableWidgetItem(rel_str)
            rel_item.setFlags(rel_item.flags() ^ Qt.ItemIsEditable)
            if folder["recommended"]:
                rel_item.setForeground(Qt.cyan)
            self.table_folders.setItem(row, 2, rel_item)

            path_item = QTableWidgetItem(folder["path"])
            path_item.setFlags(path_item.flags() ^ Qt.ItemIsEditable)
            self.table_folders.setItem(row, 3, path_item)

        # 2. Carpetas personalizadas añadidas por el usuario
        for custom_path in self.custom_folders:
            row = self.table_folders.rowCount()
            self.table_folders.insertRow(row)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if previously_checked is not None:
                is_checked = custom_path in previously_checked
            else:
                is_checked = True
            chk.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)
            chk.setData(Qt.UserRole, custom_path)
            chk.setData(Qt.UserRole + 1, True) # is_custom = True
            self.table_folders.setItem(row, 0, chk)

            name_item = QTableWidgetItem(f"⭐ {os.path.basename(custom_path)}")
            name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
            self.table_folders.setItem(row, 1, name_item)

            rel_item = QTableWidgetItem("⭐ Personalizada")
            rel_item.setFlags(rel_item.flags() ^ Qt.ItemIsEditable)
            rel_item.setForeground(Qt.yellow)
            self.table_folders.setItem(row, 2, rel_item)

            path_item = QTableWidgetItem(custom_path)
            path_item.setFlags(path_item.flags() ^ Qt.ItemIsEditable)
            self.table_folders.setItem(row, 3, path_item)

        self._update_counter_label()
        if self.txt_search.text():
            self._filter_table_rows(self.txt_search.text())

    def _filter_table_rows(self, text: str):
        """Filtra las filas visibles de la tabla según el texto de búsqueda."""
        query = text.strip().lower()
        for row in range(self.table_folders.rowCount()):
            name = self.table_folders.item(row, 1).text().lower()
            rel = self.table_folders.item(row, 2).text().lower()
            path = self.table_folders.item(row, 3).text().lower()
            matches = not query or (query in name or query in rel or query in path)
            self.table_folders.setRowHidden(row, not matches)

    def _on_table_item_clicked(self, item):
        if item.column() == 0:
            self._update_counter_label()

    def _update_counter_label(self):
        count = len(self.get_selected_paths())
        self.lbl_counter.setText(f"📌 {count} carpeta(s) seleccionadas para indexar")
        if count == 0:
            self.lbl_counter.setStyleSheet("font-size: 11px; font-weight: bold; color: #f85149;")
        else:
            self.lbl_counter.setStyleSheet("font-size: 11px; font-weight: bold; color: #7ee787;")

    def _browse_custom_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Indexar")
        if folder:
            norm = os.path.normpath(folder)
            if norm not in self.custom_folders:
                self.custom_folders.append(norm)
                current_checked = self.get_selected_paths()
                current_checked.append(norm)
                self.rebuild_table(previously_checked=current_checked)

    def _remove_selected_custom(self):
        selected_ranges = self.table_folders.selectedRanges()
        if not selected_ranges:
            QMessageBox.information(self, "Información", "Haga clic en una carpeta personalizada de la lista para seleccionarla.")
            return
        row = selected_ranges[0].topRow()
        chk = self.table_folders.item(row, 0)
        if chk and chk.data(Qt.UserRole + 1):  # is_custom
            path = chk.data(Qt.UserRole)
            if path in self.custom_folders:
                self.custom_folders.remove(path)
                current_checked = [p for p in self.get_selected_paths() if p != path]
                self.rebuild_table(previously_checked=current_checked)
        else:
            QMessageBox.information(self, "Información", "Solo se pueden eliminar carpetas añadidas manualmente.")

    def _check_recommended_only(self):
        for row in range(self.table_folders.rowCount()):
            chk = self.table_folders.item(row, 0)
            rel = self.table_folders.item(row, 2)
            if chk and rel:
                is_rec = "Recomendada" in rel.text() or "Personalizada" in rel.text()
                chk.setCheckState(Qt.Checked if is_rec else Qt.Unchecked)
        self._update_counter_label()

    def _set_all_checks(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.table_folders.rowCount()):
            chk = self.table_folders.item(row, 0)
            if chk:
                chk.setCheckState(state)
        self._update_counter_label()

    def get_selected_paths(self) -> List[str]:
        """Devuelve la lista de rutas actualmente marcadas con checkbox."""
        selected = []
        for row in range(self.table_folders.rowCount()):
            chk = self.table_folders.item(row, 0)
            if chk and chk.checkState() == Qt.Checked:
                path = chk.data(Qt.UserRole)
                if path and os.path.exists(path):
                    selected.append(path)
        return selected

    def get_custom_folders(self) -> List[str]:
        """Devuelve la lista de carpetas personalizadas."""
        return list(self.custom_folders)
