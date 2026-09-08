import sys
import os
from PyQt5.QtWidgets import QApplication

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, r"C:\Users\Drhapso\Documents\PROYECTOS IA INDEPENDIENTES\RECUPERADOR DE DATOS")

from ui.results_table import ResultsTable
from ui.preview_widget import PreviewWidget
from core.integrity_analyzer import IntegrityAnalyzer

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

print("=== TESTING QUALITY AND USABILITY IN UI (TABLE & PREVIEW) ===")

# Create sample test items
test_items = [
    {
        "id": "item_01",
        "name": "foto_playa_4k.png",
        "size": 5_000_000,
        "category": "Imágenes",
        "date": "2026-06-01 12:00:00",
        "original_path": r"C:\Users\Drhapso\Pictures\foto_playa_4k.png",
        "source_method": "Carving Forense",
        "recoverable": True,
        "usability_score": 100,
        "usability_tier": "high",
        "is_high_quality": True,
        "is_usable": True,
        "usability_label": "🌟 Alta (100%)",
        "usability_reasons": ["Resolución 4K", "Cabecera PNG válida"]
    },
    {
        "id": "item_02",
        "name": "icono_microscopico.png",
        "size": 512,
        "category": "Imágenes",
        "date": "2026-06-01 12:05:00",
        "original_path": r"C:\Users\Drhapso\Pictures\icono_microscopico.png",
        "source_method": "Thumbcache",
        "recoverable": True,
        "usability_score": 30,
        "usability_tier": "low",
        "is_high_quality": False,
        "is_usable": False,
        "usability_label": "🟠 Baja (30%)",
        "usability_reasons": ["Resolución microscópica (16x16 px)"]
    },
    {
        "id": "item_03",
        "name": "sector_vacio.bin",
        "size": 4096,
        "category": "Otros",
        "date": "2026-06-01 12:10:00",
        "original_path": r"C:\Users\Drhapso\Downloads\sector_vacio.bin",
        "source_method": "MFT Scanner",
        "recoverable": False,
        "usability_score": 5,
        "usability_tier": "unusable",
        "is_high_quality": False,
        "is_usable": False,
        "usability_label": "🔴 Inútil (5%)",
        "usability_reasons": ["Sector con 100% relleno de ceros"]
    },
    {
        "id": "item_04",
        "name": "contrato_firmado.docx",
        "size": 250_000,
        "category": "Documentos",
        "date": "2026-06-01 12:15:00",
        "original_path": r"C:\Users\Drhapso\Documents\contrato_firmado.docx",
        "source_method": "Papelera Forense",
        "recoverable": True,
        "usability_score": 95,
        "usability_tier": "high",
        "is_high_quality": True,
        "is_usable": True,
        "usability_label": "🌟 Alta (95%)",
        "usability_reasons": ["Estructura OOXML íntegra", "Texto legible"]
    },
    {
        "id": "item_05",
        "name": "clip_video.mp4",
        "size": 35_000_000,
        "category": "Video",
        "date": "2026-06-01 12:20:00",
        "original_path": r"C:\Users\Drhapso\Videos\clip_video.mp4",
        "source_method": "Carving Forense",
        "recoverable": True,
        "usability_score": 90,
        "usability_tier": "high",
        "is_high_quality": True,
        "is_usable": True,
        "usability_label": "🌟 Alta (90%)",
        "usability_reasons": ["Resolución 1080p", "Duración 15s", "Átomos sincronizados"]
    },
    {
        "id": "item_06",
        "name": "audio_fragmento.wav",
        "size": 45_000,
        "category": "Audio",
        "date": "2026-06-01 12:25:00",
        "original_path": r"C:\Users\Drhapso\Music\audio_fragmento.wav",
        "source_method": "Carving Forense",
        "recoverable": True,
        "usability_score": 60,
        "usability_tier": "medium",
        "is_high_quality": False,
        "is_usable": True,
        "usability_label": "🟡 Media (60%)",
        "usability_reasons": ["Clip de audio corto (1.5s)"]
    }
]

table = ResultsTable()
table.set_items(test_items)
assert table.table.rowCount() == 6
assert table.table.columnCount() == 9
print(f"Table initialized with {table.table.rowCount()} rows and {table.table.columnCount()} columns.")

# Test Column 3 (Calidad / Usabilidad)
col3_header = table.table.horizontalHeaderItem(3).text()
assert "Calidad" in col3_header
row0_name = table.table.item(0, 1).text()
row0_quality = table.table.item(0, 3).text()
assert any(sym in row0_quality for sym in ["🌟", "🟡", "🟠", "🔴"])
print(f"Column 3 header is '{col3_header}', row 0 ('{row0_name}') displays quality '{row0_quality}' (Correct).")

# Test Filter by High Quality Only
print("\nTesting Filter: Solo Alta Calidad...")
idx_high = table.combo_quality.findData("high")
assert idx_high >= 0
table.combo_quality.setCurrentIndex(idx_high)
assert table.table.rowCount() == 3, f"Expected 3 high quality rows, got {table.table.rowCount()}"
print(f"High Quality filter correctly returned {table.table.rowCount()} items (4K photo, Word doc, MP4 video).")

# Test Filter: Usable (High + Medium)
print("\nTesting Filter: Calidad Media y Alta...")
idx_usable = table.combo_quality.findData("usable")
table.combo_quality.setCurrentIndex(idx_usable)
assert table.table.rowCount() == 4, f"Expected 4 usable rows, got {table.table.rowCount()}"
print(f"Usable filter correctly returned {table.table.rowCount()} items.")

# Test Filter: Hide Junk (< 20%)
print("\nTesting Filter: Ocultar Inutilizables...")
idx_hide = table.combo_quality.findData("hide_junk")
table.combo_quality.setCurrentIndex(idx_hide)
assert table.table.rowCount() == 5, f"Expected 5 items (excluding null sector), got {table.table.rowCount()}"
print(f"Hide Junk filter correctly excluded the 0x00 null sector.")

# Reset Filter
table.combo_quality.setCurrentIndex(0)
assert table.table.rowCount() == 6

# Test Sort by Quality Descending
print("\nTesting Sort: Calidad Mayor a Menor...")
idx_sort_q = table.combo_sort.findData("quality_desc")
table.combo_sort.setCurrentIndex(idx_sort_q)
first_score = table.filtered_items[0]["usability_score"]
last_score = table.filtered_items[-1]["usability_score"]
assert first_score >= 90, f"Expected top score >=90, got {first_score}"
assert last_score <= 10, f"Expected bottom score <=10, got {last_score}"
print(f"Sort Quality Descending: First={table.filtered_items[0]['name']} ({first_score}%), Last={table.filtered_items[-1]['name']} ({last_score}%).")

# Test Action Button: Seleccionar Solo Alta Calidad
print("\nTesting Button: Seleccionar Solo Alta Calidad...")
table._select_high_quality_checks()
selected = table.get_selected_items()
assert len(selected) == 3, f"Expected 3 selected high quality items, got {len(selected)}"
selected_names = [it["name"] for it in selected]
assert "foto_playa_4k.png" in selected_names
assert "contrato_firmado.docx" in selected_names
assert "clip_video.mp4" in selected_names
assert "icono_microscopico.png" not in selected_names
assert "sector_vacio.bin" not in selected_names
print(f"Selected items with High Quality button: {selected_names} (100% correct, junk discarded).")

# Test PreviewWidget Usability Card
print("\nTesting PreviewWidget Usability Diagnostic Banner...")
preview = PreviewWidget()
preview.load_item(test_items[0])
assert not preview.frame_usability.isHidden()
assert "ALTA" in preview.lbl_usability_badge.text()
assert "Resolución 4K" in preview.lbl_usability_details.text()
print(f"PreviewWidget Usability Card verified: '{preview.lbl_usability_badge.text()}'")

preview.load_item(test_items[2]) # Sector vacío
assert not preview.frame_usability.isHidden()
assert "INUTILIZABLE" in preview.lbl_usability_badge.text() or "BASURA" in preview.lbl_usability_badge.text()
print(f"PreviewWidget correctly diagnosed unusable sector: '{preview.lbl_usability_badge.text()}'")

preview.clear()
assert preview.frame_usability.isHidden()
print("PreviewWidget cleared and reset cleanly.")

print("\n>>> ALL QUALITY AND USABILITY UI TESTS PASSED WITH 100% SUCCESS! <<<")
