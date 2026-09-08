"""
Módulo de Gestión de Sesiones de Exploración y Escaneo Incremental / Diferencial.
Permite guardar, restaurar y fusionar sesiones de recuperación, almacenando huellas digitales
(fingerprints) de archivos y sectores analizados para evitar volver a procesar datos sin cambios.
"""

import os
import json
import base64
import datetime
import glob
from typing import List, Dict, Any, Optional, Tuple

def _sanitize_for_json(obj: Any) -> Any:
    """Convierte de forma recursiva objetos no serializables (como datetime o bytes) a tipos nativos JSON."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, (bytes, bytearray)):
        return base64.b64encode(obj).decode("ascii")
    elif isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_sanitize_for_json(x) for x in obj]
    return obj

class SessionManager:
    """Gestiona el ciclo de vida de las sesiones de recuperación y la indexación diferencial."""

    SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")

    @classmethod
    def _ensure_dir(cls):
        os.makedirs(cls.SESSIONS_DIR, exist_ok=True)

    @classmethod
    def save_session(cls, 
                     name: str, 
                     items: List[Dict[str, Any]], 
                     targets: List[str], 
                     categories: List[str], 
                     mode: str, 
                     session_id: Optional[str] = None) -> str:
        """
        Guarda una sesión de exploración en formato JSON estructurado.
        Codifica las muestras de bytes de vista previa en base64 para persistencia transparente.
        """
        cls._ensure_dir()

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not session_id:
            now_slug = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            session_id = f"ses_{now_slug}"

        # Preparar elementos serializables
        serializable_items = []
        fingerprints = {}

        for item in items:
            clean_item = dict(item)
            # Codificar preview_bytes a base64 si existen
            if "preview_bytes" in clean_item and isinstance(clean_item["preview_bytes"], (bytes, bytearray)):
                clean_item["preview_base64"] = base64.b64encode(clean_item["preview_bytes"]).decode("ascii")
                del clean_item["preview_bytes"]

            # Sanitizar campos recursivamente (convirtiendo datetimes, bytes, etc.)
            clean_item = _sanitize_for_json(clean_item)

            # Generar huella digital (fingerprint) para análisis diferencial futuro
            fp_key = clean_item.get("original_path") or clean_item.get("data_source_path") or clean_item.get("name")
            if fp_key:
                fingerprints[fp_key] = {
                    "size": clean_item.get("size", 0),
                    "date": str(clean_item.get("date", "-")),
                    "id": clean_item.get("id", "")
                }

            serializable_items.append(clean_item)

        session_data = {
            "session_id": session_id,
            "name": name or f"Sesión {now_str}",
            "created_at": now_str,
            "updated_at": now_str,
            "targets": targets or [],
            "categories": categories or [],
            "mode": mode,
            "total_items": len(serializable_items),
            "total_size": sum(it.get("size", 0) for it in serializable_items),
            "fingerprints": fingerprints,
            "items": serializable_items
        }

        filepath = os.path.join(cls.SESSIONS_DIR, f"{session_id}.recovery_session.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)

        # Sincronización automática con la base de datos local SQLite
        try:
            from core.local_db import LocalDatabase
            LocalDatabase.save_session(session_data)
        except Exception:
            pass

        return filepath

    @classmethod
    def load_session(cls, session_id_or_path: str) -> Optional[Dict[str, Any]]:
        """
        Carga una sesión guardada y decodifica las muestras binarias para vista previa inmediata.
        """
        if os.path.isfile(session_id_or_path):
            filepath = session_id_or_path
        else:
            cls._ensure_dir()
            clean_id = session_id_or_path.replace(".recovery_session.json", "")
            filepath = os.path.join(cls.SESSIONS_DIR, f"{clean_id}.recovery_session.json")

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            # Restaurar preview_bytes desde preview_base64
            for item in session_data.get("items", []):
                if "preview_base64" in item and item["preview_base64"]:
                    try:
                        item["preview_bytes"] = base64.b64decode(item["preview_base64"])
                    except Exception:
                        item["preview_bytes"] = b""

            return session_data
        except Exception as e:
            print(f"Error cargando sesión desde {filepath}: {e}")
            return None

    @classmethod
    def list_saved_sessions(cls) -> List[Dict[str, Any]]:
        """Lista los metadatos resumidos de todas las sesiones guardadas en disco."""
        cls._ensure_dir()
        session_files = glob.glob(os.path.join(cls.SESSIONS_DIR, "*.recovery_session.json"))
        sessions = []

        for fp in session_files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                sessions.append({
                    "session_id": meta.get("session_id"),
                    "name": meta.get("name", "Sin Nombre"),
                    "created_at": meta.get("created_at", "-"),
                    "updated_at": meta.get("updated_at", "-"),
                    "total_items": meta.get("total_items", len(meta.get("items", []))),
                    "total_size": meta.get("total_size", 0),
                    "targets": meta.get("targets", []),
                    "categories": meta.get("categories", []),
                    "mode": meta.get("mode", ""),
                    "filepath": fp
                })
            except Exception:
                continue

        # Ordenar de más reciente a más antigua
        return sorted(sessions, key=lambda s: s.get("updated_at", ""), reverse=True)

    @classmethod
    def delete_session(cls, session_id_or_path: str) -> bool:
        """Elimina una sesión guardada."""
        clean_id = session_id_or_path.replace(".recovery_session.json", "")
        if os.path.isfile(session_id_or_path):
            clean_id = os.path.basename(session_id_or_path).replace(".recovery_session.json", "")
            filepath = session_id_or_path
        else:
            cls._ensure_dir()
            filepath = os.path.join(cls.SESSIONS_DIR, f"{clean_id}.recovery_session.json")

        try:
            from core.local_db import LocalDatabase
            LocalDatabase.delete_session(clean_id)
        except Exception:
            pass

        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except Exception:
                return False
        return False

    @classmethod
    def clear_all_sessions(cls) -> int:
        """
        Elimina todas las sesiones archivadas en disco y en la base de datos local.
        Retorna la cantidad de sesiones eliminadas.
        """
        cls._ensure_dir()
        try:
            from core.local_db import LocalDatabase
            LocalDatabase.clear_all_sessions()
        except Exception:
            pass

        session_files = glob.glob(os.path.join(cls.SESSIONS_DIR, "*.recovery_session.json"))
        count = 0
        for fp in session_files:
            try:
                if os.path.exists(fp):
                    os.remove(fp)
                count += 1
            except Exception:
                continue
        return count

    @classmethod
    def find_matching_session(cls, target_paths: List[str], categories: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Busca si existe una sesión guardada previa que coincida con las unidades o carpetas indicadas.
        """
        if not target_paths:
            return None

        norm_targets = set(os.path.normpath(p).lower() for p in target_paths)
        sessions = cls.list_saved_sessions()

        for s in sessions:
            s_targets = set(os.path.normpath(p).lower() for p in s.get("targets", []))
            # Coincidencia exacta de objetivos (evita que una sesión previa multiespacio contamine una unidad individual)
            if norm_targets == s_targets:
                return cls.load_session(s["filepath"])

        return None

    @classmethod
    def is_item_unchanged(cls, 
                          key: str, 
                          size: int, 
                          fingerprints: Dict[str, Any]) -> bool:
        """
        Comprueba si un elemento ya fue indexado previamente y conserva exactamente el mismo tamaño.
        """
        if not fingerprints or key not in fingerprints:
            return False

        known = fingerprints[key]
        return known.get("size") == size

    @classmethod
    def filter_and_merge_incremental(cls, 
                                     existing_session: Dict[str, Any], 
                                     new_items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Fusiona hallazgos nuevos con los hallazgos de una sesión previa sin duplicados.
        Retorna: (merged_items, count_new, count_updated)
        """
        merged_map = {}
        existing_items = existing_session.get("items", [])

        # 1. Registrar elementos existentes
        for item in existing_items:
            key = item.get("original_path") or item.get("data_source_path") or item.get("name")
            merged_map[key] = dict(item)

        count_new = 0
        count_updated = 0

        # 2. Incorporar novedades o actualizaciones
        for new_item in new_items:
            key = new_item.get("original_path") or new_item.get("data_source_path") or new_item.get("name")
            if key not in merged_map:
                count_new += 1
                item_copy = dict(new_item)
                item_copy["source_method"] = f"{new_item.get('source_method', '')} [Nuevo]"
                merged_map[key] = item_copy
            else:
                # Comprobar si cambió de tamaño
                if merged_map[key].get("size") != new_item.get("size"):
                    count_updated += 1
                    item_copy = dict(new_item)
                    item_copy["source_method"] = f"{new_item.get('source_method', '')} [Actualizado]"
                    merged_map[key] = item_copy

        merged_list = list(merged_map.values())
        return merged_list, count_new, count_updated

