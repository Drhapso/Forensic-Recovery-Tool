"""
Módulo de Verificación de Entorno y Requisitos del Sistema para Windows.
Comprueba componentes esenciales (.NET Framework, Visual C++ Redistributable,
arquitectura de 64 bits y librerías dinámicas de Qt) y despliega un cuadro de diálogo
informativo nativo de Windows (Win32) a prueba de fallos si faltase algún complemento.
"""

import os
import sys
import platform
import ctypes
try:
    import winreg
except ImportError:
    winreg = None
from typing import Dict, Any, List, Tuple


class EnvironmentChecker:
    """
    Verificador preventivo de requisitos mínimos de ejecución.
    Garantiza que el ejecutable disponga de los runtimes necesarios (.NET, VC++, Qt)
    y previene cierres silenciosos informando al usuario con ventanas emergentes claras.
    """

    VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    DOTNET_URL = "https://dotnet.microsoft.com/download/dotnet-framework"

    @classmethod
    def check_visual_cpp_redist(cls) -> Tuple[bool, str]:
        """Verifica la presencia de Microsoft Visual C++ 2015-2022 Redistributable (x64 en Windows)."""
        if sys.platform != "win32" or winreg is None:
            return True, "Entorno Linux/POSIX detectado (Runtimes C nativos GNU/glibc)"

        # Método 1: Búsqueda en Registro de Windows
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64")
        ]
        for root, subkey in reg_paths:
            try:
                with winreg.OpenKey(root, subkey) as key:
                    installed, _ = winreg.QueryValueEx(key, "Installed")
                    if installed == 1:
                        ver, _ = winreg.QueryValueEx(key, "Version")
                        return True, f"Visual C++ 2015-2022 x64 instalado (v{ver})"
            except Exception:
                pass

        # Método 2: Verificación de DLLs en System32
        sys32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
        vc_dll = os.path.join(sys32, "vcruntime140.dll")
        msvcp_dll = os.path.join(sys32, "msvcp140.dll")
        if os.path.exists(vc_dll) and os.path.exists(msvcp_dll):
            return True, "Bibliotecas de tiempo de ejecución VC++ 14.x presentes en System32"

        return False, "Falta Microsoft Visual C++ 2015-2022 Redistributable (x64)"

    @classmethod
    def check_dotnet_framework(cls) -> Tuple[bool, str]:
        """Verifica Microsoft .NET Framework (versión 4.5 o superior requerida para componentes COM/VSS en Windows)."""
        if sys.platform != "win32" or winreg is None:
            return True, "Entorno Linux/POSIX detectado (.NET no requerido)"

        reg_key = r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key) as key:
                release, _ = winreg.QueryValueEx(key, "Release")
                # 378389 corresponde a .NET 4.5
                # 528040 corresponde a .NET 4.8 (estándar en Win10/11)
                if release >= 378389:
                    return True, f".NET Framework 4.5+ verificado (Release {release})"
                else:
                    return False, f"Versión de .NET Framework obsoleta (Release {release})"
        except Exception:
            pass

        # Si no se lee la clave Full, comprobar si existe mscoree.dll en System32
        mscoree = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "mscoree.dll")
        if os.path.exists(mscoree):
            return True, ".NET Framework Runtime detectado en el sistema"

        return False, "Falta Microsoft .NET Framework 4.5 o superior"

    @classmethod
    def check_os_architecture(cls) -> Tuple[bool, str]:
        """Verifica que el sistema operativo sea de 64 bits (Windows o Linux)."""
        is_64 = sys.maxsize > 2**32 or "64" in platform.machine()
        os_name = platform.system()
        release = platform.release()
        if is_64 and os_name in ("Windows", "Linux"):
            return True, f"{os_name} {release} (64 bits - {platform.machine()})"
        return False, f"Arquitectura no compatible: {os_name} ({platform.machine()})"

    @classmethod
    def check_qt_runtime(cls) -> Tuple[bool, str]:
        """Verifica la carga correcta de PyQt5 y componentes de interfaz."""
        try:
            from PyQt5 import QtCore, QtGui, QtWidgets
            return True, f"Motor gráfico PyQt5 v{QtCore.PYQT_VERSION_STR} operativo"
        except Exception as e:
            return False, f"Fallo al inicializar librerías de interfaz Qt: {e}"

    @classmethod
    def run_preflight_checks(cls, show_dialog_on_fail: bool = True) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Ejecuta la batería preventiva de diagnóstico de entorno.
        Retorna: (todo_correcto, lista_de_resultados)
        """
        checks = [
            {"name": "Arquitectura de Windows (64-bit)", "checker": cls.check_os_architecture, "critical": True},
            {"name": "Visual C++ Redistributable (2015-2022 x64)", "checker": cls.check_visual_cpp_redist, "critical": True},
            {"name": "Microsoft .NET Framework (4.5+)", "checker": cls.check_dotnet_framework, "critical": False},
            {"name": "Entorno Gráfico PyQt5 / Multimedia", "checker": cls.check_qt_runtime, "critical": True},
        ]

        results = []
        has_critical_failure = False

        for c in checks:
            ok, msg = c["checker"]()
            results.append({
                "name": c["name"],
                "ok": ok,
                "msg": msg,
                "critical": c["critical"]
            })
            if not ok and c["critical"]:
                has_critical_failure = True

        if has_critical_failure and show_dialog_on_fail:
            cls.show_error_dialog(results)

        return not has_critical_failure, results

    @classmethod
    def show_error_dialog(cls, check_results: List[Dict[str, Any]], custom_error: str = "") -> None:
        """
        Despliega un cuadro de diálogo nativo de Windows (Win32 MessageBoxW) a prueba de fallos.
        Se ejecuta incluso si PyQt5 o los runtimes de C++ no han podido cargar.
        """
        title = "Recuperador de Datos - Requisitos del Sistema"

        body_lines = [
            "No se han podido verificar algunos complementos necesarios para ejecutar la herramienta en este equipo.",
            "",
            "DIAGNÓSTICO DE COMPONENTES:"
        ]

        missing_vc = False
        missing_dotnet = False

        for r in check_results:
            icon = "✅" if r["ok"] else ("❌ [FALTA]" if r["critical"] else "⚠️ [RECOMENDADO]")
            body_lines.append(f" {icon} {r['name']}: {r['msg']}")
            if not r["ok"]:
                if "Visual C++" in r["name"]:
                    missing_vc = True
                elif ".NET" in r["name"]:
                    missing_dotnet = True

        if custom_error:
            body_lines.extend(["", f"Detalle adicional del error: {custom_error}"])

        body_lines.extend([
            "",
            "SOLUCIÓN Y DESCARGAS OFICIALES DE MICROSOFT:",
        ])

        if missing_vc:
            body_lines.append(f"• Microsoft Visual C++ 2015-2022 (x64):\n  {cls.VC_REDIST_URL}")
        if missing_dotnet:
            body_lines.append(f"• Microsoft .NET Framework 4.8:\n  {cls.DOTNET_URL}")

        body_lines.extend([
            "",
            "Por favor, instale los paquetes faltantes y vuelva a ejecutar el programa.",
            "La herramienta requiere Windows 10/11 de 64 bits para operar en modo forense."
        ])

        full_message = "\n".join(body_lines)

        # Usar Win32 API MessageBoxW en Windows
        if sys.platform == "win32" and hasattr(ctypes, "windll"):
            try:
                ctypes.windll.user32.MessageBoxW(0, full_message, title, 0x10 | 0x10000)
                return
            except Exception:
                pass

        # Fallback en consola estándar si no es Windows o si Win32 fallase
        print("\n" + "=" * 70, file=sys.stderr)
        print(f"ERROR: {title}", file=sys.stderr)
        print(full_message, file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)


if __name__ == "__main__":
    passed, diag = EnvironmentChecker.run_preflight_checks(show_dialog_on_fail=False)
    print("Environment Diagnostic Result:", "PASSED" if passed else "FAILED")
    for item in diag:
        status = "OK" if item["ok"] else "FAIL"
        print(f" - [{status}] {item['name']}: {item['msg']}")

