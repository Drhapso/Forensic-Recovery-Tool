"""
Módulo de Base de Datos Local SQLite con Autoconstrucción de Esquema.
Permite la operación 100% local y autónoma de la herramienta, almacenando sesiones,
inventario forense de archivos, calificaciones de usabilidad, catálogo de software y auditoría.
"""

import os
import sys
import sqlite3
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple


def get_app_data_dir() -> str:
    """
    Determina la ruta óptima para almacenar la base de datos y archivos de sesión.
    Si la aplicación está en modo portable congelado (.exe), intenta escribir en la carpeta
    local './data'; si el directorio es de solo lectura (ej. Program Files), recurre a %APPDATA%.
    """
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    local_data_dir = os.path.join(base_dir, "data")
    try:
        os.makedirs(local_data_dir, exist_ok=True)
        # Probar si es escribible
        test_file = os.path.join(local_data_dir, ".perm_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return local_data_dir
    except Exception:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        fallback = os.path.join(appdata, "RecuperadorDeDatos", "data")
        os.makedirs(fallback, exist_ok=True)
        return fallback


class LocalDatabase:
    """
    Gestor de base de datos SQLite local para la suite forense.
    Autoconstruye el esquema en su primera ejecución garantizando funcionamiento 100% autónomo.
    """

    DB_NAME = "recovery_vault.db"
    _connection = None

    @classmethod
    def get_db_path(cls) -> str:
        return os.path.join(get_app_data_dir(), cls.DB_NAME)

    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        db_path = cls.get_db_path()
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")  # Alta velocidad de escritura y lectura concurrente
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @classmethod
    def init_db(cls) -> str:
        """
        Regla de inicialización: comprueba y autoconstruye el esquema completo si no existe.
        Retorna la ruta absoluta del archivo de base de datos listo para operar.
        """
        db_path = cls.get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        with cls.get_connection() as conn:
            cursor = conn.cursor()

            # 1. TABLA: SESIONES FORENSES
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    targets_json TEXT,
                    categories_json TEXT,
                    total_items INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    fingerprints_json TEXT
                );
            """)

            # 2. TABLA: ARCHIVOS RECUPERADOS / INVENTARIO FORENSE
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recovered_items (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    extension TEXT,
                    original_path TEXT,
                    size INTEGER DEFAULT 0,
                    date TEXT,
                    category TEXT,
                    source_method TEXT,
                    recoverable INTEGER DEFAULT 1,
                    integrity_status TEXT,
                    integrity_score INTEGER DEFAULT 0,
                    usability_score INTEGER DEFAULT 0,
                    usability_tier TEXT,
                    usability_label TEXT,
                    usability_reasons_json TEXT,
                    specs_json TEXT,
                    sha256_hash TEXT,
                    preview_bytes BLOB,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
            """)

            # 3. TABLA: CATÁLOGO DE SOFTWARE / JUEGOS DETECTADOS (Caché local ultra-rápida)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS software_catalog (
                    path TEXT PRIMARY KEY,
                    category TEXT,
                    detected_at TEXT
                );
            """)

            # 4. TABLA: AUDITORÍA DE EXPORTACIONES REALIZADAS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS export_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    destination_dir TEXT NOT NULL,
                    total_files INTEGER NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    report_path TEXT,
                    details_json TEXT
                );
            """)

            # 5. TABLA: CONFIGURACIÓN Y PREFERENCIAS PORTABLES
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            # Índices para búsquedas y ordenamientos instantáneos
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_session ON recovered_items(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_usability ON recovered_items(usability_score DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON recovered_items(category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(updated_at DESC);")

            conn.commit()

        return db_path

    # ==========================================================================
    # MÉTODOS CRUD: SESIONES
    # ==========================================================================

    @classmethod
    def save_session(cls, session_data: Dict[str, Any]) -> bool:
        """Guarda o actualiza una sesión completa y sus archivos asociados en SQLite."""
        cls.init_db()
        session_id = session_data.get("session_id") or f"ses_{int(datetime.datetime.now().timestamp())}"
        name = session_data.get("name", "Sesión Sin Título")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        created_at = session_data.get("created_at", now_str)
        updated_at = session_data.get("updated_at", now_str)
        mode = session_data.get("mode", "deep_forensic")
        targets = json.dumps(session_data.get("targets", []), default=str)
        categories = json.dumps(session_data.get("categories", []), default=str)
        items = session_data.get("items", [])
        fingerprints = json.dumps(session_data.get("fingerprints", {}), default=str)

        total_items = len(items)
        total_bytes = sum(it.get("size", 0) for it in items)

        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (
                    session_id, name, created_at, updated_at, mode, targets_json,
                    categories_json, total_items, total_bytes, fingerprints_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (session_id, name, created_at, updated_at, mode, targets, categories, total_items, total_bytes, fingerprints))

            # Eliminar ítems previos de la sesión para sobreescritura limpia
            cursor.execute("DELETE FROM recovered_items WHERE session_id = ?;", (session_id,))

            # Inserción en lote de ítems
            item_rows = []
            for it in items:
                i_id = it.get("id") or f"{session_id}_{it.get('name')}_{it.get('size')}"
                ext = os.path.splitext(it.get("name", ""))[1].lower()
                reasons = json.dumps(it.get("usability_reasons", []), default=str)
                specs = json.dumps(it.get("specs", {}), default=str)
                p_bytes = it.get("preview_bytes")
                if isinstance(p_bytes, str):
                    p_bytes = p_bytes.encode("utf-8")

                item_rows.append((
                    i_id, session_id, it.get("name", ""), ext, it.get("original_path", ""),
                    it.get("size", 0), str(it.get("date", "-")), it.get("category", ""),
                    it.get("source_method", ""), 1 if it.get("recoverable", True) else 0,
                    it.get("integrity_status", "Verificado"), it.get("integrity_score", 100),
                    it.get("usability_score", 85), it.get("usability_tier", "high"),
                    it.get("usability_label", ""), reasons, specs, it.get("sha256", ""),
                    p_bytes
                ))

            cursor.executemany("""
                INSERT INTO recovered_items (
                    id, session_id, name, extension, original_path, size, date, category,
                    source_method, recoverable, integrity_status, integrity_score,
                    usability_score, usability_tier, usability_label, usability_reasons_json,
                    specs_json, sha256_hash, preview_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, item_rows)

            conn.commit()
            return True

    @classmethod
    def load_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Carga una sesión y todos sus ítems recuperados desde la base de datos local."""
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?;", (session_id,))
            s_row = cursor.fetchone()
            if not s_row:
                return None

            cursor.execute("SELECT * FROM recovered_items WHERE session_id = ? ORDER BY usability_score DESC;", (session_id,))
            item_rows = cursor.fetchall()

            items = []
            for r in item_rows:
                items.append({
                    "id": r["id"],
                    "name": r["name"],
                    "original_path": r["original_path"],
                    "size": r["size"],
                    "date": r["date"],
                    "category": r["category"],
                    "source_method": r["source_method"],
                    "recoverable": bool(r["recoverable"]),
                    "integrity_status": r["integrity_status"],
                    "integrity_score": r["integrity_score"],
                    "usability_score": r["usability_score"],
                    "usability_tier": r["usability_tier"],
                    "usability_label": r["usability_label"],
                    "usability_reasons": json.loads(r["usability_reasons_json"] or "[]"),
                    "specs": json.loads(r["specs_json"] or "{}"),
                    "sha256": r["sha256_hash"],
                    "preview_bytes": r["preview_bytes"]
                })

            return {
                "session_id": s_row["session_id"],
                "name": s_row["name"],
                "created_at": s_row["created_at"],
                "updated_at": s_row["updated_at"],
                "mode": s_row["mode"],
                "targets": json.loads(s_row["targets_json"] or "[]"),
                "categories": json.loads(s_row["categories_json"] or "[]"),
                "items": items,
                "fingerprints": json.loads(s_row["fingerprints_json"] or "{}")
            }

    @classmethod
    def list_sessions(cls) -> List[Dict[str, Any]]:
        """Lista todas las sesiones almacenadas localmente ordenadas por fecha más reciente."""
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, name, created_at, updated_at, mode, total_items, total_bytes, targets_json FROM sessions ORDER BY updated_at DESC;")
            rows = cursor.fetchall()
            result = []
            for r in rows:
                result.append({
                    "session_id": r["session_id"],
                    "name": r["name"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "mode": r["mode"],
                    "total_items": r["total_items"],
                    "total_bytes": r["total_bytes"],
                    "targets": json.loads(r["targets_json"] or "[]")
                })
            return result

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        """Elimina una sesión y sus ítems asociados de la base de datos."""
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?;", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    @classmethod
    def clear_all_sessions(cls) -> int:
        """Elimina todas las sesiones e ítems de la base de datos SQLite."""
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions;")
            cursor.execute("DELETE FROM recovered_items;")
            conn.commit()
            return cursor.rowcount

    # ==========================================================================
    # CACHÉ LOCAL DEL CATÁLOGO DE SOFTWARE
    # ==========================================================================

    @classmethod
    def save_software_catalog(cls, paths: List[str]) -> None:
        """Guarda rutas de software y juegos detectados para acelerar arranques futuros."""
        cls.init_db()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO software_catalog (path, category, detected_at)
                VALUES (?, 'Software/Juego', ?);
            """, [(p, now_str) for p in paths])
            conn.commit()

    @classmethod
    def get_software_catalog(cls) -> List[str]:
        """Recupera la lista de software/juegos catalogados de la base de datos local."""
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT path FROM software_catalog;")
            rows = cursor.fetchall()
            return [r["path"] for r in rows]

    # ==========================================================================
    # AUDITORÍA DE RECUPERACIONES
    # ==========================================================================

    @classmethod
    def log_recovery_export(cls, destination: str, file_count: int, byte_count: int, report_path: str = "", details: dict = None) -> int:
        """Registra una exportación completada en el historial de auditoría."""
        cls.init_db()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        det_str = json.dumps(details or {}, default=str)
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO export_audit (timestamp, destination_dir, total_files, total_bytes, report_path, details_json)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (now_str, destination, file_count, byte_count, report_path, det_str))
            conn.commit()
            return cursor.lastrowid

