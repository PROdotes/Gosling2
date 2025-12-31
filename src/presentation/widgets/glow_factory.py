"""
GlowFactory - Unified workstation halo effects for various widgets.
Supports 'focus' triggers (for inputs) and 'hover' triggers (for buttons).
"""
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QFrame, QGraphicsBlurEffect, QHBoxLayout, 
    QLabel, QGridLayout, QPlainTextEdit, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, pyqtProperty


class GlowWidget(QWidget):
    """
    Generic wrapper that applies a blurred amber halo to a child widget.
    trigger_mode: "focus" or "hover"
    """
    def __init__(self, child_widget, trigger_mode="focus", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Balanced margin for the halo
        # 5px is the sweet spot: exactly enough for 4px blur without clipping,
        # and lets the 26px buttons fit into the 36px Title Bar.
        self.glow_margin = 5
        self.trigger_mode = trigger_mode
        self.child = child_widget
        self.glow_color = "#FFC66D" # Default workstation amber
        
        # Main layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(self.glow_margin, self.glow_margin, self.glow_margin, self.glow_margin)
        self.layout.setSpacing(0)
        # Removed strict AlignCenter to allow children to expand based on their SizePolicy
        
        # 1. THE GLOW FRAME
        self.glow_frame = QFrame(self)
        self.glow_frame.setObjectName("GlowFocusFrame")
        self.glow_frame.setStyleSheet("""
            #GlowFocusFrame {
                background-color: {self.glow_color};
                border-radius: 10px;
            }
        """)
        
        self.glow_blur = QGraphicsBlurEffect()
        self.glow_blur.setBlurRadius(4) # Toned down to 4 as per final preference
        self.glow_frame.setGraphicsEffect(self.glow_blur)
        self.glow_frame.hide()
        
        # Consistent radius for the glow
        self.glow_radius = 8
        self._update_glow_style()
        
        # 2. THE CHILD
        self.layout.addWidget(self.child, 1)
        self.child.installEventFilter(self)
        
        # Ensure glow is behind
        self.glow_frame.lower()

    def _update_glow_style(self):
        self.glow_frame.setStyleSheet(f"""
            #GlowFocusFrame {{
                background-color: {self.glow_color};
                border-radius: {self.glow_radius}px;
            }}
        """)

    def setGlowRadius(self, r):
        self.glow_radius = r
        self._update_glow_style()

    def setGlowColor(self, color):
        """Dynamic color support (e.g. blue for Music, red for System)"""
        self.glow_color = color
        self._update_glow_style()

    @pyqtProperty(str)
    def glowColor(self): return self.glow_color
    @glowColor.setter
    def glowColor(self, c): self.setGlowColor(c)

    @pyqtProperty(int)
    def glowRadius(self): return self.glow_radius
    @glowRadius.setter
    def glowRadius(self, r): self.setGlowRadius(r)

    def eventFilter(self, obj, event):
        if obj is self.child:
            if self.trigger_mode == "focus":
                if event.type() == QEvent.Type.FocusIn:
                    self._show_glow()
                elif event.type() == QEvent.Type.FocusOut:
                    self._hide_glow()
            elif self.trigger_mode == "hover":
                # ONLY show glow if the button is actually active/enabled
                if not self.child.isEnabled():
                    return super().eventFilter(obj, event)

                # Only hide if NOT checked (Underlight Logic)
                is_checked = getattr(self.child, "isChecked", lambda: False)()
                
                if event.type() == QEvent.Type.Enter:
                    self._show_glow()
                elif event.type() == QEvent.Type.Leave:
                    if not is_checked:
                        self._hide_glow()
        return super().eventFilter(obj, event)

    def _show_glow(self):
        self.glow_frame.show()
        self.glow_frame.raise_()
        self.child.raise_()
        
    def _hide_glow(self):
        self.glow_frame.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.glow_frame.setGeometry(self.child.geometry())

    def blockSignals(self, b):
        """Recursively block signals on child to prevent leaks (Fixes SidePanel ghost edits)."""
        self.child.blockSignals(b)
        return super().blockSignals(b)




class ReviewTooltip(QLabel):
    """Passive dropdown preview for long fields."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.WindowDoesNotAcceptFocus) 
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.setWordWrap(True)
        self.setStyleSheet("""
            QLabel {
                background-color: #0c0c0c;
                color: #C0C0C0;
                border: 1px solid #FFC66D;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }
        """)
        # Allow clicking links
        self.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.linkActivated.connect(self._on_link_clicked)
        self._current_indices = [] # Stores (start, end) for each item index
        self._target_edit = None

    def _on_link_clicked(self, link):
        if not self._target_edit or not link.startswith("idx_"):
            return
            
        try:
            idx = int(link.split("_")[1])
            if 0 <= idx < len(self._current_indices):
                start_pos = self._current_indices[idx]
                
                # Hack: Jump to end first to force scroll/view update
                self._target_edit.setCursorPosition(len(self._target_edit.text()))
                
                # Defer the jump-back to force the view to scroll 'leftwards' to the target
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(10, lambda: self._finish_jump(start_pos))
        except:
            pass

    def _finish_jump(self, pos):
        if self._target_edit:
            self._target_edit.setCursorPosition(pos)
            self._target_edit.setFocus()

    def update_with_cursor(self, edit_widget):
        self._target_edit = edit_widget
        text = edit_widget.text()
        cursor_pos = edit_widget.cursorPosition()
        
        if not text:
            self.hide()
            return

        # Smart Formatting & Highlighting
        has_list = "," in text
        
        display_html = ""
        self._current_indices = []
        
        if has_list:
            parts = text.split(',')
            current_idx = 0
            active_part_index = -1
            
            # 1. Map indices
            for i, part in enumerate(parts):
                part_len = len(part)
                # Store start position of this chunk (skipping the split comma logic roughly)
                # Actually, split doesn't tell us gaps. But we assume 1 char comma.
                # To be precise:
                # We should probably use regex or cumulative sum assuming ',' is the separator.
                start_pos = current_idx
                end_pos = current_idx + part_len
                
                # If this is not the first item, we likely skipped a comma
                # But wait, we iterate parts.
                # "A,B". parts=["A", "B"]. A=0-1. B=2-3.
                
                # Check for active cursor
                # Grace period: include the comma after it as "active" for that item?
                if start_pos <= cursor_pos <= end_pos + 1: 
                    active_part_index = i
                
                # Store start pos for clicking
                # Adjust start_pos to skip leading whitespace if any?
                # part includes the whitespace typically if we didn't strip it yet.
                # We strip for DISPLAY, but for CURSOR we need raw offsets.
                
                # Actually, let's keep 'part' RAW for index calculation
                # And 'clean_part' for display.
                
                # Store the start of the CONTENT (skipping leading space of the part?)
                # If text is "A, B", part 2 is " B". Start is 2.
                # User wants cursor at 3 ("B"). 
                # So we calculate whitespace offset.
                ws_len = len(part) - len(part.lstrip())
                click_target = start_pos + ws_len
                
                self._current_indices.append(click_target)
                
                current_idx += part_len + 1 # +1 for comma
            
            if active_part_index == -1: active_part_index = len(parts)-1

            # 2. Build HTML
            lines = []
            for i, part in enumerate(parts):
                clean_part = part.strip()
                style = "color: #999999; text-decoration: none;"
                if i == active_part_index:
                    style = "color: #FFC66D; font-weight: bold; text-decoration: none;"
                
                # Wrap in Link
                lines.append(f"<a href='idx_{i}' style='{style}'>{clean_part}</a>")
            
            display_html = "<br>".join(lines)
            
        else:
            display_html = text
            
        # ... Sizing Logic ...
        
        # Smart Check: Is the text actually cut off? (Using raw text)
        fm = edit_widget.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        visible_width = edit_widget.width() - 8 
        is_truncated = text_width > visible_width
        
        if not is_truncated and not has_list:
             self.hide()
             return
            
        base_geo = edit_widget.rect()
        global_pos = edit_widget.mapToGlobal(base_geo.bottomLeft())
        w = base_geo.width() 
        self.setFixedWidth(w)
        
        self.setText(display_html)
        self.adjustSize()
        
        self.move(global_pos.x(), global_pos.y() + 4)
        self.show()


class GlowLineEdit(GlowWidget):
    """Workstation Input with Amber Halo on focus."""
    def __init__(self, parent=None):
        self.edit = QLineEdit()
        self.edit.setObjectName("GlowInput")
        super().__init__(self.edit, trigger_mode="focus", parent=parent)
        
        # Preview capability
        self._preview_tip = None
        self._use_preview = False 

    def enable_overlay(self):
        """Turn on the Passive Preview mode."""
        self._use_preview = True
        # Connect signals
        self.edit.textChanged.connect(self._update_preview)
        self.edit.cursorPositionChanged.connect(lambda old, new: self._update_preview())
        
    def _update_preview(self, force_show=False):
        if self._preview_tip:
             # If forcing, show it regardless of current state
             if force_show or self._preview_tip.isVisible():
                 self._preview_tip.update_with_cursor(self.edit)

    def eventFilter(self, obj, event):
        # Intercept focus to trigger preview
        if self._use_preview and obj is self.edit:
            if event.type() == QEvent.Type.FocusIn:
                if not self._preview_tip:
                    self._preview_tip = ReviewTooltip(self.window())
                
                # Use Timer to allow layout to settle
                from PyQt6.QtCore import QTimer
                # Force show on Focus In
                QTimer.singleShot(50, lambda: self._update_preview(force_show=True))
                
            elif event.type() == QEvent.Type.FocusOut:
                if self._preview_tip:
                    self._preview_tip.hide()
            
        return super().eventFilter(obj, event)

    # Proxy methods for direct access
    def text(self): return self.edit.text()
    def setText(self, t): self.edit.setText(t)
    def setPlaceholderText(self, t): self.edit.setPlaceholderText(t)
    def setReadOnly(self, r): self.edit.setReadOnly(r)
    def setEnabled(self, e): self.edit.setEnabled(e)
    def setValidator(self, v): self.edit.setValidator(v)
    def setObjectName(self, n): self.edit.setObjectName(n)
    def setProperty(self, n, v): 
        self.edit.setProperty(n, v)
        self.edit.style().unpolish(self.edit)
        self.edit.style().polish(self.edit)    
    def setFocusPolicy(self, p): self.edit.setFocusPolicy(p)
    def clear(self): self.edit.clear()
    
    # Expose signals
    @property
    def textChanged(self): return self.edit.textChanged
    @property
    def returnPressed(self): return self.edit.returnPressed


class GlowButton(GlowWidget):
    """
    Workstation Button with Amber Halo on hover.
    Supports 'Backlit Text' system: Stacked labels in a centered grid.
    """
    clicked = pyqtSignal()
    toggled = pyqtSignal(bool)
    
    def __init__(self, text="", parent=None):
        self.btn = QPushButton()
        # Ensure the native button doesn't render its own text
        self.btn.setText("") 
        
        super().__init__(self.btn, trigger_mode="hover", parent=parent)
        policy = self.btn.sizePolicy()
        self.setSizePolicy(policy.horizontalPolicy(), policy.verticalPolicy())
        
        # Backlit Text System (Stacked Labels)
        # Use a Grid Layout to force perfect, unit-synced stacking
        self.btn_grid = QGridLayout(self.btn)
        self.btn_grid.setContentsMargins(0, 0, 0, 0)
        self.btn_grid.setSpacing(0)
        
        # 1. Text Glow (Behind)
        self.lbl_glow = QLabel(text, self.btn)
        self.lbl_glow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_glow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl_glow_blur = QGraphicsBlurEffect()
        self.lbl_glow_blur.setBlurRadius(6)
        self.lbl_glow.setGraphicsEffect(self.lbl_glow_blur)
        self.lbl_glow.hide() 
        
        # 2. Main Text (Front)
        self.lbl_main = QLabel(text, self.btn)
        self.lbl_main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_main.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Stack them in the same grid cell
        self.btn_grid.addWidget(self.lbl_glow, 0, 0)
        self.btn_grid.addWidget(self.lbl_main, 0, 0)
        
        self._update_text_styles()
        
        # Connections
        self.btn.clicked.connect(self.clicked.emit)
        self.btn.toggled.connect(self.toggled.emit)
        # Sync color state on check changes for toggle buttons
        self.btn.toggled.connect(self._on_toggled)

    def changeEvent(self, event):
        """Auto-update styles when enabled state changes (e.g. via parent)."""
        if event.type() == QEvent.Type.EnabledChange:
            self._update_text_styles()
        super().changeEvent(event)

    def showEvent(self, event):
        """Sync initial state on first show (handles startup states with blocked signals)."""
        super().showEvent(event)
        self._on_toggled(self.btn.isChecked())

    def _on_toggled(self, checked):
        if checked:
            self._show_glow()
            self.lbl_glow.show()
        else:
            # Only hide if mouse isn't currently hovering
            if not self.btn.underMouse():
                self._hide_glow()
                self.lbl_glow.hide()
        self._update_text_styles()

    def _update_text_styles(self):
        """Sync label colors with the glow color logic"""
        is_checked = self.btn.isChecked()
        is_hovered = self.btn.underMouse()
        is_enabled = self.btn.isEnabled()
        
        # 1. Main Text Color
        if not is_enabled:
            # Dead State: Ghosted Gray
            color = "#444444"
        elif is_checked:
            # Active/Locked: Amber (or Signature Color)
            color = self.glow_color
        elif is_hovered:
            # Hover: Sharp White (tactile hint)
            color = "#FFFFFF"
        else:
            # Idle: Muted Gray
            color = "#DDDDDD"
            
        self.lbl_main.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
        self.lbl_glow.setStyleSheet(f"color: {self.glow_color}; background: transparent; font-weight: bold;")
        
        # 2. Text Glow (Bleed) visibility
        # ONLY show text glow if checked
        if is_checked:
            self.lbl_glow.show()
        else:
            self.lbl_glow.hide()

    def _show_glow(self):
        super()._show_glow()
        # Z-ORDER FIX
        self.lbl_glow.raise_()
        self.lbl_main.raise_()
        self._update_text_styles()

    def _hide_glow(self):
        if not self.btn.isChecked():
            super()._hide_glow()
            self.lbl_glow.hide()
        self._update_text_styles()

    def setGlowColor(self, color):
        super().setGlowColor(color)
        self._update_text_styles()

    def setText(self, text):
        """Update the backlit labels and keep native text empty to prevent ghosting."""
        self.lbl_glow.setText(text)
        self.lbl_main.setText(text)
        self.btn.setText("") # Ensure native text is never shown
        self._update_text_styles() # Refresh color state immediately

    def setFont(self, f): 
        self.btn.setFont(f)
        self.lbl_main.setFont(f)
        self.lbl_glow.setFont(f)
    def setVisible(self, v):
        super().setVisible(v)
        self.btn.setVisible(v)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Layout handles the grid stacking automatically
        pass
    # Proxy methods
    def isChecked(self): return self.btn.isChecked()
    def isCheckable(self): return self.btn.isCheckable()
    def isEnabled(self): return self.btn.isEnabled()
    def isVisible(self): return self.btn.isVisible()
    def text(self): return self.lbl_main.text()
    def setCheckable(self, c): self.btn.setCheckable(c)
    def setChecked(self, c): self.btn.setChecked(c)
    def setIcon(self, i): 
        self.btn.setIcon(i)
        # Icons don't work with backlit text currently, so we hide main label if icon set?
        # For now, just fix the proxy issue.
    def setIconSize(self, s): self.btn.setIconSize(s)
    def setToolTip(self, t): self.btn.setToolTip(t)
    def setObjectName(self, n):
        super().setObjectName(n)
        self.btn.setObjectName(n)
        
    def setProperty(self, n, v):
        super().setProperty(n, v)
        self.btn.setProperty(n, v)
        # Force a style refresh if the property might affect QSS
        self.style().unpolish(self)
        self.style().polish(self)
        
    def setStyleSheet(self, s):
        super().setStyleSheet(s)
        self.btn.setStyleSheet(s)
    def setMinimumWidth(self, w): 
        self.btn.setMinimumWidth(w)
        super().setMinimumWidth(w + (self.glow_margin * 2))
        
    def setMinimumHeight(self, h):
        self.btn.setMinimumHeight(h)
        super().setMinimumHeight(h + (self.glow_margin * 2))

    def setMaximumWidth(self, w):
        self.btn.setMaximumWidth(w)
        super().setMaximumWidth(w + (self.glow_margin * 2))

    def setMaximumHeight(self, h):
        self.btn.setMaximumHeight(h)
        super().setMaximumHeight(h + (self.glow_margin * 2))

    def setFixedSize(self, w, h):
        self.btn.setFixedSize(w, h)
        super().setFixedSize(w + (self.glow_margin * 2), h + (self.glow_margin * 2))
        
    def setFixedWidth(self, w): 
        self.btn.setFixedWidth(w)
        super().setFixedWidth(w + (self.glow_margin * 2))
        
    def setFixedHeight(self, h): 
        self.btn.setFixedHeight(h)
        super().setFixedHeight(h + (self.glow_margin * 2))

    def setSizePolicy(self, *args):
        # Support both (h, v) and (QSizePolicy)
        if len(args) == 1:
            super().setSizePolicy(args[0])
            self.btn.setSizePolicy(args[0])
        elif len(args) == 2:
            super().setSizePolicy(args[0], args[1])
            self.btn.setSizePolicy(args[0], args[1])

    def setEnabled(self, e): 
        self.btn.setEnabled(e)
        if not e:
            self._hide_glow()
        self._update_text_styles()
        
    def setCursor(self, c): self.btn.setCursor(c)
    def setFocusPolicy(self, p): self.btn.setFocusPolicy(p)


class GlowComboBox(QWidget):
    """
    Editable ComboBox with focus glow effect.
    
    Uses a container+overlay approach instead of the wrapper approach
    (like GlowWidget) to avoid layout expansion issues in QHBoxLayout.
    The glow frame is a sibling positioned behind the combo on focus.
    """
    # Proxy the main signals
    currentIndexChanged = pyqtSignal(int)
    currentTextChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.glow_margin = 5
        self.glow_color = "#FFC66D"
        
        # Layout with margins for glow (uniform like GlowLineEdit/GlowButton)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(self.glow_margin, self.glow_margin, 
                                   self.glow_margin, self.glow_margin)
        layout.setSpacing(0)
        
        # The glow frame (sibling, hidden by default)
        self._glow_frame = QFrame(self)
        self._glow_frame.setStyleSheet(f"background-color: {self.glow_color}; border-radius: 10px;")
        self._glow_blur = QGraphicsBlurEffect()
        self._glow_blur.setBlurRadius(4)
        self._glow_frame.setGraphicsEffect(self._glow_blur)
        self._glow_frame.hide()
        
        # The actual combo
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.installEventFilter(self)
        layout.addWidget(self.combo)
        
        # Forward signals
        self.combo.currentIndexChanged.connect(self.currentIndexChanged.emit)
        self.combo.currentTextChanged.connect(self.currentTextChanged.emit)
    
    def eventFilter(self, obj, event):
        if obj is self.combo:
            if event.type() == QEvent.Type.FocusIn:
                self._show_glow()
            elif event.type() == QEvent.Type.FocusOut:
                # Don't hide glow if dropdown popup is open
                if not self.combo.view().isVisible():
                    self._hide_glow()
        return super().eventFilter(obj, event)
    
    def _show_glow(self):
        # Position glow behind combo
        self._glow_frame.setGeometry(self.combo.geometry())
        self._glow_frame.show()
        self._glow_frame.lower()
        self.combo.raise_()
    
    def _hide_glow(self):
        self._glow_frame.hide()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep glow synced if visible
        if self._glow_frame.isVisible():
            self._glow_frame.setGeometry(self.combo.geometry())
    
    def setGlowColor(self, color):
        self.glow_color = color
        self._glow_frame.setStyleSheet(f"background-color: {color}; border-radius: 10px;")
    
    # Proxy methods for QComboBox API
    def setInsertPolicy(self, p): self.combo.setInsertPolicy(p)
    def completer(self): return self.combo.completer()
    def setObjectName(self, n): 
        super().setObjectName(n)
        self.combo.setObjectName(n)
    def addItem(self, text, data=None): self.combo.addItem(text, data)
    def addItems(self, items): self.combo.addItems(items)
    def clear(self): self.combo.clear()
    def count(self): return self.combo.count()
    def currentIndex(self): return self.combo.currentIndex()
    def currentText(self): return self.combo.currentText()
    def currentData(self, role=Qt.ItemDataRole.UserRole): return self.combo.currentData(role)
    def setCurrentIndex(self, i): self.combo.setCurrentIndex(i)
    def setCurrentText(self, t): self.combo.setCurrentText(t)
    def findData(self, data): return self.combo.findData(data)
    def findText(self, text): return self.combo.findText(text)
    def itemData(self, i, role=Qt.ItemDataRole.UserRole): return self.combo.itemData(i, role)
    def setItemData(self, i, data, role=Qt.ItemDataRole.UserRole): self.combo.setItemData(i, data, role)
    def blockSignals(self, b): return self.combo.blockSignals(b)
    def setFocus(self): self.combo.setFocus()
    def setEnabled(self, e): self.combo.setEnabled(e)
    def setEditable(self, e): self.combo.setEditable(e)
    def itemText(self, i): return self.combo.itemText(i)

