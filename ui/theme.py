"""
Tema visual y estilos QSS modernos para el Recuperador de Datos.
Paleta inspirada en herramientas profesionales de ciberseguridad y análisis forense.
"""

DARK_THEME_QSS = """
/* Ventana principal y fondos */
QMainWindow, QDialog {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: transparent;
    color: #e6edf3;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    font-size: 13px;
}

/* Tarjetas y Contenedores */
QFrame#Card, QWidget#Card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px;
}

QGroupBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 24px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    color: #58a6ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #161b22;
}

/* Botones */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}

/* Botón Primario (Llamada a la acción) */
QPushButton#PrimaryButton {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
    font-weight: bold;
    font-size: 14px;
    padding: 10px 24px;
    border-radius: 6px;
}

QPushButton#PrimaryButton:hover {
    background-color: #2ea043;
    border-color: #3fb950;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1b6a2c;
}

/* Botón de Peligro / Cancelar */
QPushButton#DangerButton {
    background-color: #da3633;
    color: #ffffff;
    border: 1px solid #f85149;
    font-weight: 500;
}

QPushButton#DangerButton:hover {
    background-color: #f85149;
}

/* Botón de Administrador */
QPushButton#AdminButton {
    background-color: #1f6feb;
    color: #ffffff;
    border: 1px solid #388bfd;
    font-weight: 600;
    padding: 8px 16px;
}

QPushButton#AdminButton:hover {
    background-color: #388bfd;
}

/* Campos de entrada y desplegables */
QLineEdit, QComboBox, QSpinBox {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #58a6ff;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #30363d;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

/* Tablas */
QTableWidget {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    gridline-color: #21262d;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 6px 8px;
}

QTableWidget::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}

QTableWidget::item:hover {
    background-color: #161b22;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #30363d;
    font-weight: bold;
    text-align: left;
}

/* Pestañas (QTabWidget) */
QTabWidget::pane {
    border: 1px solid #30363d;
    background-color: #161b22;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #0d1117;
    color: #8b949e;
    border: 1px solid #30363d;
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #161b22;
    color: #58a6ff;
    border-top: 2px solid #58a6ff;
}

QTabBar::tab:hover:!selected {
    background-color: #21262d;
    color: #c9d1d9;
}

/* Barra de progreso */
QProgressBar {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #238636;
    border-radius: 5px;
}

/* Checkboxes y RadioButtons */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #e6edf3;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 4px;
}

QRadioButton::indicator {
    border-radius: 9px;
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #1f6feb;
    border-color: #58a6ff;
}

/* Barras de desplazamiento (Scrollbars) */
QScrollBar:vertical {
    background-color: #0d1117;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #58a6ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0d1117;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #30363d;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #58a6ff;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Visor de texto y logs */
QTextEdit, QPlainTextEdit {
    background-color: #090d13;
    color: #7ee787;
    border: 1px solid #30363d;
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
}

/* Barra de estado */
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #30363d;
}
"""

