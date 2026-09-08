import sys
import os
import struct
import zlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, r"C:\Users\Drhapso\Documents\PROYECTOS IA INDEPENDIENTES\RECUPERADOR DE DATOS")

from core.integrity_analyzer import IntegrityAnalyzer

print("=== TESTING INTEGRITY AND USABILITY ANALYZER ===")

# 1. Test High Quality Image (1080p PNG)
def make_test_png(w=1920, h=1080):
    raw_rows = b""
    for _ in range(min(h, 4)):
        raw_rows += b"\x00" + (b"\x80\x20\xFF" * min(w, 32))
    compressed = zlib.compress(raw_rows)
    png = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png += struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data))
    png += struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", zlib.crc32(b"IDAT" + compressed))
    png += struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))
    return png

png_high = make_test_png(1920, 1080)
item_high_img = {
    "name": "foto_playa_4k.png",
    "size": 2_500_000,
    "category": "Imágenes",
    "preview_bytes": png_high,
    "specs": {"width": 1920, "height": 1080}
}
res_high_img = IntegrityAnalyzer.analyze_item(item_high_img)
print(f"High-Res Image -> Score: {res_high_img['usability_score']}, Tier: {res_high_img['usability_tier']}, Label: {res_high_img['usability_label']}")
assert res_high_img["usability_score"] >= 80, f"Expected >=80, got {res_high_img['usability_score']}"
assert res_high_img["is_high_quality"] == True
assert res_high_img["usability_tier"] == "high"

# 2. Test Low Quality Microscopic Icon (16x16)
png_icon = make_test_png(16, 16)
item_icon = {
    "name": "icon_temp.png",
    "size": 512,
    "category": "Imágenes",
    "preview_bytes": png_icon,
    "specs": {"width": 16, "height": 16}
}
res_icon = IntegrityAnalyzer.analyze_item(item_icon)
print(f"Tiny Icon (16x16) -> Score: {res_icon['usability_score']}, Tier: {res_icon['usability_tier']}")
assert res_icon["usability_score"] < 70, f"Expected <70 for tiny icon, got {res_icon['usability_score']}"
assert res_icon["is_high_quality"] == False

# 3. Test Null-filled Sector (Sector Basura con 0x00)
null_data = b"\x00" * 4096
item_null = {
    "name": "sector_recuperado.bin",
    "size": 4096,
    "category": "Otros",
    "preview_bytes": null_data
}
res_null = IntegrityAnalyzer.analyze_item(item_null)
print(f"Null Sector -> Score: {res_null['usability_score']}, Tier: {res_null['usability_tier']}")
assert res_null["usability_score"] <= 10, f"Expected <=10 for null sector, got {res_null['usability_score']}"
assert res_null["usability_tier"] == "unusable"

# 4. Test Zero-byte File
item_zero = {
    "name": "archivo_vacio.doc",
    "size": 0,
    "category": "Documentos",
    "preview_bytes": b""
}
res_zero = IntegrityAnalyzer.analyze_item(item_zero)
assert res_zero["usability_score"] == 0
assert res_zero["usability_tier"] == "unusable"

# 5. Test High Quality Video (MP4 1080p con moov y mdat)
dummy_mp4 = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    b"\x00\x00\x01\x00moov\x00\x00\x00\x6ctkhd\x00\x00\x00\x00"
    b"\x00\x00\x02\x00mdat" + (b"\x12\x34\x56\x78" * 50)
)
item_video = {
    "name": "vacaciones.mp4",
    "size": 50_000_000,
    "category": "Video",
    "preview_bytes": dummy_mp4,
    "specs": {"width": 1920, "height": 1080, "duration": 12.5}
}
res_video = IntegrityAnalyzer.analyze_item(item_video)
print(f"High Quality Video -> Score: {res_video['usability_score']}, Tier: {res_video['usability_tier']}")
assert res_video["usability_score"] >= 80
assert res_video["is_high_quality"] == True

# 6. Test Readable Document vs Binary Garbage
text_content = ("Este es un documento forense recuperado con informe completo de actividades y registros financieros. " * 5).encode("utf-8")
item_doc_good = {
    "name": "balance_anual.txt",
    "size": len(text_content),
    "category": "Documentos",
    "preview_bytes": text_content
}
res_doc_good = IntegrityAnalyzer.analyze_item(item_doc_good)
print(f"Readable Text Doc -> Score: {res_doc_good['usability_score']}, Tier: {res_doc_good['usability_tier']}")
assert res_doc_good["usability_score"] >= 80
assert res_doc_good["is_high_quality"] == True

binary_garbage = bytes([i % 256 for i in range(256)]) * 4
item_doc_bad = {
    "name": "falso_texto.txt",
    "size": len(binary_garbage),
    "category": "Documentos",
    "preview_bytes": binary_garbage
}
res_doc_bad = IntegrityAnalyzer.analyze_item(item_doc_bad)
print(f"Binary Garbage as Text -> Score: {res_doc_bad['usability_score']}, Tier: {res_doc_bad['usability_tier']}")
assert res_doc_bad["usability_score"] < 40
assert res_doc_bad["is_high_quality"] == False

# 7. Test Batch Analysis
batch = [item_high_img, item_icon, item_null, item_video, item_doc_good, item_doc_bad]
IntegrityAnalyzer.analyze_batch(batch)
high_count = sum(1 for it in batch if it["is_high_quality"])
assert high_count == 3, f"Expected 3 high quality items, got {high_count}"
print(f"Batch Analysis: {high_count} of {len(batch)} cataloged as High Quality (Correct).")

print("\n>>> ALL INTEGRITY AND USABILITY ANALYZER TESTS PASSED WITH 100% SUCCESS! <<<")
