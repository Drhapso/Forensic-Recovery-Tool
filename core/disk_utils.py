"""
Módulo de utilidades de disco y sistema de Windows.
Permite listar unidades, obtener tipos de disco, espacio libre y verificar privilegios de Administrador.
"""

import sys
import os
import ctypes
from ctypes import wintypes
from typing import List, Dict, Any

DRIVE_TYPES = {
    0: "Desconocido",
    1: "Ruta no válida",
    2: "Extraíble (USB/SD)",
    3: "Disco Fijo (HDD/SSD)",
    4: "Unidad de Red",
    5: "CD/DVD-ROM",
    6: "Disco RAM"
}

def is_admin() -> bool:
    """Verifica si el proceso actual se está ejecutando con permisos de Administrador o root."""
    if sys.platform == "win32":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    else:
        try:
            return os.geteuid() == 0
        except Exception:
            return False

def restart_as_admin() -> bool:
    """Solicita elevación UAC (Windows) o pkexec/sudo (Linux) y relanza el programa con permisos de Administrador."""
    if is_admin():
        return True
    if sys.platform == "win32":
        try:
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            hinstance = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                params,
                None,
                1  # SW_SHOWNORMAL
            )
            if hinstance > 32:
                sys.exit(0)
                return True
            return False
        except Exception as e:
            print(f"Error al solicitar elevación en Windows: {e}")
            return False
    else:
        import subprocess
        # En Linux (Bazzite / Debian / Fedora), solicitar permisos con pkexec o sudo
        for elevator in ["pkexec", "sudo"]:
            try:
                cmd = [elevator, sys.executable] + sys.argv
                subprocess.Popen(cmd)
                sys.exit(0)
                return True
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"Error al invocar {elevator}: {e}")
        return False

def get_drives() -> List[Dict[str, Any]]:
    """Obtiene información de todas las unidades lógicas disponibles en el equipo (Windows y Linux)."""
    drives = []

    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        bitmask = kernel32.GetLogicalDrives()
        for i in range(26):
            if bitmask & (1 << i):
                drive_letter = f"{chr(65 + i)}:\\"
                dtype_code = kernel32.GetDriveTypeW(drive_letter)
                dtype_str = DRIVE_TYPES.get(dtype_code, "Desconocido")
                
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                total_free_bytes = ctypes.c_ulonglong(0)
                
                has_space = kernel32.GetDiskFreeSpaceExW(
                    drive_letter,
                    ctypes.byref(free_bytes),
                    ctypes.byref(total_bytes),
                    ctypes.byref(total_free_bytes)
                )
                
                vol_name_buf = ctypes.create_unicode_buffer(261)
                fs_name_buf = ctypes.create_unicode_buffer(261)
                vol_serial = wintypes.DWORD()
                max_comp_len = wintypes.DWORD()
                fs_flags = wintypes.DWORD()
                
                has_vol_info = kernel32.GetVolumeInformationW(
                    drive_letter,
                    vol_name_buf,
                    len(vol_name_buf),
                    ctypes.byref(vol_serial),
                    ctypes.byref(max_comp_len),
                    ctypes.byref(fs_flags),
                    fs_name_buf,
                    len(fs_name_buf)
                )
                
                vol_name = vol_name_buf.value if has_vol_info else ""
                fs_name = fs_name_buf.value if has_vol_info else "Desconocido"
                
                drives.append({
                    "letter": drive_letter,
                    "drive_name": vol_name or f"Disco local ({drive_letter[0]}:)",
                    "type": dtype_str,
                    "type_code": dtype_code,
                    "fs_name": fs_name,
                    "total_bytes": total_bytes.value if has_space else 0,
                    "free_bytes": free_bytes.value if has_space else 0,
                    "used_bytes": (total_bytes.value - free_bytes.value) if has_space else 0
                })
    else:
        # Plataformas Linux / Bazzite / Debian
        import shutil
        ignored_fs = {
            "proc", "sysfs", "devtmpfs", "tmpfs", "cgroup", "cgroup2", "pstore",
            "bpf", "autofs", "hugetlbfs", "mqueue", "debugfs", "tracefs", "fusectl",
            "configfs", "ramfs", "devpts", "securityfs", "efivarfs", "binfmt_misc"
        }
        seen_points = set()

        # 1. Leer puntos de montaje desde /proc/mounts
        if os.path.exists("/proc/mounts"):
            try:
                with open("/proc/mounts", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            dev, mount_point, fs_type = parts[0], parts[1], parts[2]
                            if fs_type in ignored_fs or not dev.startswith(("/dev/", "/run/media", "/media")):
                                continue
                            if mount_point in seen_points:
                                continue
                            seen_points.add(mount_point)

                            try:
                                usage = shutil.disk_usage(mount_point)
                                is_removable = ("/media" in mount_point or "/run/media" in mount_point)
                                drives.append({
                                    "letter": mount_point,
                                    "drive_name": os.path.basename(mount_point) or "Sistema Raíz (/)",
                                    "type": "Extraíble (USB/SD)" if is_removable else "Disco Fijo (HDD/SSD)",
                                    "type_code": 2 if is_removable else 3,
                                    "fs_name": fs_type,
                                    "total_bytes": usage.total,
                                    "free_bytes": usage.free,
                                    "used_bytes": usage.used
                                })
                            except Exception:
                                pass
            except Exception as e:
                print(f"Aviso al leer /proc/mounts en Linux: {e}")

        # Si no se detectó nada o no existe /proc/mounts, asegurar al menos la raíz /
        if not drives and os.path.exists("/"):
            try:
                usage = shutil.disk_usage("/")
                drives.append({
                    "letter": "/",
                    "drive_name": "Sistema Raíz (/)",
                    "type": "Disco Fijo (HDD/SSD)",
                    "type_code": 3,
                    "fs_name": "ext4/btrfs",
                    "total_bytes": usage.total,
                    "free_bytes": usage.free,
                    "used_bytes": usage.used
                })
            except Exception:
                pass

    return drives

def format_size(bytes_num: int) -> str:
    """Formatea bytes a representación legible (B, KB, MB, GB, TB)."""
    if bytes_num < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} PB"

