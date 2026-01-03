"""
TagPickerDialog - Smart Search & Create dialog for Tags (Genre/Mood/Custom).
Supports both mouse users (category buttons) and keyboard users (prefix syntax).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..widgets.glow_factory import GlowLineEdit, GlowButton


class TagPickerDialog(QDialog):
    """
    Smart Tag Picker with:
    - Category buttons for mouse users
    - Prefix syntax for keyboard users (e.g., m:chill, genre:rock)
    - Dynamic search across all categories
    - Create-on-the-fly for new tags
    """
    
    def __init__(self, tag_repo, default_category="Genre", parent=None):
        super().__init__(parent)
        self.tag_repo = tag_repo
        self.default_category = default_category
        self._selected_tag = None
        self._current_category_filter = None  # None = all categories
        
        self.setWindowTitle("Add Tag")
        self.setFixedSize(420, 380)
        self.setObjectName("TagPickerDialog")
        
        self._init_ui()
        self._connect_signals()
        self._refresh_list()
        self.txt_search.setFocus()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # --- Header ---
        lbl = QLabel("ADD TAG")
        lbl.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl)
        
        # --- Category Buttons ---
        cat_layout = QHBoxLayout()
        cat_layout.setSpacing(4)
        
        self.btn_genre = GlowButton("🏷️ Genre")
        self.btn_genre.setCheckable(True)
        self.btn_genre.setFixedHeight(32)
        self.btn_genre.clicked.connect(lambda: self._on_category_clicked("Genre"))
        
        self.btn_mood = GlowButton("✨ Mood")
        self.btn_mood.setCheckable(True)
        self.btn_mood.setFixedHeight(32)
        self.btn_mood.clicked.connect(lambda: self._on_category_clicked("Mood"))
        
        self.btn_other = GlowButton("📦 Other...")
        self.btn_other.setCheckable(True)
        self.btn_other.setFixedHeight(32)
        self.btn_other.clicked.connect(lambda: self._on_category_clicked(None))  # Show all
        
        cat_layout.addWidget(self.btn_genre)
        cat_layout.addWidget(self.btn_mood)
        cat_layout.addWidget(self.btn_other)
        cat_layout.addStretch()
        layout.addLayout(cat_layout)
        
        # --- Search Box ---
        self.txt_search = GlowLineEdit()
        self.txt_search.setPlaceholderText("Search or type prefix:tag (e.g., m:chill)")
        layout.addWidget(self.txt_search)
        
        # --- Status/Hint Label ---
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("TagPickerHint")
        self.lbl_status.setStyleSheet("color: #888; font-size: 11px; padding: 2px 0;")
        layout.addWidget(self.lbl_status)
        
        # --- Results List ---
        self.list_results = QListWidget()
        self.list_results.setObjectName("TagPickerList")
        self.list_results.setMinimumHeight(150)
        layout.addWidget(self.list_results)
        
        # --- Action Buttons ---
        layout.addStretch()
        btn_layout = QHBoxLayout()
        
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.setObjectName("ActionPill")
        self.btn_cancel.setProperty("action_role", "secondary")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_select = GlowButton("Select / Create")
        self.btn_select.setObjectName("ActionPill")
        self.btn_select.setProperty("action_role", "primary")
        self.btn_select.btn.setDefault(True)
        self.btn_select.clicked.connect(self._on_select)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_select)
        layout.addLayout(btn_layout)

    def _connect_signals(self):
        self.txt_search.textChanged.connect(self._on_search_changed)
        self.txt_search.returnPressed.connect(self._on_select)
        # Fix: Use itemActivated to catch Enter key on list items (as well as Double Click)
        self.list_results.itemActivated.connect(lambda item: self._on_select())
        self.list_results.currentRowChanged.connect(self._on_selection_changed)
        
        # Install event filter to capture arrow keys while typing
        self.txt_search.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Intercept arrow keys in search box to navigate list."""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        
        if obj == self.txt_search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            
            if key == Qt.Key.Key_Down:
                # Move selection down in list
                current = self.list_results.currentRow()
                if current < self.list_results.count() - 1:
                    self.list_results.setCurrentRow(current + 1)
                    # Explicitly select
                    it = self.list_results.item(current + 1)
                    if it: it.setSelected(True)
                return True  # Event handled
                
            elif key == Qt.Key.Key_Up:
                # Move selection up in list
                current = self.list_results.currentRow()
                if current > 0:
                    self.list_results.setCurrentRow(current - 1)
                return True  # Event handled
                
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                # Force selection of current item or fallback to logic
                self._on_select()
                return True
        
        return super().eventFilter(obj, event)

    def _on_category_clicked(self, category):
        """Handle category button click."""
        # Uncheck other buttons
        self.btn_genre.setChecked(category == "Genre")
        self.btn_mood.setChecked(category == "Mood")
        self.btn_other.setChecked(category is None)
        
        self._current_category_filter = category
        self._refresh_list()

    def _on_search_changed(self, text):
        """Handle search text changes - parse prefix and filter."""
        # Parse prefix if present
        prefix, tag_query = self._parse_prefix(text)
        
        if prefix:
            resolved = self._resolve_prefix(prefix)
            if resolved == "AMBIGUOUS":
                self._show_ambiguity_warning(prefix)
                self._current_category_filter = None  # Show all
            elif resolved:
                # Valid prefix - filter to that category
                self._current_category_filter = resolved
                self._update_category_buttons(resolved)
                self.lbl_status.setText(f"Category: {resolved}")
            else:
                # New category - will create on select
                self._current_category_filter = prefix.title()
                self._update_category_buttons(None)
                self.lbl_status.setText(f"New category: {prefix.title()}")
        else:
            # No prefix - use button selection or default
            if not any([self.btn_genre.isChecked(), self.btn_mood.isChecked(), self.btn_other.isChecked()]):
                # Nothing selected, default to showing all
                self._current_category_filter = None
            self.lbl_status.setText("")
        
        self._refresh_list(tag_query if prefix else text)

    def _parse_prefix(self, text):
        """Parse 'prefix:tag' format. Returns (prefix, tag) or (None, text)."""
        if ':' in text:
            parts = text.split(':', 1)
            if len(parts) == 2 and parts[0].strip():
                return parts[0].strip().lower(), parts[1].strip()
        return None, text

    def _resolve_prefix(self, prefix):
        """
        Resolve a prefix to a category name.
        Returns: category name, "AMBIGUOUS", or None (new category)
        """
        # Get all distinct categories
        categories = self._get_all_categories()
        
        # Find matches
        matches = [c for c in categories if c.lower().startswith(prefix.lower())]
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            return "AMBIGUOUS"
        else:
            return None  # New category

    def _get_all_categories(self):
        """Get all distinct tag categories from the database."""
        # Default categories always available
        categories = {"Genre", "Mood"}
        
        # Add any custom categories from DB
        try:
            # Query for distinct categories
            with self.tag_repo.get_connection() as conn:
                cursor = conn.execute("SELECT DISTINCT TagCategory FROM Tags WHERE TagCategory IS NOT NULL")
                for row in cursor.fetchall():
                    if row[0]:
                        categories.add(row[0])
        except:
            pass
        
        return sorted(categories)

    def _show_ambiguity_warning(self, prefix):
        """Show warning for ambiguous prefix."""
        categories = self._get_all_categories()
        matches = [c for c in categories if c.lower().startswith(prefix.lower())]
        self.lbl_status.setText(f"⚠️ '{prefix}:' is ambiguous: {', '.join(matches)}")
        self.lbl_status.setStyleSheet("color: #FFA500; font-size: 11px; padding: 2px 0;")

    def _update_category_buttons(self, category):
        """Update category button states based on resolved category."""
        self.btn_genre.setChecked(category == "Genre")
        self.btn_mood.setChecked(category == "Mood")
        self.btn_other.setChecked(category not in ["Genre", "Mood", None])

    def _refresh_list(self, query=""):
        """Refresh results list based on current filter and query."""
        self.list_results.clear()
        
        query = query.strip().lower()
        
        # Get tags from repository
        try:
            if self._current_category_filter:
                # Filter by category
                tags = self.tag_repo.get_all_by_category(self._current_category_filter)
            else:
                # Get all tags across categories
                tags = []
                for cat in self._get_all_categories():
                    tags.extend(self.tag_repo.get_all_by_category(cat))
            
            # Filter by query
            if query:
                tags = [t for t in tags if query in t.tag_name.lower()]
            
            # Add to list with category badges
            for tag in tags:
                icon = self._get_category_icon(tag.category)
                display = f"{icon} {tag.tag_name} ({tag.category})"
                
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, tag)
                self.list_results.addItem(item)
            
            # Add "Create new" option if query doesn't exactly match
            if query:
                exact_match = any(t.tag_name.lower() == query for t in tags)
                if not exact_match:
                    category = self._current_category_filter or self.default_category
                    create_item = QListWidgetItem(f"➕ Create \"{query}\" in {category}")
                    create_item.setData(Qt.ItemDataRole.UserRole, ("CREATE", query, category))
                    self.list_results.addItem(create_item)
            
            # Select first item
            if self.list_results.count() > 0:
                self.list_results.setCurrentRow(0)
                
        except Exception as e:
            self.lbl_status.setText(f"Error: {e}")

    def _get_category_icon(self, category):
        """Get icon for category."""
        icons = {
            "Genre": "🏷️",
            "Mood": "✨",
            "Instrument": "🎸",
            "Theme": "📚",
        }
        return icons.get(category, "📦")

    def _on_selection_changed(self, row):
        """Update button text based on selection."""
        if row < 0:
            return
        item = self.list_results.item(row)
        data = item.data(Qt.ItemDataRole.UserRole)
        
        if isinstance(data, tuple) and data[0] == "CREATE":
            self.btn_select.setText("Create")
        else:
            self.btn_select.setText("Select")

    def _on_select(self):
        """Handle selection/creation."""
        # Robustness: Check selectedItems first, then currentItem
        selected = self.list_results.selectedItems()
        item = selected[0] if selected else self.list_results.currentItem()
        
        # Fix: If no item explicitly highlighted but list has items, assume user wants the top/best match
        if not item and self.list_results.count() > 0:
            self.list_results.setCurrentRow(0)
            item = self.list_results.currentItem()
            
        if not item:
            # No selection - try to create from search text
            text = self.txt_search.text().strip()
            # If text is empty and list is empty, just close (Cancel)
            if not text:
                 self.reject()
                 return

            _, tag_query = self._parse_prefix(text)
            if tag_query:
                category = self._current_category_filter or self.default_category
                self._selected_tag, _ = self.tag_repo.get_or_create(tag_query, category)
                self.accept()
            return
        
        data = item.data(Qt.ItemDataRole.UserRole)
        
        if isinstance(data, tuple) and data[0] == "CREATE":
            # Create new tag
            _, name, category = data
            self._selected_tag, _ = self.tag_repo.get_or_create(name, category)
        else:
            # Select existing tag
            self._selected_tag = data
        
        self.accept()

    def get_selected(self):
        """Return the selected or created Tag object."""
        return self._selected_tag
