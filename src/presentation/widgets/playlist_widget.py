"""Custom playlist widget with drag and drop support"""
import os
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QStyledItemDelegate, QStyle
from PyQt6.QtCore import Qt, QRect, QSize, QUrl
from PyQt6.QtGui import QFont, QPen, QColor, QPainter
from ...business.services.metadata_service import MetadataService


class PlaylistItemDelegate(QStyledItemDelegate):
    """Custom delegate for playlist items"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.performer_font = QFont("Arial", 12, QFont.Weight.Bold)
        self.title_font = QFont("Arial", 10)

    ITEM_SPACING = 4 # Gap between items in pixels

    def paint(self, painter, option, index) -> None:
        """Custom paint for playlist items"""
        painter.save()
        
        # Adjust rect for spacing - make the visual item slightly smaller than the allocated space
        visual_rect = QRect(
            option.rect.left(),
            option.rect.top(),
            option.rect.width(),
            option.rect.height() - self.ITEM_SPACING
        )

        # Background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(visual_rect, QColor("#1E5096"))
        else:
            painter.fillRect(visual_rect, QColor("#444444"))

        # Circle (right side)
        circle_diameter = int(visual_rect.height() * 0.75)
        circle_top = visual_rect.top() + (visual_rect.height() - circle_diameter) // 2
        circle_right_padding = -int(circle_diameter * 0.3)
        circle_left = visual_rect.right() - circle_diameter - circle_right_padding
        circle_rect = QRect(circle_left, circle_top, circle_diameter, circle_diameter)

        painter.setBrush(QColor("#f44336"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(circle_rect)

        # Text
        display_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        if "|" in display_text:
            performer, title = display_text.split("|", 1)
        else:
            performer, title = display_text, ""

        padding = 5
        text_rect = QRect(
            visual_rect.left() + padding,
            visual_rect.top() + padding,
            circle_rect.left() - visual_rect.left() - 2 * padding,
            visual_rect.height() - 2 * padding
        )

        performer_rect = QRect(
            text_rect.left(), text_rect.top(),
            text_rect.width(), text_rect.height() // 2
        )
        title_rect = QRect(
            text_rect.left(), text_rect.top() + text_rect.height() // 2,
            text_rect.width(), text_rect.height() // 2
        )

        painter.setFont(self.performer_font)
        painter.setPen(QPen(option.palette.text(), 1))
        painter.drawText(
            performer_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            performer.strip()
        )

        painter.setFont(self.title_font)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title.strip()
        )

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        """Return preferred size"""
        width = option.rect.width() if option.rect.width() > 0 else 200
        # Base height 54 + spacing
        return QSize(width, 54 + self.ITEM_SPACING)


class PlaylistWidget(QListWidget):
    """Custom list widget with drag and drop for playlists"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setItemDelegate(PlaylistItemDelegate())
        self._preview_row = None
        self._preview_after = False

    def mimeData(self, items):
        """Override to add custom mime type for internal D&D verification"""
        mime = super().mimeData(items)
        if items:
            import json
            # Store paths (legacy/debug)
            paths = []
            # Store rows (for specific removal)
            rows = []
            
            for item in items:
                row = self.row(item)
                if row >= 0:
                    rows.append(row)
                
                data = item.data(Qt.ItemDataRole.UserRole)
                if data and "path" in data:
                    paths.append(data["path"])
            
            if paths:
                mime.setData("application/x-gosling-playlist-items", json.dumps(paths).encode('utf-8'))
            if rows:
                mime.setData("application/x-gosling-playlist-rows", json.dumps(rows).encode('utf-8'))
        
        return mime

    def dragEnterEvent(self, event) -> None:
        """Handle drag enter"""
        mime = event.mimeData()
        if mime.hasUrls():
            # Check if at least one file is valid audio
            has_audio = False
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    ext = path.lower().split('.')[-1]
                    if ext in ['mp3']:
                        has_audio = True
                        break
            
            if has_audio:
                event.acceptProposedAction()
            else:
                event.ignore()
        elif event.source() == self:
             event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        """Handle drag move with preview line"""
        pos = event.position().toPoint()
        index = self.indexAt(pos)

        if index.isValid():
            rect = self.visualItemRect(self.item(index.row()))
            midpoint = rect.top() + rect.height() / 2
            self._preview_row = index.row()
            self._preview_after = pos.y() >= midpoint
        else:
            self._preview_row = self.count() - 1
            self._preview_after = True

        self.viewport().update()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave"""
        self._preview_row = None
        self.viewport().update()

    def dropEvent(self, event) -> None:
        """Handle drop event"""
        mime = event.mimeData()

        if mime.hasUrls():
            pos = event.position().toPoint()
            index = self.indexAt(pos)

            if index.isValid():
                insert_row = index.row() + (1 if self._preview_after else 0)
            else:
                insert_row = self.count()

            for url in mime.urls():
                path = url.toLocalFile()
                if not os.path.isfile(path):
                    continue
                
                # Check extension
                ext = path.lower().split('.')[-1]
                if ext not in ['mp3']:
                    continue

                display_text = os.path.basename(path)
                try:
                    song = MetadataService.extract_from_mp3(path)
                    if song:
                        display_text = f"{song.get_display_performers()} | {song.get_display_title()}"
                except Exception:
                    pass

                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, {"path": path})
                self.insertItem(insert_row, item)
                insert_row += 1

            self._preview_row = None
            self.viewport().update()
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
            self._preview_row = None

    def paintEvent(self, event) -> None:
        """Custom paint to show drop preview line"""
        super().paintEvent(event)
        if self._preview_row is None:
            return

        painter = QPainter(self.viewport())
        pen = QPen(Qt.GlobalColor.red, 2)
        painter.setPen(pen)

        if self._preview_row < self.count():
            rect = self.visualItemRect(self.item(self._preview_row))
            y = rect.bottom() if self._preview_after else rect.top()
        else:
            last_rect = self.visualItemRect(self.item(self.count() - 1))
            y = last_rect.bottom()

        painter.drawLine(0, y, self.viewport().width(), y)

