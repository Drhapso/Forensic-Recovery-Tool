import os
import sys
import shutil
import tempfile
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath("."))

from core.exporter import RecoveryExporter

print("=== TESTING RECOVERY EXPORTER: ORIGINAL NAMES & FOLDER TREE RECONSTRUCTION ===")

# 1. Test Sanitization
print("\n--- 1. Testing Filename and Folder Sanitization ---")
dirty_name = 'Archivo: *Inválido? / "Doc" <v1.0> | 2026.docx'
clean_name = RecoveryExporter.sanitize_filename(dirty_name)
print(f"Sanitized filename: '{dirty_name}' -> '{clean_name}'")
assert ":" not in clean_name and "*" not in clean_name and "?" not in clean_name and '"' not in clean_name
assert "<" not in clean_name and ">" not in clean_name and "|" not in clean_name

reserved_name = "CON.txt"
clean_reserved = RecoveryExporter.sanitize_filename(reserved_name)
print(f"Sanitized reserved name: '{reserved_name}' -> '{clean_reserved}'")
assert clean_reserved.lower().startswith("rec_con")

# 2. Test AutoRecover Name Cleaning
print("\n--- 2. Testing Office AutoRecover Name Cleaning ---")
auto_word = "AutoRecovery save of Balance_General.asd"
cleaned_word = RecoveryExporter.clean_autorecover_filename(auto_word)
print(f"Cleaned AutoRecover Word: '{auto_word}' -> '{cleaned_word}'")
assert cleaned_word == "Balance_General.docx", f"Expected Balance_General.docx, got {cleaned_word}"

auto_excel = "Autoguardado de Ventas_Q3.xar"
cleaned_excel = RecoveryExporter.clean_autorecover_filename(auto_excel)
print(f"Cleaned AutoRecover Excel: '{auto_excel}' -> '{cleaned_excel}'")
assert cleaned_excel == "Ventas_Q3.xlsx", f"Expected Ventas_Q3.xlsx, got {cleaned_excel}"

# 3. Test Embedded Title Extraction (OOXML synthetic)
print("\n--- 3. Testing Embedded Title Extraction (OOXML) ---")
core_xml_content = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" 
                   xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Estrategia Corporativa 2026</dc:title>
    <dc:creator>Analista Forense</dc:creator>
</cp:coreProperties>"""

docx_bytes_io = tempfile.SpooledTemporaryFile()
with zipfile.ZipFile(docx_bytes_io, "w") as zf:
    zf.writestr("docProps/core.xml", core_xml_content)
    zf.writestr("word/document.xml", b"<w:document><w:body><w:p><w:r><w:t>Hola</w:t></w:r></w:p></w:body></w:document>")

docx_bytes_io.seek(0)
synthetic_docx_data = docx_bytes_io.read()

extracted_title = RecoveryExporter.extract_embedded_title(synthetic_docx_data, ".docx")
print(f"Extracted title from OOXML: '{extracted_title}'")
assert extracted_title == "Estrategia Corporativa 2026", f"Failed to extract title, got: {extracted_title}"

# 4. Test Export Batch with Folder Tree Reconstruction & Original Names
print("\n--- 4. Testing Export Batch with Hierarchy Rebuilding ---")
test_dest = tempfile.mkdtemp(prefix="rec_test_export_")

# Create sample source files
src_temp_dir = tempfile.mkdtemp(prefix="rec_test_src_")
src_file1 = os.path.join(src_temp_dir, "real_data1.bin")
with open(src_file1, "wb") as f:
    f.write(b"CONTENIDO REAL ARCHIVO 1 - REPORTE FORENSE EXCLUSIVO")

src_file2 = os.path.join(src_temp_dir, "$R987654.docx")
with open(src_file2, "wb") as f:
    f.write(synthetic_docx_data)

items_to_export = [
    # Item A: Normal file from Recycle Bin with full original path
    {
        "id": "item_a",
        "name": "Reporte_Trimestral.pdf",
        "original_name": "Reporte_Trimestral.pdf",
        "original_path": r"C:\Users\Admin\Documents\Finanzas\Reportes\Reporte_Trimestral.pdf",
        "original_dir": r"C:\Users\Admin\Documents\Finanzas\Reportes",
        "data_source_path": src_file1,
        "size": os.path.getsize(src_file1),
        "source_method": "Papelera Forense ($Recycle.Bin)"
    },
    # Item B: Orphan $R file from Recycle Bin where original title is extracted
    {
        "id": "item_b",
        "name": "Rescatado_$R987654.docx",
        "original_path": r"D:\Proyectos\Estrategia\antiguo.docx",
        "original_dir": r"D:\Proyectos\Estrategia",
        "data_source_path": src_file2,
        "size": len(synthetic_docx_data),
        "source_method": "Papelera (Contenedor $R Huérfano Rescatado)"
    },
    # Item C: Temp file with AutoRecover name
    {
        "id": "item_c",
        "name": "AutoRecovery save of Analisis_Costos.asd",
        "original_name": "Analisis_Costos.docx",
        "original_path": r"C:\Users\Admin\AppData\Local\Microsoft\Word\AutoRecovery save of Analisis_Costos.asd",
        "original_dir": r"C:\Users\Admin\AppData\Local\Microsoft\Word",
        "data_source_path": src_file1,
        "size": os.path.getsize(src_file1),
        "source_method": "Temporales y Borradores (Office AutoRecover)"
    },
    # Item D: Carved photo with no original path
    {
        "id": "item_d",
        "name": "Foto_Recuperada_0042.jpg",
        "original_path": "[Sector Offset 0x3f4a00]",
        "original_dir": "Sectores en Crudo (JPEG Estructural)",
        "preview_bytes": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00SAMPLE\xff\xd9",
        "size": 32,
        "category": "Imágenes",
        "is_carved": True,
        "source_method": "Carving Estructural (JPEG)"
    }
]

# Run export with tree = True and names = True
summary_tree = RecoveryExporter.export_batch(
    items_to_export,
    test_dest,
    preserve_original_names=True,
    restore_folder_tree=True
)

print(f"Export Summary (Tree Mode): {summary_tree['success_count']}/{summary_tree['total']} successful, {summary_tree['folders_count']} folders created.")
assert summary_tree["success_count"] == 4, f"Expected 4 successful exports, got {summary_tree['success_count']}"

# Verify the folder hierarchy in test_dest
expected_path_a = os.path.join(test_dest, "Disco C", "Users", "Admin", "Documents", "Finanzas", "Reportes", "Reporte_Trimestral.pdf")
print(f"Checking Path A: {expected_path_a} -> Exists: {os.path.exists(expected_path_a)}")
assert os.path.exists(expected_path_a), f"File A was not created at expected tree path: {expected_path_a}"

expected_path_b = os.path.join(test_dest, "Disco D", "Proyectos", "Estrategia", "antiguo.docx")
print(f"Checking Path B: {expected_path_b} -> Exists: {os.path.exists(expected_path_b)}")
assert os.path.exists(expected_path_b), f"File B was not created at expected tree path: {expected_path_b}"

expected_path_c = os.path.join(test_dest, "Disco C", "Users", "Admin", "AppData", "Local", "Microsoft", "Word", "Analisis_Costos.docx")
print(f"Checking Path C: {expected_path_c} -> Exists: {os.path.exists(expected_path_c)}")
assert os.path.exists(expected_path_c), f"File C (cleaned name) was not created at expected tree path: {expected_path_c}"

expected_path_d = os.path.join(test_dest, "Archivos_Tallados_Sin_Ruta", "Imágenes", "Foto_Recuperada_0042.jpg")
print(f"Checking Path D: {expected_path_d} -> Exists: {os.path.exists(expected_path_d)}")
assert os.path.exists(expected_path_d), f"File D was not created at expected carved path: {expected_path_d}"

# Check report file
report_file = summary_tree["report_path"]
assert os.path.exists(report_file), "Reporte de auditoría no existe"
with open(report_file, "r", encoding="utf-8") as rf:
    report_text = rf.read()
print("\n--- Reporte de Auditoría Generado ---")
print(report_text[:600] + "...")
assert "Preservar Nombres Originales: SÍ" in report_text
assert "Reconstruir Árbol de Carpetas: SÍ" in report_text

# 5. Test Flat Export Mode (restore_folder_tree = False)
print("\n--- 5. Testing Flat Export Mode ---")
test_dest_flat = tempfile.mkdtemp(prefix="rec_test_flat_")
summary_flat = RecoveryExporter.export_batch(
    items_to_export,
    test_dest_flat,
    preserve_original_names=True,
    restore_folder_tree=False
)

assert summary_flat["success_count"] == 4
flat_files = os.listdir(test_dest_flat)
print(f"Flat folder contents ({len(flat_files)} items): {flat_files}")
assert "Reporte_Trimestral.pdf" in flat_files
assert "Analisis_Costos.docx" in flat_files
assert "antiguo.docx" in flat_files
assert "Foto_Recuperada_0042.jpg" in flat_files
assert "reporte_recuperacion.txt" in flat_files

# Cleanup
shutil.rmtree(test_dest, ignore_errors=True)
shutil.rmtree(test_dest_flat, ignore_errors=True)
shutil.rmtree(src_temp_dir, ignore_errors=True)

print("\n>>> ALL ORIGINAL NAMES & FOLDER TREE RECONSTRUCTION TESTS PASSED WITH 100% SUCCESS! <<<")

