"""Custom playlist widget with drag and drop support"""
import os
import json
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QStyledItemDelegate, QStyle
from PyQt6.QtCore import Qt, QRect, QSize, QUrl, pyqtSignal, pyqtProperty
from PyQt6.QtGui import QFont, QPen, QColor, QPainter
from ...business.services.metadata_service import MetadataService
from ...resources import constants

class PlaylistItemDelegate(QStyledItemDelegate):
    """Custom delegate for playlist items using the Property Bridge."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.performer_font = QFont("Bahnschrift Condensed", 12, QFont.Weight.Bold)
        self.title_font = QFont("Bahnschrift Condensed", 10)
        self.mini_font = QFont("Bahnschrift Condensed", 10)
        self.mini_mode = False

    ITEM_SPACING = 4 # Gap between items in pixels

    def _get_qss_color(self, widget, prop_name: str, fallback_hex: str) -> QColor:
        color = widget.property(prop_name)
        if isinstance(color, QColor):
            return color
        return QColor(fallback_hex)

    def paint(self, painter, option, index) -> None:
        """Custom paint for playlist items"""
        painter.save()
        
        # Adjust rect for spacing
        visual_rect = QRect(
            option.rect.left(),
            option.rect.top(),
            option.rect.width(),
            option.rect.height() - self.ITEM_SPACING
        )

        # Background - fetch from widget properties (pushed by QSS)
        row_color = self._get_qss_color(option.widget, "paletteVoid", constants.COLOR_VOID)
        sel_color = self._get_qss_color(option.widget, "paletteAmber", constants.COLOR_AMBER)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(visual_rect, sel_color)
            text_color = self._get_qss_color(option.widget, "paletteBlack", constants.COLOR_BLACK)
        else:
            painter.fillRect(visual_rect, row_color)
            text_color = self._get_qss_color(option.widget, "paletteWhite", constants.COLOR_WHITE)
            # Divider
            painter.setPen(self._get_qss_color(option.widget, "paletteBlack", constants.COLOR_BLACK))
            painter.drawLine(visual_rect.bottomLeft(), visual_rect.bottomRight())
        
        # Text
        display_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        if "|" in display_text:
            parts = [p.strip() for p in display_text.split("|", 1)]
            performer = parts[0]
            title = parts[1] if len(parts) > 1 else ""
        else:
            performer, title = display_text, ""

        padding = 10
        
        if self.mini_mode:
            painter.setFont(self.mini_font)
            painter.setPen(text_color)
            combined = f"{performer.upper()} - {title}" if title else performer.upper()
            painter.drawText(
                visual_rect.adjusted(padding, 0, -padding, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                combined
            )
        else:
            # Circle
            circle_diameter = int(visual_rect.height() * 0.75)
            circle_top = visual_rect.top() + (visual_rect.height() - circle_diameter) // 2
            circle_right_padding = -int(circle_diameter * 0.3)
            circle_left = visual_rect.right() - circle_diameter - circle_right_padding
            circle_rect = QRect(circle_left, circle_top, circle_diameter, circle_diameter)

            painter.setBrush(self._get_qss_color(option.widget, "paletteMagenta", constants.COLOR_MAGENTA))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(circle_rect)

            text_rect = QRect(
                visual_rect.left() + padding,
                visual_rect.top() + padding,
                circle_rect.left() - visual_rect.left() - 2 * padding,
                visual_rect.height() - 2 * padding
            )
            performer_rect = QRect(text_rect.left(), text_rect.top(), text_rect.width(), text_rect.height() // 2)
            title_rect = QRect(text_rect.left(), text_rect.top() + text_rect.height() // 2, text_rect.width(), text_rect.height() // 2)

            painter.setFont(self.performer_font)
            painter.setPen(text_color)
            painter.drawText(performer_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, performer.strip())

            painter.setFont(self.title_font)
            painter.setPen(text_color)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title.strip())

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        width = option.rect.width() if option.rect.width() > 0 else 200
        height = 24 if self.mini_mode else 54
        return QSize(width, height + self.ITEM_SPACING)

class PlaylistWidget(QListWidget):
    """Custom list widget with formal bridge properties."""

    itemDoubleClicked = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PlaylistWidget")
        
        self._paletteAmber = QColor(constants.COLOR_AMBER)
        self._paletteMutedAmber = QColor(constants.COLOR_MUTED_AMBER)
        self._paletteMagenta = QColor(constants.COLOR_MAGENTA)
        self._paletteBlack = QColor(constants.COLOR_BLACK)
        self._paletteGray = QColor(constants.COLOR_GRAY)
        self._paletteWhite = QColor(constants.COLOR_WHITE)
        self._paletteVoid = QColor(constants.COLOR_VOID)
        self._init_setup()
    
    @pyqtProperty(QColor)
    def paletteAmber(self): return self._paletteAmber
    @paletteAmber.setter
    def paletteAmber(self, c): self._paletteAmber = c

    @pyqtProperty(QColor)
    def paletteMutedAmber(self): return self._paletteMutedAmber
    @paletteMutedAmber.setter
    def paletteMutedAmber(self, c): self._paletteMutedAmber = c

    @pyqtProperty(QColor)
    def paletteMagenta(self): return self._paletteMagenta
    @paletteMagenta.setter
    def paletteMagenta(self, c): self._paletteMagenta = c

    @pyqtProperty(QColor)
    def paletteBlack(self): return self._paletteBlack
    @paletteBlack.setter
    def paletteBlack(self, c): self._paletteBlack = c

    @pyqtProperty(QColor)
    def paletteGray(self): return self._paletteGray
    @paletteGray.setter
    def paletteGray(self, c): self._paletteGray = c

    @pyqtProperty(QColor)
    def paletteWhite(self): return self._paletteWhite
    @paletteWhite.setter
    def paletteWhite(self, c): self._paletteWhite = c

    @pyqtProperty(QColor)
    def paletteVoid(self): return self._paletteVoid
    @paletteVoid.setter
    def paletteVoid(self, c): self._paletteVoid = c

    def _init_setup(self):
        # Move setup logic here to avoid constructor bloat
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.doubleClicked.connect(self._on_table_double_click)
        self.delegate = PlaylistItemDelegate(self)
        self.setItemDelegate(self.delegate)
        self._preview_row = None
        self._preview_after = False

    def _on_table_double_click(self, index):
        item = self.itemFromIndex(index)
        if item: self.itemDoubleClicked.emit(item.data(Qt.ItemDataRole.UserRole))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        self._preview_row = self.row(self.itemAt(event.position().toPoint()))
        self._preview_after = False
        if self._preview_row != -1:
            item_rect = self.visualItemRect(self.item(self._preview_row))
            if event.position().y() > item_rect.center().y(): self._preview_after = True
        self.viewport().update()
        event.acceptProposedAction()

    def dropEvent(self, event):
        self._preview_row = None
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if paths:
                from .library_widget import LibraryWidget
                main_window = self.window()
                library_widget = main_window.findChild(LibraryWidget)
                if library_widget:
                    songs = []
                    for path in paths:
                        metadata = library_widget.metadata_service.get_metadata(path)
                        songs.append(metadata)
                    library_widget.add_to_playlist.emit(songs)
            event.acceptProposedAction()
        else: super().dropEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._preview_row is not None:
            painter = QPainter(self.viewport())
            pen = QPen(self.property("paletteAmber") or QColor(constants.COLOR_AMBER), 2)
            painter.setPen(pen)
            item = self.item(self._preview_row)
            if item:
                rect = self.visualItemRect(item)
                y = rect.bottom() if self._preview_after else rect.top()
                painter.drawLine(rect.left(), y, rect.right(), y)
            painter.end()

    def startDrag(self, supportedActions):
        from PyQt6.QtGui import QDrag
        drag_items = self.selectedItems()
        if not drag_items: return
        drag = QDrag(self)
        drag.setMimeData(self.mimeData(drag_items))
        res = drag.exec(supportedActions, Qt.DropAction.MoveAction)
        if res == Qt.DropAction.MoveAction:
            for item in drag_items:
                row = self.row(item)
                if row >= 0: self.takeItem(row)

    def set_mini_mode(self, enabled: bool) -> None:
        if self.delegate.mini_mode != enabled:
            self.delegate.mini_mode = enabled
            self.doItemsLayout()
            self.viewport().update()

    def mimeData(self, items):
        mime = super().mimeData(items)
        if items:
            paths = []
            rows = []
            for item in items:
                row = self.row(item)
                if row >= 0: rows.append(row)
                data = item.data(Qt.ItemDataRole.UserRole)
                if data and "path" in data: paths.append(data["path"])
            if paths: mime.setData("application/x-gosling-playlist-items", json.dumps(paths).encode('utf-8'))
            if rows: mime.setData("application/x-gosling-playlist-rows", json.dumps(rows).encode('utf-8'))
        return mime