"""
Módulo Forense de Análisis de Integridad y Usabilidad de Archivos.
Evalúa la completitud física, ausencia de relleno nulo (basura), reproducibilidad real
y viabilidad práctica para permitir restaurar exclusivamente archivos con alta calidad.
"""

import os
import io
import math
import struct
from typing import Dict, Any, List, Optional, Tuple

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


class IntegrityAnalyzer:
    """
    Analizador exhaustivo de integridad y usabilidad forense.
    Clasifica cada archivo en:
      - 🌟 Alta Calidad (80 - 100%): Íntegro, abrible, resolución/duración óptima, sin relleno nulo.
      - 🟡 Calidad Media (50 - 79%): Funcional con tamaño o resolución moderada o ligeras pérdidas.
      - 🟠 Baja Calidad (20 - 49%): Truncado, icono diminuto de sistema, micro-fragmento o muy degradado.
      - 🔴 Inutilizable (0 - 19%): Falso positivo, sector rellenado de ceros, sin datos decodificables.
    """

    @staticmethod
    def calculate_entropy(data: bytes) -> float:
        """Calcula la entropía de información de Shannon (0.0 a 8.0 bits/byte)."""
        if not data:
            return 0.0
        frequencies = [0] * 256
        for b in data:
            frequencies[b] += 1
        total = len(data)
        entropy = 0.0
        for count in frequencies:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        return round(entropy, 3)

    @staticmethod
    def calculate_null_ratio(data: bytes) -> float:
        """Calcula el porcentaje de bytes nulos (0x00) en la muestra."""
        if not data:
            return 1.0
        null_count = data.count(b"\x00")
        return round(null_count / len(data), 3)

    @classmethod
    def get_sample_bytes(cls, item: Dict[str, Any], max_bytes: int = 128 * 1024) -> bytes:
        """Obtiene una muestra binaria eficiente del elemento a analizar."""
        if "preview_bytes" in item and item["preview_bytes"]:
            return item["preview_bytes"][:max_bytes]

        src = item.get("data_source_path")
        if src and os.path.isfile(src):
            try:
                with open(src, "rb") as f:
                    return f.read(max_bytes)
            except Exception:
                pass

        container = item.get("container_file")
        offset = item.get("stream_offset", 0)
        size = item.get("size", 0)
        if container and os.path.isfile(container) and size > 0:
            try:
                with open(container, "rb") as cf:
                    cf.seek(offset)
                    return cf.read(min(size, max_bytes))
            except Exception:
                pass

        return b""

    @classmethod
    def analyze_item(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza un archivo individual y enriquece su diccionario con métricas de usabilidad.
        """
        name = item.get("name", "")
        ext = os.path.splitext(name)[1].lower()
        size = item.get("size", 0)
        category = item.get("category", "")
        specs = item.get("specs", {})

        sample = cls.get_sample_bytes(item, max_bytes=64 * 1024)
        sample_len = len(sample)

        reasons: List[str] = []
        score = 70  # Puntaje base inicial
        tier = "medium"

        # ----------------------------------------------------------------------
        # 1. ANÁLISIS DE TAMAÑO Y RELLENO NULO (Detección de sectores vacíos/basura)
        # ----------------------------------------------------------------------
        if size == 0:
            item["usability_score"] = 0
            item["usability_tier"] = "unusable"
            item["usability_label"] = "🔴 Inutilizable (0%)"
            item["usability_reasons"] = ["Archivo vacío (0 bytes)"]
            item["is_high_quality"] = False
            item["is_usable"] = False
            return item

        if not sample:
            item["usability_score"] = 10
            item["usability_tier"] = "unusable"
            item["usability_label"] = "🔴 Inutilizable (10%)"
            item["usability_reasons"] = ["Sin muestra de datos binarios accesible"]
            item["is_high_quality"] = False
            item["is_usable"] = False
            return item

        null_ratio = cls.calculate_null_ratio(sample)
        entropy = cls.calculate_entropy(sample)

        # Si más del 85% son ceros, es un sector libre rellenado de ceros
        if null_ratio >= 0.85:
            item["usability_score"] = 5
            item["usability_tier"] = "unusable"
            item["usability_label"] = "🔴 Inútil (5%)"
            item["usability_reasons"] = [f"Sector vacío o borrado con relleno nulo ({int(null_ratio*100)}% de ceros 0x00)"]
            item["is_high_quality"] = False
            item["is_usable"] = False
            return item

        # Si los bytes son de entropía extremadamente baja en archivos binarios
        if sample_len > 1024 and entropy < 0.6 and ext not in {".txt", ".log", ".csv"}:
            item["usability_score"] = 15
            item["usability_tier"] = "unusable"
            item["usability_label"] = "🔴 Inútil (15%)"
            item["usability_reasons"] = [f"Patrón repetitivo no estructurado (Entropía: {entropy} bits/byte)"]
            item["is_high_quality"] = False
            item["is_usable"] = False
            return item

        # ----------------------------------------------------------------------
        # 2. EVALUACIÓN ESPECÍFICA POR CATEGORÍA
        # ----------------------------------------------------------------------
        # A. IMÁGENES
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".ico"} or category == "Imágenes":
            img_score, img_reasons = cls._analyze_image(sample, ext, specs, size)
            score = img_score
            reasons.extend(img_reasons)

        # B. VIDEOS
        elif ext in {".mp4", ".mov", ".avi", ".mkv", ".webm"} or category == "Video":
            vid_score, vid_reasons = cls._analyze_video(sample, ext, specs, size)
            score = vid_score
            reasons.extend(vid_reasons)

        # C. AUDIOS
        elif ext in {".mp3", ".wav", ".m4a", ".flac", ".ogg"} or category == "Audio":
            aud_score, aud_reasons = cls._analyze_audio(sample, ext, specs, size)
            score = aud_score
            reasons.extend(aud_reasons)

        # D. DOCUMENTOS (Office OOXML, PDF, Texto)
        elif ext in {".docx", ".xlsx", ".pptx", ".pdf", ".txt", ".csv", ".json", ".xml", ".py", ".log"} or "Documento" in category:
            doc_score, doc_reasons = cls._analyze_document(sample, ext, specs, size)
            score = doc_score
            reasons.extend(doc_reasons)

        # E. COMPRIMIDOS
        elif ext in {".zip", ".rar", ".7z"} or category == "Comprimidos":
            zip_score, zip_reasons = cls._analyze_archive(sample, ext, specs, size)
            score = zip_score
            reasons.extend(zip_reasons)

        # OTROS BINARIOS
        else:
            if size > 1024 and entropy > 3.0:
                score = 75
                reasons.append("Contenido binario consistente")
            else:
                score = 50
                reasons.append("Formato genérico no estructurado")

        # ----------------------------------------------------------------------
        # 3. CONSOLIDACIÓN Y CLASIFICACIÓN FINAL
        # ----------------------------------------------------------------------
        # Asegurar rango 0 - 100
        score = max(0, min(100, int(score)))

        if score >= 80:
            tier = "high"
            label = f"🌟 Alta ({score}%)"
        elif score >= 50:
            tier = "medium"
            label = f"🟡 Media ({score}%)"
        elif score >= 20:
            tier = "low"
            label = f"🟠 Baja ({score}%)"
        else:
            tier = "unusable"
            label = f"🔴 Inútil ({score}%)"

        item["usability_score"] = score
        item["usability_tier"] = tier
        item["usability_label"] = label
        item["usability_reasons"] = reasons
        item["is_high_quality"] = (tier == "high")
        item["is_usable"] = (score >= 50)

        # Sincronizar con integrity_status si no existía
        if "integrity_status" not in item:
            item["integrity_status"] = "Íntegro" if tier == "high" else ("Parcial" if tier == "medium" else "Corrupto")
        if "integrity_score" not in item:
            item["integrity_score"] = score

        return item

    # ==========================================================================
    # EVALUADORES DETALLADOS POR FORMATO
    # ==========================================================================

    @classmethod
    def _analyze_image(cls, data: bytes, ext: str, specs: dict, size: int) -> Tuple[int, List[str]]:
        reasons = []
        score = 65

        # 1. Cabecera Magic Bytes
        has_magic = False
        if ext in {".jpg", ".jpeg"} and data.startswith(b"\xFF\xD8\xFF"):
            has_magic = True
        elif ext == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
            has_magic = True
        elif ext == ".bmp" and data.startswith(b"BM"):
            has_magic = True
        elif ext == ".gif" and (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            has_magic = True
        elif ext == ".webp" and data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
            has_magic = True

        if has_magic:
            score += 15
            reasons.append("Cabecera gráfica válida")
        else:
            score -= 30
            reasons.append("Cabecera gráfica ausente o alterada")

        # 2. Dimensiones y Megapíxeles
        w = specs.get("width", 0)
        h = specs.get("height", 0)

        if (not w or not h) and PIL_AVAILABLE:
            try:
                with Image.open(io.BytesIO(data)) as img:
                    w, h = img.size
            except Exception:
                pass

        if w and h:
            mp = round((w * h) / 1_000_000, 2)
            if w >= 1920 or h >= 1080 or mp >= 2.0:
                score += 20
                reasons.append(f"Resolución Ultra/Full HD ({w}×{h} px, {mp} MP)")
            elif w >= 800 and h >= 600:
                score += 15
                reasons.append(f"Resolución estándar alta ({w}×{h} px)")
            elif w >= 300 and h >= 300:
                score += 5
                reasons.append(f"Resolución moderada ({w}×{h} px)")
            elif w <= 64 or h <= 64:
                score -= 35
                reasons.append(f"Resolución microscópica/Icono de sistema ({w}×{h} px)")
            elif w <= 150 or h <= 150:
                score -= 20
                reasons.append(f"Miniatura de baja resolución ({w}×{h} px)")

        # 3. Fin de archivo EOI / CRC
        if ext in {".jpg", ".jpeg"}:
            if b"\xFF\xD9" in data:
                reasons.append("Marcador de fin de imagen EOI presente")
        elif ext == ".png":
            if b"IEND" in data:
                score += 5
                reasons.append("Bloque terminal IEND intacto")

        # 4. Tamaño sospechosamente diminuto
        if size < 2048:
            score -= 20
            reasons.append(f"Tamaño muy pequeño ({size} B) - posible icono o residuo")

        return score, reasons

    @classmethod
    def _analyze_video(cls, data: bytes, ext: str, specs: dict, size: int) -> Tuple[int, List[str]]:
        reasons = []
        score = 60

        if ext in {".mp4", ".mov"}:
            has_ftyp = (len(data) >= 8 and data[4:8] == b"ftyp")
            if has_ftyp:
                score += 15
                reasons.append("Contenedor MP4/MOV ISO verificado")
            else:
                score -= 20
                reasons.append("Falta cabecera ftyp de contenedor")

            has_moov = b"moov" in data
            has_mdat = b"mdat" in data

            if has_moov and has_mdat:
                score += 20
                reasons.append("Metadatos de reproducción (moov) y fotogramas (mdat) sincronizados")
            elif has_mdat and not has_moov:
                score -= 15
                reasons.append("Falta tabla de cuadros (moov) en muestra inicial")

        duration = specs.get("duration", 0.0)
        if duration >= 5.0:
            score += 15
            reasons.append(f"Duración de video completa ({duration:.1f}s)")
        elif duration >= 1.5:
            score += 10
            reasons.append(f"Clip de video válido ({duration:.1f}s)")
        elif 0 < duration < 1.0:
            score -= 25
            reasons.append(f"Micro-fragmento incompleto ({duration:.1f}s)")

        w = specs.get("width", 0)
        h = specs.get("height", 0)
        if w >= 1280 or h >= 720:
            score += 10
            reasons.append(f"Resolución HD/4K ({w}×{h} px)")

        if size < 50 * 1024:
            score -= 30
            reasons.append(f"Tamaño insuficiente para video funcional ({size} B)")

        return score, reasons

    @classmethod
    def _analyze_audio(cls, data: bytes, ext: str, specs: dict, size: int) -> Tuple[int, List[str]]:
        reasons = []
        score = 65

        if ext == ".wav" and data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
            score += 20
            reasons.append("Formato PCM WAV intacto")
        elif ext == ".mp3" and (data.startswith(b"ID3") or (len(data) > 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)):
            score += 20
            reasons.append("Secuencia de sincronización MP3 válida")

        duration = specs.get("duration", 0.0)
        if duration >= 10.0:
            score += 15
            reasons.append(f"Pista de audio completa ({duration:.1f}s)")
        elif duration >= 2.0:
            score += 10
            reasons.append(f"Grabación de audio válida ({duration:.1f}s)")
        elif 0 < duration < 0.8:
            score -= 25
            reasons.append(f"Micro-sonido o campanilla de sistema ({duration:.1f}s)")

        if size < 10 * 1024:
            score -= 20
            reasons.append(f"Muestra de audio muy reducida ({size} B)")

        return score, reasons

    @classmethod
    def _analyze_document(cls, data: bytes, ext: str, specs: dict, size: int) -> Tuple[int, List[str]]:
        reasons = []
        score = 65

        if ext in {".docx", ".xlsx", ".pptx"}:
            if data.startswith(b"PK\x03\x04"):
                score += 20
                reasons.append("Estructura ZIP/OOXML íntegra")
                try:
                    import zipfile
                    with zipfile.ZipFile(io.BytesIO(data)) as zf:
                        names = zf.namelist()
                        if any("word/document.xml" in n or "xl/sharedStrings.xml" in n or "ppt/presentation.xml" in n for n in names):
                            score += 15
                            reasons.append("Árbol de documentos Office interno intacto")
                except Exception:
                    pass
            else:
                score -= 35
                reasons.append("Cabecera OOXML corrupta o alterada")

        elif ext == ".pdf":
            if data.startswith(b"%PDF-"):
                score += 20
                reasons.append("Cabecera Adobe PDF válida")
            else:
                score -= 30
                reasons.append("Cabecera PDF no encontrada")

        elif ext in {".txt", ".csv", ".py", ".json", ".xml", ".log"}:
            try:
                text_sample = data[:4096].decode("utf-8")
                printable = sum(1 for c in text_sample if c.isprintable() or c in "\r\n\t")
                ratio = printable / max(len(text_sample), 1)
                if ratio >= 0.90:
                    score += 25
                    reasons.append(f"Texto legible codificado ({int(ratio*100)}% caracteres legibles)")
                    if len(text_sample.strip()) > 100:
                        score += 10
                        reasons.append("Párrafos de texto detectados")
                else:
                    score -= 40
                    reasons.append("Ruido binario en archivo de texto plano")
            except Exception:
                score -= 30
                reasons.append("Error decodificando caracteres de texto")

        if size < 64:
            score -= 35
            reasons.append(f"Documento sin contenido significativo ({size} B)")

        return score, reasons

    @classmethod
    def _analyze_archive(cls, data: bytes, ext: str, specs: dict, size: int) -> Tuple[int, List[str]]:
        reasons = []
        score = 60

        if ext == ".zip" and data.startswith(b"PK\x03\x04"):
            score += 25
            reasons.append("Cabecera de archivo ZIP válida")
            try:
                import zipfile
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    n_files = len(zf.namelist())
                    score += 15
                    reasons.append(f"Índice central con {n_files} archivos legibles")
            except Exception:
                pass
        elif ext == ".7z" and data.startswith(b"7z\xBC\xAF\x27\x1C"):
            score += 25
            reasons.append("Firma 7-Zip estándar verificada")
        elif ext == ".rar" and data.startswith(b"Rar!\x1A\x07"):
            score += 25
            reasons.append("Firma WinRAR estándar verificada")
        else:
            score -= 20
            reasons.append("Cabecera de archivo comprimido alterada")

        return score, reasons

    @classmethod
    def analyze_batch(cls, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Procesa una lista completa de elementos recuperados y añade calificaciones de usabilidad."""
        for item in items:
            cls.analyze_item(item)
        return items

