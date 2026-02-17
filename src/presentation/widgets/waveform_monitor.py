from typing import List, Optional, Dict
from PyQt6.QtWidgets import QFrame, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QMouseEvent, QFont
from ...resources import constants


class WaveformMonitor(QFrame):
    """
    Universal Audio Monitor. 
    Fluid, proportional rendering system that adapts to any height.
    Supports HUD overlays and regional markers.
    """
    seek_requested = pyqtSignal(float)  # Ratio 0.0-1.0
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WaveformMonitor")
        # Let layouts decide height, but keep a reasonable minimum
        self.setMinimumHeight(24)
        self.setMinimumWidth(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Data
        self._peaks: List[float] = [] 
        self._regions: List[Dict] = [] 
        self._artist = ""
        self._title = ""
        
        # State
        self._position_ratio = 0.0
        self._hover_ratio = None
        self._current_ms = 0
        self._duration_ms = 0
        self._show_hud = True
        
    def set_peaks(self, peaks: List[float]) -> None:
        print(f"WaveformMonitor.set_peaks: {len(peaks)} peaks, max={max(peaks) if peaks else 0:.3f}")
        self._peaks = peaks
        self.update()

    def set_song_info(self, artist: str, title: str) -> None:
        self._artist = artist
        self._title = title
        self.update()

    def set_position(self, ratio: float, position_ms: int = 0) -> None:
        self._position_ratio = max(0.0, min(1.0, ratio))
        self._current_ms = position_ms
        self.update()
        
    def set_duration(self, duration_ms: int) -> None:
        self._duration_ms = duration_ms
        self.update()

    def set_regions(self, regions: List[Dict]) -> None:
        self._regions = regions
        self.update()

    def set_show_hud(self, enabled: bool) -> None:
        self._show_hud = enabled
        self.update()
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.width() > 0:
            ratio = event.position().x() / self.width()
            ratio = max(0.0, min(1.0, ratio))
            self.seek_requested.emit(ratio)
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.width() > 0:
            self._hover_ratio = event.position().x() / self.width()
            self._hover_ratio = max(0.0, min(1.0, self._hover_ratio))
            self.update()
        super().mouseMoveEvent(event)
        
    def leaveEvent(self, event) -> None:
        self._hover_ratio = None
        self.update()
        super().leaveEvent(event)
        
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        self.render_waveform(painter, self.rect())

    def render_waveform(self, painter: QPainter, rect: QRect) -> None:
        """
        Responsive Renderer.
        Scales fonts and layout proportions based on current height.
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = rect.width(), rect.height()
        x, y = rect.x(), rect.y()
        
        # Determine "Richness" based on height
        is_compact = h < 60
        hud_padding = int(h * 0.05) if not is_compact else 2

        # --- 1. Background Chassis ---
        bg_gradient = QLinearGradient(x, y, x, y + h)
        bg_gradient.setColorAt(0, QColor(20, 20, 25))
        bg_gradient.setColorAt(0.5, QColor(35, 35, 45))
        bg_gradient.setColorAt(1, QColor(20, 20, 25))
        painter.fillRect(rect, bg_gradient)
        
        # --- 2. Regions (Full Height Wash) ---
        for region in self._regions:
            rx = x + int(region['start'] * w)
            rw = int((region['end'] - region['start']) * w)
            color = QColor(region.get('color', constants.COLOR_CYAN))
            color.setAlpha(30 if is_compact else 50)
            painter.fillRect(rx, y, rw, h, color)
        
        # --- 4. Peaks (Forensic Data) ---
        if self._peaks:
            num_peaks = len(self._peaks)
            
            c_active = QColor(constants.COLOR_AMBER)
            c_muted = QColor(80, 80, 90, 150)
            
            for i, peak in enumerate(self._peaks):
                # Compute exact float boundaries, then snap to int
                # This guarantees no pixel gaps between adjacent bars
                px = int(i * w / num_peaks)
                px_next = int((i + 1) * w / num_peaks)
                p_width = max(1, px_next - px)
                
                # Dynamic scaling: Exp curve to reveal transients in loud masters
                curved_peak = peak ** 1.5 
                ph = int(h * curved_peak * 0.95)
                py = y + (h - ph) // 2
                
                is_played = (i / num_peaks) <= self._position_ratio
                painter.fillRect(px, py, p_width, ph, c_active if is_played else c_muted)
        else:
             # Basic Progress indicator if no peaks
             if self._position_ratio > 0:
                 played_w = int(w * self._position_ratio)
                 painter.fillRect(x, y, played_w, h, QColor(255, 198, 109, 30))
        
        # --- 5. HUD Overlays (Floating) ---
        if self._show_hud and not is_compact:
            # Dynamic Font Sizing (Proportional)
            main_fs = max(8, int(h * 0.12))
            sub_fs = max(7, int(h * 0.08))
            
            # --- Metadata (Top Center) ---
            if self._artist or self._title:
                painter.setFont(QFont("Bahnschrift Condensed", main_fs, QFont.Weight.Bold))
                painter.setPen(QColor(constants.COLOR_AMBER))
                label = f"{self._artist} — {self._title}".upper()
                painter.drawText(rect.adjusted(0, hud_padding, 0, 0), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, label)

            # --- Time Data (Bottom Overlays) ---
            if self._duration_ms > 0:
                painter.setFont(QFont("Bahnschrift Condensed", sub_fs))
                # Current (Left)
                cur_str = self._format_time(self._current_ms)
                painter.drawText(rect.adjusted(hud_padding*2, 0, -hud_padding*2, -hud_padding), 
                               Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, cur_str)
                # Remaining (Right)
                rem_str = f"-{self._format_time(self._duration_ms - self._current_ms)}"
                painter.drawText(rect.adjusted(hud_padding*2, 0, -hud_padding*2, -hud_padding), 
                               Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, rem_str)

        # --- 6. Playhead indicator ---
        if self._position_ratio > 0:
            px = x + int(w * self._position_ratio)
            pen = QPen(QColor(constants.COLOR_AMBER))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(px, y, px, y + h)
            
        # --- 7. Hover Forensics ---
        if self._hover_ratio is not None and not is_compact:
            hx = x + int(w * self._hover_ratio)
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1)) 
            painter.drawLine(hx, y, hx, y + h)
            
            if self._duration_ms > 0:
                h_ms = int(self._hover_ratio * self._duration_ms)
                h_str = self._format_time(h_ms)
                painter.setPen(QColor(255, 255, 255, 200))
                fs = max(8, int(h * 0.1))
                painter.setFont(QFont("Bahnschrift Condensed", fs))
                painter.drawText(hx + 5, y + int(h * 0.3), h_str)

        painter.restore()

    def _format_time(self, ms: int) -> str:
        s = ms // 1000
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"
