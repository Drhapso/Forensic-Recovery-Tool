#!/usr/bin/env bash
# ==============================================================================
# Script de compilación automatizada para Linux Bazzite / Debian / Ubuntu / Fedora
# Genera el ejecutable nativo 'dist/RecuperadorDeDatos'
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo " 🐧 COMPILADOR DE RECUPERADOR DE DATOS PARA LINUX BAZZITE / DEBIAN"
echo "======================================================================"

# 1. Comprobar Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Error: Python 3 no está instalado."
    echo "En Debian/Ubuntu: sudo apt install python3 python3-pip python3-venv"
    echo "En Fedora/Bazzite: sudo dnf install python3 python3-pip"
    exit 1
fi

echo "✅ Python 3 detectado: $(python3 --version)"

# 2. Configurar entorno virtual para aislar dependencias
VENV_DIR="$SCRIPT_DIR/.venv_linux_build"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creando entorno virtual de compilación en .venv_linux_build..."
    python3 -m venv "$VENV_DIR"
fi

# Activar entorno virtual
source "$VENV_DIR/bin/activate"

# 3. Instalar o actualizar dependencias necesarias
echo "📥 Instalando dependencias de compilación (PyQt5, Pillow, PyInstaller)..."
pip install --upgrade pip
pip install pyinstaller PyQt5 Pillow

# 4. Lanzar la compilación con PyInstaller
echo "🔨 Compilando ejecutable standalone de Linux..."
python build_linux.py "$@"

# 5. Asegurar permisos de ejecución
if [ -f "$SCRIPT_DIR/dist/RecuperadorDeDatos" ]; then
    chmod +x "$SCRIPT_DIR/dist/RecuperadorDeDatos"
    echo ""
    echo "🎉 ¡LISTO! Ejecutable generado con éxito en:"
    echo "    $SCRIPT_DIR/dist/RecuperadorDeDatos"
    echo ""
    echo "Para lanzarlo ejecuta:"
    echo "    ./dist/RecuperadorDeDatos"
fi

