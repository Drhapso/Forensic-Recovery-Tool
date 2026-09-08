"""
Módulo de exploración y recuperación de Instantáneas de Volumen (Volume Shadow Copies - VSS).
Permite listar puntos de restauración del sistema y recuperar versiones anteriores de archivos sobrescritos o borrados.
"""

import os
import re
import subprocess
import datetime
from typing import List, Dict, Any, Optional
from core.disk_utils import is_admin

class ShadowExplorer:
    """Gestiona e inspecciona copias de sombra de Windows (VSS)."""

    @staticmethod
    def get_shadow_copies() -> Dict[str, Any]:
        """
        Lista las copias de sombra disponibles en el equipo usando vssadmin.
        Requiere permisos de Administrador para obtener resultados completos.
        """
        import sys
        if sys.platform != "win32":
            return {
                "success": False,
                "admin_required": False,
                "shadows": [],
                "message": "Las Instantáneas de Volumen (VSS) son exclusivas de Windows. En Linux Bazzite utilice escaneo directo o Papelera/Carving."
            }

        if not is_admin():
            return {
                "success": False,
                "admin_required": True,
                "shadows": [],
                "message": "Se requieren permisos de Administrador para acceder al Servicio de Instantáneas de Volumen (VSS)."
            }

        try:
            cmd = ["vssadmin", "list", "shadows"]
            proc = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
            stdout = proc.stdout

            shadows = []
            current_shadow = {}

            for line in stdout.splitlines():
                line = line.strip()
                if not line:
                    continue

                if "Id. de la copia de sombra:" in line or "Shadow Copy ID:" in line:
                    if current_shadow and "device_object" in current_shadow:
                        shadows.append(current_shadow)
                    current_shadow = {}
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_shadow["id"] = parts[1].strip()

                elif "Volumen original:" in line or "Original Volume:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_shadow["original_volume"] = parts[1].strip()

                elif "Volumen de la copia de sombra:" in line or "Shadow Copy Volume:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_shadow["device_object"] = parts[1].strip()

                elif "Hora de creación:" in line or "Creation Time:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_shadow["creation_time"] = parts[1].strip()

            if current_shadow and "device_object" in current_shadow:
                shadows.append(current_shadow)

            return {
                "success": True,
                "admin_required": False,
                "shadows": shadows,
                "message": f"Se encontraron {len(shadows)} instantánea(s) de volumen en el sistema."
            }

        except Exception as e:
            return {
                "success": False,
                "admin_required": False,
                "shadows": [],
                "message": f"Error consultando VSS: {e}"
            }

    @staticmethod
    def create_shadow_symlink(device_object: str, link_path: str) -> bool:
        """
        Crea un enlace simbólico de directorio hacia la instantánea de volumen
        para permitir explorar sus archivos con el explorador convencional.
        Ejemplo device_object: \\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy1\\
        """
        if not is_admin():
            return False

        try:
            # Asegurarse de que el device_object termine en barra
            if not device_object.endswith("\\"):
                device_object += "\\"

            if os.path.exists(link_path):
                subprocess.run(f'rmdir "{link_path}"', shell=True)

            cmd = f'mklink /d "{link_path}" "{device_object}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return res.returncode == 0
        except Exception as e:
            print(f"Error creando enlace simbólico VSS: {e}")
            return False

