"""
Script de compilación automatizada para la edición de demostración:
Forensic_Recovery_DEMO.exe (Windows 64-bit).
Genera un ejecutable portable autónomo (.exe) equipado con el temporizador
inviolable de 24 horas y rutina de autodestrucción/autolimpieza para distribución comercial.
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
    """Limpia compilaciones previas de la versión Demo."""
    target_exe = os.path.join(BASE_DIR, "dist", "Forensic_Recovery_DEMO.exe")
    if os.path.exists(target_exe):
        try:
            os.remove(target_exe)
        except Exception:
            backup = os.path.join(BASE_DIR, "dist", f"Forensic_Recovery_DEMO_old_{int(time.time())}.exe")
            try:
                os.rename(target_exe, backup)
            except Exception:
                pass

    for folder in ["build"]:
        folder_path = os.path.join(BASE_DIR, folder)
        if os.path.exists(folder_path):
            if sys.platform == "win32":
                try:
                    subprocess.run(
                        f'cmd /c "attrib -r -s -h \"{folder_path}\" /s /d 2>nul && rmdir /s /q \"{folder_path}\""',
                        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
            time.sleep(0.5)

def build_demo_executable(onefile: bool = True, console: bool = False):
    """Ejecuta PyInstaller para empaquetar Forensic_Recovery_DEMO.exe."""
    print("=" * 70)
    print(" 🔨 COMPILADOR AUTÓNOMO: FORENSIC RECOVERY DEMO (24 HORAS)")
    print("=" * 70)

    # Asegurar carpetas requeridas
    for sub in ["data", "sessions"]:
        os.makedirs(os.path.join(BASE_DIR, sub), exist_ok=True)

    clean_previous_builds()

    app_name = "Forensic_Recovery_DEMO"
    entry_point = os.path.join(BASE_DIR, "main_demo.py")

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

    # Carpetas de datos a incluir
    data_folders = ["core", "ui", "data", "sessions", "docs"]
    for folder in data_folders:
        src = os.path.join(BASE_DIR, folder)
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src};{folder}"])

    # Hidden imports esenciales
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
        "winreg",
        "ctypes",
        "hashlib",
        "hmac",
        "zipfile",
        "xml.etree.ElementTree"
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Archivo de entrada
    cmd.append(entry_point)

    print("\nIniciando proceso de compilación de la edición DEMO...")
    print(f"Modo: {'Archivo único (.exe portable)' if onefile else 'Carpeta distribuible'}")
    print(f"Destino previsto: dist/{app_name}.exe\n")

    start_time = time.time()
    result = subprocess.run(cmd, cwd=BASE_DIR)
    elapsed = time.time() - start_time

    if result.returncode == 0:
        exe_path = os.path.join(BASE_DIR, "dist", f"{app_name}.exe")
        print("\n" + "=" * 70)
        print(" 🎉 ¡COMPILACIÓN DE FORENSIC_RECOVERY_DEMO EXITOSA!")
        print("=" * 70)
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"Ejecutable generado: {exe_path}")
            print(f"Tamaño final: {size_mb:.2f} MB")
            print(f"Tiempo de compilación: {elapsed:.1f} segundos")
            print("\nPropiedades de la versión DEMO:")
            print("1. El temporizador de 24 horas comienza en la primera ejecución de cada máquina.")
            print("2. Protección anti-rollback detecta manipulaciones del reloj de Windows.")
            print("3. Al cumplirse las 24 horas, bloquea permanentemente y se autodestruye.")

            # Copiar documentación y paquete para testers a dist/
            dist_dir = os.path.join(BASE_DIR, "dist")
            for doc_file in ["guia_testers.html", "BIENVENIDA_TESTERS.txt"]:
                src = os.path.join(BASE_DIR, "docs", doc_file)
                if not os.path.exists(src):
                    src = os.path.join(BASE_DIR, doc_file)
                if os.path.exists(src):
                    dst = os.path.join(dist_dir, doc_file)
                    try:
                        shutil.copy2(src, dst)
                        print(f"✓ Paquete Tester sincronizado: dist/{doc_file}")
                    except Exception as e:
                        print(f"Aviso al copiar {doc_file}: {e}")
        else:
            print(f"Compilación terminada en la carpeta dist/{app_name}/")
        print("=" * 70 + "\n")
        return True
    else:
        print("\n❌ Error durante la compilación. Código de salida:", result.returncode)
        return False

if __name__ == "__main__":
    is_console = "--debug" in sys.argv
    is_onedir = "--onedir" in sys.argv
    success = build_demo_executable(onefile=not is_onedir, console=is_console)
    sys.exit(0 if success else 1)

