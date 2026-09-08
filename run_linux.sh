#!/usr/bin/env bash
# ==============================================================================
# Lanzador directo para Linux Bazzite / Debian / Ubuntu / Fedora
# Permite ejecutar la aplicación directamente sin compilar
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/dist/RecuperadorDeDatos" ]; then
    echo "🚀 Iniciando binario precompilado de Linux..."
    exec "$SCRIPT_DIR/dist/RecuperadorDeDatos" "$@"
fi

echo "🚀 Iniciando Recuperador de Datos en modo nativo Python..."

if [ ! -d "$SCRIPT_DIR/.venv_linux" ]; then
    echo "📦 Creando entorno virtual local..."
    python3 -m venv "$SCRIPT_DIR/.venv_linux"
    source "$SCRIPT_DIR/.venv_linux/bin/activate"
    pip install --upgrade pip
    pip install PyQt5 Pillow
else
    source "$SCRIPT_DIR/.venv_linux/bin/activate"
fi

exec python3 "$SCRIPT_DIR/main.py" "$@"

