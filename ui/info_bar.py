"""
Barra de Información y Telemetría en Vivo (HUD).
Muestra de forma destacada qué proceso se está ejecutando, la ruta exacta o sector actual,
cronómetro de tiempo, velocidad en tiempo real (MB/s), volumen analizado y contadores por tipo.
"""

import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from core.disk_utils import format_size

class InfoBar(QFrame):
    """HUD interactivo de telemetría y estado de escaneo en tiempo real."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet("""
            QFrame#Card {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        self.start_time = 0
        self.last_bytes = 0
        self.last_time = 0
        self.current_speed_mb = 0.0

        self.timer = QTimer(self)
        self.timer.setInterval(1000) # Actualizar cronómetro cada segundo
        self.timer.timeout.connect(self._on_timer_tick)

        self._init_ui()
        self.reset()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Fila 1: Fase Activa y Ruta Actual
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.lbl_phase = QLabel("LISTO")
        self.lbl_phase.setStyleSheet("""
            background-color: #21262d;
            color: #58a6ff;
            font-weight: bold;
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid #30363d;
        """)
        top_row.addWidget(self.lbl_phase)

        self.lbl_current_target = QLabel("Esperando inicio de escaneo...")
        self.lbl_current_target.setStyleSheet("color: #c9d1d9; font-weight: 500; font-size: 12px;")
        self.lbl_current_target.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top_row.addWidget(self.lbl_current_target, stretch=1)

        main_layout.addLayout(top_row)

        # Fila 2: Barra de Progreso con porcentaje destacado
        prog_row = QHBoxLayout()
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 5px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #238636;
                border-radius: 4px;
            }
        """)
        prog_row.addWidget(self.prog_bar)
        main_layout.addLayout(prog_row)

        # Fila 3: Rejilla de Métricas en Vivo (HUD)
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)

        # Métrica 1: Tiempo
        self.lbl_time = self._create_metric_widget("⏱️ TIEMPO", "00:00:00")
        metrics_layout.addWidget(self.lbl_time["container"])

        # Métrica 2: Velocidad
        self.lbl_speed = self._create_metric_widget("⚡ VELOCIDAD", "0.0 MB/s")
        metrics_layout.addWidget(self.lbl_speed["container"])

        # Métrica 3: Volumen / Sectores
        self.lbl_volume = self._create_metric_widget("💽 PROCESADO", "0 B")
        metrics_layout.addWidget(self.lbl_volume["container"])

        # Métrica 4: Total Encontrados
        self.lbl_found = self._create_metric_widget("🎯 ENCONTRADOS", "0")
        metrics_layout.addWidget(self.lbl_found["container"])

        # Métrica 5: Desglose por categorías
        self.lbl_breakdown = self._create_metric_widget("📊 DESGLOSE", "🖼️ 0  📄 0  🎵 0  📦 0")
        metrics_layout.addWidget(self.lbl_breakdown["container"], stretch=1)

        main_layout.addLayout(metrics_layout)

    def _create_metric_widget(self, title: str, default_val: str) -> dict:
        container = QFrame()
        container.setStyleSheet("background-color: #0d1117; border-radius: 5px; padding: 4px 8px; border: 1px solid #21262d;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; color: #8b949e; font-weight: bold;")
        layout.addWidget(lbl_t)

        lbl_v = QLabel(default_val)
        lbl_v.setStyleSheet("font-size: 12px; color: #58a6ff; font-weight: bold;")
        layout.addWidget(lbl_v)

        return {"container": container, "title": lbl_t, "value": lbl_v}

    def start(self, phase_name: str = "INICIANDO ESCANEO"):
        """Inicia el cronómetro y la barra de información."""
        self.start_time = time.time()
        self.last_time = self.start_time
        self.last_bytes = 0
        self.current_speed_mb = 0.0

        self.lbl_phase.setText(phase_name)
        self.lbl_phase.setStyleSheet("""
            background-color: #1f6feb;
            color: #ffffff;
            font-weight: bold;
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        self.lbl_current_target.setText("Iniciando indexación profunda y rastreo de sectores...")
        self.prog_bar.setValue(0)
        self.lbl_time["value"].setText("00:00:00")
        self.lbl_speed["value"].setText("Calculando...")
        self.lbl_volume["value"].setText("0 B")
        self.lbl_found["value"].setText("0")
        self.lbl_breakdown["value"].setText("🖼️ 0  📄 0  🎵 0  📦 0")
        self.timer.start()

    def update_status(self, 
                      message: str, 
                      percentage: int, 
                      current_item_path: str = "",
                      bytes_scanned: int = 0, 
                      items_count: int = 0,
                      category_counts: dict = None):
        """Actualiza todas las métricas dinámicas del HUD."""
        self.prog_bar.setValue(max(0, min(100, percentage)))

        if current_item_path:
            # Truncar visualmente la ruta si es demasiado larga para evitar desbordar
            display_path = current_item_path
            if len(display_path) > 85:
                display_path = display_path[:35] + " ... " + display_path[-45:]
            self.lbl_current_target.setText(f"📁 {display_path}")
        elif message:
            self.lbl_current_target.setText(message)

        # Actualizar volumen procesado
        if bytes_scanned > 0:
            self.lbl_volume["value"].setText(format_size(bytes_scanned))

            # Calcular velocidad instantánea
            now = time.time()
            dt = now - self.last_time
            if dt >= 0.5:
                delta_b = bytes_scanned - self.last_bytes
                speed_bytes_sec = delta_b / dt
                self.current_speed_mb = speed_bytes_sec / (1024 * 1024)
                self.lbl_speed["value"].setText(f"{self.current_speed_mb:.1f} MB/s")
                self.last_bytes = bytes_scanned
                self.last_time = now

        # Actualizar encontrados
        self.lbl_found["value"].setText(str(items_count))

        # Actualizar desglose
        if category_counts:
            img = category_counts.get("Imágenes", 0)
            doc = category_counts.get("Documentos", 0)
            media = category_counts.get("Audio", 0) + category_counts.get("Video", 0)
            zips = category_counts.get("Comprimidos", 0)
            self.lbl_breakdown["value"].setText(f"🖼️ {img}  📄 {doc}  🎵 {media}  📦 {zips}")

    def finish(self, success: bool = True, final_msg: str = ""):
        """Detiene el cronómetro y presenta el estado final."""
        self.timer.stop()
        self.prog_bar.setValue(100)

        if success:
            self.lbl_phase.setText("FINALIZADO")
            self.lbl_phase.setStyleSheet("background-color: #238636; color: white; font-weight: bold; font-size: 11px; padding: 3px 8px; border-radius: 4px;")
            self.lbl_current_target.setText(final_msg or "Escaneo forense completado exitosamente.")
        else:
            self.lbl_phase.setText("DETENIDO")
            self.lbl_phase.setStyleSheet("background-color: #da3633; color: white; font-weight: bold; font-size: 11px; padding: 3px 8px; border-radius: 4px;")
            self.lbl_current_target.setText(final_msg or "Proceso cancelado por el usuario.")

    def reset(self):
        """Reinicia el HUD al estado inicial en espera."""
        self.timer.stop()
        self.lbl_phase.setText("EN ESPERA")
        self.lbl_phase.setStyleSheet("background-color: #21262d; color: #8b949e; font-weight: bold; font-size: 11px; padding: 3px 8px; border-radius: 4px;")
        self.lbl_current_target.setText("Seleccione el método de recuperación y presione Iniciar Escaneo.")
        self.prog_bar.setValue(0)
        self.lbl_time["value"].setText("00:00:00")
        self.lbl_speed["value"].setText("0.0 MB/s")
        self.lbl_volume["value"].setText("0 B")
        self.lbl_found["value"].setText("0")
        self.lbl_breakdown["value"].setText("🖼️ 0  📄 0  🎵 0  📦 0")

    def _on_timer_tick(self):
        if self.start_time > 0:
            elapsed = int(time.time() - self.start_time)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            self.lbl_time["value"].setText(f"{hrs:02d}:{mins:02d}:{secs:02d}")

