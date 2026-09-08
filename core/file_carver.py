"""
Motor Avanzado de Recuperación de Archivos por Firmas Binarias (File Carving Estructural).
Incluye validación matemática de longitud de contenedores (cajas MP4, bloques RIFF, chunks PNG,
estructuras ZIP/OOXML, páginas SQLite) y una biblioteca exhaustiva de firmas forenses.
"""

import os
import struct
import io
import zipfile
import zlib
import hashlib
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Callable, Tuple

# Extensiones de contenedores de imágenes de disco y volcados forenses
FORENSIC_CONTAINER_EXTS = {
    ".raw", ".dd", ".img", ".vhd", ".vhdx", ".dmp", ".bin", 
    ".iso", ".vmdk", ".dmg", ".e01", ".aff"
}

# ==============================================================================
# PARSERS ESTRUCTURALES AVANZADOS (RECONSTRUCCIÓN DE MÁXIMA INTEGRIDAD)
# ==============================================================================

def parse_jpeg_structure(data: bytes, offset: int, max_limit: int = 80 * 1024 * 1024) -> Optional[Tuple[int, Dict[str, Any], int, str]]:
    """
    Analiza la estructura interna de un archivo JPEG analizando la secuencia de marcadores (SOI, APPx, DQT, DHT, SOF, SOS, EOI).
    Omite marcadores en miniaturas EXIF y busca el verdadero fin de flujo EOI (FF D9).
    Retorna: (longitud_bytes, diccionario_specs, score_integridad, estado_integridad)
    """
    if len(data) - offset < 4 or data[offset : offset + 2] != b"\xff\xd8":
        return None

    pos = offset + 2
    limit = min(len(data), offset + max_limit)
    specs = {"format": "JPEG", "width": 0, "height": 0, "channels": 3, "progressive": False}
    in_scan = False

    while pos < limit:
        if not in_scan:
            # Buscar el siguiente marcador 0xFF
            while pos < limit and data[pos] != 0xFF:
                pos += 1
            while pos < limit and data[pos] == 0xFF:
                pos += 1

            if pos >= limit:
                break

            marker = data[pos]
            pos += 1

            # Marcadores sin payload de longitud
            if marker == 0xD8:  # SOI anidado (ej. miniatura EXIF)
                continue
            elif marker == 0xD9:  # EOI
                return pos - offset, specs, 100, "Íntegro (100%)"
            elif 0xD0 <= marker <= 0xD7:  # Marcadores de reinicio RSTn
                continue
            elif marker == 0x00 or marker == 0xFF:
                continue

            # Marcadores con encabezado de longitud de 2 bytes
            if pos + 2 > limit:
                break
            seg_len = struct.unpack(">H", data[pos : pos + 2])[0]
            if seg_len < 2:
                break

            # SOF0, SOF2 (Start of Frame - Dimensiones reales de la imagen)
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                if pos + 7 <= limit:
                    specs["height"] = struct.unpack(">H", data[pos + 3 : pos + 5])[0]
                    specs["width"] = struct.unpack(">H", data[pos + 5 : pos + 7])[0]
                    specs["channels"] = data[pos + 7] if pos + 7 < limit else 3
                    if marker == 0xC2:
                        specs["progressive"] = True

            # SOS (Start of Scan - Inicio del flujo comprimido de imagen)
            if marker == 0xDA:
                in_scan = True
                pos += seg_len
                continue

            pos += seg_len
        else:
            # Dentro del flujo comprimido de entropía (Scan bitstream)
            ff_idx = data.find(b"\xff", pos, limit)
            if ff_idx == -1 or ff_idx + 1 >= limit:
                break
            next_b = data[ff_idx + 1]
            if next_b == 0x00:
                # Byte-stuffing de 0xFF literal
                pos = ff_idx + 2
            elif 0xD0 <= next_b <= 0xD7:
                # Marcadores de reinicio RSTn
                pos = ff_idx + 2
            elif next_b == 0xD9:
                # EOI legítimo del final de la imagen
                total = (ff_idx + 2) - offset
                return total, specs, 100, "Íntegro (100%)"
            elif next_b == 0xDA:
                # Siguiente escaneo (JPEG progresivo)
                pos = ff_idx + 2
                in_scan = False
            else:
                pos = ff_idx + 1

    # Si se encontraron dimensiones válidas pero el archivo se truncó antes del EOI
    if specs["width"] > 0 and specs["height"] > 0 and pos > offset + 1024:
        return pos - offset, specs, 80, "Estructura Parcial (Truncado)"
    return None

def parse_png_structure(data: bytes, offset: int, max_limit: int = 100 * 1024 * 1024) -> Optional[Tuple[int, Dict[str, Any], int, str]]:
    """
    Analiza la estructura PNG completa con verificación matemática de chunks y CRC32.
    """
    if len(data) - offset < 8 or data[offset : offset + 8] != b"\x89PNG\r\n\x1a\n":
        return None

    pos = offset + 8
    limit = min(len(data), offset + max_limit)
    specs = {"format": "PNG", "width": 0, "height": 0, "bit_depth": 8, "color_type": "RGB"}
    color_types = {0: "Grises", 2: "RGB", 3: "Paleta Indexada", 4: "Grises + Alpha", 6: "RGBA"}
    crc_valid = True

    while pos + 12 <= limit:
        chunk_len = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]

        if chunk_len > max_limit or pos + 12 + chunk_len > limit:
            break

        chunk_data = data[pos + 8 : pos + 8 + chunk_len]
        stored_crc = struct.unpack(">I", data[pos + 8 + chunk_len : pos + 12 + chunk_len])[0]
        calc_crc = zlib.crc32(data[pos + 4 : pos + 8 + chunk_len])

        if stored_crc != calc_crc:
            crc_valid = False

        if chunk_type == b"IHDR" and chunk_len >= 13:
            specs["width"] = struct.unpack(">I", chunk_data[0:4])[0]
            specs["height"] = struct.unpack(">I", chunk_data[4:8])[0]
            specs["bit_depth"] = chunk_data[8]
            specs["color_type"] = color_types.get(chunk_data[9], "RGB")

        pos += 12 + chunk_len

        if chunk_type == b"IEND":
            total = pos - offset
            status = "Íntegro (100%)" if crc_valid else "Válido (CRC Advertencia)"
            score = 100 if crc_valid else 90
            return total, specs, score, status

    if specs["width"] > 0 and pos > offset + 33:
        return pos - offset, specs, 80, "Estructura Parcial (Truncado)"
    return None

def parse_mp4_structure(data: bytes, offset: int, max_limit: int = 2 * 1024 * 1024 * 1024) -> Optional[Tuple[int, Dict[str, Any], int, str]]:
    """
    Analiza la cadena de cajas ATOM de MP4/MOV/M4V/M4A extrayendo resolución 1080p/4K y duración.
    """
    if len(data) - offset < 16:
        return None

    pos = offset
    limit = min(len(data), offset + max_limit)
    total_size = 0
    valid_boxes = {b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide", b"uuid", b"meta", b"styp", b"sidx"}
    specs = {"format": "MP4/MOV", "width": 0, "height": 0, "duration": 0.0, "brand": "isom"}
    seen_ftyp = False
    seen_mdat = False
    seen_moov = False

    while pos + 8 <= limit:
        box_size = struct.unpack(">I", data[pos : pos + 4])[0]
        box_type = data[pos + 4 : pos + 8]

        if box_size == 1:
            if pos + 16 > limit:
                break
            box_size = struct.unpack(">Q", data[pos + 8 : pos + 16])[0]
            hdr_len = 16
        elif box_size == 0:
            box_size = limit - pos
            hdr_len = 8
        elif box_size < 8:
            break
        else:
            hdr_len = 8

        if box_type == b"ftyp":
            seen_ftyp = True
            if pos + 12 <= limit:
                specs["brand"] = data[pos + 8 : pos + 12].decode("latin-1", errors="replace").strip()

        if box_type == b"mdat":
            seen_mdat = True

        if box_type == b"moov":
            seen_moov = True
            # Inspeccionar dentro de moov para mvhd y tkhd
            moov_end = min(pos + box_size, limit)
            m_pos = pos + hdr_len
            while m_pos + 8 <= moov_end:
                sub_size = struct.unpack(">I", data[m_pos : m_pos + 4])[0]
                sub_type = data[m_pos + 4 : m_pos + 8]
                if sub_size < 8 or m_pos + sub_size > moov_end:
                    break

                if sub_type == b"mvhd":
                    ver = data[m_pos + 8]
                    if ver == 0 and m_pos + 28 <= moov_end:
                        timescale = struct.unpack(">I", data[m_pos + 20 : m_pos + 24])[0]
                        dur = struct.unpack(">I", data[m_pos + 24 : m_pos + 28])[0]
                        if timescale > 0:
                            specs["duration"] = round(dur / timescale, 2)
                    elif ver == 1 and m_pos + 36 <= moov_end:
                        timescale = struct.unpack(">I", data[m_pos + 28 : m_pos + 32])[0]
                        dur = struct.unpack(">Q", data[m_pos + 32 : m_pos + 40])[0]
                        if timescale > 0:
                            specs["duration"] = round(dur / timescale, 2)

                if sub_type == b"tkhd":
                    if m_pos + 92 <= moov_end:
                        w_fixed = struct.unpack(">I", data[m_pos + 84 : m_pos + 88])[0]
                        h_fixed = struct.unpack(">I", data[m_pos + 88 : m_pos + 92])[0]
                        w = w_fixed >> 16
                        h = h_fixed >> 16
                        if w > 0 and h > 0:
                            specs["width"] = w
                            specs["height"] = h

                m_pos += sub_size

        total_size += box_size
        pos += box_size

        if pos < limit and pos + 8 <= limit:
            next_type = data[pos + 4 : pos + 8]
            if next_type not in valid_boxes and seen_ftyp and (seen_mdat or seen_moov):
                break

    if seen_ftyp and total_size > 128:
        is_complete = seen_ftyp and seen_moov and seen_mdat
        status = "Íntegro (100%)" if is_complete else "Estructura Parcial (moov o mdat faltante)"
        score = 100 if is_complete else 80
        return total_size, specs, score, status

    return None

def parse_riff_structure(data: bytes, offset: int) -> Optional[Tuple[int, str, str, str, Dict[str, Any], int, str]]:
    """Calcula el tamaño exacto e inspecciona especificaciones de audio y video RIFF (WAV, WebP, AVI)."""
    if len(data) - offset < 12 or data[offset : offset + 4] != b"RIFF":
        return None
    try:
        riff_len = struct.unpack("<I", data[offset + 4 : offset + 8])[0]
        total = riff_len + 8
        if not (64 < total <= 1024 * 1024 * 1024):
            return None

        form_type = data[offset + 8 : offset + 12]
        specs = {"format": "RIFF"}
        score = 100
        status = "Íntegro (100%)"

        if form_type == b"WAVE":
            ext = ".wav"
            cat = "Audio"
            desc = "Audio WAV"
            fmt_pos = data.find(b"fmt ", offset + 12, min(offset + 1024, len(data)))
            if fmt_pos != -1 and fmt_pos + 24 <= len(data):
                audio_fmt = struct.unpack("<H", data[fmt_pos + 8 : fmt_pos + 10])[0]
                channels = struct.unpack("<H", data[fmt_pos + 10 : fmt_pos + 12])[0]
                sample_rate = struct.unpack("<I", data[fmt_pos + 12 : fmt_pos + 16])[0]
                bits = struct.unpack("<H", data[fmt_pos + 22 : fmt_pos + 24])[0]
                specs.update({
                    "channels": "Estéreo" if channels == 2 else ("Mono" if channels == 1 else f"{channels} can."),
                    "sample_rate": f"{sample_rate} Hz",
                    "bits": f"{bits} bits",
                    "audio_format": "PCM" if audio_fmt == 1 else "Comprimido"
                })
                data_pos = data.find(b"data", fmt_pos + 16, min(offset + 2048, len(data)))
                if data_pos != -1:
                    data_bytes = struct.unpack("<I", data[data_pos + 4 : data_pos + 8])[0]
                    bytes_per_sec = sample_rate * channels * (bits // 8) if bits else 0
                    if bytes_per_sec > 0:
                        specs["duration"] = round(data_bytes / bytes_per_sec, 2)
            return total, ext, cat, desc, specs, score, status

        elif form_type == b"WEBP":
            ext = ".webp"
            cat = "Imágenes"
            desc = "Imagen WebP"
            sub = data[offset + 12 : offset + 16]
            if sub == b"VP8 " and len(data) >= offset + 30:
                w = struct.unpack("<H", data[offset + 26 : offset + 28])[0] & 0x3FFF
                h = struct.unpack("<H", data[offset + 28 : offset + 30])[0] & 0x3FFF
                specs["width"] = w
                specs["height"] = h
            elif sub == b"VP8X" and len(data) >= offset + 30:
                w = struct.unpack("<I", data[offset + 24 : offset + 27] + b"\x00")[0] + 1
                h = struct.unpack("<I", data[offset + 27 : offset + 30] + b"\x00")[0] + 1
                specs["width"] = w
                specs["height"] = h
            return total, ext, cat, desc, specs, score, status

        elif form_type == b"AVI ":
            ext = ".avi"
            cat = "Video"
            desc = "Video AVI"
            avih_pos = data.find(b"avih", offset + 12, min(offset + 512, len(data)))
            if avih_pos != -1 and avih_pos + 48 <= len(data):
                usec = struct.unpack("<I", data[avih_pos + 8 : avih_pos + 12])[0]
                tot_frames = struct.unpack("<I", data[avih_pos + 24 : avih_pos + 28])[0]
                w = struct.unpack("<I", data[avih_pos + 40 : avih_pos + 44])[0]
                h = struct.unpack("<I", data[avih_pos + 44 : avih_pos + 48])[0]
                specs["width"] = w
                specs["height"] = h
                if usec > 0:
                    fps = round(1000000 / usec, 2)
                    specs["fps"] = fps
                    specs["duration"] = round(tot_frames / fps, 2) if fps else 0
            return total, ext, cat, desc, specs, score, status

    except Exception:
        pass
    return None

def parse_gif_structure(data: bytes, offset: int) -> Optional[Tuple[int, Dict[str, Any], int, str]]:
    """Calcula el tamaño exacto y especificaciones para imágenes GIF."""
    if len(data) - offset < 13:
        return None
    sig = data[offset : offset + 6]
    if sig not in (b"GIF87a", b"GIF89a"):
        return None

    w = struct.unpack("<H", data[offset + 6 : offset + 8])[0]
    h = struct.unpack("<H", data[offset + 8 : offset + 10])[0]
    specs = {"format": sig.decode("ascii"), "width": w, "height": h}

    trailer_pos = data.find(b"\x3B", offset + 13)
    if trailer_pos != -1:
        total = (trailer_pos + 1) - offset
        return total, specs, 100, "Íntegro (100%)"
    return None

def parse_bmp_structure(data: bytes, offset: int) -> Optional[Tuple[int, Dict[str, Any], int, str]]:
    """Calcula el tamaño exacto y resolución para imágenes BMP."""
    if len(data) - offset < 26 or data[offset : offset + 2] != b"BM":
        return None
    try:
        bmp_len = struct.unpack("<I", data[offset + 2 : offset + 6])[0]
        if 54 < bmp_len < 100 * 1024 * 1024:
            w = struct.unpack("<i", data[offset + 18 : offset + 22])[0]
            h = abs(struct.unpack("<i", data[offset + 22 : offset + 26])[0])
            specs = {"format": "BMP", "width": w, "height": h}
            return bmp_len, specs, 100, "Íntegro (100%)"
    except Exception:
        pass
    return None

def get_sqlite_exact_size(data: bytes, offset: int) -> Optional[int]:
    """Calcula el tamaño exacto de una base de datos SQLite."""
    if len(data) - offset < 100 or not data[offset:].startswith(b"SQLite format 3\x00"):
        return None
    try:
        page_size = struct.unpack(">H", data[offset + 16 : offset + 18])[0]
        if page_size == 1:
            page_size = 65536
        page_count = struct.unpack(">I", data[offset + 28 : offset + 32])[0]
        if page_size >= 512 and page_count > 0:
            total = page_size * page_count
            if total <= 1024 * 1024 * 1024:
                return total
    except Exception:
        pass
    return None

def get_zip_exact_size(data: bytes, offset: int, max_limit: int = 300 * 1024 * 1024) -> Optional[int]:
    """Localiza el registro End of Central Directory (EOCD) de un archivo ZIP/Office."""
    limit = min(len(data), offset + max_limit)
    window = data[offset:limit]
    eocd_sig = b"PK\x05\x06"

    eocd_pos = window.rfind(eocd_sig)
    if eocd_pos != -1 and eocd_pos + 22 <= len(window):
        comment_len = struct.unpack("<H", window[eocd_pos + 20 : eocd_pos + 22])[0]
        total_len = eocd_pos + 22 + comment_len
        return total_len
    return None

def extract_office_preview_text(data: bytes) -> str:
    """Extrae texto legible real desde documentos Word, Excel o PowerPoint recuperados."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            namelist = zf.namelist()
            if "word/document.xml" in namelist:
                raw_xml = zf.read("word/document.xml")
                root = ET.fromstring(raw_xml)
                parts = []
                for elem in root.iter():
                    if elem.tag.endswith("}t") and elem.text:
                        parts.append(elem.text)
                return " ".join(parts)[:3000]
            elif "xl/sharedStrings.xml" in namelist:
                raw_xml = zf.read("xl/sharedStrings.xml")
                root = ET.fromstring(raw_xml)
                parts = []
                for elem in root.iter():
                    if elem.tag.endswith("}t") and elem.text:
                        parts.append(elem.text)
                return "\n".join(parts[:150])
            elif any(name.startswith("ppt/slides/slide") for name in namelist):
                slides = [n for n in namelist if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
                parts = []
                for s in sorted(slides)[:3]:
                    raw_xml = zf.read(s)
                    root = ET.fromstring(raw_xml)
                    for elem in root.iter():
                        if elem.tag.endswith("}t") and elem.text:
                            parts.append(elem.text)
                return "\n".join(parts[:150])
            elif "content.xml" in namelist:
                raw_xml = zf.read("content.xml")
                try:
                    root = ET.fromstring(raw_xml)
                    parts = [elem.text.strip() for elem in root.iter() if elem.text and elem.text.strip()]
                    if parts:
                        return " ".join(parts)[:3000]
                except Exception:
                    pass
                import re
                txt = re.sub(r"<[^>]+>", " ", raw_xml.decode("utf-8", "ignore"))
                return " ".join(txt.split())[:3000]
    except Exception:
        pass
    return ""

def refine_zip_content(data: bytes) -> tuple:
    """Inspecciona el contenido del ZIP para clasificar DOCX, XLSX, PPTX, ODF (ODT, ODS, ODP, ODG, EPUB), APK, JAR o ZIP."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            namelist = zf.namelist()
            if "mimetype" in namelist:
                try:
                    mt = zf.read("mimetype").decode("utf-8", "ignore").strip()
                    if "vnd.oasis.opendocument.text" in mt:
                        return ".odt", "Documento LibreOffice Writer (ODT)", "Documentos"
                    elif "vnd.oasis.opendocument.spreadsheet" in mt:
                        return ".ods", "Hoja de Cálculo LibreOffice Calc (ODS)", "Documentos"
                    elif "vnd.oasis.opendocument.presentation" in mt:
                        return ".odp", "Presentación LibreOffice Impress (ODP)", "Documentos"
                    elif "vnd.oasis.opendocument.graphics" in mt:
                        return ".odg", "Dibujo LibreOffice Draw (ODG)", "Documentos"
                    elif "epub+zip" in mt:
                        return ".epub", "Libro Electrónico EPUB", "Documentos"
                except Exception:
                    pass
            if any(name.startswith("word/") for name in namelist):
                return ".docx", "Documento Word (DOCX)", "Documentos"
            elif any(name.startswith("xl/") for name in namelist):
                return ".xlsx", "Hoja de Cálculo Excel (XLSX)", "Documentos"
            elif any(name.startswith("ppt/") for name in namelist):
                return ".pptx", "Presentación PowerPoint (PPTX)", "Documentos"
            elif "content.xml" in namelist and ("META-INF/manifest.xml" in namelist or "styles.xml" in namelist):
                return ".odt", "Documento Abierto OpenDocument (ODT)", "Documentos"
            elif "AndroidManifest.xml" in namelist:
                return ".apk", "Paquete Android (APK)", "Otros"
            elif any(name.startswith("META-INF/") for name in namelist):
                return ".jar", "Paquete Java (JAR)", "Otros"
    except Exception:
        pass
    return ".zip", "Archivo Comprimido (ZIP)", "Comprimidos"

# Catálogo complementario de firmas estáticas (sin JPEG ni GIF, que ahora son estructurales)
SIGNATURE_CATALOG = [
    # Imágenes avanzadas
    {"name": "Photoshop PSD", "ext": ".psd", "cat": "Imágenes", "header": b"8BPS", "footer": None, "max": 100 * 1024 * 1024},
    {"name": "TIFF Image (LE)", "ext": ".tiff", "cat": "Imágenes", "header": b"II*\x00", "footer": None, "max": 50 * 1024 * 1024},
    {"name": "TIFF Image (BE)", "ext": ".tiff", "cat": "Imágenes", "header": b"MM\x00*", "footer": None, "max": 50 * 1024 * 1024},
    # Documentos
    {"name": "PDF Document", "ext": ".pdf", "cat": "Documentos", "header": b"%PDF-", "footer": b"%%EOF", "max": 150 * 1024 * 1024},
    {"name": "Documento OLE2 (DOC/XLS/PPT)", "ext": ".doc", "cat": "Documentos", "header": b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1", "footer": None, "max": 80 * 1024 * 1024},
    {"name": "Documento Rich Text (RTF)", "ext": ".rtf", "cat": "Documentos", "header": b"{\\rtf", "footer": b"}", "max": 30 * 1024 * 1024},
    # Audio y Video
    {"name": "Audio FLAC Lossless", "ext": ".flac", "cat": "Audio", "header": b"fLaC", "footer": None, "max": 80 * 1024 * 1024},
    {"name": "Audio OGG Vorbis", "ext": ".ogg", "cat": "Audio", "header": b"OggS", "footer": None, "max": 80 * 1024 * 1024},
    {"name": "Audio MP3 (ID3)", "ext": ".mp3", "cat": "Audio", "header": b"ID3", "footer": None, "max": 40 * 1024 * 1024},
    {"name": "Video MKV / WebM", "ext": ".mkv", "cat": "Video", "header": b"\x1A\x45\xDF\xA3", "footer": None, "max": 300 * 1024 * 1024},
    # Comprimidos
    {"name": "7-Zip Archive", "ext": ".7z", "cat": "Comprimidos", "header": b"7z\xBC\xAF\x27\x1C", "footer": None, "max": 300 * 1024 * 1024},
    {"name": "RAR Archive v4", "ext": ".rar", "cat": "Comprimidos", "header": b"Rar!\x1A\x07\x00", "footer": None, "max": 300 * 1024 * 1024},
    {"name": "RAR Archive v5", "ext": ".rar", "cat": "Comprimidos", "header": b"Rar!\x1A\x07\x01\x00", "footer": None, "max": 300 * 1024 * 1024},
    {"name": "GZip Compressed", "ext": ".gz", "cat": "Comprimidos", "header": b"\x1F\x8B\x08", "footer": None, "max": 100 * 1024 * 1024}
]

class FileCarver:
    """Motor forense de alto rendimiento para tallado por firmas binarias."""

    def __init__(self, chunk_size: int = 4 * 1024 * 1024):
        self.chunk_size = chunk_size  # Bloques de 4MB para máxima velocidad
        self.is_cancelled = False
        self.global_carved_counter = 0

    def cancel(self):
        self.is_cancelled = True

    def scan_stream(self, 
                    stream, 
                    total_bytes: int,
                    selected_categories: Optional[List[str]] = None,
                    progress_callback: Optional[Callable[[str, int, int, int, str], None]] = None,
                    selected_doc_extensions: Optional[List[str]] = None,
                    selected_extensions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Escanea un flujo en bloques de 4MB aplicando validación estructural.
        progress_callback recibe: (mensaje, porcentaje, items_count, bytes_scanned, current_target)
        """
        self.is_cancelled = False
        recovered_items = []
        bytes_scanned = 0
        overlap_size = 128 * 1024  # 128 KB de solapamiento
        prev_tail = b""
        carved_count = 0

        doc_exts = {e.lower() for e in selected_doc_extensions} if selected_doc_extensions is not None else None
        all_exts = {e.lower() for e in selected_extensions} if selected_extensions is not None else None

        allow_images = not selected_categories or "Imágenes" in selected_categories
        allow_docs = not selected_categories or "Documentos" in selected_categories
        if allow_docs and doc_exts is not None and len(doc_exts) == 0:
            allow_docs = False

        allow_media = not selected_categories or "Audio" in selected_categories or "Video" in selected_categories
        allow_zips = not selected_categories or "Comprimidos" in selected_categories

        # Filtrar firmas por categoría y por extensiones de documento específicas si aplica
        active_sigs = SIGNATURE_CATALOG
        if selected_categories:
            active_sigs = [s for s in SIGNATURE_CATALOG if s["cat"] in selected_categories]

        if doc_exts is not None:
            ole2_family = {".doc", ".xls", ".ppt", ".msg", ".dot", ".xlt", ".pps", ".asd", ".wbk"}
            filtered_sigs = []
            for s in active_sigs:
                if s["cat"] == "Documentos":
                    if s["ext"] == ".doc":
                        if any(ext in doc_exts for ext in ole2_family):
                            filtered_sigs.append(s)
                    else:
                        if s["ext"].lower() in doc_exts:
                            filtered_sigs.append(s)
                else:
                    filtered_sigs.append(s)
            active_sigs = filtered_sigs

        while not self.is_cancelled:
            chunk = stream.read(self.chunk_size)
            if not chunk:
                break

            current_data = prev_tail + chunk
            chunk_offset = max(0, bytes_scanned - len(prev_tail))
            bytes_scanned += len(chunk)
            data_len = len(current_data)

            # 1. Carving Estructural: MP4/MOV (Audio / Video con metadatos 4K/1080p y duración)
            if allow_media:
                pos = 0
                while pos < data_len - 16:
                    ftyp_pos = current_data.find(b"ftyp", pos)
                    if ftyp_pos == -1 or ftyp_pos < 4:
                        break
                    atom_start = ftyp_pos - 4
                    mp4_res = parse_mp4_structure(current_data, atom_start)
                    if mp4_res:
                        exact_size, specs, score, status = mp4_res
                        abs_off = chunk_offset + atom_start
                        carved_count += 1
                        sample = current_data[atom_start : atom_start + min(exact_size, 65536)]
                        res_str = f" {specs['width']}x{specs['height']}" if specs.get("width") else ""
                        dur_str = f" {specs['duration']}s" if specs.get("duration") else ""
                        recovered_items.append({
                            "id": f"carved_{carved_count}",
                            "name": f"Video_Recuperado_{carved_count:04d}.mp4",
                            "original_path": f"[Sector Offset {abs_off:#x}]",
                            "original_dir": "Sectores en Crudo (MP4/MOV)",
                            "size": exact_size,
                            "date": "-",
                            "category": "Video",
                            "source_method": f"Carving Estructural (MP4{res_str}{dur_str})",
                            "recoverable": True,
                            "stream_offset": abs_off,
                            "preview_bytes": sample,
                            "is_carved": True,
                            "specs": specs,
                            "integrity_score": score,
                            "integrity_status": status
                        })
                        pos = atom_start + exact_size
                    else:
                        pos = ftyp_pos + 4

            # 2. Carving Estructural: JPEG (Imágenes con recorrido de marcadores y anti-truncamiento)
            if allow_images:
                pos = 0
                while pos < data_len - 16:
                    jpg_pos = current_data.find(b"\xff\xd8\xff", pos)
                    if jpg_pos == -1:
                        break
                    jpg_res = parse_jpeg_structure(current_data, jpg_pos)
                    if jpg_res:
                        exact_size, specs, score, status = jpg_res
                        abs_off = chunk_offset + jpg_pos
                        carved_count += 1
                        sample = current_data[jpg_pos : jpg_pos + min(exact_size, 65536)]
                        dim_str = f" ({specs['width']}x{specs['height']})" if specs.get("width") else ""
                        recovered_items.append({
                            "id": f"carved_{carved_count}",
                            "name": f"Foto_Recuperada_{carved_count:04d}.jpg",
                            "original_path": f"[Sector Offset {abs_off:#x}]",
                            "original_dir": "Sectores en Crudo (JPEG Estructural)",
                            "size": exact_size,
                            "date": "-",
                            "category": "Imágenes",
                            "source_method": f"Carving Estructural (JPEG{dim_str})",
                            "recoverable": True,
                            "stream_offset": abs_off,
                            "preview_bytes": sample,
                            "is_carved": True,
                            "specs": specs,
                            "integrity_score": score,
                            "integrity_status": status
                        })
                        pos = jpg_pos + exact_size
                    else:
                        pos = jpg_pos + 3

            # 3. Carving Estructural: PNG (Imágenes con verificación CRC32 de chunks)
            if allow_images:
                pos = 0
                while pos < data_len - 16:
                    png_pos = current_data.find(b"\x89PNG\r\n\x1a\n", pos)
                    if png_pos == -1:
                        break
                    png_res = parse_png_structure(current_data, png_pos)
                    if png_res:
                        exact_size, specs, score, status = png_res
                        abs_off = chunk_offset + png_pos
                        carved_count += 1
                        sample = current_data[png_pos : png_pos + min(exact_size, 65536)]
                        dim_str = f" ({specs['width']}x{specs['height']})" if specs.get("width") else ""
                        recovered_items.append({
                            "id": f"carved_{carved_count}",
                            "name": f"Imagen_Recuperada_{carved_count:04d}.png",
                            "original_path": f"[Sector Offset {abs_off:#x}]",
                            "original_dir": "Sectores en Crudo (PNG Estructural)",
                            "size": exact_size,
                            "date": "-",
                            "category": "Imágenes",
                            "source_method": f"Carving Estructural (PNG{dim_str})",
                            "recoverable": True,
                            "stream_offset": abs_off,
                            "preview_bytes": sample,
                            "is_carved": True,
                            "specs": specs,
                            "integrity_score": score,
                            "integrity_status": status
                        })
                        pos = png_pos + exact_size
                    else:
                        pos = png_pos + 8

            # 4. Carving Estructural: RIFF (WAV / WebP / AVI con extracción de dimensiones y audio)
            if allow_media or allow_images:
                pos = 0
                while pos < data_len - 12:
                    riff_pos = current_data.find(b"RIFF", pos)
                    if riff_pos == -1:
                        break
                    riff_res = parse_riff_structure(current_data, riff_pos)
                    if riff_res:
                        exact_size, ext, cat, desc, specs, score, status = riff_res
                        include = False
                        if cat == "Audio" and allow_media:
                            include = True
                        elif cat == "Video" and allow_media:
                            include = True
                        elif cat == "Imágenes" and allow_images:
                            include = True

                        if include:
                            abs_off = chunk_offset + riff_pos
                            carved_count += 1
                            sample = current_data[riff_pos : riff_pos + min(exact_size, 65536)]
                            recovered_items.append({
                                "id": f"carved_{carved_count}",
                                "name": f"Recuperado_{carved_count:04d}{ext}",
                                "original_path": f"[Sector Offset {abs_off:#x}]",
                                "original_dir": f"Sectores en Crudo (RIFF {cat})",
                                "size": exact_size,
                                "date": "-",
                                "category": cat,
                                "source_method": f"Carving Estructural ({desc})",
                                "recoverable": True,
                                "stream_offset": abs_off,
                                "preview_bytes": sample,
                                "is_carved": True,
                                "specs": specs,
                                "integrity_score": score,
                                "integrity_status": status
                            })
                            pos = riff_pos + exact_size
                            continue
                    pos = riff_pos + 4

            # 5. Carving Estructural: GIF
            if allow_images:
                pos = 0
                while pos < data_len - 13:
                    idx = current_data.find(b"GIF8", pos)
                    if idx == -1:
                        break
                    gif_res = parse_gif_structure(current_data, idx)
                    if gif_res:
                        exact_size, specs, score, status = gif_res
                        abs_off = chunk_offset + idx
                        carved_count += 1
                        recovered_items.append({
                            "id": f"carved_{carved_count}",
                            "name": f"Animacion_{carved_count:04d}.gif",
                            "original_path": f"[Sector Offset {abs_off:#x}]",
                            "original_dir": "Sectores en Crudo (GIF)",
                            "size": exact_size,
                            "date": "-",
                            "category": "Imágenes",
                            "source_method": f"Carving Estructural (GIF {specs.get('width', 0)}x{specs.get('height', 0)})",
                            "recoverable": True,
                            "stream_offset": abs_off,
                            "preview_bytes": current_data[idx : idx + min(exact_size, 65536)],
                            "is_carved": True,
                            "specs": specs,
                            "integrity_score": score,
                            "integrity_status": status
                        })
                        pos = idx + exact_size
                    else:
                        pos = idx + 4

            # 6. Carving Estructural: BMP
            if allow_images:
                pos = 0
                while pos < data_len - 26:
                    bmp_pos = current_data.find(b"BM", pos)
                    if bmp_pos == -1:
                        break
                    bmp_res = parse_bmp_structure(current_data, bmp_pos)
                    if bmp_res:
                        b_size, specs, score, status = bmp_res
                        abs_off = chunk_offset + bmp_pos
                        carved_count += 1
                        recovered_items.append({
                            "id": f"carved_{carved_count}",
                            "name": f"Imagen_{carved_count:04d}.bmp",
                            "original_path": f"[Sector Offset {abs_off:#x}]",
                            "original_dir": "Sectores en Crudo (BMP)",
                            "size": b_size,
                            "date": "-",
                            "category": "Imágenes",
                            "source_method": f"Carving Estructural (BMP {specs.get('width', 0)}x{specs.get('height', 0)})",
                            "recoverable": True,
                            "stream_offset": abs_off,
                            "preview_bytes": current_data[bmp_pos : bmp_pos + min(b_size, 65536)],
                            "is_carved": True,
                            "specs": specs,
                            "integrity_score": score,
                            "integrity_status": status
                        })
                        pos = bmp_pos + b_size
                    else:
                        pos = bmp_pos + 2

            # 7. Carving Estructural: ZIP, Office OOXML (DOCX, XLSX, PPTX) y ODF (ODT, ODS, ODP)
            if allow_docs or allow_zips:
                pos = 0
                while pos < data_len - 30:
                    zip_pos = current_data.find(b"PK\x03\x04", pos)
                    if zip_pos == -1:
                        break
                    z_size = get_zip_exact_size(current_data, zip_pos)
                    if z_size:
                        abs_off = chunk_offset + zip_pos
                        file_bytes = current_data[zip_pos : zip_pos + min(z_size, data_len - zip_pos)]
                        ext, desc, cat = refine_zip_content(file_bytes)
                        text_summary = extract_office_preview_text(file_bytes)

                        include = False
                        if cat == "Documentos" and allow_docs:
                            if doc_exts is None or ext.lower() in doc_exts:
                                include = True
                        elif cat == "Comprimidos" and allow_zips:
                            include = True

                        if include:
                            carved_count += 1
                            recovered_items.append({
                                "id": f"carved_{carved_count}",
                                "name": f"Documento_{carved_count:04d}{ext}",
                                "original_path": f"[Sector Offset {abs_off:#x}]",
                                "original_dir": "Sectores en Crudo (ZIP/OOXML/ODF)",
                                "size": z_size,
                                "date": "-",
                                "category": cat,
                                "source_method": f"Carving Estructural ({desc})",
                                "recoverable": True,
                                "stream_offset": abs_off,
                                "preview_bytes": file_bytes[:65536],
                                "preview_text": text_summary,
                                "is_carved": True,
                                "integrity_score": 100,
                                "integrity_status": "Íntegro (100%)"
                            })
                        pos = zip_pos + z_size
                    else:
                        pos = zip_pos + 4

            # 6. Carving de Firmas Estáticas (JPEG, PDF, 7Z, RAR, FLAC, etc.)
            for sig in active_sigs:
                header = sig["header"]
                footer = sig.get("footer")
                max_s = sig.get("max", 50 * 1024 * 1024)

                pos = 0
                while pos < data_len - len(header):
                    idx = current_data.find(header, pos)
                    if idx == -1:
                        break

                    file_size = 0
                    if footer:
                        foot_idx = current_data.find(footer, idx + len(header))
                        if foot_idx != -1 and (foot_idx - idx) < max_s:
                            file_size = (foot_idx + len(footer)) - idx
                    else:
                        file_size = min(max_s, 5 * 1024 * 1024)

                    if file_size > 0:
                        abs_off = chunk_offset + idx
                        file_bytes = current_data[idx : idx + min(file_size, data_len - idx)]
                        carved_count += 1
                        recovered_items.append({
                            "id": f"carved_{carved_count}",
                            "name": f"Archivo_{carved_count:04d}{sig['ext']}",
                            "original_path": f"[Sector Offset {abs_off:#x}]",
                            "original_dir": "Sectores en Crudo",
                            "size": file_size,
                            "date": "-",
                            "category": sig["cat"],
                            "source_method": f"Carving ({sig['name']})",
                            "recoverable": True,
                            "stream_offset": abs_off,
                            "preview_bytes": file_bytes[:4096],
                            "is_carved": True
                        })
                        pos = idx + file_size
                    else:
                        pos = idx + len(header)

            prev_tail = chunk[-overlap_size:] if len(chunk) >= overlap_size else chunk

            if progress_callback and total_bytes > 0:
                pct = min(100, int((bytes_scanned / total_bytes) * 100))
                progress_callback(
                    f"Analizando sectores ({bytes_scanned // (1024*1024)} MB procesados, {carved_count} encontrados)...",
                    pct,
                    carved_count,
                    bytes_scanned,
                    f"Sector {chunk_offset:#010x}"
                )

        if all_exts is not None:
            recovered_items = [
                it for it in recovered_items
                if not os.path.splitext(it.get("name", ""))[1].lower() or os.path.splitext(it.get("name", ""))[1].lower() in all_exts
            ]

        return recovered_items

    def scan_path(self, 
                  target_path: str,
                  selected_categories: Optional[List[str]] = None,
                  progress_callback: Optional[Callable[[str, int, int, int, str], None]] = None,
                  skip_software: bool = True,
                  fingerprints: Optional[Dict[str, Any]] = None,
                  selected_doc_extensions: Optional[List[str]] = None,
                  selected_extensions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Escanea una ruta (archivo, carpeta o volumen).
        Si skip_software es True, poda automáticamente carpetas de juegos y programas instalados.
        Si fingerprints está presente, omite archivos conocidos que no hayan cambiado de tamaño.
        Si selected_doc_extensions está presente, filtra archivos y firmas de documentos.
        Si selected_extensions está presente, filtra exhaustivamente cualquier formato seleccionado.
        """
        if not os.path.exists(target_path):
            if not target_path.startswith(("\\\\.\\", "/dev/")):
                return []

        doc_exts = {e.lower() for e in selected_doc_extensions} if selected_doc_extensions is not None else None
        all_exts = {e.lower() for e in selected_extensions} if selected_extensions is not None else None

        if os.path.isdir(target_path):
            from core.software_filter import SoftwareFilter
            from core.context_router import ContextRouter

            if skip_software:
                SoftwareFilter.build_catalog()

            items = []
            file_list = []
            for root, dirs, files in os.walk(target_path):
                if self.is_cancelled:
                    break

                # 1. Poda inteligente de software, juegos y dependencias
                if skip_software:
                    dirs[:] = [
                        d for d in dirs 
                        if not SoftwareFilter.should_skip_folder(os.path.join(root, d))[0]
                    ]

                # 2. Poda contextual según el tipo de archivo buscado
                if selected_categories:
                    dirs[:] = [
                        d for d in dirs 
                        if not ContextRouter.should_skip_by_context(os.path.join(root, d), selected_categories)[0]
                    ]

                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    # CRÍTICO: En búsqueda de datos perdidos, OMITIR TODOS LOS DATOS EXISTENTES.
                    # No abrir ni tallar archivos activos normales (.docx, .pdf, .jpg, etc.).
                    # Solo indexar y procesar imágenes de disco forenses o volcados binarios.
                    if ext in FORENSIC_CONTAINER_EXTS:
                        file_list.append(os.path.join(root, f))
            
            total = len(file_list)
            total_bytes_scanned = 0
            for i, fp in enumerate(file_list):
                if self.is_cancelled:
                    break
                try:
                    fsize = os.path.getsize(fp)
                    # Comprobación incremental: omitir si ya fue analizado previamente sin cambios
                    if fingerprints and fp in fingerprints and fingerprints[fp].get("size") == fsize:
                        continue

                    total_bytes_scanned += fsize
                    with open(fp, "rb") as fh:
                        res = self.scan_stream(
                            fh, 
                            fsize, 
                            selected_categories, 
                            None, 
                            selected_doc_extensions=selected_doc_extensions,
                            selected_extensions=selected_extensions
                        )
                        fp_name = os.path.basename(fp)
                        fp_dir = os.path.dirname(fp)
                        for r_idx, r in enumerate(res):
                            self.global_carved_counter += 1
                            r["container_file"] = fp
                            abs_off = r.get("stream_offset", 0)
                            r["id"] = f"carved_{hashlib.md5(f'{fp}_{abs_off}_{r_idx}'.encode()).hexdigest()[:12]}"
                            r["original_path"] = f"{fp_name} [Offset {abs_off:#x}]"
                            r["original_dir"] = fp_dir
                            r["is_carved"] = True
                        items.extend(res)
                except Exception:
                    continue

                if progress_callback:
                    pct = int(((i + 1) / max(total, 1)) * 100)
                    progress_callback(
                        f"Escaneando imagen forense {os.path.basename(fp)}...",
                        pct,
                        len(items),
                        total_bytes_scanned,
                        fp
                    )
            return items

        # Archivo único, imagen de disco o dispositivo en bruto
        ext = os.path.splitext(target_path)[1].lower()
        is_raw_device = target_path.startswith(("\\\\.\\", "/dev/"))

        # Si es un archivo regular de usuario activo (no imagen forense ni dispositivo en bruto),
        # NO se debe tallar como fuente de recuperación para no indexar datos existentes.
        if not is_raw_device and ext not in FORENSIC_CONTAINER_EXTS:
            return []

        try:
            fsize = os.path.getsize(target_path) if not is_raw_device else 0
        except Exception:
            fsize = 0

        try:
            with open(target_path, "rb") as fh:
                res = self.scan_stream(
                    fh, 
                    fsize, 
                    selected_categories, 
                    progress_callback, 
                    selected_doc_extensions=selected_doc_extensions,
                    selected_extensions=selected_extensions
                )
                tp_name = os.path.basename(target_path)
                tp_dir = os.path.dirname(target_path)
                for r_idx, r in enumerate(res):
                    self.global_carved_counter += 1
                    r["container_file"] = target_path
                    abs_off = r.get("stream_offset", 0)
                    r["id"] = f"carved_{hashlib.md5(f'{target_path}_{abs_off}_{r_idx}'.encode()).hexdigest()[:12]}"
                    if tp_name:
                        r["original_path"] = f"{tp_name} [Offset {abs_off:#x}]"
                        r["original_dir"] = tp_dir
                    else:
                        r["original_path"] = f"[Sector Offset {abs_off:#x} en {target_path}]"
                    r["is_carved"] = True
                return res
        except Exception:
            return []
