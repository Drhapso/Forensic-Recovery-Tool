"""
Componente de tabla de resultados con búsqueda instantánea, filtrado por categorías y tipos de archivo,
ordenamiento dinámico multinivel (nombre, tipo de archivo, ruta original y tamaño) y selección masiva.
"""

import os
from typing import List, Dict, Any, Set
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal
from core.disk_utils import format_size

FORMAT_DESCRIPTIONS = {
    # Documentos y Suites Ofimáticas
    ".docx": "📘 .DOCX (Microsoft Word)",
    ".doc": "📘 .DOC (Word 97-2003)",
    ".docm": "📘 .DOCM (Word con Macros)",
    ".dotx": "📘 .DOTX (Plantilla Word)",
    ".dot": "📘 .DOT (Plantilla Word Clásica)",
    ".rtf": "📝 .RTF (Texto Enriquecido)",
    ".asd": "💾 .ASD (AutoRecuperación Word)",
    ".wbk": "💾 .WBK (Respaldo Word)",
    ".xlsx": "📊 .XLSX (Microsoft Excel)",
    ".xls": "📊 .XLS (Excel 97-2003)",
    ".xlsm": "📊 .XLSM (Excel con Macros)",
    ".xlsb": "📊 .XLSB (Excel Binario)",
    ".xltx": "📊 .XLTX (Plantilla Excel)",
    ".csv": "📊 .CSV (Valores por Comas)",
    ".tsv": "📊 .TSV (Valores Tabulados)",
    ".xar": "💾 .XAR (AutoRecuperación Excel)",
    ".pptx": "📽️ .PPTX (Microsoft PowerPoint)",
    ".ppt": "📽️ .PPT (PowerPoint 97-2003)",
    ".pptm": "📽️ .PPTM (PowerPoint con Macros)",
    ".ppsx": "📽️ .PPSX (Presentación Directa)",
    ".pps": "📽️ .PPS (Diapositivas PowerPoint)",
    ".pdf": "📕 .PDF (Adobe Acrobat)",
    ".epub": "📚 .EPUB (Libro Electrónico)",
    ".mobi": "📚 .MOBI (Libro Mobipocket)",
    ".xps": "📑 .XPS (XML Paper Spec)",
    ".odt": "📑 .ODT (LibreOffice Writer)",
    ".ods": "📑 .ODS (LibreOffice Calc)",
    ".odp": "📑 .ODP (LibreOffice Impress)",
    ".odg": "📑 .ODG (LibreOffice Draw)",
    ".txt": "📄 .TXT (Texto Plano)",
    ".md": "📄 .MD (Markdown)",
    ".log": "📄 .LOG (Registro de Texto)",
    ".xml": "🌐 .XML (Datos XML)",
    ".html": "🌐 .HTML (Documento HTML)",
    ".htm": "🌐 .HTM (Página Web)",
    ".msg": "✉️ .MSG (Mensaje Outlook)",
    ".pub": "📰 .PUB (Microsoft Publisher)",
    ".one": "📓 .ONE (Notas OneNote)",
    ".accdb": "🗄️ .ACCDB (Base Datos Access)",
    ".mdb": "🗄️ .MDB (Access 97-2003)",
    # Imágenes
    ".jpg": "🖼️ .JPG (Imagen JPEG)",
    ".jpeg": "🖼️ .JPEG (Imagen JPEG)",
    ".png": "🖼️ .PNG (Imagen PNG)",
    ".gif": "🖼️ .GIF (Animación GIF)",
    ".bmp": "🖼️ .BMP (Mapa de Bits)",
    ".webp": "🖼️ .WEBP (Imagen WebP)",
    # Audio / Video
    ".mp4": "🎬 .MP4 (Video MPEG-4)",
    ".mkv": "🎬 .MKV (Video Matroska)",
    ".avi": "🎬 .AVI (Video AVI)",
    ".mp3": "🎵 .MP3 (Audio MP3)",
    ".wav": "🎵 .WAV (Audio WAV)",
    ".flac": "🎵 .FLAC (Audio Lossless)",
    # Comprimidos
    ".zip": "📦 .ZIP (Archivo Comprimido)",
    ".rar": "📦 .RAR (Archivo RAR)",
    ".7z": "📦 .7Z (Archivo 7-Zip)"
}

class NumericTableWidgetItem(QTableWidgetItem):
    """Permite ordenar números (como bytes de tamaño) por su valor real en lugar de texto alfabético."""
    def __init__(self, text: str, sort_value: int):
        super().__init__(text)
        self.sort_value = sort_value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.sort_value < other.sort_value
        return super().__lt__(other)


class ResultsTable(QWidget):
    """Tabla interactiva de archivos recuperados con filtrado por tipo y ordenamiento avanzado."""

    item_selected = pyqtSignal(dict)
    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_items: List[Dict[str, Any]] = []
        self.filtered_items: List[Dict[str, Any]] = []
        self.checked_item_ids: Set[str] = set()
        self._is_populating = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # -------------------------------------------------------------
        # FILA 1: FILTROS (Búsqueda, Categoría, Tipo de Archivo / Extensión y Limpiar)
        # -------------------------------------------------------------
        filters_frame = QFrame()
        filters_frame.setStyleSheet("background-color: #161b22; border-radius: 6px; padding: 4px; border: 1px solid #30363d;")
        filters_layout = QHBoxLayout(filters_frame)
        filters_layout.setContentsMargins(6, 4, 6, 4)
        filters_layout.setSpacing(8)

        # 1. Búsqueda rápida de texto
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Buscar por nombre o ruta...")
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.textChanged.connect(self._apply_filters_and_sort)
        filters_layout.addWidget(self.txt_search, stretch=3)

        # 2. Filtro por Categoría General
        lbl_cat = QLabel("Categoría:")
        lbl_cat.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: bold;")
        filters_layout.addWidget(lbl_cat)

        self.combo_category = QComboBox()
        self.combo_category.addItems([
            "Todas las Categorías",
            "Imágenes",
            "Documentos",
            "Audio",
            "Video",
            "Comprimidos",
            "Código/Desarrollo",
            "Otros"
        ])
        self.combo_category.currentIndexChanged.connect(self._on_category_changed)
        filters_layout.addWidget(self.combo_category, stretch=2)

        # 3. Filtro por Tipo de Archivo / Extensión Específica
        lbl_ext = QLabel("Tipo / Ext:")
        lbl_ext.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: bold;")
        filters_layout.addWidget(lbl_ext)

        self.combo_extension = QComboBox()
        self.combo_extension.addItem("Todos los Tipos (*.*)", "")
        self.combo_extension.currentIndexChanged.connect(self._apply_filters_and_sort)
        filters_layout.addWidget(self.combo_extension, stretch=2)

        # 4. Filtro por Calidad / Usabilidad Forense
        lbl_quality = QLabel("Calidad:")
        lbl_quality.setStyleSheet("color: #e3b341; font-size: 11px; font-weight: bold;")
        filters_layout.addWidget(lbl_quality)

        self.combo_quality = QComboBox()
        self.combo_quality.addItem("Todas las Calidades", "all")
        self.combo_quality.addItem("🌟 Solo Alta Calidad (≥ 80%)", "high")
        self.combo_quality.addItem("🌟+🟡 Media y Alta (≥ 50%)", "usable")
        self.combo_quality.addItem("🛡️ Ocultar Inutilizables (< 20%)", "hide_junk")
        self.combo_quality.currentIndexChanged.connect(self._apply_filters_and_sort)
        filters_layout.addWidget(self.combo_quality, stretch=2)

        # 5. Botón Limpiar Filtros
        self.btn_clear_filters = QPushButton("🔄 Limpiar")
        self.btn_clear_filters.setToolTip("Restablecer la búsqueda y los filtros de tipo de archivo y calidad.")
        self.btn_clear_filters.clicked.connect(self._clear_filters)
        filters_layout.addWidget(self.btn_clear_filters)

        layout.addWidget(filters_frame)

        # -------------------------------------------------------------
        # FILA 2: ORDENAMIENTO (Nombre, Tipo, Ruta, Tamaño, Calidad) Y SELECCIÓN
        # -------------------------------------------------------------
        sort_frame = QFrame()
        sort_frame.setStyleSheet("background-color: #161b22; border-radius: 6px; padding: 4px; border: 1px solid #30363d;")
        sort_layout = QHBoxLayout(sort_frame)
        sort_layout.setContentsMargins(6, 4, 6, 4)
        sort_layout.setSpacing(8)

        lbl_sort = QLabel("🔃 Organizar por:")
        lbl_sort.setStyleSheet("color: #58a6ff; font-size: 11px; font-weight: bold;")
        sort_layout.addWidget(lbl_sort)

        self.combo_sort = QComboBox()
        self.combo_sort.addItem("📝 Nombre (A → Z)", "name_asc")
        self.combo_sort.addItem("📝 Nombre (Z → A)", "name_desc")
        self.combo_sort.addItem("🏷️ Tipo de Archivo (A → Z)", "type_asc")
        self.combo_sort.addItem("🏷️ Tipo de Archivo (Z → A)", "type_desc")
        self.combo_sort.addItem("🌟 Calidad (Mayor a Menor)", "quality_desc")
        self.combo_sort.addItem("🌟 Calidad (Menor a Mayor)", "quality_asc")
        self.combo_sort.addItem("💾 Tamaño (Mayor a Menor)", "size_desc")
        self.combo_sort.addItem("💾 Tamaño (Menor a Mayor)", "size_asc")
        self.combo_sort.addItem("📂 Ruta Original (A → Z)", "path_asc")
        self.combo_sort.addItem("📂 Ruta Original (Z → A)", "path_desc")
        self.combo_sort.addItem("🕒 Fecha (Más reciente)", "date_desc")
        self.combo_sort.addItem("🕒 Fecha (Más antigua)", "date_asc")
        self.combo_sort.currentIndexChanged.connect(self._apply_filters_and_sort)
        sort_layout.addWidget(self.combo_sort, stretch=3)

        sort_layout.addStretch()

        # Botón de selección inteligente de Alta Calidad
        self.btn_select_high = QPushButton("🌟 Solo Alta Calidad")
        self.btn_select_high.setStyleSheet("background-color: #238636; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px;")
        self.btn_select_high.setToolTip("Marca exclusivamente los archivos con alta usabilidad verificada (≥ 80%) y desmarca elementos de baja calidad o basura.")
        self.btn_select_high.clicked.connect(self._select_high_quality_checks)
        sort_layout.addWidget(self.btn_select_high)

        # Botones de selección masiva
        self.btn_select_all = QPushButton("✔ Todos")
        self.btn_select_all.clicked.connect(lambda: self._set_all_checks(True))
        sort_layout.addWidget(self.btn_select_all)

        self.btn_select_visible = QPushButton("✔ Solo Visibles")
        self.btn_select_visible.setToolTip("Marca las casillas únicamente de los archivos que coinciden con los filtros actuales.")
        self.btn_select_visible.clicked.connect(self._select_visible_checks)
        sort_layout.addWidget(self.btn_select_visible)

        self.btn_deselect_all = QPushButton("✖ Deseleccionar")
        self.btn_deselect_all.clicked.connect(lambda: self._set_all_checks(False))
        sort_layout.addWidget(self.btn_deselect_all)

        layout.addWidget(sort_frame)

        # -------------------------------------------------------------
        # TABLA PRINCIPAL DE DATOS (9 Columnas)
        # -------------------------------------------------------------
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "✔", "Nombre de Archivo", "Tipo", "Calidad / Integridad", "Categoría", "Tamaño", "Fecha", "Método de Origen", "Ruta Original / Detalle"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 36)

        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.setColumnWidth(1, 210)

        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 65)

        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(3, 140)

        header.setSectionResizeMode(4, QHeaderView.Interactive)
        self.table.setColumnWidth(4, 100)

        header.setSectionResizeMode(5, QHeaderView.Interactive)
        self.table.setColumnWidth(5, 95)

        header.setSectionResizeMode(6, QHeaderView.Interactive)
        self.table.setColumnWidth(6, 130)

        header.setSectionResizeMode(7, QHeaderView.Interactive)
        self.table.setColumnWidth(7, 150)

        header.setSectionResizeMode(8, QHeaderView.Stretch)

        # Sincronizar clic en cabeceras con el selector de orden
        header.sectionClicked.connect(self._on_header_section_clicked)

        self.table.itemClicked.connect(self._on_table_item_clicked)
        self.table.itemSelectionChanged.connect(self._on_row_selection_changed)
        layout.addWidget(self.table)

        # -------------------------------------------------------------
        # BARRA INFERIOR DE RESUMEN
        # -------------------------------------------------------------
        footer = QHBoxLayout()
        self.lbl_stats = QLabel("0 archivos encontrados")
        self.lbl_stats.setStyleSheet("color: #8b949e;")
        footer.addWidget(self.lbl_stats)
        footer.addStretch()

        self.lbl_selection = QLabel("0 seleccionados (0 B)")
        self.lbl_selection.setStyleSheet("color: #58a6ff; font-weight: bold;")
        footer.addWidget(self.lbl_selection)

        layout.addLayout(footer)

    def _get_item_key(self, item: dict) -> str:
        """Genera una clave unívoca para preservar el estado de selección."""
        item_id = item.get("id", "")
        container = item.get("container_file", "")
        path = item.get("original_path", "")
        name = item.get("name", "")
        size = item.get("size", 0)
        if container:
            return f"{item_id}_{container}_{path}_{size}"
        elif item_id and path and not path.startswith("["):
            return f"{item_id}_{path}"
        elif item_id and path:
            return f"{item_id}_{path}_{size}_{name}"
        elif item_id:
            return f"{item_id}_{name}_{size}"
        return f"{path or name}_{size}_{item.get('date', '')}"

    @staticmethod
    def _extract_extension(filename: str) -> str:
        """Extrae la extensión en minúsculas (ej. '.docx') o devuelve 'sin extensión'."""
        ext = os.path.splitext(filename or "")[1].lower()
        return ext if ext else "sin extensión"

    def set_items(self, items: list):
        """Carga una nueva lista completa de elementos encontrados y actualiza filtros dinámicos."""
        self.all_items = items
        # Por defecto, marcar todos los elementos como seleccionados
        self.checked_item_ids = {self._get_item_key(it) for it in items if it.get("recoverable", True)}
        self._populate_extension_filter()
        self._apply_filters_and_sort()

    def clear(self):
        """Limpia todos los elementos y restablece controles."""
        self.all_items = []
        self.filtered_items = []
        self.checked_item_ids.clear()
        self.table.setRowCount(0)
        self._populate_extension_filter()
        self._update_stats_label()

    def get_selected_items(self, only_visible: bool = False) -> list:
        """Retorna la lista de elementos actualmente marcados con checkbox."""
        pool = self.filtered_items if only_visible else self.all_items
        selected = []
        for item in pool:
            key = self._get_item_key(item)
            if key in self.checked_item_ids:
                selected.append(item)
        return selected

    def _populate_extension_filter(self):
        """Genera dinámicamente las extensiones encontradas en la sesión con su conteo y descripciones."""
        self.combo_extension.blockSignals(True)
        current_selection = self.combo_extension.currentData() or ""
        self.combo_extension.clear()
        self.combo_extension.addItem("Todos los Tipos (*.*)", "")

        if not self.all_items:
            self.combo_extension.blockSignals(False)
            return

        # Contar frecuencias de extensiones
        ext_counts: Dict[str, int] = {}
        for it in self.all_items:
            ext = self._extract_extension(it.get("name", ""))
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

        # Ordenar por frecuencia descendente
        sorted_exts = sorted(ext_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

        restore_idx = 0
        for idx, (ext, count) in enumerate(sorted_exts, start=1):
            if ext in FORMAT_DESCRIPTIONS:
                label = f"{FORMAT_DESCRIPTIONS[ext]} ({count})"
            else:
                label = f"{ext.upper() if ext.startswith('.') else ext} ({count})"
            self.combo_extension.addItem(label, ext)
            if ext == current_selection:
                restore_idx = idx

        self.combo_extension.setCurrentIndex(restore_idx)
        self.combo_extension.blockSignals(False)

    def _on_category_changed(self):
        """Al cambiar de categoría, actualiza la lista visual respetando las extensiones compatibles."""
        self._apply_filters_and_sort()

    def _clear_filters(self):
        """Restablece la búsqueda de texto y los filtros de tipo de archivo y calidad."""
        self.txt_search.blockSignals(True)
        self.combo_category.blockSignals(True)
        self.combo_extension.blockSignals(True)
        self.combo_quality.blockSignals(True)

        self.txt_search.clear()
        self.combo_category.setCurrentIndex(0)
        self.combo_extension.setCurrentIndex(0)
        self.combo_quality.setCurrentIndex(0)

        self.txt_search.blockSignals(False)
        self.combo_category.blockSignals(False)
        self.combo_extension.blockSignals(False)
        self.combo_quality.blockSignals(False)

        self._apply_filters_and_sort()

    def _apply_filters_and_sort(self):
        """Filtra y organiza los archivos según los criterios seleccionados por el usuario."""
        query = self.txt_search.text().strip().lower()
        cat_filter = self.combo_category.currentText()
        ext_filter = self.combo_extension.currentData() or ""
        qual_filter = self.combo_quality.currentData() or "all"
        sort_mode = self.combo_sort.currentData() or "name_asc"

        # 1. Filtrado
        candidates = []
        for item in self.all_items:
            name = item.get("name", "")
            name_lower = name.lower()
            orig = item.get("original_path", "").lower()
            category = item.get("category", "")
            ext = self._extract_extension(name)

            # Filtro por texto de búsqueda
            if query and (query not in name_lower and query not in orig):
                continue

            # Filtro por categoría
            if cat_filter != "Todas las Categorías" and category != cat_filter:
                continue

            # Filtro por tipo de archivo / extensión
            if ext_filter and ext != ext_filter:
                continue

            # Filtro por calidad y usabilidad forense
            score = item.get("usability_score", 85 if item.get("recoverable", True) else 10)
            if qual_filter == "high":
                if not (item.get("is_high_quality") or score >= 80 or item.get("usability_tier") == "high"):
                    continue
            elif qual_filter == "usable":
                if not (item.get("is_usable") or score >= 50 or item.get("usability_tier") in {"high", "medium"}):
                    continue
            elif qual_filter == "hide_junk":
                if score < 20 or item.get("usability_tier") == "unusable":
                    continue

            candidates.append(item)

        # 2. Organización y Ordenamiento
        if sort_mode == "name_asc":
            candidates.sort(key=lambda x: x.get("name", "").lower())
        elif sort_mode == "name_desc":
            candidates.sort(key=lambda x: x.get("name", "").lower(), reverse=True)
        elif sort_mode == "type_asc":
            candidates.sort(key=lambda x: (self._extract_extension(x.get("name", "")), x.get("name", "").lower()))
        elif sort_mode == "type_desc":
            candidates.sort(key=lambda x: (self._extract_extension(x.get("name", "")), x.get("name", "").lower()), reverse=True)
        elif sort_mode == "quality_desc":
            candidates.sort(key=lambda x: x.get("usability_score", 0), reverse=True)
        elif sort_mode == "quality_asc":
            candidates.sort(key=lambda x: x.get("usability_score", 0))
        elif sort_mode == "size_desc":
            candidates.sort(key=lambda x: x.get("size", 0), reverse=True)
        elif sort_mode == "size_asc":
            candidates.sort(key=lambda x: x.get("size", 0))
        elif sort_mode == "path_asc":
            candidates.sort(key=lambda x: (x.get("original_path", "").lower(), x.get("name", "").lower()))
        elif sort_mode == "path_desc":
            candidates.sort(key=lambda x: (x.get("original_path", "").lower(), x.get("name", "").lower()), reverse=True)
        elif sort_mode == "date_desc":
            candidates.sort(key=lambda x: str(x.get("date", "")), reverse=True)
        elif sort_mode == "date_asc":
            candidates.sort(key=lambda x: str(x.get("date", "")))

        self.filtered_items = candidates

        # 3. Renderizado en QTableWidget
        self._is_populating = True
        self.table.setRowCount(0)

        for item in self.filtered_items:
            self._add_row(item)

        self._is_populating = False
        self._update_stats_label()

    def _add_row(self, item: dict):
        row = self.table.rowCount()
        self.table.insertRow(row)

        key = self._get_item_key(item)
        is_checked = key in self.checked_item_ids

        # Columna 0: Checkbox
        chk_item = QTableWidgetItem()
        chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        chk_item.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)
        chk_item.setData(Qt.UserRole, item)
        self.table.setItem(row, 0, chk_item)

        # Columna 1: Nombre de archivo
        name_item = QTableWidgetItem(item.get("name", ""))
        name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
        self.table.setItem(row, 1, name_item)

        # Columna 2: Tipo de archivo / Extensión
        ext = self._extract_extension(item.get("name", ""))
        display_ext = ext.upper() if ext.startswith(".") else ext
        ext_item = QTableWidgetItem(display_ext)
        ext_item.setFlags(ext_item.flags() ^ Qt.ItemIsEditable)
        ext_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 2, ext_item)

        # Columna 3: Calidad / Usabilidad Forense (Ordenamiento numérico por puntaje real)
        score = item.get("usability_score", 85 if item.get("recoverable", True) else 10)
        label = item.get("usability_label")
        if not label:
            if score >= 80:
                label = f"🌟 Alta ({score}%)"
            elif score >= 50:
                label = f"🟡 Media ({score}%)"
            elif score >= 20:
                label = f"🟠 Baja ({score}%)"
            else:
                label = f"🔴 Inútil ({score}%)"

        quality_item = NumericTableWidgetItem(label, score)
        quality_item.setFlags(quality_item.flags() ^ Qt.ItemIsEditable)
        quality_item.setTextAlignment(Qt.AlignCenter)
        if score >= 80:
            quality_item.setForeground(QColor("#3fb950"))
        elif score >= 50:
            quality_item.setForeground(QColor("#d29922"))
        elif score >= 20:
            quality_item.setForeground(QColor("#db6d28"))
        else:
            quality_item.setForeground(QColor("#f85149"))

        reasons = item.get("usability_reasons", [])
        if reasons:
            quality_item.setToolTip("\n".join(f"• {r}" for r in reasons))
        self.table.setItem(row, 3, quality_item)

        # Columna 4: Categoría
        cat_item = QTableWidgetItem(item.get("category", ""))
        cat_item.setFlags(cat_item.flags() ^ Qt.ItemIsEditable)
        self.table.setItem(row, 4, cat_item)

        # Columna 5: Tamaño (Ordenamiento numérico por bytes reales)
        size_bytes = item.get("size", 0)
        size_item = NumericTableWidgetItem(format_size(size_bytes), size_bytes)
        size_item.setFlags(size_item.flags() ^ Qt.ItemIsEditable)
        size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 5, size_item)

        # Columna 6: Fecha
        date_item = QTableWidgetItem(str(item.get("date", "-")))
        date_item.setFlags(date_item.flags() ^ Qt.ItemIsEditable)
        self.table.setItem(row, 6, date_item)

        # Columna 7: Método de Origen
        method_item = QTableWidgetItem(item.get("source_method", ""))
        method_item.setFlags(method_item.flags() ^ Qt.ItemIsEditable)
        self.table.setItem(row, 7, method_item)

        # Columna 8: Ruta original / Detalle
        path_item = QTableWidgetItem(item.get("original_path", ""))
        path_item.setFlags(path_item.flags() ^ Qt.ItemIsEditable)
        self.table.setItem(row, 8, path_item)

    def _select_high_quality_checks(self):
        """Marca exclusivamente los archivos evaluados con alta calidad y usabilidad (≥ 80%)."""
        pool = self.filtered_items if len(self.filtered_items) < len(self.all_items) else self.all_items
        high_keys = set()
        for it in pool:
            score = it.get("usability_score", 85 if it.get("recoverable", True) else 10)
            if it.get("is_high_quality") or score >= 80 or it.get("usability_tier") == "high":
                high_keys.add(self._get_item_key(it))
        self.checked_item_ids = high_keys

        for row in range(self.table.rowCount()):
            chk_item = self.table.item(row, 0)
            if chk_item:
                data_item = chk_item.data(Qt.UserRole)
                if data_item:
                    k = self._get_item_key(data_item)
                    chk_item.setCheckState(Qt.Checked if k in self.checked_item_ids else Qt.Unchecked)

        self._update_stats_label()
        self.selection_changed.emit()

    def _on_header_section_clicked(self, logical_index: int):
        """Sincroniza el clic en la cabecera de la tabla con las opciones de ordenamiento."""
        column_to_modes = {
            1: ("name_asc", "name_desc"),
            2: ("type_asc", "type_desc"),
            3: ("quality_desc", "quality_asc"),
            5: ("size_desc", "size_asc"),
            6: ("date_desc", "date_asc"),
            8: ("path_asc", "path_desc")
        }
        if logical_index in column_to_modes:
            mode_pair = column_to_modes[logical_index]
            current_mode = self.combo_sort.currentData()
            next_mode = mode_pair[1] if current_mode == mode_pair[0] else mode_pair[0]

            idx = self.combo_sort.findData(next_mode)
            if idx >= 0:
                self.combo_sort.setCurrentIndex(idx)

    def _on_table_item_clicked(self, item: QTableWidgetItem):
        if item.column() == 0:
            data_item = item.data(Qt.UserRole)
            if data_item:
                key = self._get_item_key(data_item)
                if item.checkState() == Qt.Checked:
                    self.checked_item_ids.add(key)
                else:
                    self.checked_item_ids.discard(key)
            self._update_stats_label()
            self.selection_changed.emit()

    def _on_row_selection_changed(self):
        selected_ranges = self.table.selectedRanges()
        if selected_ranges:
            row = selected_ranges[0].topRow()
            chk_item = self.table.item(row, 0)
            if chk_item:
                data_item = chk_item.data(Qt.UserRole)
                if data_item:
                    self.item_selected.emit(data_item)

    def _set_all_checks(self, checked: bool):
        """Selecciona o deselecciona la totalidad de los archivos cargados."""
        if checked:
            self.checked_item_ids = {self._get_item_key(it) for it in self.all_items}
        else:
            self.checked_item_ids.clear()

        # Actualizar visualmente la tabla
        for row in range(self.table.rowCount()):
            chk_item = self.table.item(row, 0)
            if chk_item:
                chk_item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

        self._update_stats_label()
        self.selection_changed.emit()

    def _select_visible_checks(self):
        """Marca las casillas exclusivamente de los archivos que cumplen con los filtros visibles."""
        visible_keys = {self._get_item_key(it) for it in self.filtered_items}
        self.checked_item_ids = set(visible_keys)

        for row in range(self.table.rowCount()):
            chk_item = self.table.item(row, 0)
            if chk_item:
                chk_item.setCheckState(Qt.Checked)

        self._update_stats_label()
        self.selection_changed.emit()

    def _update_stats_label(self):
        total = len(self.all_items)
        visible = len(self.filtered_items)
        selected_items = self.get_selected_items()
        selected_count = len(selected_items)
        selected_size = sum(it.get("size", 0) for it in selected_items)

        visible_selected = self.get_selected_items(only_visible=True)
        vis_count = len(visible_selected)
        vis_size = sum(it.get("size", 0) for it in visible_selected)

        self.lbl_stats.setText(f"{visible} archivo(s) visibles de {total} totales")

        if visible < total and selected_count != vis_count:
            self.lbl_selection.setText(
                f"{vis_count} visibles marcados ({format_size(vis_size)}) | Total lote: {selected_count} ({format_size(selected_size)})"
            )
        else:
            self.lbl_selection.setText(f"{selected_count} seleccionados ({format_size(selected_size)})")


