"""Custom playlist widget with drag and drop support"""
import os
import json
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QStyledItemDelegate, QStyle
from PyQt6.QtCore import Qt, QRect, QSize, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QPen, QColor, QPainter
from ...business.services.metadata_service import MetadataService


class PlaylistItemDelegate(QStyledItemDelegate):
    """Custom delegate for playlist items"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.performer_font = QFont("Bahnschrift Condensed", 12, QFont.Weight.Bold)
        self.title_font = QFont("Bahnschrift Condensed", 10)
        self.mini_font = QFont("Bahnschrift Condensed", 10)
        self.mini_mode = False

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
            painter.fillRect(visual_rect, QColor("#FF8C00")) # Industrial Amber Selection
            painter.setPen(QColor("#000")) # Black text on selection
        else:
            painter.fillRect(visual_rect, QColor("#111111")) # Machined Black 
            # Add subtle bottom line
            painter.setPen(QColor("#000"))
            painter.drawLine(visual_rect.bottomLeft(), visual_rect.bottomRight())
        

        # Text
        display_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        if "|" in display_text:
            parts = [p.strip() for p in display_text.split("|", 1)]
            performer = parts[0]
            title = parts[1] if len(parts) > 1 else ""
        else:
            performer, title = display_text, ""

        padding = 5
        
        if self.mini_mode:
            # High-density Surgical Row
            painter.setFont(self.mini_font)
            painter.setPen(QPen(option.palette.text() if not (option.state & QStyle.StateFlag.State_Selected) else Qt.GlobalColor.white, 1))
            
            # Draw combined text: PERFORMER - Title
            combined = f"{performer.upper()} - {title}" if title else performer.upper()
            painter.drawText(
                visual_rect.adjusted(padding, 0, -padding, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                combined
            )
        else:
            # Full Consumer Row
            # Circle (right side)
            circle_diameter = int(visual_rect.height() * 0.75)
            circle_top = visual_rect.top() + (visual_rect.height() - circle_diameter) // 2
            circle_right_padding = -int(circle_diameter * 0.3)
            circle_left = visual_rect.right() - circle_diameter - circle_right_padding
            circle_rect = QRect(circle_left, circle_top, circle_diameter, circle_diameter)

            painter.setBrush(QColor("#f44336"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(circle_rect)

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
        # Mini: 28px, Full: 54px (+ spacing)
        height = 24 if self.mini_mode else 54
        return QSize(width, height + self.ITEM_SPACING)


class PlaylistWidget(QListWidget):
    """Custom list widget with drag and drop for playlists"""

    itemDoubleClicked = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Double Click to Play
        self.doubleClicked.connect(self._on_table_double_click)
        
        self.delegate = PlaylistItemDelegate(self)
        self.setItemDelegate(self.delegate)
        
        self._preview_row = None
        self._preview_after = False

    def startDrag(self, supportedActions):
        """Override startDrag to control removal logic"""
        from PyQt6.QtGui import QDrag
        
        # Capture items explicitly BEFORE drag starts
        drag_items = self.selectedItems()
        if not drag_items:
            return

        drag = QDrag(self)
        drag.setMimeData(self.mimeData(drag_items))
        # drag.setPixmap(self.grab().scaledToWidth(200)) # Optional visual
        
        # Execute drag
        res = drag.exec(supportedActions, Qt.DropAction.MoveAction)
        
        # Manual Cleanup if MoveAction
        if res == Qt.DropAction.MoveAction:
            # Safe removal: Remove captured original items
            for item in drag_items:
                row = self.row(item)
                if row >= 0:
                    self.takeItem(row)

    def set_mini_mode(self, enabled: bool) -> None:
        """Toggle detailed vs. high-density row rendering"""
        if self.delegate.mini_mode != enabled:
            self.delegate.mini_mode = enabled
            # Force refresh of all items
            self.doItemsLayout()
            self.viewport().update()

    def mimeData(self, items):
        """Override to add custom mime type for internal D&D verification"""
        mime = super().mimeData(items)
        if items:
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
        if mime.hasFormat("application/x-gosling-library-rows"):
            event.acceptProposedAction()
        elif mime.hasUrls():
            # Check if at least one URL is an MP3
            has_mp3 = any(url.toLocalFile().lower().endswith('.mp3') for url in mime.urls())
            if has_mp3:
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
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        
        if index.isValid():
            insert_row = index.row() + (1 if self._preview_after else 0)
        else:
            insert_row = self.count()

        # 1. Incoming from Gosling Library (Optimized)
        if mime.hasFormat("application/x-gosling-library-rows"):
            try:
                songs = json.loads(mime.data("application/x-gosling-library-rows").data().decode('utf-8'))
                for s in songs:
                    display_text = f"{s['performer']} | {s['title']}"
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, {"path": s['path']})
                    self.insertItem(insert_row, item)
                    insert_row += 1
                event.acceptProposedAction()
            except Exception:
                event.ignore()
            self._preview_row = None
            self.viewport().update()
            return

        # 2. Incoming Local Files
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if not os.path.isfile(path):
                    continue
                
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
            event.acceptProposedAction()
            self._preview_row = None
            self.viewport().update()
            return
        
        # 3. Internal Move
        super().dropEvent(event)
        self._preview_row = None

    def paintEvent(self, event) -> None:
        """Custom paint to show drop preview line"""
        super().paintEvent(event)
        if self._preview_row is None:
            return

        painter = QPainter(self.viewport())
        pen = QPen(QColor("#FF8C00"), 2) # Industrial Amber Preview Line
        painter.setPen(pen)

        if self._preview_row < self.count():
            item = self.item(self._preview_row)
            if item:
                rect = self.visualItemRect(item)
                y = rect.bottom() if self._preview_after else rect.top()
                painter.drawLine(0, y, self.viewport().width(), y)
        elif self.count() > 0:
            last_item = self.item(self.count() - 1)
            if last_item:
                last_rect = self.visualItemRect(last_item)
                y = last_rect.bottom()
                painter.drawLine(0, y, self.viewport().width(), y)

    def _on_table_double_click(self, index) -> None:
        """Handle double click on item"""
        item = self.item(index.row())
        if item:
            self.itemDoubleClicked.emit(item)