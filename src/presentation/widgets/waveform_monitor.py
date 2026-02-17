from typing import List, Dict
from PyQt6.QtWidgets import QFrame, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient,
    QMouseEvent, QFont
)
from ...resources import constants


class WaveformMonitor(QFrame):
    """
    Universal Audio Monitor.
    Fluid rendering system with two layout tiers:
      - Full:    metadata + time readouts + peak bars
      - Compact: time readouts + peak bars (no metadata)
    """
    seek_requested = pyqtSignal(float)

    # -- Palette (derived from constants) --
    _BG_TOP = QColor(0x11, 0x11, 0x11)
    _BG_MID = QColor(0x1A, 0x1A, 0x1A)
    _BG_BOT = QColor(0x08, 0x08, 0x08)

    # Played: bright amber — the "lit" side of the playhead
    _PEAK_PLAYED = QColor(0xDD, 0xA0, 0x4A)
    _PEAK_PLAYED_DIM = QColor(0xB0, 0x7C, 0x32)
    # Unplayed: very dark gray — visible shape against
    # the background but clearly recedes next to played
    _PEAK_UNPLAYED = QColor(0x2E, 0x2E, 0x30)
    _PEAK_UNPLAYED_DIM = QColor(0x22, 0x22, 0x24)

    _PLAYHEAD = QColor(constants.COLOR_AMBER)
    _HOVER_LINE = QColor(255, 255, 255, 70)

    _TEXT_AMBER = QColor(constants.COLOR_AMBER)
    _TEXT_DIM = QColor(0xCC, 0xB8, 0x96)
    _TEXT_TIME = QColor(0xCC, 0xCC, 0xCC)
    _TEXT_HOVER = QColor(255, 255, 255, 200)

    # -- Font constants --
    _FONT_LABEL = "Bahnschrift Condensed"
    _FONT_DATA = "Consolas"

    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self.setObjectName("WaveformMonitor")
        self.setMinimumHeight(24)
        self.setMinimumWidth(100)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
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
        self._compact = compact

    # -- Public API -----------------------------------------------

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        self.update()

    def set_peaks(self, peaks: List[float]) -> None:
        self._peaks = peaks
        self.update()

    def set_song_info(self, artist: str, title: str) -> None:
        self._artist = artist
        self._title = title
        self.update()

    def set_position(
        self, ratio: float, position_ms: int = 0
    ) -> None:
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

    # -- Input Events ---------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (event.button() == Qt.MouseButton.LeftButton
                and self.width() > 0):
            ratio = event.position().x() / self.width()
            self.seek_requested.emit(
                max(0.0, min(1.0, ratio))
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.width() > 0:
            r = event.position().x() / self.width()
            self._hover_ratio = max(0.0, min(1.0, r))
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_ratio = None
        self.update()
        super().leaveEvent(event)

    # -- Rendering ------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        self.render_waveform(painter, self.rect())

    def render_waveform(
        self, painter: QPainter, rect: QRect
    ) -> None:
        painter.save()
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        w, h = rect.width(), rect.height()
        x, y = rect.x(), rect.y()

        # ----- 1. Background Chassis -----
        bg = QLinearGradient(x, y, x, y + h)
        bg.setColorAt(0.0, self._BG_TOP)
        bg.setColorAt(0.5, self._BG_MID)
        bg.setColorAt(1.0, self._BG_BOT)
        painter.fillRect(rect, bg)

        # Subtle top-edge bevel (satin-metal highlight)
        painter.setPen(QPen(QColor(0x33, 0x33, 0x33), 1))
        painter.drawLine(x, y, x + w, y)

        # ----- 2. Region Washes -----
        for region in self._regions:
            rx = x + int(region['start'] * w)
            rw = int((region['end'] - region['start']) * w)
            c = QColor(
                region.get('color', constants.COLOR_CYAN)
            )
            c.setAlpha(35)
            painter.fillRect(rx, y, rw, h, c)

        # ----- 3. Peak Bars -----
        if self._peaks:
            self._draw_peaks(painter, x, y, w, h)
        elif self._position_ratio > 0:
            # Fallback progress wash
            pw = int(w * self._position_ratio)
            painter.fillRect(
                x, y, pw, h,
                QColor(0xFF, 0xC6, 0x6D, 25)
            )

        # ----- 4. HUD Overlays -----
        if self._show_hud:
            self._draw_hud(painter, rect, w, h)

        # ----- 5. Playhead -----
        if self._position_ratio > 0:
            px = x + int(w * self._position_ratio)
            pen = QPen(self._PLAYHEAD)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(px, y, px, y + h)

        # ----- 6. Hover Cursor -----
        if self._hover_ratio is not None:
            self._draw_hover(painter, x, y, w, h)

        painter.restore()

    # -- Peak Rendering -------------------------------------------

    def _draw_peaks(
        self, painter: QPainter,
        x: int, y: int, w: int, h: int
    ) -> None:
        num = len(self._peaks)
        pos = self._position_ratio

        # Pre-build played/unplayed gradients
        g_played = QLinearGradient(0, y, 0, y + h)
        g_played.setColorAt(0.0, self._PEAK_PLAYED)
        g_played.setColorAt(0.5, self._PEAK_PLAYED_DIM)
        g_played.setColorAt(1.0, self._PEAK_PLAYED)

        g_unplayed = QLinearGradient(0, y, 0, y + h)
        g_unplayed.setColorAt(0.0, self._PEAK_UNPLAYED_DIM)
        g_unplayed.setColorAt(0.5, self._PEAK_UNPLAYED)
        g_unplayed.setColorAt(1.0, self._PEAK_UNPLAYED_DIM)

        for i, peak in enumerate(self._peaks):
            # Pixel boundaries (gap-free)
            bx = x + int(i * w / num)
            bx_next = x + int((i + 1) * w / num)
            bw = max(1, bx_next - bx)

            # Soft curve to reveal transient detail
            curved = peak ** 1.25
            bar_h = max(1, int(h * curved * 0.90))
            bar_y = y + (h - bar_h) // 2

            played = (i / num) <= pos
            grad = g_played if played else g_unplayed
            painter.fillRect(bx, bar_y, bw, bar_h, grad)

    # -- HUD Rendering --------------------------------------------

    def _draw_hud(
        self, painter: QPainter, rect: QRect,
        w: int, h: int
    ) -> None:
        pad = max(4, int(w * 0.01))

        # Font sizes: capped to avoid oversized text
        if self._compact:
            meta_pt = min(9, max(7, int(h * 0.12)))
            time_pt = min(8, max(7, int(h * 0.10)))
        else:
            meta_pt = min(11, max(8, int(h * 0.16)))
            time_pt = min(10, max(7, int(h * 0.12)))

        # -- Metadata (top-center, skip in compact) --
        pill = QColor(0, 0, 0, 160)
        pill_pad_x = 4
        pill_pad_y = 2

        if not self._compact and (self._artist or self._title):
            font_meta = QFont(
                self._FONT_LABEL, meta_pt,
                QFont.Weight.Bold
            )
            painter.setFont(font_meta)
            label = (
                f"{self._artist}  \u2014  {self._title}"
            ).upper()

            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label)
            th = fm.height()
            tx = rect.x() + (w - tw) // 2
            ty = rect.y() + pad

            painter.fillRect(
                tx - pill_pad_x, ty - pill_pad_y,
                tw + pill_pad_x * 2, th + pill_pad_y * 2,
                pill
            )
            painter.setPen(self._TEXT_DIM)
            painter.drawText(
                tx, ty + fm.ascent(), label
            )

        # -- Time readouts (bottom corners) --
        if self._duration_ms > 0:
            font_time = QFont(self._FONT_DATA, time_pt)
            painter.setFont(font_time)

            cur = self._fmt(self._current_ms)
            rem = "-" + self._fmt(
                self._duration_ms - self._current_ms
            )

            fm = painter.fontMetrics()
            th = fm.height()

            # Current time — bottom-left
            tw_cur = fm.horizontalAdvance(cur)
            tx_cur = rect.x() + pad + 2
            ty_cur = rect.y() + h - pad - th
            painter.fillRect(
                tx_cur - pill_pad_x,
                ty_cur - pill_pad_y,
                tw_cur + pill_pad_x * 2,
                th + pill_pad_y * 2,
                pill
            )
            painter.setPen(self._TEXT_TIME)
            painter.drawText(
                tx_cur, ty_cur + fm.ascent(), cur
            )

            # Remaining time — bottom-right
            tw_rem = fm.horizontalAdvance(rem)
            tx_rem = rect.x() + w - pad - 2 - tw_rem
            ty_rem = ty_cur
            painter.fillRect(
                tx_rem - pill_pad_x,
                ty_rem - pill_pad_y,
                tw_rem + pill_pad_x * 2,
                th + pill_pad_y * 2,
                pill
            )
            painter.setPen(self._TEXT_TIME)
            painter.drawText(
                tx_rem, ty_rem + fm.ascent(), rem
            )

    # -- Hover Tooltip --------------------------------------------

    def _draw_hover(
        self, painter: QPainter,
        x: int, y: int, w: int, h: int
    ) -> None:
        ratio = self._hover_ratio
        if ratio is None:
            return
        hx = x + int(w * ratio)

        # Vertical cursor line
        painter.setPen(QPen(self._HOVER_LINE, 1))
        painter.drawLine(hx, y, hx, y + h)

        if self._duration_ms <= 0:
            return

        h_ms = int(ratio * self._duration_ms)
        r_ms = self._duration_ms - h_ms
        h_str = self._fmt(h_ms)
        r_str = "-" + self._fmt(r_ms)

        fs = min(9, max(7, int(h * 0.10)))
        painter.setFont(QFont(self._FONT_DATA, fs))
        painter.setPen(self._TEXT_HOVER)

        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(h_str)

        # Position labels left/right of cursor line
        ty = y + int(h * 0.35)
        margin = 4
        painter.drawText(hx - tw - margin, ty, h_str)
        painter.drawText(hx + margin, ty, r_str)

    # -- Utilities ------------------------------------------------

    @staticmethod
    def _fmt(ms: int) -> str:
        s = max(0, ms) // 1000
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"
