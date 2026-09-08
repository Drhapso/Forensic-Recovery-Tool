import os
import sys
import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath("."))

from core.session_manager import SessionManager, _sanitize_for_json
from core.local_db import LocalDatabase

print("=== TESTING JSON SERIALIZATION WITH DATETIME OBJECTS ===")

test_obj = {
    "str_val": "hola",
    "int_val": 42,
    "dt_val": datetime.datetime(2026, 9, 6, 17, 10, 0),
    "date_val": datetime.date(2026, 9, 6),
    "bytes_val": b"forensic_magic_bytes",
    "nested": {
        "inner_dt": datetime.datetime.now(),
        "items": [1, 2, datetime.datetime(2025, 1, 1, 12, 0, 0)]
    }
}

sanitized = _sanitize_for_json(test_obj)
print("[OK] _sanitize_for_json output:")
print(f"  dt_val -> {type(sanitized['dt_val'])}: {sanitized['dt_val']}")
print(f"  nested.inner_dt -> {type(sanitized['nested']['inner_dt'])}: {sanitized['nested']['inner_dt']}")

raw_datetime_items = [
    {
        "id": "recycle_test_001",
        "name": "Archivo_Prueba.docx",
        "original_path": r"C:\Users\Test\Documents\Archivo_Prueba.docx",
        "original_dir": r"C:\Users\Test\Documents",
        "size": 1048576,
        "date": "2026-09-06 17:00:00",
        "raw_date": datetime.datetime.now(),
        "category": "Documentos",
        "source_method": "Papelera Forense ($Recycle.Bin)",
        "recoverable": True,
        "usability_score": 95,
        "usability_tier": "high",
        "usability_label": "🌟 Alta (95%)",
        "usability_reasons": ["Documento válido"],
        "specs": {
            "timestamp": datetime.datetime.now(),
            "pages": 12
        }
    },
    {
        "id": "temp_test_002",
        "name": "Borrador.asd",
        "original_path": r"C:\Users\Test\AppData\Local\Temp\Borrador.asd",
        "size": 65536,
        "date": "2026-09-06 17:05:00",
        "raw_date": datetime.datetime(2026, 9, 6, 17, 5, 0),
        "category": "Documentos (Office AutoRecover)",
        "source_method": "Temporales y Borradores",
        "recoverable": True
    }
]

saved_path = SessionManager.save_session(
    name="Test Sesión Datetime Sanitization",
    items=raw_datetime_items,
    targets=[r"C:\Users\Test\Documents"],
    categories=["Documentos"],
    mode="deep_forensic",
    session_id="ses_test_datetime_fix"
)

print(f"[OK] Session saved without JSON serialization error to: {saved_path}")

loaded = SessionManager.load_session("ses_test_datetime_fix")
assert loaded is not None, "Error: La sesión no pudo cargarse"
assert loaded["total_items"] == 2, f"Total items mismatch: {loaded['total_items']}"
item0 = loaded["items"][0]
print(f"[OK] Loaded item 0: name='{item0['name']}', date='{item0['date']}', raw_date='{item0.get('raw_date')}'")

db_loaded = LocalDatabase.load_session("ses_test_datetime_fix")
if db_loaded:
    print(f"[OK] LocalDatabase loaded session: {db_loaded['name']} with {len(db_loaded['items'])} items")

SessionManager.delete_session("ses_test_datetime_fix")
print("[OK] Test session deleted cleanly.")

print(">>> ALL DATETIME JSON SERIALIZATION TESTS PASSED WITH 100% SUCCESS! <<<")

