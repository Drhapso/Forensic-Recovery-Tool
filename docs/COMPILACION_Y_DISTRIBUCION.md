# 🔨 Guía de Compilación, Empaquetado y Distribución

Esta guía detalla el procedimiento técnico para compilar el **Recuperador de Datos Forense** en ejecutables autónomos y portables tanto para **Windows (.exe)** como para **Linux (ELF)**, sin necesidad de que los usuarios finales instalen Python, PyQt5 ni dependencias externas.

---

## 1. Compilación para Windows (.exe)

### 1.1 Requisitos Previos en el Entorno de Compilación
Para compilar el binario en Windows, el equipo de desarrollo debe contar con:
* **Python 3.10, 3.11, 3.12, 3.13 o 3.14 (64 bits)** instalado.
* Paquetes de Python requeridos (instalables vía `pip`):
  ```powershell
  pip install pyinstaller PyQt5 Pillow
  ```

### 1.2 Métodos de Compilación en Windows

#### Método 1: Doble Clic con `build.bat` (Recomendado)
En el explorador de archivos de Windows, haga doble clic en:
```
build.bat
```
El script validará el entorno, limpiará compilaciones temporales previas y ejecutará `build_exe.py`.

#### Método 2: Desde Consola PowerShell / CMD
Abra una terminal en la raíz del proyecto y ejecute:
```powershell
python build_exe.py
```

### 1.3 Parámetros Avanzados de Compilación (`build_exe.py`)

| Parámetro / Argumento | Descripción y Uso |
|---|---|
| *(Sin parámetros)* | Genera un archivo ejecutable único (`--onefile`), en modo ventana sin consola negra (`--noconsole`). El resultado se ubica en `dist/RecuperadorDeDatos.exe`. |
| `--debug` | Habilita la consola de depuración en segundo plano (`--console`). Útil para diagnosticar excepciones no capturadas o inspeccionar trazas de error en tiempo real. |
| `--onedir` | Empaqueta la aplicación en una carpeta con archivos sueltos en lugar de un único ejecutable comprimido. Acelera el tiempo de arranque inicial en máquinas con discos lentos. |

Ejemplos:
```powershell
# Compilación estándar para distribución a usuarios:
python build_exe.py

# Compilación con consola visible para pruebas y depuración:
python build_exe.py --debug

# Compilación en carpeta suelta:
python build_exe.py --onedir
```

### 1.4 Manejo Automático de Bloqueos de Archivo en Windows
En Windows, si el archivo `dist/RecuperadorDeDatos.exe` está siendo ejecutado o se encuentra bloqueado por el explorador de archivos, PyInstaller suele fallar con error de permisos (`PermissionError: [WinError 5] Acceso denegado`).

`build_exe.py` cuenta con un mecanismo de protección integrado:
1. Intenta eliminar el binario anterior.
2. Si está bloqueado, lo renombra automáticamente a un archivo temporal de respaldo (`RecuperadorDeDatos_old_<timestamp>.exe`), liberando inmediatamente la ruta `RecuperadorDeDatos.exe` para que PyInstaller complete la compilación sin errores.

### 1.5 Resultado del Binario de Windows
* **Ruta de salida:** `dist/RecuperadorDeDatos.exe`
* **Tamaño aproximado:** ~256 MB (incluye Python completo, DLLs de Qt5, plugins de plataforma `qwindows.dll`, códecs multimedia y SQLite).
* **Portabilidad:** 100% autónomo. Puede copiarse a una memoria USB y ejecutarse en cualquier equipo con Windows 10 u 11 de 64 bits.

---

## 2. Compilación y Exportación para Linux

La suite está diseñada con una capa de abstracción compatible con **Linux Bazzite, Debian, Ubuntu, Fedora y SteamOS**.

### 2.1 Opción A: Compilación Nativa ELF con `build_linux.sh`
Para generar un binario nativo de Linux (sin extensión `.exe`):

1. Otorgue permisos de ejecución al script:
   ```bash
   chmod +x build_linux.sh
   ```
2. Ejecute la compilación:
   ```bash
   ./build_linux.sh
   ```
3. El script creará un entorno virtual aislado (`.venv_linux_build`), instalará las librerías necesarias y generará el ejecutable:
   ```bash
   dist/RecuperadorDeDatos
   ```
4. Para ejecutarlo:
   ```bash
   ./dist/RecuperadorDeDatos
   ```

### 2.2 Opción B: Compilación en Bazzite mediante Distrobox
Dado que **Linux Bazzite** es un sistema inmutable (basado en Fedora Atomic con rpm-ostree), se recomienda compilar utilizando el subsistema **Distrobox** incluido por defecto:

```bash
# 1. Crear e ingresar a un contenedor Debian o Fedora para desarrollo:
distrobox create -i debian:latest -n dev-recuperador
distrobox enter dev-recuperador

# 2. Instalar dependencias del sistema requeridas para compilar PyQt5:
sudo apt update && sudo apt install -y python3 python3-pip python3-venv libgl1 libegl1 libglib2.0-0

# 3. Compilar el ejecutable nativo:
chmod +x build_linux.sh
./build_linux.sh
```

### 2.3 Opción C: Ejecución Inmediata en Bazzite vía Wine / Proton
Dado que Bazzite incluye **Wine** y **Proton** preinstalados de fábrica para videojuegos:
* Puede copiar directamente `dist/RecuperadorDeDatos.exe` a Bazzite y hacer clic derecho → **"Abrir con Wine"**.
* O ejecutarlo desde la terminal:
  ```bash
  wine dist/RecuperadorDeDatos.exe
  ```

---

## 3. Integración en el Escritorio (Desktop Entry)

Para integrar la aplicación en el menú del sistema operativo en Linux:

1. El archivo `RecuperadorDeDatos.desktop` se encuentra en la raíz del proyecto.
2. Cópielo a la carpeta de aplicaciones del usuario:
   ```bash
   mkdir -p ~/.local/share/applications
   cp RecuperadorDeDatos.desktop ~/.local/share/applications/
   ```
3. La aplicación aparecerá en el menú de KDE Plasma, GNOME y lanzadores de Bazzite.

---

## 4. Estructura de Archivos Necesaria para Distribución Portátil

Si va a distribuir la herramienta en una memoria USB o compartirla en red, solo necesita copiar los siguientes elementos:

```
Carpeta_Distribucion/
└── RecuperadorDeDatos.exe    # El ejecutable único autónomo
```

Al ejecutarse, la aplicación generará automáticamente en su propio directorio:
* `data/recovery_vault.db`: Base de datos SQLite local para historiales y caché.
* `sessions/`: Directorio donde se guardan las sesiones de exploración en formato JSON.

No requiere la presencia de código fuente `.py`, carpetas virtuales ni archivos de configuración externos.

