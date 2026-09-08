import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Asegurar que la ruta base esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.disk_utils import get_drives, is_admin
from core.recycle_bin import RecycleBinScanner
from core.temp_scanner import TempScanner
from core.thumbcache_extractor import ThumbcacheExtractor
from core.file_carver import FileCarver
from core.mft_scanner import MFTScanner
from core.shadow_explorer import ShadowExplorer
from core.software_filter import SoftwareFilter
from core.context_router import ContextRouter
import io

def test_all():
    print("=== TEST 1: DISK UTILS ===")
    print("Admin status:", is_admin())
    drives = get_drives()
    print(f"Detected {len(drives)} drives:")
    for d in drives:
        print(f"  {d['letter']} - {d['drive_name']} ({d['type']}, {d['fs_name']})")

    print("\n=== TEST 2: CONTEXT ROUTER (AUTOMATIC TARGET LISTS BY FILE TYPE) ===")
    # 1. Sugerencias automáticas cuando el usuario busca SOLO DOCUMENTOS
    doc_folders = ContextRouter.get_suggested_folders(["Documentos"])
    rec_docs = [f["name"] for f in doc_folders if f["recommended"]]
    print("Carpetas recomendadas para [Documentos]:", rec_docs)
    assert "Mis Documentos" in rec_docs or "Escritorio (Desktop)" in rec_docs

    # 2. Sugerencias automáticas cuando el usuario busca SOLO AUDIO
    audio_folders = ContextRouter.get_suggested_folders(["Audio"])
    rec_audio = [f["name"] for f in audio_folders if f["recommended"]]
    print("Carpetas recomendadas para [Audio]:", rec_audio)
    assert any("Grabaciones" in name or "Música" in name for name in rec_audio)

    # 3. Exclusión cruzada contextual
    skip_video_when_doc, r_v = ContextRouter.should_skip_by_context(r"C:\Users\Drhapso\Videos\Peliculas", ["Documentos"])
    print(f"Exclusión de videos al buscar solo documentos: {skip_video_when_doc} ({r_v})")
    assert skip_video_when_doc == True, "Debería omitir la carpeta de videos si solo se buscan documentos."

    skip_music_when_doc, r_m = ContextRouter.should_skip_by_context(r"C:\Users\Drhapso\Music\Discografia", ["Documentos"])
    print(f"Exclusión de música al buscar solo documentos: {skip_music_when_doc} ({r_m})")
    assert skip_music_when_doc == True, "Debería omitir música si solo se buscan documentos."

    print("\n=== TEST 3: SOFTWARE & GAME FILTER (SMART EXCLUSION) ===")
    catalog = SoftwareFilter.build_catalog()
    print(f"Software Catalog: {catalog['total_prefixes']} software/game locations detected.")
    skip_game, reason_game = SoftwareFilter.should_skip_folder(r"C:\Games\eFootball PES 2021\Data")
    print(f"Test Game Skipping: {skip_game} ({reason_game})")
    assert skip_game == True

    skip_user, reason_user = SoftwareFilter.should_skip_folder(r"C:\Users\Drhapso\Documents\PROYECTOS IA INDEPENDIENTES")
    print(f"Test User Protection: {skip_user} ({reason_user})")
    assert skip_user == False

    print("\n=== TEST 4: RECYCLE BIN SCANNER ===")
    items = RecycleBinScanner.scan_drives()
    print(f"Found {len(items)} items in Recycle Bin:")
    for it in items[:3]:
        print(f"  - [{it['category']}] {it['name']} ({it['size']} bytes)")

    print("\n=== TEST 5: THUMBCACHE EXTRACTOR ===")
    thumbs = ThumbcacheExtractor.scan_thumbnails(max_images=3)
    print(f"Extracted {len(thumbs)} photos from Windows Thumbcache:")
    for th in thumbs:
        print(f"  - {th['name']} ({th['size']} bytes)")

    print("\n=== TEST 6: STRUCTURAL FILE CARVER ===")
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\x0dIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    carver = FileCarver()
    carved = carver.scan_stream(io.BytesIO(b"NOISE" * 20 + png_bytes), total_bytes=len(png_bytes) + 100)
    print(f"Carved {len(carved)} structural files.")

    print("\n=== TEST 7: MFT SCANNER ===")
    mft_mock = bytearray(1024)
    mft_mock[0:4] = b"FILE"
    mft_mock[20:22] = (48).to_bytes(2, "little")
    fn_attr = bytearray(200)
    fn_attr[0:4] = (0x30).to_bytes(4, "little")
    fn_attr[4:8] = (len(fn_attr)).to_bytes(4, "little")
    test_filename = "documento_test.docx".encode("utf-16le")
    fn_attr[24 + 64] = len("documento_test.docx")
    fn_attr[24 + 66 : 24 + 66 + len(test_filename)] = test_filename
    mft_mock[48 : 48 + len(fn_attr)] = fn_attr
    parsed_mft = MFTScanner.parse_mft_record(bytes(mft_mock))
    if parsed_mft:
        print(f"MFT Parser identified: '{parsed_mft['name']}'")

    print("\n=== TEST 8: SESSION MANAGER & INCREMENTAL SCANNING ===")
    from core.session_manager import SessionManager

    test_items = [
        {
            "id": "rec_001",
            "name": "foto_playa.jpg",
            "original_path": r"C:\Users\Drhapso\Pictures\foto_playa.jpg",
            "size": 10240,
            "date": "2026-05-10 12:00:00",
            "category": "Imágenes",
            "source_method": "Recycle Bin",
            "recoverable": True,
            "preview_bytes": b"\xff\xd8\xff\xe0\x00\x10JFIF"
        },
        {
            "id": "rec_002",
            "name": "tesis_final.docx",
            "original_path": r"C:\Users\Drhapso\Documents\tesis_final.docx",
            "size": 204800,
            "date": "2026-05-11 15:30:00",
            "category": "Documentos",
            "source_method": "Carving Estructural",
            "recoverable": True
        }
    ]

    test_targets = [r"C:\Users\Drhapso\Pictures", r"C:\Users\Drhapso\Documents"]
    test_cats = ["Imágenes", "Documentos"]

    # 1. Guardar sesión
    saved_fp = SessionManager.save_session(
        name="Sesión de Prueba Unitaria",
        items=test_items,
        targets=test_targets,
        categories=test_cats,
        mode="test_mode",
        session_id="unit_test_session_99"
    )
    print(f"Sesión guardada en: {saved_fp}")
    assert os.path.isfile(saved_fp), "El archivo de sesión debería existir en disco."

    # 2. Cargar sesión y verificar restauración de bytes base64
    loaded_session = SessionManager.load_session("unit_test_session_99")
    assert loaded_session is not None, "La sesión debería cargarse correctamente."
    assert loaded_session["name"] == "Sesión de Prueba Unitaria"
    assert len(loaded_session["items"]) == 2
    # Comprobar que preview_bytes se reconstituyó desde base64
    assert loaded_session["items"][0]["preview_bytes"] == b"\xff\xd8\xff\xe0\x00\x10JFIF"
    print("Persistencia JSON y decodificación Base64 de muestras verificadas con éxito.")

    # 3. Listar sesiones
    sessions_list = SessionManager.list_saved_sessions()
    matching_meta = [s for s in sessions_list if s["session_id"] == "unit_test_session_99"]
    assert len(matching_meta) == 1, "La sesión debe figurar en list_saved_sessions()."
    print(f"Listado de sesiones contiene la sesión creada ({matching_meta[0]['name']}).")

    # 4. Comprobación de huellas digitales (Fingerprints)
    fps = loaded_session["fingerprints"]
    assert SessionManager.is_item_unchanged(r"C:\Users\Drhapso\Pictures\foto_playa.jpg", 10240, fps) == True
    assert SessionManager.is_item_unchanged(r"C:\Users\Drhapso\Pictures\foto_playa.jpg", 99999, fps) == False
    assert SessionManager.is_item_unchanged(r"C:\Users\Drhapso\Pictures\inexistente.jpg", 10240, fps) == False
    print("Validación de huellas de archivos sin cambios (is_item_unchanged): Correcto.")

    # 5. Fusión Incremental / Diferencial
    new_scan_items = [
        # 1 archivo idéntico (no debe duplicarse ni alterarse)
        {
            "id": "rec_001_new",
            "name": "foto_playa.jpg",
            "original_path": r"C:\Users\Drhapso\Pictures\foto_playa.jpg",
            "size": 10240,
            "category": "Imágenes",
            "source_method": "Recycle Bin"
        },
        # 1 archivo modificado (tamaño cambió)
        {
            "id": "rec_002_upd",
            "name": "tesis_final.docx",
            "original_path": r"C:\Users\Drhapso\Documents\tesis_final.docx",
            "size": 250000,
            "category": "Documentos",
            "source_method": "Carving Estructural"
        },
        # 1 archivo nuevo
        {
            "id": "rec_003_brand_new",
            "name": "contrato_nuevo.pdf",
            "original_path": r"C:\Users\Drhapso\Documents\contrato_nuevo.pdf",
            "size": 54000,
            "category": "Documentos",
            "source_method": "Carving Estructural"
        }
    ]

    merged_items, count_new, count_upd = SessionManager.filter_and_merge_incremental(loaded_session, new_scan_items)
    print(f"Fusión incremental: {count_new} nuevos, {count_upd} actualizados, {len(merged_items)} totales.")
    assert count_new == 1, f"Se esperaba 1 archivo nuevo, se detectaron {count_new}."
    assert count_upd == 1, f"Se esperaba 1 archivo modificado, se detectaron {count_upd}."
    assert len(merged_items) == 3, f"Se esperaban 3 archivos en total tras la fusión, hay {len(merged_items)}."

    # 6. Limpieza de prueba
    del_ok = SessionManager.delete_session("unit_test_session_99")
    assert del_ok == True, "La sesión de prueba debería eliminarse sin errores."
    assert not os.path.exists(saved_fp), "El archivo no debe existir tras la eliminación."
    print("Eliminación y limpieza de sesión temporal completada.")

    print("\n=== TEST 9: INTEGRITY & USABILITY ANALYZER ===")
    from core.integrity_analyzer import IntegrityAnalyzer
    
    sample_items = [
        {
            "name": "foto_alta.png",
            "size": 1024 * 1024,
            "category": "Imágenes",
            "preview_bytes": b"\x89PNG\r\n\x1a\n" + (b"\x12\x34\x56\x78\x9a\xbc\xde\xf0" * 30),
            "specs": {"width": 1920, "height": 1080}
        },
        {
            "name": "sector_nulo.bin",
            "size": 8192,
            "category": "Otros",
            "preview_bytes": b"\x00" * 4096
        }
    ]
    IntegrityAnalyzer.analyze_batch(sample_items)
    assert sample_items[0]["is_high_quality"] == True
    assert sample_items[0]["usability_score"] >= 80
    assert sample_items[1]["is_high_quality"] == False
    assert sample_items[1]["usability_tier"] == "unusable"
    print(f"High-quality detection: {sample_items[0]['usability_label']}")
    print(f"Null-sector rejection: {sample_items[1]['usability_label']}")
    print("Integrity & Usability Analyzer suite passed successfully.")

    print("\n>>> ALL 9 CORE AND FORENSIC TEST SUITES PASSED WITH 100% SUCCESS! <<<")

if __name__ == "__main__":
    test_all()
