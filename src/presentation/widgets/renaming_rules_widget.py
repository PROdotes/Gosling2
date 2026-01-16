from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QPushButton, QDialog, 
    QLineEdit, QTextEdit, QMessageBox, QFrame,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QFont
from .glow_factory import GlowButton, GlowLineEdit

class RuleEditorDialog(QDialog):
    """
    Mini-dialog to add/edit a single renaming rule.
    Returns dict: { "match_genres": [...], "target_path": "..." }
    """
    def __init__(self, rule_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Renaming Rule")
        self.setMinimumWidth(500)
        self.rule_data = rule_data or {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Match Genres
        lbl_match = QLabel("Applies to Genres:")
        lbl_match.setObjectName("FieldLabel")
        layout.addWidget(lbl_match)
        
        self.txt_genres = GlowLineEdit()
        self.txt_genres.setPlaceholderText("e.g. Pop, Dance, Top 40 (comma separated)")
        current_genres = self.rule_data.get("match_genres", [])
        if isinstance(current_genres, list):
            self.txt_genres.setText(", ".join(current_genres))
        layout.addWidget(self.txt_genres)
        
        # Target Path
        lbl_target = QLabel("Rename files to:")
        lbl_target.setObjectName("FieldLabel")
        layout.addWidget(lbl_target)
        
        self.txt_target = GlowLineEdit()
        self.txt_target.setPlaceholderText("{Genre}/{Year}/{Artist} - {Title}")
        self.txt_target.setText(self.rule_data.get("target_path", ""))
        layout.addWidget(self.txt_target)

        # Help / Instructions
        help_frame = QFrame()
        help_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 4px; padding: 8px;")
        help_layout = QVBoxLayout(help_frame)
        help_layout.setContentsMargins(5,5,5,5)
        
        help_lbl = QLabel(
            "<b>Available Variables:</b><br>"
            "<span style='color: #aaa;'>{Artist}, {Title}, {Album}, {Year}, {Genre}, {BPM}, {Composers}</span><br><br>"
            "<b>Tips:</b><br>"
            "• Use <span style='font-family: monospace; background-color: #444; padding: 2px;'>/</span> to create folders (e.g. <span style='font-style: italic;'>{Genre}/{Artist}/{Title}</span>)<br>"
            "• File extensions (mp3/wav) are added automatically."
        )
        help_lbl.setStyleSheet("font-size: 11px; color: #ddd;")
        help_lbl.setWordWrap(True)
        help_lbl.setTextFormat(Qt.TextFormat.RichText)
        help_layout.addWidget(help_lbl)
        layout.addWidget(help_frame)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_cancel = GlowButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = GlowButton("Save Rule")
        btn_ok.clicked.connect(self.accept)
        
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def get_data(self):
        raw_genres = self.txt_genres.text().split(',')
        clean_genres = [g.strip() for g in raw_genres if g.strip()]
        
        return {
            "match_genres": clean_genres,
            "target_path": self.txt_target.text().strip()
        }

class RuleListItemWidget(QWidget):
    """
    Custom widget to render a rule item nicely in the list.
    Displays Genres (Condition) and Target Path (Action).
    """
    def __init__(self, rule_data, parent=None):
        super().__init__(parent)
        self._setup_ui(rule_data)
        
    def _setup_ui(self, data):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # Top Row: Genres
        genres_str = ", ".join(data.get("match_genres", []))
            
        lbl_genres = QLabel(f"IF GENRE IS:  <b>{genres_str}</b>")
        lbl_genres.setStyleSheet("font-size: 12px; color: #ddd;")
        lbl_genres.setTextFormat(Qt.TextFormat.RichText)
        lbl_genres.setWordWrap(True)
        
        # Bottom Row: Target (styled like code)
        target = data.get("target_path", "")
        lbl_target = QLabel(f"→  {target}")
        lbl_target.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; color: #8EC07C; margin-left: 10px;")
        
        layout.addWidget(lbl_genres)
        layout.addWidget(lbl_target)

class RenamingRulesWidget(QWidget):
    """
    Widget for managing the list of Renaming Rules.
    Talks to RenamingService API.
    """
    
    def __init__(self, renaming_service, parent=None):
        super().__init__(parent)
        self.renaming_service = renaming_service
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Header / Explanation
        info_frame = QFrame()
        info_frame.setStyleSheet("border-left: 2px solid #8EC07C; padding-left: 10px;") # Green accent line
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(0,0,0,0)
        
        info = QLabel(
            "Sort your library automatically. The system processes rules from top to bottom; "
            "the first rule that matches the song's genre will be used."
        )
        info.setStyleSheet("color: #bbbbbb; font-size: 12px;")
        info.setWordWrap(True)
        info_layout.addWidget(info)
        
        layout.addWidget(info_frame)
        
        # Default Rule Row (Styled Box)
        def_frame = QFrame()
        def_frame.setObjectName("PanelWidget") # Use generic panel style if avail, else fallback
        def_frame.setStyleSheet("""
            QFrame {
                background-color: #242424; 
                border: 1px solid #333; 
                border-radius: 6px;
            }
        """)
        def_layout = QVBoxLayout(def_frame)
        def_layout.setContentsMargins(15, 15, 15, 15)
        def_layout.setSpacing(8)
        
        lbl_def = QLabel("DEFAULT PATTERN (FALLBACK)")
        lbl_def.setStyleSheet("font-weight: bold; font-size: 11px; color: #888; letter-spacing: 1px;")
        
        self.txt_default = GlowLineEdit()
        self.txt_default.setPlaceholderText("{Artist} - {Title}")
        self.txt_default.setStyleSheet("font-family: Consolas, monospace; font-size: 13px;") 
        
        def_layout.addWidget(lbl_def)
        def_layout.addWidget(self.txt_default)
        
        layout.addWidget(def_frame)
        
        # Rules List Section
        lbl_rules = QLabel("GENRE RULES")
        lbl_rules.setStyleSheet("font-weight: bold; font-size: 11px; color: #888; letter-spacing: 1px; margin-top: 10px;")
        layout.addWidget(lbl_rules)
        
        # The List
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("FilterTree")
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                alternate-background-color: #242424;
                border: 1px solid #333;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #2a2a2a;
                color: #dddddd;
            }
            QListWidget::item:selected {
                background-color: #3a3a3a;
                border: 1px solid #555;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
        """)
        self.list_widget.doubleClicked.connect(self._edit_current_item)
        layout.addWidget(self.list_widget)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        
        self.btn_add = GlowButton("Add Rule")
        self.btn_add.clicked.connect(self._add_rule)
        
        self.btn_edit = GlowButton("Edit")
        self.btn_edit.clicked.connect(self._edit_current_item)
        
        self.btn_remove = GlowButton("Remove")
        self.btn_remove.setStyleSheet("background-color: #442222; color: #ffaaaa;") # Subtle warning color
        self.btn_remove.clicked.connect(self._remove_rule)
        
        self.btn_up = GlowButton("▲")
        self.btn_up.setFixedWidth(40)
        self.btn_up.setToolTip("Move Rule Up (Higher Priority)")
        self.btn_up.clicked.connect(self._move_up)
        
        self.btn_down = GlowButton("▼")
        self.btn_down.setFixedWidth(40)
        self.btn_down.setToolTip("Move Rule Down (Lower Priority)")
        self.btn_down.clicked.connect(self._move_down)
        
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_remove)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_up)
        toolbar.addWidget(self.btn_down)
        
        layout.addLayout(toolbar)

    def _load_data(self):
        rules = self.renaming_service.get_rules()
        self.txt_default.setText(rules.get("default_rule", ""))
        
        self.list_widget.clear()
        for rule in rules.get("routing_rules", []):
            self._add_list_item(rule)

    def _add_list_item(self, rule_data):
        item = QListWidgetItem(self.list_widget)
        
        # Dynamic height calculation
        genres = rule_data.get("match_genres", [])
        text_len = sum(len(g) for g in genres) + (len(genres) * 2) # approx length
        # Base height 60, add 18px for every ~90 chars over the first 90
        # This is strictly visual, the actual widget will word wrap, but QListWidget needs to know space to reserve
        height = 60
        if text_len > 90:
             lines = (text_len // 90)
             height += (lines * 14)

        item.setSizeHint(QSize(0, height)) 
        item.setData(Qt.ItemDataRole.UserRole, rule_data)
        
        widget = RuleListItemWidget(rule_data)
        self.list_widget.setItemWidget(item, widget)

    def _add_rule(self):
        dlg = RuleEditorDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if data["match_genres"] and data["target_path"]:
                self._load_with_new_rule(data)

    def _load_with_new_rule(self, new_data):
        # We need to save the current state first properly or just append to list
        # Simply appending to UI:
        self._add_list_item(new_data)
        self.list_widget.scrollToBottom()

    def _edit_current_item(self):
        item = self.list_widget.currentItem()
        if not item: return
        
        old_data = item.data(Qt.ItemDataRole.UserRole)
        dlg = RuleEditorDialog(old_data, self)
        if dlg.exec():
            new_data = dlg.get_data()
            if new_data["match_genres"] and new_data["target_path"]:
                # Update Data
                item.setData(Qt.ItemDataRole.UserRole, new_data)
                
                # Recalculate height
                genres = new_data.get("match_genres", [])
                text_len = sum(len(g) for g in genres) + (len(genres) * 2)
                height = 60
                if text_len > 90:
                    lines = (text_len // 90)
                    height += (lines * 14)
                item.setSizeHint(QSize(0, height))
                
                # Update Visuals
                widget = RuleListItemWidget(new_data)
                self.list_widget.setItemWidget(item, widget)

    def _remove_rule(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            msg = "Are you sure you want to remove this rule?"
            if QMessageBox.question(self, "Confirm Remove", msg) == QMessageBox.StandardButton.Yes:
                self.list_widget.takeItem(row)

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            # Recreate because takeItem detaches widget
            data = item.data(Qt.ItemDataRole.UserRole)
            
            # Insert new
            self.list_widget.insertItem(row - 1, item)
            
            # Restore widget and SizeHint
            # Since item still has its SizeHint from before, we just need to re-set the widget
            # But takeItem might strip widget, preserving item props? Yes.
            self.list_widget.setItemWidget(item, RuleListItemWidget(data))
            self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            data = item.data(Qt.ItemDataRole.UserRole)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setItemWidget(item, RuleListItemWidget(data))
            self.list_widget.setCurrentRow(row + 1)

    def save_changes(self):
        """Called by parent dialog on Save."""
        rules_list = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            rules_list.append(item.data(Qt.ItemDataRole.UserRole))
            
        full_config = {
            "routing_rules": rules_list,
            "default_rule": self.txt_default.text().strip()
        }
        
        self.renaming_service.save_rules(full_config)
