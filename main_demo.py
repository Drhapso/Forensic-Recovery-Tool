"""
Punto de entrada exclusivo para Forensic Recovery DEMO (Versión de Evaluación 24 Horas).
Valida el temporizador de 24 horas antes de inicializar la interfaz gráfica.
Si la prueba ha expirado o se detecta manipulación, bloquea el acceso,
notifica al usuario e inicia la rutina de autodestrucción/autolimpieza física.
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
from core.trial_manager import TrialManager
from ui.main_window import MainWindow


def exception_hook(exctype, value, tb):
    """Manejador global de excepciones para evitar cierres inesperados sin diagnóstico."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print("EXCEPCIÓN NO CONTROLADA (DEMO):", err_msg, file=sys.stderr)
    try:
        if QApplication.instance():
            QMessageBox.critical(
                None,
                "Error en la Aplicación (DEMO)",
                f"Ocurrió un error inesperado durante la ejecución:\n\n{value}\n\nConsulte el diagnóstico del sistema para más detalles."
            )
        else:
            EnvironmentChecker.show_error_dialog([], custom_error=str(value))
    except Exception:
        EnvironmentChecker.show_error_dialog([], custom_error=str(value))


def main():
    # 0. Soporte de extensión por línea de comandos para el desarrollador
    for idx, arg in enumerate(sys.argv[1:]):
        if arg.startswith("--grant-trial-extension="):
            key = arg.split("=", 1)[1]
            if TrialManager.grant_trial_extension(key):
                print("[TrialManager] Extensión de prueba autorizada con éxito.")
                sys.exit(0)
            else:
                print("[TrialManager] Error: Clave de extensión inválida o no coincide con este equipo.")
                sys.exit(1)
        elif arg == "--grant-trial-extension" and idx + 2 < len(sys.argv):
            key = sys.argv[idx + 2]
            if TrialManager.grant_trial_extension(key):
                print("[TrialManager] Extensión de prueba autorizada con éxito.")
                sys.exit(0)
            else:
                print("[TrialManager] Error: Clave de extensión inválida o no coincide con este equipo.")
                sys.exit(1)

    # Parámetros de diagnóstico y mantenimiento (paridad con versión comercial)
    if "--check-env" in sys.argv:
        passed, diag = EnvironmentChecker.run_preflight_checks(show_dialog_on_fail=False)
        print("ESTADO DEL ENTORNO (DEMO):", "CORRECTO" if passed else "FALLÓ")
        for d in diag:
            icon = "[OK]" if d["ok"] else "[FALTA]"
            print(f" {icon} {d['name']}: {d['msg']}")
        sys.exit(0 if passed else 1)

    if "--init-db" in sys.argv:
        db_path = LocalDatabase.init_db()
        print("Base de datos local inicializada en (DEMO):", db_path)
        sys.exit(0)

    # 1. Soporte para pantallas de alta resolución (High-DPI / 4K)
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    app.setApplicationName("ForensicRecoveryDEMO")
    app.setOrganizationName("DataRecoverySuite")

    # 2. Control de Licencia y Temporizador de 24 Horas
    trial_status = TrialManager.check_or_init_trial()

    if trial_status.get("is_expired"):
        reason = trial_status.get("reason", "TIME_LIMIT_EXCEEDED")
        build_tag = trial_status.get("build_tag", "DEMO-v1.0")
        if reason == "CLOCK_ROLLBACK_DETECTED":
            msg = (
                "⚠️ Manipulación de Fecha/Hora Detectada.\n\n"
                "Se detectó un cambio regresivo en el reloj del sistema para alterar el temporizador de evaluación.\n"
                "Esta versión de prueba ha sido bloqueada permanentemente en este equipo.\n\n"
                "El ejecutable se autodestruirá de forma inmediata."
            )
        elif reason == "TOKEN_CLONED_FROM_ANOTHER_MACHINE":
            msg = (
                "⚠️ Firma de Hardware Inválida.\n\n"
                "Este ejecutable de demostración o sus archivos de estado pertenecen a otro equipo.\n"
                "Esta versión de prueba ha sido bloqueada permanentemente.\n\n"
                "El ejecutable se autodestruirá de forma inmediata."
            )
        else:
            msg = (
                f"⏰ Período de Demostración Expirado (24 Horas Agotadas).\n\n"
                f"El período de prueba de 24 horas para la compilación '{build_tag}' ha finalizado en este equipo.\n"
                f"Esta compilación de prueba ha quedado bloqueada e inutilizable.\n\n"
                f"• Si el desarrollador libera una futura versión de prueba (Beta / Preview), podrá probarla en este equipo.\n"
                f"• Para utilizar la herramienta de forma definitiva y sin límites, adquiera la versión comercial completa.\n\n"
                f"El archivo ejecutable actual se autodestruirá de forma segura."
            )

        QMessageBox.critical(
            None,
            f"Forensic Recovery DEMO ({build_tag}) - Licencia Expirada",
            msg
        )
        TrialManager.trigger_self_destruction()
        sys.exit(0)

    # 3. Diagnóstico preventivo de entorno (.NET, Visual C++, Arquitectura, Qt)
    env_ok, _ = EnvironmentChecker.run_preflight_checks(show_dialog_on_fail=True)
    if not env_ok:
        sys.exit(1)

    # 4. Inicialización de Base de Datos Local
    try:
        LocalDatabase.init_db()
    except Exception as e:
        print(f"Advertencia: No se pudo inicializar la base de datos local: {e}", file=sys.stderr)

    # 5. Iniciar Ventana Principal en Modo Demostración
    window = MainWindow(is_demo=True)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

