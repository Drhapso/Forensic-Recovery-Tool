"""
Módulo forense y de recuperación de la Papelera de Reciclaje ($Recycle.Bin) de Windows.
Analiza la estructura interna de metadatos ($I), contenedores de datos ($R)
y recupera archivos $R huérfanos cuyos metadatos fueron eliminados por herramientas de limpieza.
"""

import os
import struct
import datetime
import shutil
from typing import List, Dict, Any, Optional, Callable

# Categorías de archivos
EXT_CATEGORIES = {
    "Imágenes": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".svg", ".ico", ".psd", ".raw", ".cr2", ".nef", ".arw", ".heic"},
    "Documentos": {
        ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".rtf", ".odt",
        ".ods", ".odp", ".csv", ".tsv", ".md", ".xml", ".html", ".htm", ".log",
        ".docm", ".dotx", ".dot", ".asd", ".wbk", ".xlsm", ".xlsb", ".xltx", ".xar",
        ".pptm", ".ppsx", ".pps", ".epub", ".mobi", ".xps", ".odg", ".msg", ".pub",
        ".one", ".accdb", ".mdb"
    },
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".mid", ".midi"},
    "Video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".ts"},
    "Comprimidos": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".iso", ".xz"},
    "Código/Desarrollo": {".py", ".js", ".ts", ".css", ".json", ".sql", ".cpp", ".c", ".h", ".cs", ".java", ".php"},
    "Bases de Datos": {".db", ".sqlite", ".sqlite3"}
}

def get_file_category(filename: str) -> str:
    """Determina la categoría de un archivo a partir de su nombre o extensión."""
    if filename.startswith("."):
        ext = filename.lower()
    else:
        _, ext = os.path.splitext(filename.lower())
    for cat, exts in EXT_CATEGORIES.items():
        if ext in exts:
            return cat
    return "Otros"

get_category_for_ext = get_file_category

def filetime_to_datetime(filetime: int) -> datetime.datetime:
    """Convierte un timestamp Windows FILETIME (intervalos de 100ns desde 1601-01-01) a datetime."""
    try:
        epoch_start = datetime.datetime(1601, 1, 1)
        return epoch_start + datetime.timedelta(microseconds=filetime // 10)
    except Exception:
        return datetime.datetime.now()

def detect_extension_from_magic_bytes(filepath: str) -> str:
    """Identifica la extensión real de un archivo binario a partir de sus primeros bytes."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(32)
        if not header:
            return ".bin"

        if header.startswith(b"\xFF\xD8\xFF"):
            return ".jpg"
        elif header.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return ".gif"
        elif header.startswith(b"%PDF-"):
            return ".pdf"
        elif header.startswith(b"PK\x03\x04"):
            return ".zip"
        elif header.startswith(b"7z\xBC\xAF\x27\x1C"):
            return ".7z"
        elif header.startswith(b"Rar!\x1A\x07"):
            return ".rar"
        elif header.startswith(b"BM"):
            return ".bmp"
        elif header.startswith(b"ID3") or (len(header) > 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
            return ".mp3"
        elif header.startswith(b"RIFF"):
            if len(header) >= 12:
                sub = header[8:12]
                if sub == b"WAVE":
                    return ".wav"
                elif sub == b"WEBP":
                    return ".webp"
                elif sub == b"AVI ":
                    return ".avi"
            return ".riff"
        elif header.startswith(b"fLaC"):
            return ".flac"
        elif header.startswith(b"OggS"):
            return ".ogg"
        elif header.startswith(b"\x1A\x45\xDF\xA3"):
            return ".mkv"
        elif len(header) >= 8 and header[4:8] == b"ftyp":
            return ".mp4"
        elif header.startswith(b"SQLite format 3\x00"):
            return ".db"
        elif header.startswith(b"{\\rtf"):
            return ".rtf"
        elif header.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"):
            return ".doc"
        elif header.startswith(b"MZ"):
            return ".exe"
    except Exception:
        pass
    return ".bin"

class RecycleBinScanner:
    """Escanea y extrae elementos de la Papelera de Reciclaje de Windows incluyendo huérfanos."""

    @staticmethod
    def scan_drives(drives: Optional[List[str]] = None, 
                    progress_callback: Optional[Callable[[str, int, str], None]] = None) -> List[Dict[str, Any]]:
        """
        Escanea la papelera de reciclaje en las unidades indicadas (o todas las detectadas).
        progress_callback recibe: (mensaje_estado, porcentaje, ruta_actual)
        """
        if not drives:
            from core.disk_utils import get_drives
            drives = [d["letter"] for d in get_drives()]

        recovered_items = []
        total_drives = len(drives)

        for drive_idx, drive in enumerate(drives):
            recycle_dir = os.path.join(drive, "$Recycle.Bin")
            if progress_callback:
                progress_callback(f"Escaneando Papelera en unidad {drive}...", int((drive_idx / total_drives) * 100), recycle_dir)

            if not os.path.exists(recycle_dir):
                continue

            try:
                sids = os.listdir(recycle_dir)
            except Exception:
                continue

            for sid in sids:
                sid_path = os.path.join(recycle_dir, sid)
                try:
                    entries = os.listdir(sid_path)
                except Exception:
                    continue

                i_files = set(f for f in entries if f.startswith("$I"))
                r_files = set(f for f in entries if f.startswith("$R"))
                processed_r = set()

                # 1. Procesar pares válidos ($I y $R)
                for ifile in i_files:
                    i_path = os.path.join(sid_path, ifile)
                    r_name = "$R" + ifile[2:]
                    r_path = os.path.join(sid_path, r_name)
                    processed_r.add(r_name)

                    if progress_callback:
                        progress_callback("Analizando registro de papelera...", int((drive_idx / total_drives) * 100), i_path)

                    try:
                        with open(i_path, "rb") as f:
                            data = f.read()

                        if len(data) < 24:
                            continue

                        version = struct.unpack("<Q", data[:8])[0]
                        size = struct.unpack("<Q", data[8:16])[0]
                        filetime = struct.unpack("<Q", data[16:24])[0]
                        del_date = filetime_to_datetime(filetime)

                        orig_path = ""
                        if version == 1:
                            raw_path = data[24:544]
                            orig_path = raw_path.decode("utf-16le", errors="ignore").split("\x00")[0]
                        elif version == 2:
                            if len(data) >= 28:
                                path_len = struct.unpack("<I", data[24:28])[0]
                                raw_path = data[28:28 + path_len * 2]
                                orig_path = raw_path.decode("utf-16le", errors="ignore").split("\x00")[0]
                        else:
                            orig_path = f"Desconocido_{ifile[2:]}"

                        if not orig_path:
                            orig_path = f"Sin_Nombre_{ifile[2:]}"

                        filename = os.path.basename(orig_path)
                        r_exists = os.path.exists(r_path)
                        actual_size = os.path.getsize(r_path) if r_exists else size

                        item = {
                            "id": f"recycle_{sid}_{ifile}",
                            "name": filename,
                            "original_name": filename,
                            "original_path": orig_path,
                            "original_dir": os.path.dirname(orig_path),
                            "data_source_path": r_path,
                            "meta_source_path": i_path,
                            "size": actual_size,
                            "date": del_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(del_date, datetime.datetime) else str(del_date),
                            "raw_date": del_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(del_date, datetime.datetime) else str(del_date),
                            "category": get_file_category(filename),
                            "source_method": "Papelera Forense ($Recycle.Bin)",
                            "recoverable": r_exists,
                            "drive": drive,
                            "sid": sid,
                            "is_folder": os.path.isdir(r_path) if r_exists else False
                        }
                        recovered_items.append(item)

                    except Exception as parse_err:
                        print(f"Error procesando {i_path}: {parse_err}")
                        continue

                # 2. Rescatar archivos $R Huérfanos (cuyo $I fue eliminado por CCleaner / Windows)
                orphan_r_files = r_files - processed_r
                for r_orphan in orphan_r_files:
                    r_orphan_path = os.path.join(sid_path, r_orphan)
                    if not os.path.exists(r_orphan_path):
                        continue

                    try:
                        stat = os.stat(r_orphan_path)
                        size = stat.st_size
                        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

                        # Detectar extensión real mediante Magic Bytes
                        detected_ext = detect_extension_from_magic_bytes(r_orphan_path)
                        name_orphan = f"Rescatado_{r_orphan}{detected_ext}"

                        # Intentar extraer título incrustado si es documento u otro formato
                        from core.exporter import RecoveryExporter
                        embedded_title = RecoveryExporter.extract_embedded_title(r_orphan_path, detected_ext)
                        orig_name = f"{embedded_title}{detected_ext}" if embedded_title else name_orphan

                        if progress_callback:
                            progress_callback(f"Rescatando archivo huérfano {r_orphan}...", int((drive_idx / total_drives) * 100), r_orphan_path)

                        item = {
                            "id": f"recycle_orphan_{sid}_{r_orphan}",
                            "name": orig_name if orig_name != name_orphan else name_orphan,
                            "original_name": orig_name,
                            "original_path": f"Papelera Huérfana ({r_orphan})",
                            "original_dir": sid_path,
                            "data_source_path": r_orphan_path,
                            "meta_source_path": "",
                            "size": size,
                            "date": mtime.strftime("%Y-%m-%d %H:%M:%S") if isinstance(mtime, datetime.datetime) else str(mtime),
                            "raw_date": mtime.strftime("%Y-%m-%d %H:%M:%S") if isinstance(mtime, datetime.datetime) else str(mtime),
                            "category": get_file_category(name_orphan),
                            "source_method": "Papelera (Contenedor $R Huérfano Rescatado)",
                            "recoverable": True,
                            "drive": drive,
                            "sid": sid,
                            "is_folder": os.path.isdir(r_orphan_path)
                        }
                        recovered_items.append(item)
                    except Exception:
                        continue

        # 3. Soporte para Papelera de Reciclaje de Linux (FreeDesktop Trash en Bazzite / Debian)
        user_home = os.environ.get("HOME", os.path.expanduser("~"))
        linux_trash_dirs = [
            os.path.join(user_home, ".local", "share", "Trash"),
        ]
        for d in drives:
            for t_name in [".Trash-1000", ".Trash", ".Trash-0"]:
                tp = os.path.join(d, t_name)
                if os.path.exists(tp):
                    linux_trash_dirs.append(tp)

        for trash_base in linux_trash_dirs:
            files_dir = os.path.join(trash_base, "files")
            info_dir = os.path.join(trash_base, "info")
            if not os.path.exists(files_dir):
                continue
            try:
                for fname in os.listdir(files_dir):
                    fpath = os.path.join(files_dir, fname)
                    orig_path = fname
                    mtime = None
                    info_path = os.path.join(info_dir, f"{fname}.trashinfo")
                    if os.path.exists(info_path):
                        try:
                            with open(info_path, "r", encoding="utf-8", errors="ignore") as inf:
                                for l in inf:
                                    if l.startswith("Path="):
                                        orig_path = l.split("Path=", 1)[1].strip()
                                    elif l.startswith("DeletionDate="):
                                        d_str = l.split("DeletionDate=", 1)[1].strip()
                                        mtime = datetime.datetime.fromisoformat(d_str)
                        except Exception:
                            pass

                    try:
                        stat = os.stat(fpath)
                        size = stat.st_size
                        if mtime is None:
                            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

                        date_str = mtime.strftime("%Y-%m-%d %H:%M:%S") if isinstance(mtime, datetime.datetime) else str(mtime)
                        base_name = os.path.basename(orig_path) or fname

                        item = {
                            "id": f"linux_trash_{fname}",
                            "name": base_name,
                            "original_name": base_name,
                            "original_path": orig_path,
                            "original_dir": os.path.dirname(orig_path) or trash_base,
                            "data_source_path": fpath,
                            "meta_source_path": info_path if os.path.exists(info_path) else "",
                            "size": size,
                            "date": date_str,
                            "raw_date": date_str,
                            "category": get_file_category(base_name),
                            "source_method": "Papelera Forense (Linux FreeDesktop Trash)",
                            "recoverable": True,
                            "drive": trash_base,
                            "sid": "linux_user",
                            "is_folder": os.path.isdir(fpath)
                        }
                        recovered_items.append(item)
                    except Exception:
                        continue
            except Exception:
                pass

        if progress_callback:
            progress_callback("Escaneo de papelera finalizado.", 100, "")

        return recovered_items
