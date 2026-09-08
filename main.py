"""
Punto de entrada principal para el Recuperador de Datos.
Configura soporte de alta resolución (High DPI) y lanza la interfaz gráfica.
"""

import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

# Asegurar que el directorio raíz del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.env_checker import EnvironmentChecker
from core.local_db import LocalDatabase
from ui.main_window import MainWindow

def exception_hook(exctype, value, tb):
    """Manejador global de excepciones para evitar cierres inesperados sin diagnóstico."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print("EXCEPCIÓN NO CONTROLADA:", err_msg, file=sys.stderr)
    try:
        if QApplication.instance():
            QMessageBox.critical(
                None,
                "Error en la Aplicación",
                f"Ocurrió un error inesperado durante la ejecución:\n\n{value}\n\nConsulte el diagnóstico del sistema para más detalles."
            )
        else:
            EnvironmentChecker.show_error_dialog([], custom_error=str(value))
    except Exception:
        EnvironmentChecker.show_error_dialog([], custom_error=str(value))

def main():
    # 1. Parámetros de línea de comandos auxiliares
    if "--check-env" in sys.argv:
        passed, diag = EnvironmentChecker.run_preflight_checks(show_dialog_on_fail=False)
        print("ESTADO DEL ENTORNO:", "CORRECTO" if passed else "FALLÓ")
        for d in diag:
            icon = "[OK]" if d["ok"] else "[FALTA]"
            print(f" {icon} {d['name']}: {d['msg']}")
        sys.exit(0 if passed else 1)

    if "--init-db" in sys.argv:
        db_path = LocalDatabase.init_db()
        print("Base de datos local inicializada en:", db_path)
        sys.exit(0)

    # 2. Diagnóstico preventivo de entorno (.NET, Visual C++, Arquitectura, Qt)
    env_ok, _ = EnvironmentChecker.run_preflight_checks(show_dialog_on_fail=True)
    if not env_ok:
        sys.exit(1)

    # 3. Autoconstrucción e inicialización de la Base de Datos Local SQLite
    try:
        LocalDatabase.init_db()
    except Exception as e:
        print(f"Advertencia: No se pudo inicializar la base de datos local: {e}", file=sys.stderr)

    # 4. Soporte para pantallas de alta resolución (High-DPI / 4K)
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    app.setApplicationName("RecuperadorDeDatos")
    app.setOrganizationName("DataRecoverySuite")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

