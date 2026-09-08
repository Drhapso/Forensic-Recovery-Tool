"""
Módulo de Ruteo Contextual de Directorios y Perfilado de Búsqueda.
Genera listados automáticos de carpetas prioritarias según el tipo de archivo buscado
(Documentos, Imágenes, Audio, Video, Comprimidos, Código) y aplica reglas de exclusión cruzada
para evitar indexar carpetas masivas que no corresponden a la búsqueda.
"""

import os
from typing import List, Dict, Any, Tuple, Set

class ContextRouter:
    """Gestiona las asociaciones entre categorías de archivo y ubicaciones lógicas del sistema."""

    @staticmethod
    def _resolve_user_folder(base_user: str, *candidates: str) -> str:
        for c in candidates:
            full = os.path.join(base_user, c)
            if os.path.exists(full):
                return full
        return os.path.join(base_user, candidates[0])

    @classmethod
    def get_known_user_locations(cls) -> Dict[str, str]:
        """Obtiene las rutas canónicas del perfil de usuario y servicios en la nube (Windows y Linux)."""
        import sys
        if sys.platform == "win32":
            user = os.environ.get("USERPROFILE", os.path.expanduser("~"))
            app_data = os.environ.get("APPDATA", "")
            local_app_data = os.environ.get("LOCALAPPDATA", "")
        else:
            user = os.environ.get("HOME", os.path.expanduser("~"))
            app_data = os.path.join(user, ".config")
            local_app_data = os.path.join(user, ".local", "share")

        locations = {
            "documents": cls._resolve_user_folder(user, "Documents", "Documentos"),
            "pictures": cls._resolve_user_folder(user, "Pictures", "Imágenes", "Imagenes"),
            "videos": cls._resolve_user_folder(user, "Videos", "Vídeos"),
            "music": cls._resolve_user_folder(user, "Music", "Música"),
            "downloads": cls._resolve_user_folder(user, "Downloads", "Descargas"),
            "desktop": cls._resolve_user_folder(user, "Desktop", "Escritorio"),
            "sound_recordings": os.path.join(user, "Documents", "Grabaciones de sonido"),
            "onedrive": os.path.join(user, "OneDrive"),
            "onedrive_docs": os.path.join(user, "OneDrive", "Documents"),
            "onedrive_pics": os.path.join(user, "OneDrive", "Pictures"),
            "office_unsaved": os.path.join(local_app_data, "Microsoft", "Office", "UnsavedFiles"),
            "word_drafts": os.path.join(app_data, "Microsoft", "Word"),
            "excel_drafts": os.path.join(app_data, "Microsoft", "Excel"),
            "thumbcache": os.path.join(local_app_data, "Microsoft", "Windows", "Explorer"),
            "projects": os.path.join(user, "Documents", "PROYECTOS IA INDEPENDIENTES")
        }
        return locations

    @classmethod
    def get_suggested_folders(cls, active_categories: List[str] = None) -> List[Dict[str, Any]]:
        """
        Genera la lista de carpetas disponibles con recomendaciones basadas
        en las categorías de archivo activas.
        """
        locs = cls.get_known_user_locations()
        cats = set(active_categories) if active_categories else {"Imágenes", "Documentos", "Audio", "Video", "Comprimidos"}

        candidates = [
            # 1. Documentos
            {
                "id": "docs_main",
                "name": "Mis Documentos",
                "path": locs["documents"],
                "category_tag": "Documentos",
                "for_categories": {"Documentos", "Código/Desarrollo"},
                "icon": "📄"
            },
            {
                "id": "desktop_main",
                "name": "Escritorio (Desktop)",
                "path": locs["desktop"],
                "category_tag": "General",
                "for_categories": {"Documentos", "Imágenes", "Audio", "Video", "Comprimidos", "Código/Desarrollo"},
                "icon": "🖥️"
            },
            {
                "id": "downloads_main",
                "name": "Descargas (Downloads)",
                "path": locs["downloads"],
                "category_tag": "General",
                "for_categories": {"Documentos", "Imágenes", "Audio", "Video", "Comprimidos"},
                "icon": "📥"
            },
            {
                "id": "office_unsaved",
                "name": "Borradores de Office (Word/Excel Unsaved)",
                "path": locs["office_unsaved"],
                "category_tag": "Documentos",
                "for_categories": {"Documentos"},
                "icon": "💾"
            },
            # 2. Imágenes / Fotos
            {
                "id": "pics_main",
                "name": "Mis Imágenes (Pictures)",
                "path": locs["pictures"],
                "category_tag": "Imágenes",
                "for_categories": {"Imágenes"},
                "icon": "🖼️"
            },
            # 3. Audio / Grabaciones
            {
                "id": "music_main",
                "name": "Mi Música (Music)",
                "path": locs["music"],
                "category_tag": "Audio",
                "for_categories": {"Audio"},
                "icon": "🎵"
            },
            {
                "id": "sound_recordings",
                "name": "Grabaciones de Sonido / Voz",
                "path": locs["sound_recordings"],
                "category_tag": "Audio",
                "for_categories": {"Audio"},
                "icon": "🎙️"
            },
            # 4. Videos / Capturas
            {
                "id": "videos_main",
                "name": "Mis Videos (Videos / Capturas)",
                "path": locs["videos"],
                "category_tag": "Video",
                "for_categories": {"Video"},
                "icon": "🎬"
            },
            # 5. Proyectos y Código
            {
                "id": "projects_user",
                "name": "Proyectos de Código / Desarrollo",
                "path": locs["projects"],
                "category_tag": "Código",
                "for_categories": {"Código/Desarrollo", "Documentos"},
                "icon": "💻"
            },
            # 6. OneDrive
            {
                "id": "onedrive_main",
                "name": "OneDrive en la Nube",
                "path": locs["onedrive"],
                "category_tag": "Cloud",
                "for_categories": {"Documentos", "Imágenes"},
                "icon": "☁️"
            }
        ]

        results = []
        for c in candidates:
            # Solo incluir si la ruta realmente existe en el equipo
            if os.path.exists(c["path"]):
                # Es recomendada si sus categorías objetivo coinciden con las activas del usuario
                is_recommended = bool(c["for_categories"] & cats)
                results.append({
                    "id": c["id"],
                    "name": c["name"],
                    "path": c["path"],
                    "category_tag": c["category_tag"],
                    "recommended": is_recommended,
                    "icon": c["icon"]
                })

        return results

    @classmethod
    def should_skip_by_context(cls, folder_path: str, active_categories: List[str]) -> Tuple[bool, str]:
        """
        Determina si una carpeta debe ser omitida porque pertenece a un dominio
        multimedia o de datos que no forma parte de la búsqueda activa del usuario.
        """
        if not active_categories:
            return False, ""

        cats = set(active_categories)
        norm = os.path.normpath(folder_path).lower()
        base_name = os.path.basename(norm)

        # Regla 1: Si NO se busca Video, omitir carpetas de bibliotecas de video masivas
        if "Video" not in cats:
            if base_name in {"videos", "captures", "movies", "películas", "peliculas", "recordings"} or "\\videos\\" in norm:
                return True, "Omitida por contexto (No se seleccionó Video)"

        # Regla 2: Si NO se busca Audio, omitir bibliotecas de música
        if "Audio" not in cats:
            if base_name in {"music", "música", "musica", "grabaciones de sonido", "podcasts", "audiobooks"} or "\\music\\" in norm:
                return True, "Omitida por contexto (No se seleccionó Audio)"

        # Regla 3: Si NO se busca Código ni Documentos, omitir carpetas de proyectos y repositorios
        if "Código/Desarrollo" not in cats and "Documentos" not in cats:
            if base_name in {"proyectos", "projects", "source", "repos", ".git"} or "proyectos ia" in norm:
                return True, "Omitida por contexto (No se seleccionó Documentos ni Código)"

        return False, ""

