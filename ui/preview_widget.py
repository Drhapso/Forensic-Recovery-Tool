"""
Componente de previsualización forense multifuncional para archivos recuperados.
Incluye visor de imágenes interactivo con zoom/paneo e info técnica/EXIF, reproductor multimedia
integrado para audio y video (QMediaPlayer + QVideoWidget), extractor de contenido para documentos
Office (DOCX, XLSX, PPTX) y PDF, visor hexadecimal con cálculo de entropía de Shannon y diagnóstico de integridad.
"""

import os
import io
import math
import struct
import tempfile
import hashlib
import zipfile
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QScrollArea, QFrame, QSlider, QSplitter
)
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor
from PyQt5.QtCore import Qt, QUrl, QTimer

from core.disk_utils import format_size

# Compatibilidad segura con QtMultimedia y PIL
try:
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
    from PyQt5.QtMultimediaWidgets import QVideoWidget
    QT_MULTIMEDIA_AVAILABLE = True
except Exception:
    QT_MULTIMEDIA_AVAILABLE = False

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


class PreviewWidget(QWidget):
    """Panel de previsualización profesional con pestañas dinámicas y reproductores integrados."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item = None
        self._temp_media_file = None
        self._current_pixmap = None
        self._zoom_factor = 1.0

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        # 1. ENCABEZADO Y BADGE DE INTEGRIDAD FORENSE
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #161b22; border-radius: 6px; padding: 6px; border: 1px solid #30363d;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)

        lbl_title = QLabel("🛡️ VISTA PREVIA & DIAGNÓSTICO")
        lbl_title.setStyleSheet("font-weight: bold; color: #58a6ff; font-size: 12px;")
        header_layout.addWidget(lbl_title)

        header_layout.addStretch()

        self.lbl_integrity = QLabel("ESTADO: SIN SELECCIÓN")
        self.lbl_integrity.setStyleSheet("padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px; background-color: #21262d; color: #8b949e;")
        header_layout.addWidget(self.lbl_integrity)

        main_layout.addWidget(header_frame)

        # Panel de Usabilidad y Diagnóstico de Calidad
        self.frame_usability = QFrame()
        self.frame_usability.setStyleSheet("background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 6px;")
        self.frame_usability.setVisible(False)
        usability_layout = QVBoxLayout(self.frame_usability)
        usability_layout.setContentsMargins(6, 4, 6, 4)
        usability_layout.setSpacing(2)

        self.lbl_usability_badge = QLabel("🌟 USABILIDAD: ALTA (100%)")
        self.lbl_usability_badge.setStyleSheet("font-weight: bold; font-size: 11px; color: #3fb950;")
        usability_layout.addWidget(self.lbl_usability_badge)

        self.lbl_usability_details = QLabel("Diagnóstico de viabilidad...")
        self.lbl_usability_details.setStyleSheet("color: #8b949e; font-size: 10px;")
        self.lbl_usability_details.setWordWrap(True)
        usability_layout.addWidget(self.lbl_usability_details)

        main_layout.addWidget(self.frame_usability)

        # 2. PESTAÑAS DE CONTENIDO
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # ----------------------------------------------------------------------
        # PESTAÑA 1: VISUAL (Imágenes con Zoom interactivo y detalles técnicos)
        # ----------------------------------------------------------------------
        self.tab_visual = QWidget()
        visual_layout = QVBoxLayout(self.tab_visual)
        visual_layout.setContentsMargins(4, 4, 4, 4)
        visual_layout.setSpacing(4)

        # Barra de herramientas de Zoom
        zoom_bar = QHBoxLayout()
        zoom_bar.setSpacing(6)

        self.btn_zoom_in = QPushButton("➕ Acercar")
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        zoom_bar.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("➖ Alejar")
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        zoom_bar.addWidget(self.btn_zoom_out)

        self.btn_zoom_100 = QPushButton("🔍 100%")
        self.btn_zoom_100.clicked.connect(self._zoom_reset)
        zoom_bar.addWidget(self.btn_zoom_100)

        self.btn_zoom_fit = QPushButton("↔ Ajustar")
        self.btn_zoom_fit.clicked.connect(self._zoom_fit)
        zoom_bar.addWidget(self.btn_zoom_fit)

        self.lbl_zoom_val = QLabel("100%")
        self.lbl_zoom_val.setStyleSheet("color: #8b949e; font-size: 11px;")
        zoom_bar.addWidget(self.lbl_zoom_val)

        zoom_bar.addStretch()
        visual_layout.addLayout(zoom_bar)

        # Área desplazable para la imagen
        self.scroll_image = QScrollArea()
        self.scroll_image.setStyleSheet("background-color: #090d13; border: 1px solid #30363d; border-radius: 6px;")
        self.scroll_image.setWidgetResizable(True)
        self.lbl_image = QLabel("Seleccione un archivo para previsualizar")
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setStyleSheet("color: #8b949e; background-color: transparent;")
        self.scroll_image.setWidget(self.lbl_image)
        visual_layout.addWidget(self.scroll_image, stretch=1)

        # Barra de especificaciones técnicas de la imagen
        self.lbl_image_specs = QLabel("Sin especificaciones")
        self.lbl_image_specs.setStyleSheet("color: #58a6ff; font-size: 11px; background-color: #161b22; padding: 4px 8px; border-radius: 4px;")
        visual_layout.addWidget(self.lbl_image_specs)

        self.tabs.addTab(self.tab_visual, "🖼️ Visual")

        # ----------------------------------------------------------------------
        # PESTAÑA 2: MULTIMEDIA (Reproductor de Audio y Video integrado)
        # ----------------------------------------------------------------------
        self.tab_media = QWidget()
        media_layout = QVBoxLayout(self.tab_media)
        media_layout.setContentsMargins(6, 6, 6, 6)
        media_layout.setSpacing(6)

        if QT_MULTIMEDIA_AVAILABLE:
            self.player = QMediaPlayer(self)
            self.video_widget = QVideoWidget()
            self.video_widget.setStyleSheet("background-color: #000000; border-radius: 6px; border: 1px solid #30363d;")
            self.video_widget.setMinimumHeight(180)
            self.player.setVideoOutput(self.video_widget)
            media_layout.addWidget(self.video_widget, stretch=1)

            # Tarjeta de estado de Audio (visible cuando es audio)
            self.card_audio = QFrame()
            self.card_audio.setStyleSheet("background-color: #161b22; border-radius: 6px; padding: 12px; border: 1px solid #30363d;")
            audio_box = QVBoxLayout(self.card_audio)
            self.lbl_audio_icon = QLabel("🎵 REPRODUCTOR DE AUDIO FORENSE")
            self.lbl_audio_icon.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff;")
            self.lbl_audio_icon.setAlignment(Qt.AlignCenter)
            audio_box.addWidget(self.lbl_audio_icon)
            self.card_audio.setVisible(False)
            media_layout.addWidget(self.card_audio)

            # Barra de tiempo y controles
            controls_layout = QHBoxLayout()
            self.btn_play_pause = QPushButton("▶ Reproducir")
            self.btn_play_pause.setObjectName("PrimaryButton")
            self.btn_play_pause.clicked.connect(self._toggle_playback)
            controls_layout.addWidget(self.btn_play_pause)

            self.btn_stop = QPushButton("⏹ Parar")
            self.btn_stop.clicked.connect(self._stop_playback)
            controls_layout.addWidget(self.btn_stop)

            # Barra de progreso deslizable
            self.slider_timeline = QSlider(Qt.Horizontal)
            self.slider_timeline.setRange(0, 0)
            self.slider_timeline.sliderMoved.connect(self._set_media_position)
            controls_layout.addWidget(self.slider_timeline, stretch=1)

            self.lbl_time = QLabel("00:00 / 00:00")
            self.lbl_time.setStyleSheet("font-size: 11px; color: #8b949e; font-family: monospace;")
            controls_layout.addWidget(self.lbl_time)

            # Control de Volumen
            lbl_vol = QLabel("🔊")
            controls_layout.addWidget(lbl_vol)
            self.slider_volume = QSlider(Qt.Horizontal)
            self.slider_volume.setRange(0, 100)
            self.slider_volume.setValue(80)
            self.slider_volume.setMaximumWidth(80)
            self.slider_volume.valueChanged.connect(self.player.setVolume)
            controls_layout.addWidget(self.slider_volume)

            media_layout.addLayout(controls_layout)

            # Conectar eventos del reproductor
            self.player.positionChanged.connect(self._on_media_position_changed)
            self.player.durationChanged.connect(self._on_media_duration_changed)
        else:
            lbl_no_media = QLabel("Soporte QtMultimedia no disponible en este sistema.")
            lbl_no_media.setAlignment(Qt.AlignCenter)
            media_layout.addWidget(lbl_no_media)

        # Especificaciones del archivo multimedia
        self.lbl_media_specs = QLabel("Especificaciones multimedia no disponibles")
        self.lbl_media_specs.setStyleSheet("color: #7ee787; font-size: 11px; background-color: #161b22; padding: 4px 8px; border-radius: 4px;")
        media_layout.addWidget(self.lbl_media_specs)

        self.tabs.addTab(self.tab_media, "🎬 Multimedia")

        # ----------------------------------------------------------------------
        # PESTAÑA 3: DOCUMENTO / TEXTO / CÓDIGO (Office DOCX/XLSX/PPTX, PDF, etc.)
        # ----------------------------------------------------------------------
        self.tab_text = QWidget()
        text_layout = QVBoxLayout(self.tab_text)
        text_layout.setContentsMargins(4, 4, 4, 4)
        text_layout.setSpacing(4)

        self.lbl_doc_info = QLabel("Vista previa de contenido textual")
        self.lbl_doc_info.setStyleSheet("color: #8b949e; font-size: 11px;")
        text_layout.addWidget(self.lbl_doc_info)

        self.txt_content = QTextEdit()
        self.txt_content.setReadOnly(True)
        self.txt_content.setFont(QFont("Consolas", 10))
        self.txt_content.setPlaceholderText("Vista previa de texto o documento no disponible.")
        text_layout.addWidget(self.txt_content)

        # Tabla para archivos contenidos en ZIP / Comprimidos
        self.table_zip = QTableWidget(0, 3)
        self.table_zip.setHorizontalHeaderLabels(["Archivo Contenido", "Tamaño Descomprimido", "Comprimido"])
        self.table_zip.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_zip.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table_zip.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table_zip.verticalHeader().setVisible(False)
        self.table_zip.setVisible(False)
        text_layout.addWidget(self.table_zip)

        self.tabs.addTab(self.tab_text, "📄 Documento / Texto")

        # ----------------------------------------------------------------------
        # PESTAÑA 4: HEXADECIMAL FORENSE (Con Entropía de Shannon)
        # ----------------------------------------------------------------------
        self.tab_hex = QWidget()
        hex_layout = QVBoxLayout(self.tab_hex)
        hex_layout.setContentsMargins(4, 4, 4, 4)
        hex_layout.setSpacing(4)

        # Barra de análisis de cabecera y entropía
        hex_info_layout = QHBoxLayout()
        self.lbl_hex_sig = QLabel("Firma no identificada")
        self.lbl_hex_sig.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px;")
        hex_info_layout.addWidget(self.lbl_hex_sig)

        hex_info_layout.addStretch()

        self.lbl_entropy = QLabel("Entropía: 0.000")
        self.lbl_entropy.setStyleSheet("color: #e3b341; font-weight: bold; font-size: 11px; background-color: #161b22; padding: 2px 6px; border-radius: 4px;")
        hex_info_layout.addWidget(self.lbl_entropy)

        hex_layout.addLayout(hex_info_layout)

        self.txt_hex = QTextEdit()
        self.txt_hex.setReadOnly(True)
        self.txt_hex.setFont(QFont("Consolas", 9))
        hex_layout.addWidget(self.txt_hex)

        self.tabs.addTab(self.tab_hex, "🔢 Hexadecimal")

        # ----------------------------------------------------------------------
        # PESTAÑA 5: METADATOS Y HASH
        # ----------------------------------------------------------------------
        self.tab_meta = QWidget()
        meta_layout = QVBoxLayout(self.tab_meta)
        meta_layout.setContentsMargins(4, 4, 4, 4)

        self.table_meta = QTableWidget(0, 2)
        self.table_meta.setHorizontalHeaderLabels(["Propiedad Forense", "Valor Detectado"])
        self.table_meta.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_meta.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_meta.verticalHeader().setVisible(False)
        meta_layout.addWidget(self.table_meta)

        self.btn_hash = QPushButton("🔒 Calcular Hash de Integridad SHA-256")
        self.btn_hash.clicked.connect(self._compute_hash)
        meta_layout.addWidget(self.btn_hash)

        self.tabs.addTab(self.tab_meta, "📊 Metadatos")

    def load_item(self, item: Optional[dict]):
        """Carga y procesa un elemento recuperado para su previsualización completa."""
        self._stop_playback()
        self.current_item = item
        self._clear_views()

        if not item:
            return

        # 1. Integridad y Usabilidad Forense
        if "usability_score" not in item:
            from core.integrity_analyzer import IntegrityAnalyzer
            IntegrityAnalyzer.analyze_item(item)

        status = item.get("integrity_status", "Estructura Verificada" if item.get("recoverable") else "Inaccesible")
        score = item.get("usability_score", item.get("integrity_score", 100 if item.get("recoverable") else 0))
        tier = item.get("usability_tier", "high" if score >= 80 else ("medium" if score >= 50 else "low"))
        self._set_integrity_badge(status, score, tier)
        self._update_usability_card(item)

        # 2. Obtener muestra de bytes (hasta 64KB)
        data = self._get_item_data_sample(item, max_bytes=64 * 1024)

        # 3. Metadatos
        self._populate_metadata(item, data)

        # 4. Procesar vistas según el tipo de archivo
        ext = os.path.splitext(item.get("name", ""))[1].lower()
        cat = item.get("category", "")

        has_image = self._render_image(item, data)
        has_media = self._setup_multimedia(item, ext, cat)
        has_text = self._render_text_and_docs(item, data, ext)
        self._render_hex(data)

        # 5. Seleccionar la pestaña óptima automáticamente
        if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".flac", ".ogg"} and has_media:
            self.tabs.setCurrentWidget(self.tab_media)
        elif ext in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".ico", ".tiff"} and has_image:
            self.tabs.setCurrentWidget(self.tab_visual)
        elif ext in {".docx", ".xlsx", ".pptx", ".pdf", ".txt", ".log", ".json", ".xml", ".csv", ".py", ".zip"}:
            self.tabs.setCurrentWidget(self.tab_text)
        elif item.get("is_carved"):
            self.tabs.setCurrentWidget(self.tab_hex)
        else:
            self.tabs.setCurrentWidget(self.tab_meta)

    def clear(self):
        """Limpia todas las vistas y recursos."""
        self.load_item(None)

    def _cleanup_temp_media(self):
        if QT_MULTIMEDIA_AVAILABLE and hasattr(self, "player"):
            try:
                self.player.setMedia(QMediaContent())
            except Exception:
                pass
        if self._temp_media_file and os.path.exists(self._temp_media_file):
            try:
                os.remove(self._temp_media_file)
            except Exception:
                pass
            self._temp_media_file = None

    def _clear_views(self):
        self._stop_playback()
        self._cleanup_temp_media()
        self.frame_usability.setVisible(False)
        self.lbl_image.clear()
        self.lbl_image.setText("Sin vista previa visual")
        self._current_pixmap = None
        self._zoom_factor = 1.0
        self.lbl_zoom_val.setText("100%")
        self.lbl_image_specs.setText("Sin especificaciones")

        self.txt_content.clear()
        self.txt_content.setVisible(True)
        self.table_zip.setVisible(False)
        self.table_zip.setRowCount(0)
        self.lbl_doc_info.setText("Vista previa de contenido textual")

        self.txt_hex.clear()
        self.lbl_hex_sig.setText("Firma no analizada")
        self.lbl_entropy.setText("Entropía: 0.000")

        self.table_meta.setRowCount(0)
        self.btn_hash.setEnabled(True)
        self.btn_hash.setText("🔒 Calcular Hash de Integridad SHA-256")
        self.lbl_integrity.setText("ESTADO: SIN SELECCIÓN")
        self.lbl_integrity.setStyleSheet("padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px; background-color: #21262d; color: #8b949e;")

    def _update_usability_card(self, item: dict):
        score = item.get("usability_score", 85)
        tier = item.get("usability_tier", "high")
        reasons = item.get("usability_reasons", [])

        if tier == "high":
            color = "#3fb950"
            icon = "🌟"
            title = f"{icon} USABILIDAD ALTA ({score}%) - ARCHIVO ÓPTIMO PARA RECUPERAR"
        elif tier == "medium":
            color = "#d29922"
            icon = "🟡"
            title = f"{icon} USABILIDAD MEDIA ({score}%) - RECUPERABLE CON POSIBLES DETALLES"
        elif tier == "low":
            color = "#db6d28"
            icon = "🟠"
            title = f"{icon} BAJA CALIDAD ({score}%) - PARCIAL O MUY DEGRADADO"
        else:
            color = "#f85149"
            icon = "🔴"
            title = f"{icon} INUTILIZABLE / BASURA ({score}%) - NO RECOMENDADO"

        self.lbl_usability_badge.setText(title)
        self.lbl_usability_badge.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {color};")

        if reasons:
            details = " • " + " | ".join(reasons)
        else:
            details = "Estructura física y tamaño válidos."
        self.lbl_usability_details.setText(f"Diagnóstico: {details}")
        self.frame_usability.setVisible(True)

    def _set_integrity_badge(self, status: str, score: int, tier: str = ""):
        if tier == "high" or "Íntegro" in status or score >= 80:
            style = "background-color: #238636; color: #ffffff;"
            icon = "🛡️"
        elif tier == "medium" or "Parcial" in status or "Válido" in status or score >= 50:
            style = "background-color: #bb8009; color: #ffffff;"
            icon = "⚠️"
        else:
            style = "background-color: #da3633; color: #ffffff;"
            icon = "❌"

        self.lbl_integrity.setText(f"{icon} ESTADO: {status.upper()} ({score}%)")
        self.lbl_integrity.setStyleSheet(f"padding: 2px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; {style}")

    def _get_item_data_sample(self, item: dict, max_bytes: int = 64 * 1024) -> bytes:
        if "preview_bytes" in item and item["preview_bytes"]:
            return item["preview_bytes"][:max_bytes]

        src = item.get("data_source_path")
        if src and os.path.isfile(src):
            try:
                with open(src, "rb") as f:
                    return f.read(max_bytes)
            except Exception:
                return b""

        container = item.get("container_file")
        if container and os.path.isfile(container):
            try:
                offset = item.get("stream_offset", 0)
                with open(container, "rb") as f:
                    f.seek(offset)
                    return f.read(max_bytes)
            except Exception:
                return b""

        return b""

    # ==========================================================================
    # VISUAL: IMÁGENES, ZOOM Y DETALLES TÉCNICOS
    # ==========================================================================

    def _render_image(self, item: dict, data: bytes) -> bool:
        ext = os.path.splitext(item.get("name", ""))[1].lower()
        if not data:
            self.lbl_image.setText(f"Sin muestra gráfica para [{ext or 'archivo'}]")
            return False

        pix = QPixmap()
        loaded = pix.loadFromData(data)
        if not loaded and PIL_AVAILABLE:
            try:
                im = Image.open(io.BytesIO(data))
                im_rgb = im.convert("RGBA")
                data_bytes = im_rgb.tobytes("raw", "RGBA")
                qim = QImage(data_bytes, im.size[0], im.size[1], QImage.Format_RGBA8888)
                pix = QPixmap.fromImage(qim)
                loaded = not pix.isNull()
            except Exception:
                pass

        if loaded:
            self._current_pixmap = pix
            self._zoom_factor = 1.0
            self._update_image_display()

            # Extraer especificaciones técnicas y EXIF
            w, h = pix.width(), pix.height()
            specs_item = item.get("specs", {})
            if specs_item.get("width"):
                w, h = specs_item["width"], specs_item["height"]

            mp = round((w * h) / 1_000_000, 2)
            ratio = self._get_aspect_ratio_str(w, h)

            exif_info = ""
            if PIL_AVAILABLE:
                try:
                    pil_img = Image.open(io.BytesIO(data))
                    raw_exif = getattr(pil_img, "_getexif", lambda: None)()
                    if raw_exif:
                        cam = raw_exif.get(0x0110) or raw_exif.get(0x010F)  # Model o Make
                        date_taken = raw_exif.get(0x9003)  # DateTimeOriginal
                        if cam:
                            exif_info += f" | Cámara: {cam}"
                        if date_taken:
                            exif_info += f" | Captura: {date_taken}"
                except Exception:
                    pass

            self.lbl_image_specs.setText(f"📐 {w} × {h} px ({mp} MP) | Relación: {ratio} | Formato: {ext.upper()}{exif_info}")
            return True

        self.lbl_image.setText(f"Vista previa gráfica no disponible\npara el tipo [{ext or 'desconocido'}]")
        return False

    def _get_aspect_ratio_str(self, w: int, h: int) -> str:
        if not w or not h:
            return "N/A"
        gcd = math.gcd(w, h)
        return f"{w // gcd}:{h // gcd}"

    def _zoom_in(self):
        if self._current_pixmap:
            self._zoom_factor = min(self._zoom_factor * 1.25, 5.0)
            self._update_image_display()

    def _zoom_out(self):
        if self._current_pixmap:
            self._zoom_factor = max(self._zoom_factor * 0.8, 0.2)
            self._update_image_display()

    def _zoom_reset(self):
        if self._current_pixmap:
            self._zoom_factor = 1.0
            self._update_image_display()

    def _zoom_fit(self):
        if self._current_pixmap:
            vp_w = self.scroll_image.viewport().width() - 20
            vp_h = self.scroll_image.viewport().height() - 20
            if vp_w > 0 and vp_h > 0 and self._current_pixmap.width() > 0:
                scale_w = vp_w / self._current_pixmap.width()
                scale_h = vp_h / self._current_pixmap.height()
                self._zoom_factor = min(scale_w, scale_h, 1.0)
                self._update_image_display()

    def _update_image_display(self):
        if not self._current_pixmap:
            return
        target_w = int(self._current_pixmap.width() * self._zoom_factor)
        target_h = int(self._current_pixmap.height() * self._zoom_factor)
        scaled = self._current_pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_image.setPixmap(scaled)
        self.lbl_zoom_val.setText(f"{int(self._zoom_factor * 100)}%")

    # ==========================================================================
    # MULTIMEDIA: REPRODUCTOR DE AUDIO Y VIDEO INTEGRADO
    # ==========================================================================

    def _setup_multimedia(self, item: dict, ext: str, cat: str) -> bool:
        if not QT_MULTIMEDIA_AVAILABLE:
            return False

        is_video = ext in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
        is_audio = ext in {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}

        if not (is_video or is_audio):
            return False

        media_file = self._prepare_media_file(item, ext)
        if not media_file or not os.path.exists(media_file):
            return False

        # Configurar aspecto visual según tipo
        if is_video:
            self.video_widget.setVisible(True)
            self.card_audio.setVisible(False)
        else:
            self.video_widget.setVisible(False)
            self.card_audio.setVisible(True)
            self.lbl_audio_icon.setText(f"🎵 {item.get('name', 'Pista de Audio')}")

        specs = item.get("specs", {})
        spec_text = []
        if specs.get("width"):
            spec_text.append(f"Resolución: {specs['width']}x{specs['height']}")
        if specs.get("duration"):
            spec_text.append(f"Duración: {specs['duration']}s")
        if specs.get("sample_rate"):
            spec_text.append(f"Muestreo: {specs['sample_rate']}")
        if specs.get("channels"):
            spec_text.append(f"Canales: {specs['channels']}")

        specs_str = " | ".join(spec_text) or f"Contenedor: {ext.upper()} | Tamaño: {format_size(item.get('size', 0))}"
        self.lbl_media_specs.setText(f"🎬 {specs_str}")

        content = QMediaContent(QUrl.fromLocalFile(media_file))
        self.player.setMedia(content)
        self.btn_play_pause.setText("▶ Reproducir")
        return True

    def _prepare_media_file(self, item: dict, ext: str) -> Optional[str]:
        src = item.get("data_source_path")
        if src and os.path.isfile(src):
            return src

        # Extraer muestra para reproducir
        data = None
        if "preview_bytes" in item and item["preview_bytes"]:
            data = item["preview_bytes"]

        container = item.get("container_file")
        offset = item.get("stream_offset", 0)
        size = item.get("size", 0)
        if container and os.path.isfile(container) and size > 0:
            try:
                with open(container, "rb") as cf:
                    cf.seek(offset)
                    data = cf.read(min(size, 25 * 1024 * 1024))  # Hasta 25MB para playback fluido
            except Exception:
                pass

        if data:
            temp_path = os.path.join(tempfile.gettempdir(), f"forensic_media_preview{ext}")
            try:
                with open(temp_path, "wb") as tf:
                    tf.write(data)
                self._temp_media_file = temp_path
                return temp_path
            except Exception:
                pass
        return None

    def _toggle_playback(self):
        if not QT_MULTIMEDIA_AVAILABLE:
            return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play_pause.setText("▶ Reproducir")
        else:
            self.player.play()
            self.btn_play_pause.setText("⏸ Pausar")

    def _stop_playback(self):
        if QT_MULTIMEDIA_AVAILABLE and hasattr(self, "player"):
            self.player.stop()
            self.btn_play_pause.setText("▶ Reproducir")
            self.lbl_time.setText("00:00 / 00:00")
            self.slider_timeline.setValue(0)

    def _on_media_position_changed(self, position: int):
        self.slider_timeline.blockSignals(True)
        self.slider_timeline.setValue(position)
        self.slider_timeline.blockSignals(False)
        self._update_time_label(position, self.player.duration())

    def _on_media_duration_changed(self, duration: int):
        self.slider_timeline.setRange(0, duration)
        self._update_time_label(self.player.position(), duration)

    def _set_media_position(self, position: int):
        if QT_MULTIMEDIA_AVAILABLE and hasattr(self, "player"):
            self.player.setPosition(position)

    def _update_time_label(self, pos_ms: int, dur_ms: int):
        pos_sec = pos_ms // 1000
        dur_sec = dur_ms // 1000
        p_str = f"{pos_sec // 60:02d}:{pos_sec % 60:02d}"
        d_str = f"{dur_sec // 60:02d}:{dur_sec % 60:02d}"
        self.lbl_time.setText(f"{p_str} / {d_str}")

    # ==========================================================================
    # DOCUMENTOS, TEXTO Y ARCHIVOS COMPRIMIDOS
    # ==========================================================================

    def _render_text_and_docs(self, item: dict, data: bytes, ext: str) -> bool:
        # 1. Documento Office con texto pre-extraído
        if "preview_text" in item and item["preview_text"]:
            self.txt_content.setText(item["preview_text"])
            self.lbl_doc_info.setText(f"📄 Contenido de Documento Extraído ({len(item['preview_text'])} caracteres)")
            return True

        # 2. Intentar extraer texto de Office en tiempo real si tenemos datos
        if ext in {".docx", ".xlsx", ".pptx"} and data:
            text_extracted = self._extract_office_text_on_the_fly(data, ext)
            if text_extracted:
                self.txt_content.setText(text_extracted)
                self.lbl_doc_info.setText(f"📄 Texto de Documento Office Extraído ({len(text_extracted)} caracteres)")
                return True

        # 3. Archivo ZIP / Comprimido: Mostrar árbol de archivos internos
        if ext in {".zip", ".jar", ".apk"} and data:
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    infolist = zf.infolist()
                    self.txt_content.setVisible(False)
                    self.table_zip.setVisible(True)
                    self.table_zip.setRowCount(len(infolist))
                    for r, zi in enumerate(infolist):
                        self.table_zip.setItem(r, 0, QTableWidgetItem(zi.filename))
                        self.table_zip.setItem(r, 1, QTableWidgetItem(format_size(zi.file_size)))
                        self.table_zip.setItem(r, 2, QTableWidgetItem(format_size(zi.compress_size)))
                    self.lbl_doc_info.setText(f"📦 Contenido del Archivo Comprimido ({len(infolist)} elementos)")
                    return True
            except Exception:
                pass

        # 4. Decodificación de Texto Plano / Código
        if data:
            for enc in ["utf-8", "latin-1", "cp1252"]:
                try:
                    decoded = data.decode(enc)
                    printable = sum(c.isprintable() or c in "\r\n\t" for c in decoded)
                    if printable / max(len(decoded), 1) > 0.85:
                        self.txt_content.setText(decoded[:8000])
                        self.lbl_doc_info.setText(f"📝 Texto plano / Código ({enc.upper()})")
                        return True
                except Exception:
                    continue

        self.txt_content.setText("[Contenido binario no representable como texto plano]")
        return False

    def _extract_office_text_on_the_fly(self, data: bytes, ext: str) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = zf.namelist()
                if ext == ".docx" and "word/document.xml" in names:
                    root = ET.fromstring(zf.read("word/document.xml"))
                    return " ".join(e.text for e in root.iter() if e.tag.endswith("}t") and e.text)[:4000]
                elif ext == ".xlsx" and "xl/sharedStrings.xml" in names:
                    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                    return "\n".join(e.text for e in root.iter() if e.tag.endswith("}t") and e.text)[:2000]
        except Exception:
            pass
        return ""

    # ==========================================================================
    # HEXADECIMAL Y ENTROPÍA DE SHANNON
    # ==========================================================================

    def _render_hex(self, data: bytes):
        if not data:
            self.txt_hex.setText("No hay datos binarios disponibles.")
            return

        # 1. Identificar cabecera conocida (Magic Bytes)
        sig_name = self._identify_magic_bytes(data)
        self.lbl_hex_sig.setText(f"📌 {sig_name}")

        # 2. Entropía de Shannon
        entropy = self._calculate_entropy(data)
        entropy_type = "Comprimido/Cifrado" if entropy > 7.2 else ("Estructurado" if entropy > 4.5 else "Baja Entropía/Texto")
        self.lbl_entropy.setText(f"Entropía: {entropy:.3f} bits/byte ({entropy_type})")

        # 3. Volcado Hexadecimal (1KB)
        lines = []
        chunk = data[:1024]
        for i in range(0, len(chunk), 16):
            row_bytes = chunk[i : i + 16]
            hex_str = " ".join(f"{b:02X}" for b in row_bytes)
            if len(row_bytes) > 8:
                hex_str = hex_str[:23] + "  " + hex_str[24:]
            hex_str = hex_str.ljust(49)
            ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in row_bytes)
            lines.append(f"{i:08X}  {hex_str}  |{ascii_str}|")

        self.txt_hex.setText("\n".join(lines))

    def _identify_magic_bytes(self, data: bytes) -> str:
        if len(data) >= 8 and data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "Cabecera: PNG Image (89 50 4E 47)"
        elif len(data) >= 3 and data.startswith(b"\xff\xd8\xff"):
            return "Cabecera: JPEG/JFIF Image (FF D8 FF)"
        elif len(data) >= 4 and data.startswith(b"PK\x03\x04"):
            return "Cabecera: ZIP / Documento Office OOXML (50 4B 03 04)"
        elif len(data) >= 4 and data.startswith(b"%PDF"):
            return "Cabecera: Documento PDF (25 50 44 46)"
        elif len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WAVE":
            return "Cabecera: Audio RIFF/WAVE (52 49 46 46)"
        elif len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "Cabecera: Imagen WebP (52 49 46 46)"
        elif len(data) >= 8 and b"ftyp" in data[:16]:
            return "Cabecera: Contenedor ISO Base Media MP4/MOV (ftyp)"
        elif len(data) >= 6 and (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            return "Cabecera: Imagen GIF (47 49 46 38)"
        elif len(data) >= 2 and data.startswith(b"BM"):
            return "Cabecera: Imagen Bitmap BMP (42 4D)"
        return "Cabecera Binaria General"

    def _calculate_entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        length = len(data)
        freq = {}
        for b in data:
            freq[b] = freq.get(b, 0) + 1
        entropy = 0.0
        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    # ==========================================================================
    # METADATOS Y HASH
    # ==========================================================================

    def _populate_metadata(self, item: dict, data: bytes):
        props = [
            ("Nombre de Archivo", item.get("name", "-")),
            ("Categoría", item.get("category", "-")),
            ("Tamaño en Disco", f"{format_size(item.get('size', 0))} ({item.get('size', 0):,} bytes)"),
            ("Fecha Registrada", str(item.get("date", "-"))),
            ("Método de Recuperación", item.get("source_method", "-")),
            ("Ruta de Origen", item.get("original_path", "-")),
            ("Diagnóstico de Integridad", item.get("integrity_status", "Estructura Verificada")),
            ("Puntaje Forense", f"{item.get('integrity_score', 100)} / 100")
        ]

        specs = item.get("specs", {})
        if specs:
            for k, v in specs.items():
                props.append((f"Especificación: {k.capitalize()}", str(v)))

        self.table_meta.setRowCount(len(props))
        for row, (prop, val) in enumerate(props):
            p_item = QTableWidgetItem(prop)
            p_item.setFlags(p_item.flags() ^ Qt.ItemIsEditable)
            p_item.setForeground(Qt.gray)

            v_item = QTableWidgetItem(str(val))
            v_item.setFlags(v_item.flags() ^ Qt.ItemIsEditable)

            self.table_meta.setItem(row, 0, p_item)
            self.table_meta.setItem(row, 1, v_item)

    def _compute_hash(self):
        if not self.current_item:
            return

        src = self.current_item.get("data_source_path")
        if src and os.path.isfile(src):
            try:
                self.btn_hash.setText("Calculando SHA-256...")
                self.btn_hash.setEnabled(False)
                h = hashlib.sha256()
                with open(src, "rb") as f:
                    while chunk := f.read(256 * 1024):
                        h.update(chunk)
                val = h.hexdigest()
                row = self.table_meta.rowCount()
                self.table_meta.insertRow(row)
                self.table_meta.setItem(row, 0, QTableWidgetItem("Hash SHA-256"))
                self.table_meta.setItem(row, 1, QTableWidgetItem(val))
                self.btn_hash.setText("Hash SHA-256 Calculado")
            except Exception as e:
                self.btn_hash.setText(f"Error: {e}")
        elif "preview_bytes" in self.current_item and self.current_item["preview_bytes"]:
            val = hashlib.sha256(self.current_item["preview_bytes"]).hexdigest()
            row = self.table_meta.rowCount()
            self.table_meta.insertRow(row)
            self.table_meta.setItem(row, 0, QTableWidgetItem("SHA-256 (Muestra)"))
            self.table_meta.setItem(row, 1, QTableWidgetItem(val))
            self.btn_hash.setText("Hash SHA-256 Calculado (Muestra)")
        else:
            self.btn_hash.setText("No disponible para este origen")

    def closeEvent(self, event):
        self._stop_playback()
        self._cleanup_temp_media()
        super().closeEvent(event)


