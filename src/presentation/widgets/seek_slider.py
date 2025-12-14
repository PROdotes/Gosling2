"""Custom seek slider widget with time tooltip"""
from PyQt6.QtWidgets import QSlider, QToolTip
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer


from ...resources.constants import SLIDER_SIZE


class SeekSlider(QSlider):
    """Custom slider with hover tooltip showing time"""
    
    seekRequested = pyqtSignal(int)

    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None) -> None:
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self.total_duration_secs = 0
        self._last_tooltip = None

    def updateDuration(self, duration_ms: int) -> None:
        """Update duration when media changes"""
        self.setRange(0, duration_ms)
        if duration_ms > 0:
            self.total_duration_secs = duration_ms / 1000
        else:
            self.total_duration_secs = 0

    def enterEvent(self, event) -> None:
        """Show tooltip on mouse enter"""
        self._update_tooltip(event)
        super().enterEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Update tooltip on mouse move"""
        self._update_tooltip(event)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        """Seek on click"""
        if self.total_duration_secs > 0 and event.button() == Qt.MouseButton.LeftButton:
            pos_ratio = event.position().x() / self.width()
            pos_ratio = max(0, min(1, pos_ratio))
            new_value = int(pos_ratio * self.maximum())
            self.setValue(new_value)
            self.seekRequested.emit(new_value)
        else:
            super().mousePressEvent(event)

    def _update_tooltip(self, event) -> None:
        """Update the time tooltip"""
        if self.total_duration_secs <= 0:
            return

        pos_ratio = event.position().x() / self.width()
        pos_ratio = max(0, min(1, pos_ratio))
        hover_time = pos_ratio * self.total_duration_secs
        time_left = self.total_duration_secs - hover_time

        minutes = int(hover_time // 60)
        seconds = int(hover_time % 60)
        minutes_left = int(time_left // 60)
        seconds_left = int(time_left % 60)

        text = f"{minutes:02d}:{seconds:02d} / -{minutes_left:02d}:{seconds_left:02d}"

        if text != self._last_tooltip:
            QToolTip.showText(self.mapToGlobal(event.position().toPoint()), text)
            self._last_tooltip = text

    def sizeHint(self) -> QSize:
        """Return preferred size"""
        hint = super().sizeHint()
        if self.orientation() == Qt.Orientation.Horizontal:
            hint.setHeight(SLIDER_SIZE)
        return hint

