"""Custom playlist widget with drag and drop support"""
import os
import json
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QStyledItemDelegate, QStyle
from PyQt6.QtCore import Qt, QRect, QSize, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QPen, QColor, QPainter
from ...business.services.metadata_service import MetadataService
from ...resources import constants


class PlaylistItemDelegate(QStyledItemDelegate):
    """Custom delegate for playlist items.
    Reads colors from QPalette (QSS-controlled), falls back to constants.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.performer_font = QFont("Bahnschrift Condensed", 12, QFont.Weight.Bold)
        self.title_font = QFont("Bahnschrift Condensed", 10)
        self.mini_font = QFont("Bahnschrift Condensed", 10)
        self.mini_mode = False

    ITEM_SPACING = 4

    def paint(self, painter, option, index) -> None:
        """Custom paint for playlist items with live playback sweep"""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Read colors from palette (QSS-controlled)
        palette = option.palette
        base_color = palette.color(palette.ColorRole.Base)
        alt_color = palette.color(palette.ColorRole.AlternateBase)
        text_color = palette.color(palette.ColorRole.Text)
        highlight_color = palette.color(palette.ColorRole.Highlight)
        highlight_text = palette.color(palette.ColorRole.HighlightedText)
        
        visual_rect = QRect(
            option.rect.left(),
            option.rect.top(),
            option.rect.width(),
            option.rect.height() - self.ITEM_SPACING
        )

        # Basic row background
        is_selected = option.state & QStyle.StateFlag.State_Selected
        row_bg = alt_color if alt_color.isValid() else QColor(constants.COLOR_VOID)
        sel_bg = highlight_color if highlight_color.isValid() else QColor(constants.COLOR_AMBER)
        
        if is_selected:
            painter.fillRect(visual_rect, sel_bg)
            txt_color = highlight_text if highlight_text.isValid() else QColor(constants.COLOR_BLACK)
        else:
            painter.fillRect(visual_rect, row_bg)
            txt_color = text_color if text_color.isValid() else QColor(constants.COLOR_WHITE)
            divider = base_color if base_color.isValid() else QColor(constants.COLOR_BLACK)
            painter.setPen(divider)
            painter.drawLine(visual_rect.bottomLeft(), visual_rect.bottomRight())
        
        # Metadata extraction
        data = index.data(Qt.ItemDataRole.UserRole) or {}
        duration_sec = data.get('duration', 0)
        
        # --- PLAYBACK SWEEP (User Request) ---
        is_playing = (self.parent() and getattr(self.parent(), '_active_row', -1) == index.row())
        current_dur_str = ""
        
        if is_playing and duration_sec > 0:
            current_ms = getattr(self.parent(), '_current_pos_ms', 0)
            progress = min(1.0, current_ms / (duration_sec * 1000.0))
            
            # Draw Progress Sweep (Darker Overlay)
            sweep_width = int(visual_rect.width() * progress)
            sweep_rect = QRect(visual_rect.left(), visual_rect.top(), sweep_width, visual_rect.height())
            
            overlay = QColor(0, 0, 0, 60) # 60 alpha dark wash
            painter.fillRect(sweep_rect, overlay)
            
            # Format elapsed time
            em, es = divmod(int(current_ms // 1000), 60)
            current_dur_str = f"{em}:{es:02d}/"

        # Format total duration
        m, s = divmod(int(duration_sec), 60)
        total_dur_str = f"{m}:{s:02d}"
        display_duration = f"{current_dur_str}{total_dur_str}"

        # Text Preparation
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
            painter.setPen(txt_color)
            combined = f"{performer.upper()} - {title}" if title else performer.upper()
            
            # Left: Performer - Title
            painter.drawText(
                visual_rect.adjusted(padding, 0, -padding, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                combined
            )
            # Right: Duration
            painter.drawText(
                visual_rect.adjusted(padding, 0, -padding, 0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                display_duration
            )
        else:
            # Circle (semantic: always magenta)
            circle_diameter = int(visual_rect.height() * 0.75)
            circle_top = visual_rect.top() + (visual_rect.height() - circle_diameter) // 2
            circle_right_padding = -int(circle_diameter * 0.3)
            circle_left = visual_rect.right() - circle_diameter - circle_right_padding
            circle_rect = QRect(circle_left, circle_top, circle_diameter, circle_diameter)

            painter.setBrush(QColor(constants.COLOR_MAGENTA))
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

            # Left side content
            painter.setFont(self.performer_font)
            painter.setPen(txt_color)
            painter.drawText(performer_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, performer.upper())

            painter.setFont(self.title_font)
            painter.setPen(txt_color)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title.strip())
            
            # Sub-Title Duration Readout (Right-aligned)
            painter.setFont(self.mini_font)
            painter.setPen(txt_color)
            dur_rect = QRect(text_rect.left(), title_rect.top(), text_rect.width(), title_rect.height())
            painter.drawText(dur_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, display_duration)

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        width = option.rect.width() if option.rect.width() > 0 else 200
        height = 24 if self.mini_mode else 54
        return QSize(width, height + self.ITEM_SPACING)


class PlaylistWidget(QListWidget):
    """Custom list widget for playlist."""

    itemDoubleClicked = pyqtSignal(object)
    playlist_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PlaylistWidget")
        self._init_setup()
    
    def _init_setup(self):
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        # self.doubleClicked.connect(self._on_table_double_click)
        self.delegate = PlaylistItemDelegate(self)
        self.setItemDelegate(self.delegate)
        self._preview_row = None
        self._preview_after = False
        
        # Playback Tracking (T-?? / User Request)
        self._active_row = -1
        self._current_pos_ms = 0
        
        # Connect model signals for automatic change detection
        # Use weakref proxy or a safer lambda to avoid RuntimeError on deletion
        self.model().rowsInserted.connect(self._safe_emit_changed)
        self.model().rowsRemoved.connect(self._safe_emit_changed)
        self.model().modelReset.connect(self._safe_emit_changed)

    def _safe_emit_changed(self, *args):
        """Safely emit signal, preventing 'object deleted' errors."""
        try:
            # Basic sanity check: if 'self' is still a valid Qt object
            self.playlist_changed.emit()
        except (RuntimeError, AttributeError):
            pass
    
    def update_playback_progress(self, row: int, pos_ms: int):
        """Update the progress of the currently playing item."""
        self._active_row = row
        self._current_pos_ms = pos_ms
        # High-frequency trigger for visual sweep
        self.viewport().update()

    # def _on_table_double_click(self, index):
    #     item = self.itemFromIndex(index)
    #     if item: self.itemDoubleClicked.emit(item.data(Qt.ItemDataRole.UserRole))

    def dragLeaveEvent(self, event):
        self._preview_row = None
        self.viewport().update()
        super().dragLeaveEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if item:
            self._preview_row = self.row(item)
            item_rect = self.visualItemRect(item)
            self._preview_after = event.position().y() > item_rect.center().y()
        else:
            # Hovering empty space -> Append to bottom
            if self.count() > 0:
                self._preview_row = self.count() - 1 
                self._preview_after = True
            else:
                self._preview_row = None # Empty list handled elsewhere or no line needed
                
        self.viewport().update()
        event.acceptProposedAction()

    def dropEvent(self, event):
        # 1. Self-Reordering (Internal Move)
        if event.source() == self:
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            
            # Manual Move Logic
            # 1. Gather Items
            items = self.selectedItems()
            if not items: return
            
            # Sort by row to handle removals cleanly
            rows = sorted([self.row(i) for i in items])
            
            # 2. Extract Data
            moved_data = []
            for item in items:
                data = item.data(Qt.ItemDataRole.UserRole)
                text = item.text() # "Performer | Title"
                moved_data.append((text, data))
            
            # 3. Determine Insertion Point
            # Use preview_row as the base
            target_row = self._preview_row if self._preview_row is not None else self.count()
            if self._preview_after and self._preview_row is not None:
                target_row += 1
            
            # 4. Remove Originals (Adjust target_row dynamically)
            # We must be careful: if we remove items ABOVE target_row, target_row shifts down.
            rows_above_target = [r for r in rows if r < target_row]
            shift = len(rows_above_target)
            final_row = target_row - shift
            
            for item in items:
                self.takeItem(self.row(item)) # Removes from list, row becomes -1
                
            # 5. Insert New Items
            from PyQt6.QtWidgets import QListWidgetItem
            for text, data in reversed(moved_data):
                new_item = QListWidgetItem(text)
                new_item.setData(Qt.ItemDataRole.UserRole, data)
                self.insertItem(final_row, new_item)
                # Select the moved items? Optional polish.
                new_item.setSelected(True)

            self._preview_row = None
            self.viewport().update()
            
            # startDrag loop checks self.row(item) >= 0. 
            # Since we took originals, their row is -1.
            # So startDrag will safely do nothing.
            return
            
        # Target Row Logic (For External Drops)
        if self._preview_row is not None:
             drop_row = self._preview_row
             # If dropping "after" the item, increment index
             if self._preview_after:
                 drop_row += 1
        else:
             # Dropping in void -> append to end
             drop_row = self.count()

        self._preview_row = None
        
        # 2. Internal Drag (from Library via Custom MIME)
        if event.mimeData().hasFormat("application/x-gosling-library-rows"):
            json_data = event.mimeData().data("application/x-gosling-library-rows").data().decode('utf-8')
            try:
                songs = json.loads(json_data)
                
                # Direct Insertion (Standardized)
                from PyQt6.QtWidgets import QListWidgetItem
                
                # Reverse iterate if inserting so they appear in correct order
                for s in reversed(songs):
                     title_disp = s.get('title', 'Unknown Title')
                     perf_disp = s.get('performer', 'Unknown Artist')
                     path = s.get('path')
                     duration = s.get('duration', 0)
                     
                     list_item = QListWidgetItem(f"{perf_disp} | {title_disp}")
                     list_item.setData(Qt.ItemDataRole.UserRole, {
                         "path": path,
                         "duration": duration
                     })
                     self.insertItem(drop_row, list_item)
                          
                event.acceptProposedAction()
                return
            except Exception as e:
                print(f"Error processing library drop: {e}")
                return

        # 3. External Drag (Files from Explorer)
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if paths:
                from .library_widget import LibraryWidget
                main_window = self.window()
                library_widget = main_window.findChild(LibraryWidget)
                if library_widget:
                    
                    # Pre-calculate songs to insert
                    songs_to_insert = []
                    for path in paths:
                        try:
                            song_obj = library_widget.metadata_service.extract_from_mp3(path)
                            songs_to_insert.append({
                                "path": path,
                                "performer": song_obj.performers[0] if song_obj.performers else (song_obj.artist or "Unknown"),
                                "title": song_obj.title or "Unknown Title"
                            })
                        except Exception as e:
                            print(f"Error parsing drop: {e}")
                            songs_to_insert.append({"path": path, "performer": "Unknown", "title": "Unknown Title"})

                    # Direct Insertion
                    from PyQt6.QtWidgets import QListWidgetItem
                    for s in reversed(songs_to_insert):
                         list_item = QListWidgetItem(f"{s['performer']} | {s['title']}")
                         list_item.setData(Qt.ItemDataRole.UserRole, {
                             "path": s['path'],
                             "duration": s.get('duration', 0)
                         })
                         self.insertItem(drop_row, list_item)

                self.playlist_changed.emit()
                event.acceptProposedAction()
        else: super().dropEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._preview_row is not None:
            painter = QPainter(self.viewport())
            pen = QPen(QColor(constants.COLOR_AMBER), 2)
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