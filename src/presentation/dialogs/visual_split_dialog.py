import re
from typing import List, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QWidget, QDialogButtonBox,
    QFrame, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class VisualSplitDialog(QDialog):
    """
    Dialog for interactively splitting complex entity strings.
    User can toggle delimiters to choose where to split.
    """
    
    def __init__(self, original_text: str, service_provider=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Split Artists")
        self.resize(600, 450)
        
        self.services = service_provider
        self.original_text = original_text
        self.tokens: List[dict] = []  
        self.custom_delims: List[str] = [] # User-added split words
        
        # Expanded Regex for common music delimiters
        self.delim_pattern = r'(,\s*|\s+&\s+|\s+feat\.?\s+|\s+ft\.?\s+|\s+featuring\s+|\s+inc\.?\s+|\s+w/\s+|\s+with\s+|\s+vs\.?\s+|\s+and\s+|\s+pres\.?\s+|\s+presents\s+|/|;)'
        self.delim_regex = re.compile(self.delim_pattern, re.IGNORECASE)
        
        self._parse_tokens(original_text)
        self._init_ui()
        self._update_preview()
        
    def _parse_tokens(self, text: str, preserve_states=False):
        """
        Parse text into segments and delimiters.
        If preserve_states is True, it tries to keep the 'active' status 
        of delimiters that were already present by tracking their text and order.
        """
        old_states = {} # Map of "delim_text" -> [list of booleans for each occurrence]
        if preserve_states:
            for t in self.tokens:
                if t['is_delim']:
                    txt = t['text']
                    if txt not in old_states:
                        old_states[txt] = []
                    old_states[txt].append(t['active'])

        self.tokens = []
        
        # Merge default pattern with custom delimiters
        active_pattern = self.delim_pattern
        if self.custom_delims:
            # Escape custom delims and join with |
            custom_pattern = "|".join([re.escape(d) for d in self.custom_delims])
            active_pattern = active_pattern.replace(")", f"|\\s+{custom_pattern}\\s+|{custom_pattern})")
            
        active_regex = re.compile(active_pattern, re.IGNORECASE)
        parts = active_regex.split(text)
        
        # Track which index we are on for each delimiter text to restore state correctly
        occurrence_counters = {} 
        
        for i, part in enumerate(parts):
            if not part: continue
            is_delim = bool(active_regex.fullmatch(part))
            
            active = is_delim
            if is_delim:
                # Get the counter for this specific delimiter string (e.g. ", ")
                occ_idx = occurrence_counters.get(part, 0)
                
                # Check if we have a recorded state for this specific occurrence
                if part in old_states and occ_idx < len(old_states[part]):
                    active = old_states[part][occ_idx]
                
                # Increment counter for next time we see this exact string
                occurrence_counters[part] = occ_idx + 1
                
            self.tokens.append({'text': part, 'is_delim': is_delim, 'active': active})

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 1. Manual Split Input
        top_bar = QHBoxLayout()
        self.txt_custom_input = QLineEdit()
        self.txt_custom_input.setPlaceholderText("Missing a split word? Type it here... (e.g. 'inc', 'x', '-')")
        self.txt_custom_input.returnPressed.connect(self._add_custom_delim)
        
        btn_add_delim = QPushButton("Add Split")
        btn_add_delim.clicked.connect(self._add_custom_delim)
        
        top_bar.addWidget(self.txt_custom_input)
        top_bar.addWidget(btn_add_delim)
        layout.addLayout(top_bar)

        # Instructions
        lbl_instr = QLabel("Click on the tokens below to toggle Split (Red) or Join (Gray).")
        lbl_instr.setStyleSheet("color: #888; font-style: italic; margin-top: 4px;")
        layout.addWidget(lbl_instr)
        
        # 1. Interactive Area (Flow Layout roughly simulated with QHBox wrapped or similar)
        # Since we want a flow of text, a FlowLayout would be ideal, but for simplicity
        # let's use a QScrollArea with a horizontal layout that wraps, or just a QWidget with a custom flow layout.
        # Actually, let's try a simple Horizontal Layout with a scrollbar if it gets too long, 
        # but pure horizontal might be bad for long strings.
        # Let's use a custom FlowLayout approach using a simple widget container.
        
        self.token_container = QWidget()
        self.token_container.setStyleSheet("background-color: #2b2b2b; border-radius: 6px;")
        
        # We'll use a Flow Layout implementation. 
        # Since PyQt6 doesn't have a built-in FlowLayout, we can simulate it 
        # or just use a horizontal one for now if strings aren't massive.
        # Let's stick to a scrollable horizontal area for step 1 to be safe.
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.token_container)
        scroll.setFixedHeight(100)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.token_layout = QHBoxLayout(self.token_container)
        self.token_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # self.token_layout.setContentsMargins(10, 10, 10, 10) # Optional margins
        
        self._render_tokens()
        layout.addWidget(scroll)
        
        # 2. Preview Area
        lbl_preview = QLabel("Resulting Entities:")
        lbl_preview.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_preview)
        
        self.preview_area = QWidget()
        # Use a vertical layout for the list of resulting chips/strings
        self.preview_layout = QVBoxLayout(self.preview_area)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setWidget(self.preview_area)
        layout.addWidget(preview_scroll)
        
        # 3. Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def _render_tokens(self):
        """Create widgets for each token."""
        # Clear existing
        while self.token_layout.count():
            child = self.token_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        for idx, token in enumerate(self.tokens):
            if token['is_delim']:
                display_text = token['text'].strip()
                # Qt uses '&' for shortcuts (mnemonics). We must escape it to '&&' to show it.
                display_text = display_text.replace("&", "&&")
                
                btn = QPushButton(display_text)
                btn.setCheckable(True)
                btn.setChecked(token['active'])
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                # Ensure width is at least enough for one character + padding
                btn.setMinimumWidth(30)
                
                # Store index to update state
                btn.setProperty("token_index", idx)
                
                # Styles
                self._update_delim_style(btn)
                
                btn.clicked.connect(lambda checked, b=btn: self._on_delim_toggled(b, checked))
                self.token_layout.addWidget(btn)
            else:
                lbl = QLabel(token['text'])
                lbl.setStyleSheet("font-size: 14px; padding: 4px; font-weight: 500;")
                self.token_layout.addWidget(lbl)
                
        self.token_layout.addStretch()

    def _add_custom_delim(self):
        """Add a user-defined word to the delimiter list and re-parse."""
        text = self.txt_custom_input.text().strip()
        if not text or text in self.custom_delims:
            return
            
        self.custom_delims.append(text)
        self.txt_custom_input.clear()
        
        # Re-parse (preserving states) and render!
        self._parse_tokens(self.original_text, preserve_states=True)
        self._render_tokens()
        self._update_preview()

    def _update_delim_style(self, btn: QPushButton):
        """Update style based on active state."""
        if btn.isChecked():
            # Active Split (Red/Scissor style)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #d32f2f;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #b71c1c; }
            """)
            btn.setToolTip("Click to JOIN")
        else:
            # Inactive (Join/Transparent style)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #424242;
                    color: #aaa;
                    border: 1px solid #666;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: #616161; }
            """)
            btn.setToolTip("Click to SPLIT")

    def _on_delim_toggled(self, btn: QPushButton, checked: bool):
        idx = btn.property("token_index")
        self.tokens[idx]['active'] = checked
        self._update_delim_style(btn)
        self._update_preview()

    def _update_preview(self):
        """Construct the resulting list based on active delimiters."""
        # Clear preview
        while self.preview_layout.count():
            child = self.preview_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        results = self.get_result()
            
        for name in results:
            # Create a row widget for each name with status
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 4, 0, 4)
            
            # Chip
            lbl = QLabel(name)
            lbl.setStyleSheet("""
                background-color: #007acc;
                color: white;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
            """)
            
            # Status
            status_text = ""
            status_color = "#888"
            
            if self.services:
                svc = self.services.contributor_service
                # Quick check if exists
                exists = svc.get_by_name(name)
                if exists:
                    status_text = "✓ Existing Artist"
                    status_color = "#4CAF50" # Green
                else:
                    status_text = "+ Will Create New"
                    status_color = "#FFC107" # Amber
            
            lbl_status = QLabel(status_text)
            lbl_status.setStyleSheet(f"color: {status_color}; font-size: 12px; margin-left: 10px;")
            
            row_layout.addWidget(lbl)
            row_layout.addWidget(lbl_status)
            row_layout.addStretch()
            
            self.preview_layout.addWidget(row)
            
        self.preview_layout.addStretch()

    def get_result(self) -> List[str]:
        """Return the final list of strings."""
        current_segment = ""
        results = []
        
        for token in self.tokens:
            if token['is_delim']:
                if token['active']:
                    if current_segment.strip():
                        results.append(current_segment.strip())
                    current_segment = ""
                else:
                    current_segment += token['text']
            else:
                current_segment += token['text']
                
        if current_segment.strip():
            results.append(current_segment.strip())
            
        return results
