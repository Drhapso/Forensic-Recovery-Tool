"""
Diálogo de Gestión y Restauración de Sesiones Guardadas.
Permite explorar sesiones históricas, cargarlas directamente a la tabla de resultados,
renombrarlas o eliminarlas sin tener que reescanear los discos.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QInputDialog, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from core.session_manager import SessionManager
from core.disk_utils import format_size

class SessionDialog(QDialog):
    """Diálogo modal para cargar, administrar y reanudar sesiones guardadas."""

    session_loaded = pyqtSignal(dict)  # Emite el diccionario de la sesión seleccionada
    new_session_requested = pyqtSignal()  # Solicita iniciar una nueva sesión limpia

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestor de Sesiones de Exploración Guardadas")
        self.resize(850, 480)
        self.sessions = []
        self._init_ui()
        self.refresh_sessions()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Encabezado
        lbl_title = QLabel("📂 SESIONES DE EXPLORACIÓN GUARDADAS")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel("Seleccione una sesión previa para restaurar los archivos encontrados o reanudar el análisis.")
        lbl_desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(lbl_desc)

        # Tabla de Sesiones
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Nombre de Sesión", "Fecha de Actualización", "Archivos", "Tamaño Total", "Modo", "Ubicaciones Analizadas"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 220)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.setColumnWidth(1, 150)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 90)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(3, 100)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        self.table.setColumnWidth(4, 110)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

        self.table.itemDoubleClicked.connect(self._on_load_clicked)
        layout.addWidget(self.table)

        # Barra de Botones
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_load = QPushButton("📂 Cargar Sesión en Tabla")
        self.btn_load.setObjectName("PrimaryButton")
        self.btn_load.clicked.connect(self._on_load_clicked)
        btn_bar.addWidget(self.btn_load)

        self.btn_rename = QPushButton("✏️ Renombrar...")
        self.btn_rename.clicked.connect(self._on_rename_clicked)
        btn_bar.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("🗑️ Eliminar")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        btn_bar.addWidget(self.btn_delete)

        self.btn_clear_all = QPushButton("🧹 Purgar Todo...")
        self.btn_clear_all.setToolTip("Eliminar todas las sesiones archivadas en disco para comenzar completamente de cero.")
        self.btn_clear_all.clicked.connect(self._on_clear_all_clicked)
        btn_bar.addWidget(self.btn_clear_all)

        btn_bar.addStretch()

        self.btn_new_session = QPushButton("➕ Iniciar Sesión Limpia")
        self.btn_new_session.setToolTip("Cerrar este diálogo y comenzar una nueva sesión de recuperación limpia.")
        self.btn_new_session.setStyleSheet("background-color: #21262d; border: 1px solid #388bfd; color: #58a6ff; font-weight: bold;")
        self.btn_new_session.clicked.connect(self._on_new_session_clicked)
        btn_bar.addWidget(self.btn_new_session)

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_close)

        layout.addLayout(btn_bar)

    def refresh_sessions(self):
        """Recarga la lista de sesiones desde disco."""
        self.sessions = SessionManager.list_saved_sessions()
        self.table.setRowCount(0)

        for s in self.sessions:
            row = self.table.rowCount()
            self.table.insertRow(row)

            name_item = QTableWidgetItem(s.get("name", "Sin Nombre"))
            name_item.setData(Qt.UserRole, s)
            name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            date_item = QTableWidgetItem(s.get("updated_at", "-"))
            date_item.setFlags(date_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 1, date_item)

            count_item = QTableWidgetItem(f"{s.get('total_items', 0):,}")
            count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            count_item.setFlags(count_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 2, count_item)

            size_item = QTableWidgetItem(format_size(s.get("total_size", 0)))
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            size_item.setFlags(size_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 3, size_item)

            mode_item = QTableWidgetItem(s.get("mode", "-"))
            mode_item.setFlags(mode_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 4, mode_item)

            targets_str = ", ".join(s.get("targets", [])) or "Todas"
            targets_item = QTableWidgetItem(targets_str)
            targets_item.setFlags(targets_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 5, targets_item)

        if self.sessions:
            self.table.selectRow(0)

    def _get_selected_session_meta(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return None
        row = selected_ranges[0].topRow()
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _on_load_clicked(self):
        meta = self._get_selected_session_meta()
        if not meta:
            QMessageBox.warning(self, "Sin Selección", "Seleccione una sesión de la tabla para cargar.")
            return

        full_session = SessionManager.load_session(meta["filepath"])
        if full_session:
            self.session_loaded.emit(full_session)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "No se pudo leer el archivo de la sesión.")

    def _on_rename_clicked(self):
        meta = self._get_selected_session_meta()
        if not meta:
            return

        current_name = meta.get("name", "")
        new_name, ok = QInputDialog.getText(self, "Renombrar Sesión", "Nuevo nombre de la sesión:", text=current_name)
        if ok and new_name.strip():
            full_session = SessionManager.load_session(meta["filepath"])
            if full_session:
                full_session["name"] = new_name.strip()
                SessionManager.save_session(
                    name=new_name.strip(),
                    items=full_session.get("items", []),
                    targets=full_session.get("targets", []),
                    categories=full_session.get("categories", []),
                    mode=full_session.get("mode", ""),
                    session_id=full_session.get("session_id")
                )
                self.refresh_sessions()

    def _on_delete_clicked(self):
        meta = self._get_selected_session_meta()
        if not meta:
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Desea eliminar permanentemente la sesión '{meta.get('name')}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            SessionManager.delete_session(meta["filepath"])
            self.refresh_sessions()

    def _on_new_session_clicked(self):
        """Solicita iniciar una nueva sesión limpia cerrando este diálogo."""
        self.new_session_requested.emit()
        self.accept()

    def _on_clear_all_clicked(self):
        """Elimina permanentemente todas las sesiones archivadas tras confirmación."""
        if not self.sessions:
            QMessageBox.information(self, "Historial Vacío", "No hay sesiones guardadas en el historial.")
            return

        reply = QMessageBox.warning(
            self,
            "Confirmar Purga Total",
            "¿Está seguro de que desea eliminar permanentemente todas las sesiones guardadas en disco?\n\n"
            "Esta acción no se puede deshacer y el escáner incremental no reutilizará índices pasados.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            count = SessionManager.clear_all_sessions()
            self.refresh_sessions()
            QMessageBox.information(
                self,
                "Historial Limpiado",
                f"Se han eliminado exitosamente {count} sesión(es) guardadas."
            )


