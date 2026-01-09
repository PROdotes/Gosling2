from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QPushButton, QDialog, 
    QLineEdit, QTextEdit, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor
from .glow_factory import GlowButton, GlowLineEdit

class RuleEditorDialog(QDialog):
    """
    Mini-dialog to add/edit a single renaming rule.
    Returns dict: { "match_genres": [...], "target_path": "..." }
    """
    def __init__(self, rule_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Rule")
        self.setMinimumWidth(400)
        self.rule_data = rule_data or {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Match Genres
        lbl_match = QLabel("MATCH GENRES (Comma Separated)")
        lbl_match.setObjectName("FieldLabel")
        layout.addWidget(lbl_match)
        
        self.txt_genres = GlowLineEdit()
        self.txt_genres.setPlaceholderText("Pop, Dance, Top 40")
        current_genres = self.rule_data.get("match_genres", [])
        if isinstance(current_genres, list):
            self.txt_genres.setText(", ".join(current_genres))
        layout.addWidget(self.txt_genres)
        
        # Target Path
        lbl_target = QLabel("TARGET PATTERN")
        lbl_target.setObjectName("FieldLabel")
        layout.addWidget(lbl_target)
        
        self.txt_target = GlowLineEdit()
        self.txt_target.setPlaceholderText("{Genre}/{Year}/{Filename}")
        self.txt_target.setText(self.rule_data.get("target_path", ""))
        layout.addWidget(self.txt_target)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_cancel = GlowButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = GlowButton("OK")
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
        
        # Header / Explanation
        info = QLabel("Rules are processed in order. The first matching rule wins.")
        info.setObjectName("InfoLabel") 
        info.setStyleSheet("color: #888888; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Default Rule Row
        def_layout = QHBoxLayout()
        lbl_def = QLabel("Default Rule:")
        lbl_def.setFixedWidth(80)
        self.txt_default = GlowLineEdit()
        self.txt_default.setPlaceholderText("{Genre}/{Year}/{Filename}")
        def_layout.addWidget(lbl_def)
        def_layout.addWidget(self.txt_default)
        layout.addLayout(def_layout)
        
        # The List
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("FilterTree")  # Reuse existing dark list style
        self.list_widget.setAlternatingRowColors(False)  # FilterTree style doesn't use alternating
        self.list_widget.doubleClicked.connect(self._edit_current_item)
        layout.addWidget(self.list_widget)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.btn_add = GlowButton("Add Rule")
        self.btn_add.clicked.connect(self._add_rule)
        
        self.btn_edit = GlowButton("Edit")
        self.btn_edit.clicked.connect(self._edit_current_item)
        
        self.btn_remove = GlowButton("Remove")
        self.btn_remove.clicked.connect(self._remove_rule)
        
        self.btn_up = GlowButton("▲")
        self.btn_up.setFixedWidth(30)
        self.btn_up.clicked.connect(self._move_up)
        
        self.btn_down = GlowButton("▼")
        self.btn_down.setFixedWidth(30)
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
        genres = ", ".join(rule_data.get("match_genres", []))
        target = rule_data.get("target_path", "")
        text = f"IF Genre IN [{genres}] → {target}"
        
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, rule_data)
        self.list_widget.addItem(item)

    def _add_rule(self):
        dlg = RuleEditorDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            if data["match_genres"] and data["target_path"]:
                self._add_list_item(data)

    def _edit_current_item(self):
        item = self.list_widget.currentItem()
        if not item: return
        
        old_data = item.data(Qt.ItemDataRole.UserRole)
        dlg = RuleEditorDialog(old_data, self)
        if dlg.exec():
            new_data = dlg.get_data()
            if new_data["match_genres"] and new_data["target_path"]:
                item.setData(Qt.ItemDataRole.UserRole, new_data)
                genres = ", ".join(new_data.get("match_genres", []))
                item.setText(f"IF Genre IN [{genres}] → {new_data['target_path']}")

    def _remove_rule(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
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
