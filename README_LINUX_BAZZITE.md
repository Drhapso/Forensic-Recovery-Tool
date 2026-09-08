# Guía de Uso y Exportación para Linux Bazzite (y sistemas basados en Debian/Fedora)

Esta suite de recuperación de datos ha sido adaptada para funcionar de manera **100% multiplataforma**, soportando tanto **Windows** como **Linux (Bazzite, Debian, Ubuntu, Fedora, SteamOS)**.

A continuación se describen las tres formas de utilizar la herramienta en Linux Bazzite:

---

## ⚡ Opción 1: Ejecución Inmediata con Wine / Proton (Sin necesidad de compilar)

Dado que **Bazzite** es una distribución de Linux especializada en gaming (construida sobre Fedora Atomic con soporte nativo para Steam Deck y PC), incluye **Wine, Proton y Bottles preinstalados de fábrica**.

1. Copia el archivo ejecutable ya compilado:
   ```
   dist/RecuperadorDeDatos.exe
   ```
   a tu equipo con Bazzite (o tu tarjeta MicroSD / memoria USB).
2. **Para ejecutar con doble clic:**
   - Haz clic derecho sobre `RecuperadorDeDatos.exe`.
   - Selecciona **"Abrir con Wine Windows Program Loader"** (o agrégalo a Steam como juego no perteneciente a Steam usando Proton Experimental / GE-Proton).
3. **Para ejecutar desde la terminal en Bazzite:**
   ```bash
   wine dist/RecuperadorDeDatos.exe
   ```
   *El ejecutable contiene SQLite embebido y todas las librerías necesarias, por lo que arrancará de inmediato.*

---

## 🐧 Opción 2: Compilar el Binario Nativo ELF para Linux (`dist/RecuperadorDeDatos`)

Si deseas generar un **ejecutable nativo de Linux** (archivo binario sin extensión `.exe` que corre directamente sobre el kernel de Linux y glibc sin capas de compatibilidad):

### A) En Bazzite directamente (o mediante Distrobox Debian):
Bazzite incluye **Distrobox** integrado por defecto para instalar paquetes de cualquier distribución sin alterar la inmutabilidad del sistema base.

1. Abre la terminal en Bazzite y entra a la carpeta del proyecto:
   ```bash
   cd "RECUPERADOR DE DATOS"
   ```

2. Si usas un contenedor Debian en Bazzite (o cualquier sistema Debian/Ubuntu):
   ```bash
   # Crear e iniciar contenedor Debian si no lo tienes:
   distrobox create -i debian:latest -n debian-dev
   distrobox enter debian-dev
   ```

3. Ejecuta el script de compilación automatizado:
   ```bash
   chmod +x build_linux.sh
   ./build_linux.sh
   ```

4. **¡Listo!** El script:
   - Creará un entorno virtual aislado `.venv_linux_build`.
   - Instalará `pyinstaller`, `PyQt5` y `Pillow`.
   - Generará el ejecutable autónomo:
     ```
     dist/RecuperadorDeDatos
     ```
   - Le asignará permisos de ejecución (`chmod +x`).

5. Para ejecutar el binario nativo:
   ```bash
   ./dist/RecuperadorDeDatos
   ```

---

## 🚀 Opción 3: Lanzador Directo en Python (`run_linux.sh`)

Si no deseas empaquetar un archivo binario único y prefieres ejecutar la aplicación al instante desde su código fuente en Linux:

```bash
chmod +x run_linux.sh
./run_linux.sh
```

El script detectará o creará automáticamente un entorno virtual local, instalará los requerimientos gráficos de PyQt5 y lanzará la suite forense.

---

## 🖥️ Integración con el Escritorio de Bazzite (KDE Plasma / GNOME)

Para que la aplicación aparezca en el menú de aplicaciones de Bazzite con su icono:

1. Copia el archivo `RecuperadorDeDatos.desktop` a la carpeta de aplicaciones del usuario:
   ```bash
   mkdir -p ~/.local/share/applications
   cp RecuperadorDeDatos.desktop ~/.local/share/applications/
   ```
2. Asegúrate de que apunte a la ruta donde guardaste `dist/RecuperadorDeDatos`.
3. Ya podrás buscar **"Recuperador de Datos Forense"** en el lanzador de aplicaciones de Bazzite.

---

## 🛡️ Capacidades Nativas en Linux
- **Detección de Unidades:** Analiza puntos de montaje reales desde `/proc/mounts`, incluyendo discos externos USB y particiones en `/run/media/$USER` o `/media`.
- **Papelera de Reciclaje FreeDesktop:** Localiza y analiza archivos eliminados con sus registros de origen desde `~/.local/share/Trash/files` y metadatos `*.trashinfo`.
- **Rutas de Usuario Estándar (XDG):** Compatible con `$HOME` (`Documentos`, `Descargas`, `Imágenes`, `Música`, `Vídeos`, `Escritorio`).
- **Permisos de Administrador (Root):** Detecta elevación mediante `os.geteuid() == 0` y solicita permisos elevados con `pkexec` o `sudo` cuando se requiera acceso a bajo nivel.

