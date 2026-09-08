"""
Prueba de integración de UI para el modo DEMO (MainWindow con is_demo=True).
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui.main_window import MainWindow

def test_demo_ui():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    window = MainWindow(is_demo=True)
    assert window.is_demo is True, "is_demo debe ser True"
    assert window.demo_banner is not None, "demo_banner debe estar instanciado"
    assert "DEMO" in window.windowTitle(), "El título de la ventana debe contener DEMO"
    
    print("[OK] MainWindow(is_demo=True) instanciado correctamente con banner y titulo.")
    window.close()
    print("PASS: test_demo_ui completado con exito.")

if __name__ == "__main__":
    test_demo_ui()
