"""
Script de compilación automatizada a ejecutable autónomo (ELF / App) para Linux (Bazzite / Debian / Ubuntu / Fedora).
Empaqueta toda la suite forense con PyInstaller para generar un ejecutable portable independiente
que se puede ejecutar con doble clic o desde terminal en cualquier distribución Linux de 64 bits.
"""

import os
import sys
import shutil
import subprocess
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def clean_previous_builds():
    """Limpia directorios de compilación previos."""
    for folder in ["build", "dist"]:
        folder_path = os.path.join(BASE_DIR, folder)
        if os.path.exists(folder_path):
            print(f"Limpiando carpeta previa: {folder}/")
            try:
                shutil.rmtree(folder_path, ignore_errors=True)
            except Exception as e:
                print(f"Aviso al limpiar {folder}: {e}")

def build_executable_linux(onefile: bool = True, console: bool = False):
    """Ejecuta PyInstaller con configuraciones adaptadas a Linux / POSIX."""
    print("=" * 70)
    print(" 🐧 COMPILADOR AUTÓNOMO: RECUPERADOR DE DATOS FORENSE (LINUX / BAZZITE)")
    print("=" * 70)

    # Asegurar que existan las carpetas requeridas
    for sub in ["data", "sessions"]:
        os.makedirs(os.path.join(BASE_DIR, sub), exist_ok=True)

    clean_previous_builds()

    app_name = "RecuperadorDeDatos"
    entry_point = os.path.join(BASE_DIR, "main.py")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", app_name,
        "--clean",
        "--noconfirm",
    ]

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    if console:
        cmd.append("--console")
    else:
        cmd.append("--windowed")

    # Carpetas de datos con separador POSIX (:)
    data_folders = ["core", "ui", "data", "sessions"]
    for folder in data_folders:
        src = os.path.join(BASE_DIR, folder)
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src}:{folder}"])

    # Hidden imports para Linux (sin winreg)
    hidden_imports = [
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.QtMultimedia",
        "PyQt5.QtMultimediaWidgets",
        "PIL",
        "PIL.Image",
        "PIL.ExifTags",
        "sqlite3",
        "ctypes",
        "hashlib",
        "zipfile",
        "xml.etree.ElementTree"
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    cmd.append(entry_point)

    print("\nIniciando compilación con PyInstaller en Linux...")
    print(f"Destino: dist/{app_name}\n")

    start_time = time.time()
    result = subprocess.run(cmd, cwd=BASE_DIR)
    elapsed = time.time() - start_time

    if result.returncode == 0:
        exe_path = os.path.join(BASE_DIR, "dist", app_name)
        if os.path.exists(exe_path):
            try:
                os.chmod(exe_path, 0o755)
            except Exception:
                pass
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print("\n" + "=" * 70)
            print(" 🎉 ¡COMPILACIÓN EXITOSA PARA LINUX / BAZZITE!")
            print("=" * 70)
            print(f"Ejecutable generado: {exe_path}")
            print(f"Tamaño final: {size_mb:.2f} MB")
            print(f"Tiempo: {elapsed:.1f} segundos")
            print("\nPara ejecutar:")
            print(f"  chmod +x dist/{app_name}")
            print(f"  ./dist/{app_name}")
            print("=" * 70)
        return True
    else:
        print(f"\n❌ Error durante la compilación. Código de salida: {result.returncode}")
        return False

if __name__ == "__main__":
    is_onefile = "--onedir" not in sys.argv
    is_console = "--console" in sys.argv
    success = build_executable_linux(onefile=is_onefile, console=is_console)
    sys.exit(0 if success else 1)

