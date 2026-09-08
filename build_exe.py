"""
Script de compilación automatizada a ejecutable autónomo (.exe) para Windows.
Utiliza PyInstaller para empaquetar toda la suite forense, incluyendo PyQt5,
Pillow, base de datos SQLite y módulos de inspección profunda, generando
un ejecutable portable listo para operar sin necesidad de instalar dependencias.
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
    """Limpia directorios de compilación previos para asegurar un empaquetado limpio."""
    target_exe = os.path.join(BASE_DIR, "dist", "RecuperadorDeDatos.exe")
    if os.path.exists(target_exe):
        try:
            os.remove(target_exe)
        except Exception:
            backup = os.path.join(BASE_DIR, "dist", f"RecuperadorDeDatos_old_{int(time.time())}.exe")
            try:
                os.rename(target_exe, backup)
            except Exception:
                pass

    for folder in ["build"]:
        folder_path = os.path.join(BASE_DIR, folder)
        if os.path.exists(folder_path):
            print(f"Limpiando carpeta previa: {folder}/")
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

def sync_documentation():
    """Regenera los portales HTML y asegura que los manuales estén al día."""
    gen_script = os.path.join(BASE_DIR, "scratch", "generate_doc_html.py")
    if os.path.exists(gen_script):
        try:
            print("\n[DocSync] Actualizando portales de documentación HTML...")
            subprocess.run([sys.executable, gen_script], cwd=BASE_DIR, check=False)
        except Exception as e:
            print(f"Aviso al regenerar documentación: {e}")

    # Copiar manual de usuario independiente a dist/
    dist_dir = os.path.join(BASE_DIR, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    for user_doc in ["manual_usuario.html"]:
        src = os.path.join(BASE_DIR, "docs", user_doc)
        if not os.path.exists(src):
            src = os.path.join(BASE_DIR, user_doc)
        if os.path.exists(src):
            try:
                shutil.copy2(src, os.path.join(dist_dir, user_doc))
                print(f"✓ Manual de Usuario sincronizado: dist/{user_doc}")
            except Exception as e:
                print(f"Aviso al copiar {user_doc}: {e}")

def sync_demo_build(onefile: bool = True, console: bool = False):
    """Compila y actualiza automáticamente la edición DEMO para testers."""
    print("\n" + "=" * 70)
    print(" 🔄 SINCRONIZANDO EDICIÓN DEMO PARA TESTERS (Forensic_Recovery_DEMO.exe)")
    print("=" * 70)
    cmd = [sys.executable, os.path.join(BASE_DIR, "build_demo.py")]
    if not onefile:
        cmd.append("--onedir")
    if console:
        cmd.append("--debug")
    res = subprocess.run(cmd, cwd=BASE_DIR)
    return res.returncode == 0

def print_distribution_summary():
    """Muestra un resumen ordenado y verificado de todos los artefactos en dist/."""
    dist_dir = os.path.join(BASE_DIR, "dist")
    print("\n" + "=" * 70)
    print(" 📦 PAQUETE DE DISTRIBUCIÓN COMPLETO Y SINCRONIZADO (dist/)")
    print("=" * 70)

    comercial_items = ["RecuperadorDeDatos.exe", "manual_usuario.html"]
    tester_items = ["Forensic_Recovery_DEMO.exe", "guia_testers.html", "BIENVENIDA_TESTERS.txt"]

    print(" 🏷️  VERSIÓN COMERCIAL COMPLETA:")
    for item in comercial_items:
        p = os.path.join(dist_dir, item)
        if os.path.exists(p):
            size = os.path.getsize(p)
            size_str = f"{size / (1024*1024):.2f} MB" if size > 1024*1024 else f"{size / 1024:.1f} KB"
            print(f"    ✓ {item:<30} [{size_str}]")
        else:
            print(f"    ✗ {item:<30} [NO ENCONTRADO]")

    print("\n 🧪 EDICIÓN DE DEMOSTRACIÓN PARA TESTERS (24 HORAS):")
    for item in tester_items:
        p = os.path.join(dist_dir, item)
        if os.path.exists(p):
            size = os.path.getsize(p)
            size_str = f"{size / (1024*1024):.2f} MB" if size > 1024*1024 else f"{size / 1024:.1f} KB"
            print(f"    ✓ {item:<30} [{size_str}]")
        else:
            print(f"    ✗ {item:<30} [NO ENCONTRADO]")
    print("=" * 70 + "\n")

def build_executable(onefile: bool = True, console: bool = False, sync_demo: bool = True):
    """Ejecuta PyInstaller con todos los parámetros forenses necesarios y sincroniza la demo."""
    print("=" * 70)
    print(" 🔨 COMPILADOR AUTÓNOMO: RECUPERADOR DE DATOS FORENSE (WINDOWS)")
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
        cmd.append("--windowed")  # Sin ventana de consola negra para el usuario final

    # Carpetas de datos a incluir (formato origen;destino en Windows)
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

    print("\nIniciando proceso de compilación con PyInstaller...")
    print(f"Modo: {'Archivo único (.exe portable)' if onefile else 'Carpeta distribuible'}")
    print(f"Destino previsto: dist/{app_name}.exe\n")

    start_time = time.time()
    result = subprocess.run(cmd, cwd=BASE_DIR)
    elapsed = time.time() - start_time

    if result.returncode == 0:
        exe_path = os.path.join(BASE_DIR, "dist", f"{app_name}.exe")
        print("\n" + "=" * 70)
        print(" 🎉 ¡COMPILACIÓN DEL RECUPERADOR COMERCIAL EXITOSA!")
        print("=" * 70)
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"Ejecutable generado: {exe_path}")
            print(f"Tamaño final: {size_mb:.2f} MB")
            print(f"Tiempo de compilación: {elapsed:.1f} segundos")
        else:
            print(f"Compilación terminada en la carpeta dist/{app_name}/")

        # 1. Sincronizar documentación y manuales
        sync_documentation()

        # 2. Sincronizar automáticamente la edición DEMO para testers
        if sync_demo:
            sync_demo_build(onefile=onefile, console=console)

        # 3. Resumen final consolidado
        print_distribution_summary()
        return True
    else:
        print("\n❌ Error durante la compilación. Código de salida:", result.returncode)
        return False

if __name__ == "__main__":
    is_console = "--debug" in sys.argv
    is_onedir = "--onedir" in sys.argv
    skip_demo = "--no-demo" in sys.argv or "--skip-demo" in sys.argv
    success = build_executable(onefile=not is_onedir, console=is_console, sync_demo=not skip_demo)
    sys.exit(0 if success else 1)

