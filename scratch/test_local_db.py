import sys
import os
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, r"C:\Users\Drhapso\Documents\PROYECTOS IA INDEPENDIENTES\RECUPERADOR DE DATOS")

from core.local_db import LocalDatabase

print("=== TESTING LOCAL DATABASE (SQLITE AUTO-SCHEMA & CRUD) ===")

# 1. Test Database Initialization and Auto-schema
db_path = LocalDatabase.init_db()
assert os.path.isfile(db_path), f"Database file should exist at {db_path}"
print(f"1. Database verified at: {db_path}")

# Verify tables exist
with LocalDatabase.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    assert "sessions" in tables
    assert "recovered_items" in tables
    assert "software_catalog" in tables
    assert "export_audit" in tables
    assert "app_config" in tables
    print(f"2. Auto-schema tables verified: {tables}")

# 2. Test Session and Recovered Items Persistence
session_test = {
    "session_id": "test_local_db_001",
    "name": "Sesión Local de Prueba SQLite",
    "mode": "deep_forensic",
    "targets": [r"C:\Users\Drhapso\Documents"],
    "categories": ["Documentos", "Imágenes"],
    "items": [
        {
            "id": "item_sql_01",
            "name": "foto_playa.png",
            "original_path": r"C:\Users\Drhapso\Pictures\foto_playa.png",
            "size": 1048576,
            "date": "2026-06-01 10:00:00",
            "category": "Imágenes",
            "source_method": "Carving Forense",
            "recoverable": True,
            "integrity_status": "Íntegro",
            "integrity_score": 100,
            "usability_score": 100,
            "usability_tier": "high",
            "usability_label": "🌟 Alta (100%)",
            "usability_reasons": ["Resolución 1080p", "Sin relleno nulo"],
            "specs": {"width": 1920, "height": 1080},
            "sha256": "abcdef1234567890",
            "preview_bytes": b"\x89PNG\r\n\x1a\n"
        }
    ],
    "fingerprints": {"k1": "fp1"}
}

saved = LocalDatabase.save_session(session_test)
assert saved == True
print("3. Session and items saved to SQLite successfully.")

# 3. Test Session Loading
loaded = LocalDatabase.load_session("test_local_db_001")
assert loaded is not None
assert loaded["name"] == "Sesión Local de Prueba SQLite"
assert len(loaded["items"]) == 1
assert loaded["items"][0]["usability_score"] == 100
assert loaded["items"][0]["usability_tier"] == "high"
assert loaded["items"][0]["specs"]["width"] == 1920
assert loaded["items"][0]["preview_bytes"] == b"\x89PNG\r\n\x1a\n"
print("4. Session reloaded from SQLite with exact types, specs, and binary preview bytes.")

# 4. Test Listing Sessions
sessions_list = LocalDatabase.list_sessions()
assert any(s["session_id"] == "test_local_db_001" for s in sessions_list)
print(f"5. Session listing verified (Total sessions in DB: {len(sessions_list)}).")

# 5. Test Software Catalog Caching
LocalDatabase.save_software_catalog([r"C:\Program Files\App1", r"C:\Games\Game2"])
cached = LocalDatabase.get_software_catalog()
assert r"C:\Program Files\App1" in cached
assert r"C:\Games\Game2" in cached
print("6. Software catalog caching verified.")

# 6. Test Export Audit Logging
audit_id = LocalDatabase.log_recovery_export(
    destination=r"D:\Recuperados",
    file_count=1,
    byte_count=1048576,
    report_path=r"D:\Recuperados\reporte.txt",
    details={"mode": "test"}
)
assert audit_id > 0
print(f"7. Export audit logged with ID #{audit_id}.")

# 7. Test Session Deletion
deleted = LocalDatabase.delete_session("test_local_db_001")
assert deleted == True
assert LocalDatabase.load_session("test_local_db_001") is None
# Check cascade
with LocalDatabase.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM recovered_items WHERE session_id = 'test_local_db_001';")
    assert cursor.fetchone()[0] == 0
print("8. Session deletion and foreign key cascade verified.")

print("\n>>> ALL LOCAL DATABASE TESTS PASSED WITH 100% SUCCESS! <<<")

