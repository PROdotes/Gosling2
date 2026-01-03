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


class TagCollisionDialog(QDialog):
    """
    Human-friendly resolver for tag name conflicts.
    Offers: "Just This Song", "All Songs", or "Cancel".
    """
    def __init__(self, old_name, new_name, category, affected_count=0, has_selection=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"'{new_name}' Already Exists")
        self.setObjectName("TagCollisionDialog")
        self.setFixedWidth(380)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        layout.addStretch(1)
        
        lbl_header = QLabel(f"'{new_name}' already exists as a {category}.")
        lbl_header.setObjectName("CollisionMessage")
        lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_header.setWordWrap(True)
        layout.addWidget(lbl_header)
        
        lbl_question = QLabel("What would you like to do?")
        lbl_question.setObjectName("CollisionDescription")
        lbl_question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_question)
        
        layout.addStretch(1)
        
        # Options
        btns = QVBoxLayout()
        btns.setSpacing(8)
        
        # OPTION A: Just This Song/Selection (safest)
        if has_selection:
            self.btn_this = GlowButton("SWITCH JUST THIS SONG")
            self.btn_this.setObjectName("ActionPill")
            self.btn_this.setProperty("action_role", "primary")
            self.btn_this.setToolTip(f"Remove '{old_name}', add '{new_name}' to current selection only")
            self.btn_this.clicked.connect(lambda: self.done(3))  # Code 3 = Local swap
            self.btn_this.setDefault(True)
            btns.addWidget(self.btn_this)
        
        # OPTION B: All Songs (global merge)
        song_word = "song" if affected_count == 1 else "songs"
        self.btn_all = GlowButton(f"REPLACE EVERYWHERE ({affected_count} {song_word})")
        self.btn_all.setObjectName("ActionPill")
        self.btn_all.setProperty("action_role", "secondary")
        self.btn_all.setToolTip(f"Merge '{old_name}' into '{new_name}' globally - affects all songs")
        self.btn_all.clicked.connect(lambda: self.done(1))  # Code 1 = Global merge
        btns.addWidget(self.btn_all)
        
        # OPTION C: Cancel
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.setObjectName("ActionPill")
        self.btn_cancel.setProperty("action_role", "ghost")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        
        layout.addLayout(btns)
        layout.addStretch(1)



class TagPickerDialog(QDialog):
    """
    Smart Tag Picker with:
    - Category buttons for mouse users
    - Prefix syntax for keyboard users (e.g., m:chill, genre:rock)
    - Dynamic search across all categories
    - Create-on-the-fly for new tags
    """
    
    def __init__(self, tag_repo, default_category="Genre", target_tag=None, parent=None):
        super().__init__(parent)
        self.tag_repo = tag_repo
        self.default_category = default_category
        self.target_tag = target_tag
        self._selected_tag = None
        self._current_category_filter = None  # None = all categories
        
        if self.target_tag:
            self.setWindowTitle(f"Rename: {self.target_tag.tag_name}")
            self._current_category_filter = self.target_tag.category
        else:
            self.setWindowTitle("Add Tag")
            self._current_category_filter = self.default_category
            
        self.setFixedSize(420, 380)
        self.setObjectName("TagPickerDialog")
        
        self._init_ui()
        self._connect_signals()
        self._refresh_list()
        
        # Defer focus + select to after dialog is shown (timing fix)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._focus_and_select)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # --- Header ---
        title_text = "RENAME TAG" if self.target_tag else "ADD TAG"
        lbl = QLabel(title_text)
        lbl.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl)
        
        # --- Dynamic Category Buttons ---
        cat_layout = QHBoxLayout()
        cat_layout.setSpacing(4)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        
        # Cache category buttons for toggle logic
        self.category_buttons = {}
        
        # Emoji map for known categories (fallback to 📌 for custom)
        category_emoji = {
            "Genre": "🏷️",
            "Mood": "✨",
            "Era": "📅",
            "Status": "⏳",
            "Theme": "🎭",
            "Energy": "⚡",
        }
        
        # Query distinct categories from DB
        categories = self.tag_repo.get_distinct_categories()
        
        # Glow colors for tag categories
        category_colors = {
            "Genre": "#FFC66D",   # Amber
            "Mood": "#32A8FF",    # Blue
            "Era": "#9B59B6",     # Purple
            "Status": "#E53935",  # Red
            "Theme": "#4DFFB8",   # Teal
            "Energy": "#FF4DFF",  # Magenta
        }
        
        for cat in categories:
            emoji = category_emoji.get(cat, "📌")
            btn = GlowButton(f"{emoji} {cat}")
            btn.setCheckable(True)
            if cat == self._current_category_filter:
                btn.setChecked(True)
            # Set glow color for this category (fallback to amber)
            glow_color = category_colors.get(cat, "#FFC66D")
            btn.setGlowColor(glow_color)
            btn.clicked.connect(lambda c=cat: self._on_category_clicked(c))
            cat_layout.addWidget(btn)
            self.category_buttons[cat] = btn
        
        cat_layout.addStretch()
        layout.addLayout(cat_layout)
        
        # --- Search Box ---
        self.txt_search = GlowLineEdit()
        if self.target_tag:
            self.txt_search.setText(self.target_tag.tag_name)
            # Note: selectAll() handled in _focus_and_select (deferred for proper timing)
        else:
            self.txt_search.setPlaceholderText("Search or type prefix:tag (e.g., m:chill)")
        layout.addWidget(self.txt_search)
        
        # --- Status/Hint Label (hidden by default, shown when needed) ---
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("TagPickerHint")
        self.lbl_status.setStyleSheet("color: #888; font-size: 11px; padding: 0; margin: 0;")
        self.lbl_status.setFixedHeight(0)  # Hide until needed
        layout.addWidget(self.lbl_status)
        
        # --- Results List ---
        self.list_results = QListWidget()
        self.list_results.setObjectName("TagPickerList")
        self.list_results.setMinimumHeight(120)
        layout.addWidget(self.list_results, 1)  # Let list expand
        
        # --- Action Buttons (sized via QSS #TagPickerPill) ---
        btn_layout = QHBoxLayout()
        
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.setObjectName("TagPickerPill")
        self.btn_cancel.setProperty("action_role", "secondary")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_select = GlowButton("UPDATE" if self.target_tag else "Select")
        self.btn_select.setObjectName("TagPickerPill")
        self.btn_select.setProperty("action_role", "primary")
        self.btn_select.btn.setDefault(True)
        self.btn_select.clicked.connect(self._on_select)
        
        if self.target_tag:
            self.btn_remove = GlowButton("Remove")
            self.btn_remove.setObjectName("TagPickerPill")
            self.btn_remove.setProperty("action_role", "destructive")
            self.btn_remove.clicked.connect(lambda: self.done(2))
            btn_layout.addWidget(self.btn_remove)
            
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_select)
        
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(btn_layout)
        layout.setContentsMargins(16, 12, 16, 16)

    def _connect_signals(self):
        self.txt_search.textChanged.connect(self._on_search_changed)
        self.txt_search.returnPressed.connect(self._on_select)
        # Fix: Use itemActivated to catch Enter key on list items (as well as Double Click)
        self.list_results.itemActivated.connect(lambda item: self._on_select())
        self.list_results.currentRowChanged.connect(self._on_selection_changed)
        
        # Install event filter to capture arrow keys while typing
        self.txt_search.installEventFilter(self)

    def _focus_and_select(self):
        """Focus the search box and place cursor at end (for editing)."""
        self.txt_search.edit.setFocus()
        # Cursor at END, not select-all, so user can append/fix typos
        self.txt_search.edit.setCursorPosition(len(self.txt_search.text()))

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
        """Handle category button click - toggle the clicked one, uncheck others."""
        for cat_name, btn in self.category_buttons.items():
            btn.setChecked(cat_name == category)
        
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
            if not any(btn.isChecked() for btn in self.category_buttons.values()):
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
        for cat_name, btn in self.category_buttons.items():
            btn.setChecked(cat_name == category)

    def _refresh_list(self, query=""):
        """Refresh results list based on current filter and query."""
        self.list_results.clear()
        
        query = query.strip().lower()
        
        # Get tags from repository
        try:
            if query:
                # Global Search (Speed Mode)
                # Fetch all tags if query is present, regardless of category filter
                tags = self.tag_repo.get_all_tags()
                tags = [t for t in tags if query in t.tag_name.lower()]
                
                # Prioritize matches in current category filter (if active)
                if self._current_category_filter:
                    tags.sort(key=lambda t: 0 if t.category == self._current_category_filter else 1)
            else:
                # Lazy Mode: Filter by category
                if self._current_category_filter:
                    tags = self.tag_repo.get_all_by_category(self._current_category_filter)
                else:
                    tags = self.tag_repo.get_all_tags()
            
            # Add "Create new" option FIRST if query doesn't exactly match IN THIS CATEGORY
            # This prioritizes CREATION (Speed) over selection of partial matches
            if query:
                current_cat = self._current_category_filter or self.default_category
                # Check if exact match exists specifically in the target category
                exact_match_in_cat = any(
                    t.tag_name.lower() == query and t.category == current_cat 
                    for t in tags
                )
                
                if not exact_match_in_cat:
                    create_item = QListWidgetItem(f"➕ Create \"{query}\" in {current_cat}")
                    create_item.setData(Qt.ItemDataRole.UserRole, ("CREATE", query, current_cat))
                    self.list_results.addItem(create_item)
            
            # Add existing tags (Global matches)
            for tag in tags:
                icon = self._get_category_icon(tag.category)
                display = f"{icon} {tag.tag_name} ({tag.category})"
                
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, tag)
                self.list_results.addItem(item)
            
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
            "Era": "📅",
            "Status": "⏳",
            "Energy": "⚡",
        }
        return icons.get(category, "📦")

    def _on_selection_changed(self, row):
        """Update UI based on selection."""
        if row < 0: return
        item = self.list_results.item(row)
        data = item.data(Qt.ItemDataRole.UserRole)
        
        if isinstance(data, tuple) and data[0] == "CREATE":
            self.btn_select.setText("UPDATE" if self.target_tag else "Create")
        else:
            self.btn_select.setText("UPDATE" if self.target_tag else "Select")

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

    def get_new_name(self):
        """Return the text currently in the search box (for rename)."""
        return self.txt_search.text().strip()

    def get_target_category(self):
        """Return the currently selected category filter."""
        # Use active filter, or default, or fallback to target tag's original category
        return self._current_category_filter or self.default_category




