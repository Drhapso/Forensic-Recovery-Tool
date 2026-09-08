"""
Módulo de recuperación de Archivos No Guardados, Temporales y Auto-Recuperación.
Escanea carpetas de Microsoft Office UnsavedFiles, AutoRecover, Notepad++, VS Code,
%TEMP%, y caches de miniaturas de Windows.
"""

import os
import re
import glob
import datetime
from typing import List, Dict, Any, Optional, Callable
from core.recycle_bin import get_file_category

class TempScanner:
    """Escanea ubicaciones de archivos temporales y copias de seguridad automáticas."""

    @staticmethod
    def get_candidate_locations() -> List[Dict[str, str]]:
        """Obtiene una lista de rutas conocidas donde se guardan borradores y temporales."""
        user_profile = os.environ.get("USERPROFILE", "")
        app_data = os.environ.get("APPDATA", "")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        temp_dir = os.environ.get("TEMP", "")

        locations = [
            # Office UnsavedFiles
            {
                "name": "Office - Archivos No Guardados",
                "path": os.path.join(local_app_data, "Microsoft", "Office", "UnsavedFiles"),
                "category": "Office Unsaved"
            },
            # Word AutoRecover
            {
                "name": "Word - AutoRecuperación (.asd / .wbk)",
                "path": os.path.join(app_data, "Microsoft", "Word"),
                "category": "Word Drafts"
            },
            # Excel AutoRecover
            {
                "name": "Excel - AutoRecuperación (.xar)",
                "path": os.path.join(app_data, "Microsoft", "Excel"),
                "category": "Excel Drafts"
            },
            # PowerPoint AutoRecover
            {
                "name": "PowerPoint - AutoRecuperación",
                "path": os.path.join(app_data, "Microsoft", "PowerPoint"),
                "category": "PowerPoint Drafts"
            },
            # Notepad++ Backups
            {
                "name": "Notepad++ - Copias de seguridad automáticas",
                "path": os.path.join(app_data, "Notepad++", "backup"),
                "category": "Editor Backups"
            },
            # VS Code Unsaved Backups
            {
                "name": "VS Code - Archivos de sesión no guardados",
                "path": os.path.join(app_data, "Code", "Backups"),
                "category": "Editor Backups"
            },
            # Adobe AutoRecover
            {
                "name": "Adobe - Auto-recuperación",
                "path": os.path.join(app_data, "Adobe", "AutoRecover"),
                "category": "Adobe Drafts"
            },
            # Carpeta %TEMP% del usuario
            {
                "name": "Directorio Temporal del Usuario (%TEMP%)",
                "path": temp_dir,
                "category": "Windows Temp"
            }
        ]

        # Filtrar solo las carpetas que realmente existen
        return [loc for loc in locations if loc["path"] and os.path.exists(loc["path"])]

    @classmethod
    def scan_temp_and_drafts(cls, 
                             progress_callback: Optional[Callable[[str, int], None]] = None) -> List[Dict[str, Any]]:
        """
        Escanea todas las rutas candidatas y recopila archivos recuperables.
        """
        locations = cls.get_candidate_locations()
        recovered_items = []
        total_locs = len(locations)

        # Extensiones de alto interés para recuperación en temporales
        INTEREST_EXTENSIONS = {
            ".asd", ".wbk", ".xar", ".tmp", ".bak",
            ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
            ".pdf", ".txt", ".csv", ".rtf",
            ".jpg", ".jpeg", ".png", ".webp", ".bmp",
            ".zip", ".rar", ".7z"
        }

        for idx, loc in enumerate(locations):
            loc_path = loc["path"]
            loc_name = loc["name"]
            if progress_callback:
                progress_callback(f"Explorando {loc_name}...", int((idx / max(total_locs, 1)) * 100))

            try:
                # Recorrido recursivo moderado (máximo 3 niveles de profundidad para evitar loops en %TEMP%)
                for root, dirs, files in os.walk(loc_path):
                    # Evitar entrar en miles de subcarpetas irrelevantes de cache web
                    rel_depth = root[len(loc_path):].count(os.sep)
                    if rel_depth > 3:
                        dirs.clear()
                        continue

                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        full_path = os.path.join(root, file)

                        # En carpetas especializadas (UnsavedFiles, AutoRecover, backup), incluir todo lo relevante.
                        # En %TEMP%, SOLO incluir borradores de autorecuperación (~WRL, .asd, .wbk, .xar, ~*.tmp, .bak)
                        is_specialized = "Temp" not in loc["category"]
                        if not is_specialized:
                            is_draft_pattern = file.startswith("~") or ext in {".asd", ".wbk", ".xar", ".bak"}
                            if not is_draft_pattern:
                                continue

                        try:
                            stat = os.stat(full_path)
                            size = stat.st_size
                            if size == 0:
                                continue

                            # En %TEMP%, ignorar archivos mayores a 500MB de instaladores
                            if not is_specialized and size > 500 * 1024 * 1024:
                                continue

                            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

                            category = get_file_category(file)
                            orig_name = file
                            if ext in {".asd", ".wbk", ".xar"}:
                                category = "Documentos (Office AutoRecover)"
                                m = re.match(r"(?:AutoRecovery save of |Autoguardado de |Copia de seguridad de )(.*)\.(?:asd|wbk|xar)$", file, re.IGNORECASE)
                                if m:
                                    base_clean = m.group(1).strip()
                                    clean_ext = ".docx" if ext in {".asd", ".wbk"} else (".xlsx" if ext == ".xar" else ".docx")
                                    orig_name = f"{base_clean}{clean_ext}"
                            elif re.match(r"~WRL\d{4}\.tmp", file, re.IGNORECASE):
                                orig_name = "Documento_Word_Autoguardado.docx"

                            recovered_items.append({
                                "id": f"temp_{abs(hash(full_path))}",
                                "name": orig_name if orig_name != file else file,
                                "original_name": orig_name,
                                "raw_temp_name": file,
                                "original_path": full_path,
                                "original_dir": root,
                                "data_source_path": full_path,
                                "meta_source_path": full_path,
                                "size": size,
                                "date": mtime.strftime("%Y-%m-%d %H:%M:%S") if isinstance(mtime, datetime.datetime) else str(mtime),
                                "raw_date": mtime.strftime("%Y-%m-%d %H:%M:%S") if isinstance(mtime, datetime.datetime) else str(mtime),
                                "category": category,
                                "source_method": f"Temporales y Borradores ({loc['name']})",
                                "recoverable": True,
                                "drive": loc_path[:3],
                                "is_folder": False
                            })
                        except (PermissionError, FileNotFoundError):
                            continue

            except Exception as e:
                print(f"Error escaneando ubicación {loc_path}: {e}")
                continue

        if progress_callback:
            progress_callback("Escaneo de temporales y borradores completado.", 100)

        return recovered_items

