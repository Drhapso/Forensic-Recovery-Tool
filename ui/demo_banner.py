"""
Banner interactivo de cuenta regresiva para la versión DEMO de 24 Horas.
Muestra el tiempo restante en tiempo real, barra de consumo temporal,
indicadores visuales y advertencia de caducidad.
"""

import sys
import os
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QProgressBar, QMessageBox, QDialog, QTextBrowser, QDialogButtonBox,
    QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices
from core.trial_manager import TrialManager, TRIAL_DURATION_SECONDS


class DemoBanner(QFrame):
    """Banner visual que informa al usuario sobre el estado de la prueba de 24 horas."""

    trial_expired = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DemoBanner")
        self.setStyleSheet("""
            QFrame#DemoBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3d1f00, stop:0.5 #2d1600, stop:1 #1c1103);
                border: 1px solid #d29922;
                border-radius: 8px;
                padding: 4px;
            }
        """)

        self._init_ui()

        # Temporizador de actualización cada 1 segundo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_countdown)
        self.timer.start(1000)

        self._update_countdown()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(15)

        # Icono e información
        vbox_info = QVBoxLayout()
        vbox_info.setSpacing(2)

        self.lbl_title = QLabel("⏳ VERSIÓN DE DEMOSTRACIÓN (PRUEBA EVALUATIVA 24H)")
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #f0883e;")

        self.lbl_detail = QLabel("Copia portable temporal. Se autodestruirá e inutilizará de forma permanente al agotarse el tiempo.")
        self.lbl_detail.setStyleSheet("font-size: 11px; color: #c9d1d9;")

        vbox_info.addWidget(self.lbl_title)
        vbox_info.addWidget(self.lbl_detail)
        layout.addLayout(vbox_info, stretch=2)

        # Barra y tiempo restante
        vbox_time = QVBoxLayout()
        vbox_time.setSpacing(4)
        vbox_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.lbl_time = QLabel("Calculando...")
        self.lbl_time.setAlignment(Qt.AlignRight)
        self.lbl_time.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffd33d; font-family: 'Consolas', monospace;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, TRIAL_DURATION_SECONDS)
        self.progress_bar.setValue(TRIAL_DURATION_SECONDS)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #d29922;
                border-radius: 2px;
            }
        """)

        vbox_time.addWidget(self.lbl_time)
        vbox_time.addWidget(self.progress_bar)
        layout.addLayout(vbox_time)

        # Botón de Guía para Testers
        self.btn_guide = QPushButton("🧪 Guía del Tester")
        self.btn_guide.setToolTip("Información de bienvenida, expectativas reales y áreas en desarrollo para evaluadores.")
        self.btn_guide.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #2ea043;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        self.btn_guide.clicked.connect(self._show_tester_guide)
        layout.addWidget(self.btn_guide)

        # Botón de información comercial
        self.btn_buy = QPushButton("💎 Licencia Completa")
        self.btn_buy.setToolTip("Información sobre cómo adquirir la versión comercial permanente sin límites.")
        self.btn_buy.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #388bfd;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #388bfd;
            }
        """)
        self.btn_buy.clicked.connect(self._show_buy_info)
        layout.addWidget(self.btn_buy)

    def _show_tester_guide(self):
        """Muestra la guía completa de bienvenida para evaluadores en una ventana modal y permite abrirla en el navegador."""
        dlg = QDialog(self)
        dlg.setWindowTitle("🧪 Guía de Bienvenida e Introducción para Evaluadores (Beta Testers)")

        screen = QApplication.primaryScreen().availableGeometry() if QApplication.primaryScreen() else None
        dlg_w = min(860, int(screen.width() * 0.85)) if screen else 860
        dlg_h = min(620, int(screen.height() * 0.80)) if screen else 620
        dlg.resize(dlg_w, dlg_h)
        dlg_layout = QVBoxLayout(dlg)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)

        candidate_dirs = [
            getattr(sys, "_MEIPASS", ""),
            os.path.dirname(sys.executable) if hasattr(sys, "executable") else "",
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            os.getcwd(),
        ]

        guide_md_path = None
        guide_html_path = None

        for cdir in candidate_dirs:
            if not cdir:
                continue
            # Buscar archivo markdown
            md_try1 = os.path.join(cdir, "docs", "GUIA_PARA_TESTERS.md")
            md_try2 = os.path.join(cdir, "GUIA_PARA_TESTERS.md")
            if not guide_md_path:
                if os.path.exists(md_try1):
                    guide_md_path = md_try1
                elif os.path.exists(md_try2):
                    guide_md_path = md_try2

            # Buscar archivo HTML responsivo
            html_try1 = os.path.join(cdir, "docs", "guia_testers.html")
            html_try2 = os.path.join(cdir, "guia_testers.html")
            if not guide_html_path:
                if os.path.exists(html_try1):
                    guide_html_path = html_try1
                elif os.path.exists(html_try2):
                    guide_html_path = html_try2

        if guide_md_path and os.path.exists(guide_md_path):
            try:
                with open(guide_md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if hasattr(browser, "setMarkdown"):
                    browser.setMarkdown(content)
                else:
                    browser.setPlainText(content)
            except Exception:
                browser.setPlainText("No se pudo cargar la guía.")
        else:
            browser.setPlainText("Guía para testers no encontrada.")

        dlg_layout.addWidget(browser)

        # Botonera inferior: Botón abrir en navegador + botón cerrar
        btn_layout = QHBoxLayout()
        if guide_html_path and os.path.exists(guide_html_path):
            btn_browser = QPushButton("🌐 Abrir en Navegador Web (HTML Interactivo)")
            btn_browser.setStyleSheet("""
                QPushButton {
                    background-color: #238636;
                    color: #ffffff;
                    font-weight: bold;
                    border: 1px solid #2ea043;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2ea043;
                }
            """)
            target_html = guide_html_path
            btn_browser.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(target_html)))
            btn_layout.addWidget(btn_browser)

        btn_layout.addStretch()

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        ok_btn = btn_box.button(QDialogButtonBox.Ok)
        if ok_btn:
            ok_btn.setText("Cerrar")
        btn_box.accepted.connect(dlg.accept)
        btn_layout.addWidget(btn_box)

        dlg_layout.addLayout(btn_layout)
        dlg.exec_()

    def _update_countdown(self):
        status = TrialManager.check_or_init_trial()
        if status.get("is_expired"):
            self.lbl_time.setText("00h 00m 00s (EXPIRADO)")
            self.progress_bar.setValue(0)
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f85149; }")
            self.timer.stop()
            self.trial_expired.emit()
            return

        remaining = status.get("remaining_seconds", 0)
        formatted = TrialManager.format_remaining_time(remaining)
        self.lbl_time.setText(f"Restante: {formatted}")
        self.progress_bar.setValue(remaining)

        # Advertencia en color rojo en la última hora
        if remaining < 3600:
            self.lbl_time.setStyleSheet("font-size: 14px; font-weight: bold; color: #f85149; font-family: 'Consolas', monospace;")
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f85149; }")

    def _show_buy_info(self):
        from PyQt5.QtWidgets import QInputDialog
        msg = (
            "🛡️ Forensic Data Recovery Suite - Versión Comercial Permanente\n\n"
            "La versión comercial incluye:\n"
            " • Sin límite de tiempo (licencia perpetua).\n"
            " • Recuperación y exportación de archivos ilimitada.\n"
            " • Compatibilidad con unidades físicas en bruto y copias de sombra VSS.\n"
            " • Soporte técnico prioritario y actualizaciones continuas.\n\n"
            "Esta versión preliminar está limitada a 24 horas en este equipo.\n"
            "Las futuras versiones de prueba previas a la comercial dispondrán de su propio ciclo de evaluación.\n\n"
            "¿Desea ingresar una clave de extensión de prueba autorizada por el desarrollador?"
        )
        reply = QMessageBox.question(
            self,
            "Adquirir Licencia Comercial o Extensión",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            key, ok = QInputDialog.getText(self, "Clave de Autorización", "Ingrese la clave de extensión proporcionada por el desarrollador:")
            if ok and key:
                if TrialManager.grant_trial_extension(key.strip()):
                    QMessageBox.information(self, "Extensión Concedida", "✓ Clave validada con éxito.\nSe ha habilitado un nuevo ciclo de evaluación de 24 horas para este equipo.")
                    self._update_countdown()
                    if not self.timer.isActive():
                        self.timer.start(1000)
                else:
                    QMessageBox.warning(self, "Clave Inválida", "La clave ingresada no es válida para este equipo o no coincide.")

