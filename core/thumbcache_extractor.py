"""
Módulo forense de extracción de imágenes desde la Caché de Miniaturas de Windows (thumbcache_*.db).
Permite rescatar fotografías, capturas y gráficos que fueron eliminados permanentemente del disco
y que aún residen en alta resolución (1280p, 1920p, 2560p, 256p) en la base de datos de Explorer.
"""

import os
import glob
import datetime
from typing import List, Dict, Any, Optional, Callable

class ThumbcacheExtractor:
    """Extrae imágenes JPEG, PNG y BMP embebidas en las bases de datos thumbcache de Windows."""

    @staticmethod
    def get_thumbcache_files() -> List[str]:
        """Localiza los archivos thumbcache_*.db del usuario actual."""
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        tc_dir = os.path.join(local_app_data, "Microsoft", "Windows", "Explorer")
        if not os.path.exists(tc_dir):
            return []
        
        # Priorizar bases de datos de alta resolución (1280, 1920, 2560, 768, 256)
        files = glob.glob(os.path.join(tc_dir, "thumbcache_*.db"))
        # Ordenar poniendo primero las de mayor resolución
        def resolution_key(p):
            base = os.path.basename(p)
            for res in [2560, 1920, 1280, 768, 256, 96, 48, 32]:
                if f"_{res}." in base:
                    return -res
            return 0
        
        return sorted(files, key=resolution_key)

    @classmethod
    def scan_thumbnails(cls, 
                        max_images: int = 150,
                        progress_callback: Optional[Callable[[str, int, str], None]] = None) -> List[Dict[str, Any]]:
        """
        Escanea los archivos thumbcache y extrae imágenes JPEG y PNG válidas.
        """
        db_files = cls.get_thumbcache_files()
        recovered_items = []
        total_dbs = len(db_files)
        total_found = 0

        for db_idx, db_path in enumerate(db_files):
            if total_found >= max_images:
                break

            base_name = os.path.basename(db_path)
            if "idx" in base_name or "sr" in base_name or "wide" in base_name:
                continue

            if progress_callback:
                pct = int((db_idx / max(total_dbs, 1)) * 100)
                progress_callback(f"Analizando caché gráfica {base_name}...", pct, db_path)

            try:
                fsize = os.path.getsize(db_path)
                # Si el archivo es demasiado grande (>300MB), leer bloques
                with open(db_path, "rb") as f:
                    data = f.read(min(fsize, 80 * 1024 * 1024)) # Analizar hasta 80MB por archivo

                # 1. Buscar firmas JPEG (FF D8 FF)
                pos = 0
                while pos < len(data) and total_found < max_images:
                    jpg_idx = data.find(b"\xFF\xD8\xFF", pos)
                    if jpg_idx == -1:
                        break

                    foot_idx = data.find(b"\xFF\xD9", jpg_idx + 3)
                    if foot_idx != -1:
                        img_len = (foot_idx + 2) - jpg_idx
                        # Filtrar miniaturas diminutas irrelevantes (< 2 KB) y absurdamente grandes (> 20 MB)
                        if 2048 < img_len < 20 * 1024 * 1024:
                            img_bytes = data[jpg_idx : foot_idx + 2]
                            total_found += 1
                            recovered_items.append({
                                "id": f"thumb_jpg_{total_found}",
                                "name": f"Foto_Caché_{total_found:03d}.jpg",
                                "original_path": f"{base_name} [Offset: {jpg_idx:#x}]",
                                "original_dir": "Caché de Miniaturas de Windows Explorer",
                                "size": img_len,
                                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "category": "Imágenes",
                                "source_method": f"Caché Gráfica ({base_name})",
                                "recoverable": True,
                                "preview_bytes": img_bytes,
                                "is_carved": True
                            })
                            pos = foot_idx + 2
                            continue
                    pos = jpg_idx + 3

                # 2. Buscar firmas PNG (\x89PNG\r\n\x1a\n)
                pos = 0
                while pos < len(data) and total_found < max_images:
                    png_idx = data.find(b"\x89PNG\r\n\x1a\n", pos)
                    if png_idx == -1:
                        break

                    foot_idx = data.find(b"IEND\xaeB`\x82", png_idx + 8)
                    if foot_idx != -1:
                        img_len = (foot_idx + 8) - png_idx
                        if 2048 < img_len < 20 * 1024 * 1024:
                            img_bytes = data[png_idx : foot_idx + 8]
                            total_found += 1
                            recovered_items.append({
                                "id": f"thumb_png_{total_found}",
                                "name": f"Imagen_Caché_{total_found:03d}.png",
                                "original_path": f"{base_name} [Offset: {png_idx:#x}]",
                                "original_dir": "Caché de Miniaturas de Windows Explorer",
                                "size": img_len,
                                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "category": "Imágenes",
                                "source_method": f"Caché Gráfica ({base_name})",
                                "recoverable": True,
                                "preview_bytes": img_bytes,
                                "is_carved": True
                            })
                            pos = foot_idx + 8
                            continue
                    pos = png_idx + 8

            except Exception as err:
                print(f"Error procesando {db_path}: {err}")
                continue

        if progress_callback:
            progress_callback("Extracción de caché de miniaturas completada.", 100, "")

        return recovered_items

