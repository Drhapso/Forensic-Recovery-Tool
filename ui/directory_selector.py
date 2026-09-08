r"""
Componente interactivo para Selección de Alcance de Indexación.
Muestra directamente un listado de carpetas y unidades para recuperación con casillas
de verificación interactivas, barra de herramientas y sincronización contextual.
"""

import os
from typing import List, Set
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFileDialog, QMessageBox,
    QAbstractItemView, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from core.context_router import ContextRouter
from core.disk_utils import get_drives, format_size


class ScopeRadioProxy:
    """Proxy para compatibilidad hacia atrás con código o tests que consulten rb_auto/rb_manual/rb_drive."""
    def __init__(self, selector: 'DirectorySelector', mode: str):
        self._selector = selector
        self._mode = mode

    def isChecked(self) -> bool:
        if self._mode == "auto":
            return self._selector._is_auto_mode
        elif self._mode == "manual":
            return not self._selector._is_auto_mode
        elif self._mode == "drive":
            return self._selector.has_drive_selected()
        return False

    def setChecked(self, value: bool):
        if value:
            if self._mode == "auto":
                self._selector.select_recommended_only()
            elif self._mode == "manual":
                self._selector._is_auto_mode = False
            elif self._mode == "drive":
                self._selector.select_drives_only()


class DirectorySelector(QWidget):
    """Listado directo e interactivo de carpetas y unidades de recuperación sin menú desplegable."""

    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_categories = ["Imágenes", "Documentos", "Audio", "Video", "Comprimidos"]
        self.custom_folders: List[str] = []
        self._is_auto_mode = True
        self._is_populating = False

        # Combo interno oculto solo para compatibilidad con código legacy
        self.combo_scope = QComboBox()
        self.combo_scope.addItem("auto", "auto")
        self.combo_scope.addItem("manual", "manual")
        self.combo_scope.addItem("drive", "drive")

        self._init_ui()

        # Proxies para compatibilidad
        self.rb_auto = ScopeRadioProxy(self, "auto")
        self.rb_manual = ScopeRadioProxy(self, "manual")
        self.rb_drive = ScopeRadioProxy(self, "drive")

        self.rebuild_folder_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Fila 1: Título y ayuda breve del listado
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        lbl_header = QLabel("📁 Carpetas y Unidades para Recuperación:")
        lbl_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #58a6ff;")
        header_row.addWidget(lbl_header)

        header_row.addStretch()

        self.lbl_counter_badge = QLabel("0 seleccionadas")
        self.lbl_counter_badge.setStyleSheet("font-size: 11px; color: #7ee787; font-weight: bold;")
        header_row.addWidget(self.lbl_counter_badge)

        layout.addLayout(header_row)

        # Fila 2: Listado Embebido Directo de Carpetas (QListWidget con Checkboxes)
        self.list_folders = QListWidget()
        self.list_folders.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_folders.setMinimumHeight(140)
        self.list_folders.setMaximumHeight(190)
        self.list_folders.setStyleSheet("""
            QListWidget {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px 6px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #161b22;
            }
            QListWidget::item:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }
        """)
        self.list_folders.itemChanged.connect(self._on_item_changed)
        self.list_folders.itemDoubleClicked.connect(self.select_single_item)
        layout.addWidget(self.list_folders)

        # Fila 3: Barra de Herramientas de Acciones Rápidas
        btn_toolbar = QHBoxLayout()
        btn_toolbar.setSpacing(6)

        btn_style = """
            QPushButton {
                font-size: 11px;
                padding: 4px 8px;
                border-radius: 4px;
                background-color: #21262d;
                border: 1px solid #30363d;
                color: #c9d1d9;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #ffffff;
                border-color: #58a6ff;
            }
        """

        self.btn_add_folder = QPushButton("➕ Añadir...")
        self.btn_add_folder.setToolTip("Agregar una carpeta personalizada del sistema para escanear.")
        self.btn_add_folder.setStyleSheet(btn_style)
        self.btn_add_folder.clicked.connect(self._browse_custom_folder)
        btn_toolbar.addWidget(self.btn_add_folder)

        self.btn_remove_folder = QPushButton("➖ Quitar")
        self.btn_remove_folder.setToolTip("Quitar la carpeta personalizada seleccionada del listado.")
        self.btn_remove_folder.setStyleSheet(btn_style)
        self.btn_remove_folder.clicked.connect(self._remove_custom_folder)
        btn_toolbar.addWidget(self.btn_remove_folder)

        self.btn_recommended = QPushButton("🎯 Recomendadas")
        self.btn_recommended.setToolTip("Marcar las carpetas recomendadas según los tipos de archivo seleccionados.")
        self.btn_recommended.setStyleSheet(btn_style)
        self.btn_recommended.clicked.connect(self.select_recommended_only)
        btn_toolbar.addWidget(self.btn_recommended)

        self.btn_isolate = QPushButton("🎯 Solo Esta")
        self.btn_isolate.setToolTip("Desmarca todo y activa exclusivamente la carpeta o unidad seleccionada.")
        self.btn_isolate.setStyleSheet(btn_style)
        self.btn_isolate.clicked.connect(lambda: self.select_single_item())
        btn_toolbar.addWidget(self.btn_isolate)

        btn_toolbar.addStretch()

        self.btn_select_all = QPushButton("✔ Todas")
        self.btn_select_all.setToolTip("Marcar todas las carpetas y unidades del listado.")
        self.btn_select_all.setStyleSheet(btn_style)
        self.btn_select_all.clicked.connect(lambda: self._set_all_checks(True))
        btn_toolbar.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("✖ Ninguna")
        self.btn_deselect_all.setToolTip("Desmarcar todas las carpetas del listado.")
        self.btn_deselect_all.setStyleSheet(btn_style)
        self.btn_deselect_all.clicked.connect(lambda: self._set_all_checks(False))
        btn_toolbar.addWidget(self.btn_deselect_all)

        layout.addLayout(btn_toolbar)

        # Fila 4: Etiqueta de Resumen del Alcance
        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.lbl_summary)

    def rebuild_folder_list(self, previously_checked: Set[str] = None):
        """
        Reconstruye el listado directo con carpetas del sistema, unidades y carpetas personalizadas.
        Si previously_checked es None, marca automáticamente las recomendadas.
        """
        self._is_populating = True
        self.list_folders.blockSignals(True)
        self.list_folders.clear()

        suggested = ContextRouter.get_suggested_folders(self.active_categories)
        drives = get_drives()

        # 1. Carpetas del Sistema / Usuario
        for folder in suggested:
            path = folder["path"]
            if not os.path.exists(path):
                continue

            rec = folder["recommended"]
            if previously_checked is not None:
                checked = path in previously_checked
            else:
                checked = rec

            badge = " 🎯" if rec else ""
            item_text = f"{folder['icon']} {folder['name']}{badge}"

            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            item.setData(Qt.UserRole, path)
            item.setData(Qt.UserRole + 1, False)  # is_custom = False
            item.setData(Qt.UserRole + 2, False)  # is_drive = False
            item.setData(Qt.UserRole + 3, rec)    # is_recommended = rec

            item.setToolTip(f"{folder['name']}\nRuta en disco: {path}\nRelevancia: {'Recomendada para tipos activos' if rec else folder['category_tag']}")
            self.list_folders.addItem(item)

        # 2. Carpetas Personalizadas Añadidas por el Usuario
        for cpath in self.custom_folders:
            if not os.path.exists(cpath):
                continue

            checked = (cpath in previously_checked) if previously_checked is not None else True
            item_text = f"➕ {os.path.basename(cpath) or cpath} (Personalizada)"

            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            item.setData(Qt.UserRole, cpath)
            item.setData(Qt.UserRole + 1, True)   # is_custom = True
            item.setData(Qt.UserRole + 2, False)  # is_drive = False
            item.setData(Qt.UserRole + 3, False)  # is_recommended = False

            item.setToolTip(f"Carpeta Personalizada:\n{cpath}")
            self.list_folders.addItem(item)

        # 3. Unidades del Sistema (Particiones de Disco)
        for d in drives:
            d_letter = d["letter"]
            free_str = format_size(d["free_bytes"])
            total_str = format_size(d["total_bytes"])
            item_text = f"💽 Unidad {d_letter} ({d['drive_name']}) [{d['type']}]"

            checked = (d_letter in previously_checked) if previously_checked is not None else False

            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            item.setData(Qt.UserRole, d_letter)
            item.setData(Qt.UserRole + 1, False)  # is_custom = False
            item.setData(Qt.UserRole + 2, True)   # is_drive = True
            item.setData(Qt.UserRole + 3, False)  # is_recommended = False

            item.setToolTip(f"Unidad de Disco {d_letter}\nNombre: {d['drive_name']}\nEspacio: {free_str} libre de {total_str}")
            self.list_folders.addItem(item)

        self.list_folders.blockSignals(False)
        self._is_populating = False

        self._update_summary()

    def select_single_item(self, target_item: QListWidgetItem = None):
        """Desmarca todo y deja marcada exclusivamente la carpeta o unidad indicada."""
        if target_item is None:
            target_item = self.list_folders.currentItem()
        if not target_item:
            return

        self._is_populating = True
        self.list_folders.blockSignals(True)
        for i in range(self.list_folders.count()):
            it = self.list_folders.item(i)
            if it is target_item:
                it.setCheckState(Qt.Checked)
            else:
                it.setCheckState(Qt.Unchecked)
        self.list_folders.blockSignals(False)
        self._is_populating = False
        self._is_auto_mode = False
        self._update_summary()
        self.selection_changed.emit()

    def _on_item_changed(self, item: QListWidgetItem):
        if self._is_populating:
            return
        self._is_auto_mode = False
        self._update_summary()
        self.selection_changed.emit()

    def _update_summary(self):
        paths = self.get_target_paths()
        count = len(paths)
        self.lbl_counter_badge.setText(f"{count} activa(s)")

        if count == 0:
            self.lbl_summary.setText("⚠️ Ninguna carpeta seleccionada. Marque al menos una ubicación para recuperar.")
            self.lbl_summary.setStyleSheet("color: #e3b341; font-size: 11px;")
        else:
            names = []
            drives_in_paths = set()
            for i in range(self.list_folders.count()):
                it = self.list_folders.item(i)
                if it.checkState() == Qt.Checked:
                    clean_name = it.text().split(" [")[0].replace("📄 ", "").replace("🖥️ ", "").replace("📥 ", "").replace("🖼️ ", "").replace("🎵 ", "").replace("🎬 ", "").replace("💾 ", "").replace("💽 ", "").replace("➕ ", "")
                    names.append(clean_name)
                    p = it.data(Qt.UserRole)
                    if p and len(p) >= 2 and p[1] == ":":
                        drives_in_paths.add(p[:2].upper())
            preview_str = ", ".join(names[:2])
            if count > 2:
                preview_str += f" y {count - 2} más"

            if len(drives_in_paths) > 1:
                self.lbl_summary.setText(f"🎯 {count} ubicaciones ({preview_str}). ⚠️ Advertencia: {len(drives_in_paths)} unidades distintas activas ({', '.join(sorted(drives_in_paths))}).")
                self.lbl_summary.setStyleSheet("color: #e3b341; font-size: 11px;")
            else:
                self.lbl_summary.setText(f"🎯 {count} ubicación(es) lista(s) ({preview_str}).")
                self.lbl_summary.setStyleSheet("color: #7ee787; font-size: 11px;")

    def _browse_custom_folder(self):
        """Abre un explorador para añadir una carpeta adicional al listado."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Carpeta para Recuperación",
            os.path.expanduser("~")
        )
        if folder:
            norm = os.path.normpath(folder)
            if norm not in self.custom_folders:
                self.custom_folders.append(norm)
                curr_checked = set(self.get_target_paths())
                curr_checked.add(norm)
                self.rebuild_folder_list(previously_checked=curr_checked)
                self.selection_changed.emit()

    def _remove_custom_folder(self):
        """Elimina la carpeta personalizada actualmente seleccionada en el listado."""
        curr = self.list_folders.currentItem()
        if not curr:
            QMessageBox.information(
                self,
                "Quitar Carpeta",
                "Seleccione primero en la lista la carpeta personalizada que desea quitar."
            )
            return

        is_custom = curr.data(Qt.UserRole + 1)
        path = curr.data(Qt.UserRole)
        if not is_custom:
            QMessageBox.information(
                self,
                "Carpeta del Sistema",
                "Las carpetas estándar y unidades del sistema no se eliminan de la lista; puede desmarcarlas usando su casilla de verificación."
            )
            return

        if path in self.custom_folders:
            self.custom_folders.remove(path)
            curr_checked = set(self.get_target_paths())
            curr_checked.discard(path)
            self.rebuild_folder_list(previously_checked=curr_checked)
            self.selection_changed.emit()

    def select_recommended_only(self):
        """Marca exclusivamente las carpetas recomendadas por las categorías activas."""
        self._is_populating = True
        self.list_folders.blockSignals(True)
        for i in range(self.list_folders.count()):
            it = self.list_folders.item(i)
            is_rec = bool(it.data(Qt.UserRole + 3))
            it.setCheckState(Qt.Checked if is_rec else Qt.Unchecked)
        self.list_folders.blockSignals(False)
        self._is_populating = False
        self._is_auto_mode = True
        self._update_summary()
        self.selection_changed.emit()

    def select_drives_only(self):
        """Marca exclusivamente las unidades de disco (para compatibilidad de modo drive)."""
        self._is_populating = True
        self.list_folders.blockSignals(True)
        for i in range(self.list_folders.count()):
            it = self.list_folders.item(i)
            is_drive = bool(it.data(Qt.UserRole + 2))
            it.setCheckState(Qt.Checked if is_drive else Qt.Unchecked)
        self.list_folders.blockSignals(False)
        self._is_populating = False
        self._is_auto_mode = False
        self._update_summary()
        self.selection_changed.emit()

    def _set_all_checks(self, checked: bool):
        """Marca o desmarca todos los elementos del listado."""
        self._is_populating = True
        self.list_folders.blockSignals(True)
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.list_folders.count()):
            it = self.list_folders.item(i)
            it.setCheckState(state)
        self.list_folders.blockSignals(False)
        self._is_populating = False
        self._is_auto_mode = False
        self._update_summary()
        self.selection_changed.emit()

    def has_drive_selected(self) -> bool:
        """Indica si al menos una unidad de disco completa está marcada."""
        for i in range(self.list_folders.count()):
            it = self.list_folders.item(i)
            if it.checkState() == Qt.Checked and bool(it.data(Qt.UserRole + 2)):
                return True
        return False

    def is_recommended_mode(self) -> bool:
        return self._is_auto_mode

    def update_categories(self, active_categories: List[str]):
        """Actualiza las recomendaciones dinámicas según los tipos de archivo seleccionados."""
        self.active_categories = active_categories
        curr_checked = set(self.get_target_paths())
        self.rebuild_folder_list(previously_checked=curr_checked if not self._is_auto_mode else None)
        self.selection_changed.emit()

    def refresh_drives(self):
        """Actualiza la lista de unidades del sistema manteniendo la selección actual."""
        curr_checked = set(self.get_target_paths())
        self.rebuild_folder_list(previously_checked=curr_checked)

    def get_target_paths(self) -> List[str]:
        """Retorna la lista de rutas objetivo a escanear a partir de los elementos marcados."""
        targets = []
        for i in range(self.list_folders.count()):
            it = self.list_folders.item(i)
            if it.checkState() == Qt.Checked:
                path = it.data(Qt.UserRole)
                if path and os.path.exists(path) and path not in targets:
                    targets.append(path)
        return targets
