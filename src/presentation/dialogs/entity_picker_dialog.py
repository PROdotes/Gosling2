"""
EntityPickerDialog 🔍
Universal search/create/rename dialog for entities.

Follows the TagPickerDialog UX pattern but is configurable for:
- Tags (with extensible categories)
- Artists (with fixed types: Person/Group/Alias)
- Publishers (no types)

Usage:
    from src.presentation.dialogs.entity_picker_dialog import EntityPickerDialog
    from src.core.picker_config import get_tag_picker_config
    
    # Tags
    dialog = EntityPickerDialog(
        service_provider=self.services,
        config=get_tag_picker_config(),
        target_entity=existing_tag,  # Edit mode, or None for Add mode
        parent=self
    )
"""

from typing import Any, Optional, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QWheelEvent

from ..widgets.glow_factory import GlowLineEdit, GlowButton
from src.core.picker_config import PickerConfig


class HorizontalScrollArea(QScrollArea):
    """QScrollArea that converts vertical mouse wheel to horizontal scrolling."""
    
    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        delta = int(delta / 2)
        h_bar = self.horizontalScrollBar()
        h_bar.setValue(h_bar.value() - delta)
        event.accept()


class EntityPickerDialog(QDialog):
    """
    Universal entity picker with search, create, and rename support.
    
    Configurable via PickerConfig for different entity types.
    """
    
    def __init__(
        self,
        service_provider: Any,
        config: PickerConfig,
        target_entity: Any = None,
        exclude_ids: set = None,
        parent: QWidget = None
    ):
        """
        Args:
            service_provider: Object with service attributes
            config: PickerConfig defining behavior for this entity type
            target_entity: Existing entity for edit mode, None for add mode
            exclude_ids: IDs to exclude from the list
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.services = service_provider
        self.config = config
        self.target_entity = target_entity
        self.exclude_ids = exclude_ids or set()
        
        self._selected_entity = None
        self._rename_info = None
        self._current_type_filter = None
        
        # Get the service
        self.service = getattr(service_provider, config.service_attr, None)
        if not self.service:
            raise ValueError(f"Service not found: {config.service_attr}")
        
        # Set initial state
        if self.target_entity:
            self.setWindowTitle(config.title_edit)
            self._current_type_filter = config.type_fn(target_entity)
        else:
            self.setWindowTitle(config.title_add)
            # If only one type button is configured, pre-filter to that type
            # This handles filtered pickers like "Add Alias" which restrict to same type
            if len(config.type_buttons) == 1:
                self._current_type_filter = config.type_buttons[0]
            elif config.default_type and config.default_type in config.type_buttons:
                self._current_type_filter = config.default_type
            else:
                self._current_type_filter = None  # Default to ALL
        
        self.setFixedSize(420, 420)
        self.setObjectName("EntityPickerDialog")

        # Dynamic type buttons (for Tags)
        if not self.config.type_buttons and hasattr(self.service, "get_distinct_categories"):
            self.config.type_buttons = self.service.get_distinct_categories()
            
            # Fetch icons and colors from ID3Registry
            from src.core.registries.id3_registry import ID3Registry
            for cat in self.config.type_buttons:
                self.config.type_icons[cat] = ID3Registry.get_category_icon(cat, default="📌")
                self.config.type_colors[cat] = ID3Registry.get_category_color(cat, default="#FFC66D")
        
        self._init_ui()
        self._connect_signals()
        self._refresh_list()
        
        # Defer focus
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._focus_search)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # --- Header ---
        title_text = self.config.title_edit if self.target_entity else self.config.title_add
        lbl = QLabel(title_text.upper())
        lbl.setObjectName("DialogFieldLabel")
        layout.addWidget(lbl)
        
        # --- Type Buttons (if configured) ---
        if self.config.type_buttons:
            self._init_type_buttons(layout)
        
        # --- Search Box ---
        self.txt_search = GlowLineEdit()
        if self.target_entity:
            self.txt_search.setText(self.config.display_fn(self.target_entity))
        else:
            self.txt_search.setPlaceholderText(self.config.search_placeholder)
        layout.addWidget(self.txt_search)
        
        # --- Status Label ---
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("EntityPickerHint")
        self.lbl_status.setStyleSheet("color: #888; font-size: 11px; padding: 0; margin: 0;")
        self.lbl_status.setFixedHeight(0)
        layout.addWidget(self.lbl_status)
        
        # --- Results List ---
        self.list_results = QListWidget()
        self.list_results.setObjectName("EntityPickerList")
        self.list_results.setMinimumHeight(120)
        layout.addWidget(self.list_results, 1)
        
        # --- Action Buttons ---
        btn_layout = QHBoxLayout()
        
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.setObjectName("TagPickerPill")
        self.btn_cancel.setProperty("action_role", "secondary")
        self.btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_select = GlowButton("UPDATE" if self.target_entity else "Select")
        self.btn_select.setObjectName("TagPickerPill")
        self.btn_select.setProperty("action_role", "primary")
        self.btn_select.btn.setDefault(True)
        self.btn_select.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_select.clicked.connect(self._on_select)
        
        if self.target_entity and self.config.allow_remove:
            self.btn_remove = GlowButton("Remove")
            self.btn_remove.setObjectName("TagPickerPill")
            self.btn_remove.setProperty("action_role", "destructive")
            self.btn_remove.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.btn_remove.clicked.connect(lambda: self.done(2))
            btn_layout.addWidget(self.btn_remove)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_select)
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(btn_layout)
        layout.setContentsMargins(16, 12, 16, 16)
    
    def _init_type_buttons(self, layout: QVBoxLayout):
        """Create type/category button row."""
        type_scroll = HorizontalScrollArea()
        type_scroll.setObjectName("TagCategoryScroll")
        type_scroll.setWidgetResizable(True)
        type_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        type_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        type_scroll.setFrameShape(QFrame.Shape.NoFrame)
        type_scroll.setFixedHeight(50)
        
        container = QWidget()
        container.setObjectName("TagCategoryContainer")
        type_layout = QHBoxLayout(container)
        type_layout.setSpacing(4)
        type_layout.setContentsMargins(0, 0, 0, 0)
        
        self.type_buttons = {}
        
        # --- Add "ALL" Button (only if multiple types) ---
        if len(self.config.type_buttons) > 1:
            btn_all = GlowButton("★ ALL")
            btn_all.setCheckable(True)
            btn_all.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn_all.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn_all.setGlowColor("#FFFFFF")
            if self._current_type_filter is None:
                btn_all.setChecked(True)
            btn_all.clicked.connect(lambda: self._on_type_clicked(None))
            type_layout.addWidget(btn_all)
            self.type_buttons[None] = btn_all
        
        for type_name in self.config.type_buttons:
            icon = self.config.type_icons.get(type_name, "📦")
            color = self.config.type_colors.get(type_name, "#FFC66D")
            
            btn = GlowButton(f"{icon} {type_name}")
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Arrow keys control list
            
            if type_name == self._current_type_filter:
                btn.setChecked(True)
            
            btn.setGlowColor(color)
            btn.clicked.connect(lambda t=type_name: self._on_type_clicked(t))
            
            type_layout.addWidget(btn)
            self.type_buttons[type_name] = btn
        
        type_layout.addStretch()
        type_scroll.setWidget(container)
        layout.addWidget(type_scroll)
    
    def _connect_signals(self):
        self.txt_search.textChanged.connect(self._on_search_changed)
        self.txt_search.returnPressed.connect(self._on_select)
        self.list_results.itemActivated.connect(lambda: self._on_select())
        self.list_results.currentRowChanged.connect(self._on_selection_changed)
        
        # Install filter on the actual interactive parts
        self.txt_search.edit.installEventFilter(self)
        self.list_results.installEventFilter(self)
    
    def _focus_search(self):
        self.txt_search.edit.setFocus()
        self.txt_search.edit.setCursorPosition(len(self.txt_search.text()))
    
    def eventFilter(self, obj, event):
        """Keyboard shortcuts for list navigation and category switching."""
        from PyQt6.QtCore import QEvent
        
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            is_alt = bool(modifiers & Qt.KeyboardModifier.AltModifier)
            
            # --- GLOBAL SHORTCUTS (List or Search) ---
            if key == Qt.Key.Key_Left and is_alt:
                self._cycle_category(-1)
                return True
            elif key == Qt.Key.Key_Right and is_alt:
                self._cycle_category(1)
                return True
            
            # --- SEARCH BOX SPECIFIC ---
            if obj == self.txt_search.edit:
                if key == Qt.Key.Key_Down:
                    current = self.list_results.currentRow()
                    if current < self.list_results.count() - 1:
                        self.list_results.setCurrentRow(current + 1)
                    return True
                
                elif key == Qt.Key.Key_Up:
                    current = self.list_results.currentRow()
                    if current > 0:
                        self.list_results.setCurrentRow(current - 1)
                    return True
                
                elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._on_select()
                    return True
            
            # --- LIST SPECIFIC ---
            elif obj == self.list_results:
                if key == Qt.Key.Key_Escape:
                    self.reject()
                    return True
                # Standard items (Return/Enter) are handled by itemActivated
        
        return super().eventFilter(obj, event)

    def _cycle_category(self, delta: int):
        """Cycle through available category buttons."""
        if not self.type_buttons:
            return
            
        # 1. Get ordered list of keys (None first IF it exists in our map, then others)
        keys = []
        if None in self.type_buttons:
            keys.append(None)
        keys.extend(self.config.type_buttons)
        
        # 2. Find current index
        try:
            current_idx = keys.index(self._current_type_filter)
        except ValueError:
            current_idx = 0
            
        # 3. Calculate next index (with wrapping)
        next_idx = (current_idx + delta) % len(keys)
        next_type = keys[next_idx]
        
        # 4. Trigger click
        self._on_type_clicked(next_type)
    
    def _on_type_clicked(self, type_name: str):
        """Handle type button click."""
        for t, btn in self.type_buttons.items():
            btn.setChecked(t == type_name)
        
        self._current_type_filter = type_name
        self._refresh_list()
        self.txt_search.edit.setFocus()
    
    def _on_search_changed(self, text: str):
        """Handle search text changes."""
        # Parse prefix if present
        prefix, query = self._parse_prefix(text)
        
        if prefix:
            resolved = self._resolve_prefix(prefix)
            if resolved == "AMBIGUOUS":
                self._show_status(f"⚠️ '{prefix}:' is ambiguous")
            elif resolved:
                self._current_type_filter = resolved
                self._update_type_buttons(resolved)
            elif not self.config.allow_new_types:
                self._show_status(f"❌ Unknown type: '{prefix}'")
            else:
                self._current_type_filter = prefix.title()
                self._update_type_buttons(None)
        else:
            self._show_status("")
        
        self._refresh_list(query if prefix else text)
    
    def _parse_prefix(self, text: str):
        """Parse 'prefix:value' format."""
        if ':' in text:
            parts = text.split(':', 1)
            if len(parts) == 2 and parts[0].strip():
                return parts[0].strip().lower(), parts[1].strip()
        return None, text
    
    def _resolve_prefix(self, prefix: str):
        """Resolve prefix to type name."""
        # Direct match in prefix map
        if prefix in self.config.prefix_map:
            return self.config.prefix_map[prefix]
        
        # Partial match in type buttons
        matches = [t for t in self.config.type_buttons if t.lower().startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            return "AMBIGUOUS"
        
        return None if self.config.allow_new_types else "UNKNOWN"
    
    def _update_type_buttons(self, type_name: Optional[str]):
        """Update type button checked states."""
        for t, btn in self.type_buttons.items():
            btn.setChecked(t == type_name)
    
    def _show_status(self, text: str):
        """Update status label."""
        self.lbl_status.setText(text)
        self.lbl_status.setFixedHeight(20 if text else 0)
    
    def _refresh_list(self, query: str = ""):
        """Refresh the results list."""
        self.list_results.clear()
        query = query.strip().lower()
        
        try:
            # Get entities
            entities = self._get_entities(query)
            
            # Filter by exclusions
            entities = [e for e in entities if self.config.id_fn(e) not in self.exclude_ids]
            
            # --- EDIT MODE: Add Rename option ---
            if self.target_entity:
                self._maybe_add_rename_option(query)
            
            # --- Add Create option ---
            if self.config.allow_create:
                self._maybe_add_create_option(query, entities)
            
            # --- Add existing entities ---
            for entity in entities:
                self._add_entity_item(entity)
            
            # Select first item
            if self.list_results.count() > 0:
                self.list_results.setCurrentRow(0)
                
        except Exception as e:
            self._show_status(f"Error: {e}")
    
    def _get_entities(self, query: str) -> List[Any]:
        """Get entities based on current filter."""
        if query:
            # 1. Search (Universal/Specialized)
            if hasattr(self.service, self.config.search_fn):
                search_method = getattr(self.service, self.config.search_fn)
                entities = search_method(query)
                
                # Check if we should filter the search results by type
                if self._current_type_filter:
                    # T-Fix: Case-insensitive comparison (DB='group' vs UI='Group')
                    entities = [e for e in entities if self.config.type_fn(e).lower() == self._current_type_filter.lower()]
                
                # Double-check match for safety, but be inclusive (check aliases for artists)
                def matches(e):
                    display_name = self.config.display_fn(e).lower()
                    if query in display_name:
                        return True
                    # Specialized check for contributors with matched_alias
                    if hasattr(e, 'matched_alias') and e.matched_alias and query in e.matched_alias.lower():
                        return True
                    return False
                    
                entities = [e for e in entities if matches(e)]
            else:
                entities = []
        else:
            # 2. Browsing (By Category or All)
            if self._current_type_filter and hasattr(self.service, self.config.get_by_type_fn):
                method = getattr(self.service, self.config.get_by_type_fn)
                entities = method(self._current_type_filter)
            elif hasattr(self.service, 'get_all'):
                entities = self.service.get_all()
            else:
                entities = []
        
        # FILTER: Respect allowed types from config.type_buttons
        # This ensures "ALL" only shows allowed types when picker is restricted
        # Use case-insensitive comparison (type_fn may return 'person', buttons have 'Person')
        if self.config.type_buttons:
            allowed_types_lower = {t.lower() for t in self.config.type_buttons}
            entities = [e for e in entities if self.config.type_fn(e).lower() in allowed_types_lower]
        
        return entities
    
    def _maybe_add_rename_option(self, query: str):
        """Add Rename option if name or type changed."""
        original_name = self.config.display_fn(self.target_entity).lower()
        original_type = self.config.type_fn(self.target_entity)
        
        current_name = self.txt_search.text().strip()
        current_name_lower = current_name.lower() if current_name else ""
        current_type = self._current_type_filter or original_type
        
        name_changed = current_name_lower and current_name_lower != original_name
        type_changed = current_type != original_type
        
        if name_changed or type_changed:
            display_name = current_name if current_name else self.config.display_fn(self.target_entity)
            
            if name_changed and type_changed:
                label = f"✏️ Rename & Move to \"{display_name}\" in {current_type}"
            elif type_changed:
                label = f"📦 Move to {current_type}" # Keep name, just move
            else:
                label = f"✏️ Rename to \"{display_name}\""
            
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, ("RENAME", display_name, current_type))
            self.list_results.addItem(item)
    
    def _maybe_add_create_option(self, query: str, entities: List[Any]):
        """Add Create option if no exact match."""
        current_name = self.txt_search.text().strip()
        if not current_name:
            return
        
        # Determine types to offer
        # If a category is selected, only offer creation in that category.
        # If ALL is selected, offer all available categories.
        if self._current_type_filter:
            types_to_offer = [self._current_type_filter]
        else:
            types_to_offer = self.config.type_buttons or [self.config.default_type]


            
        for t in types_to_offer:
            # if not t: continue  <-- REMOVED: support empty type strings (Publishers)

            
            # Check for exact match in this specific type
            # (Allows creating 'Queen' as Person even if 'Queen' Group exists)
            exact_match = any(
                self.config.display_fn(e).lower() == current_name.lower() 
                and self.config.type_fn(e).lower() == t.lower()
                for e in entities
            )
            
            if not exact_match:
                type_suffix = f" as {t}" if len(types_to_offer) > 1 or t else ""
                item = QListWidgetItem(f"➕ Create \"{current_name}\"{type_suffix}")
                item.setData(Qt.ItemDataRole.UserRole, ("CREATE", current_name, t))
                self.list_results.addItem(item)

        # T-82/92: Spotify CamelCase Splitter Shortcut (Move outside loop to de-duplicate)
        service = getattr(self.services, 'spotify_parsing_service', None)
        if service and service.is_camel_case(current_name):
            # Use the current filter type, or fallback to the config default (usually 'Person')
            target_t = self._current_type_filter or self.config.default_type
            spotify_item = QListWidgetItem(f"🎵 Create from Spotify (Split \"{current_name}\")")
            spotify_item.setData(Qt.ItemDataRole.UserRole, ("CREATE_SPOTIFY", current_name, target_t))
            self.list_results.addItem(spotify_item)
    
    def _add_entity_item(self, entity: Any):
        """Add an entity to the list."""
        icon = self.config.icon_fn(entity)
        name = self.config.display_fn(entity)
        type_name = self.config.type_fn(entity)
        
        display = f"{icon} {name}"
        if type_name:
            display += f" ({type_name})"
        
        item = QListWidgetItem(display)
        item.setData(Qt.ItemDataRole.UserRole, entity)
        self.list_results.addItem(item)
    
    def _on_selection_changed(self, row: int):
        """Update button text based on selection."""
        if row < 0:
            return
        
        item = self.list_results.item(row)
        data = item.data(Qt.ItemDataRole.UserRole)
        
        if isinstance(data, tuple):
            action = data[0]
            if action == "RENAME":
                if "Move to" in item.text(): # Matches "Move to" or "Rename & Move to"
                    self.btn_select.setText("MOVE")
                else:
                    self.btn_select.setText("RENAME")
            elif action == "CREATE":
                self.btn_select.setText("UPDATE" if self.target_entity else "Create")
        else:
            self.btn_select.setText("UPDATE" if self.target_entity else "Select")
    
    def _on_select(self):
        """Handle selection."""
        selected = self.list_results.selectedItems()
        item = selected[0] if selected else self.list_results.currentItem()
        
        if not item and self.list_results.count() > 0:
            self.list_results.setCurrentRow(0)
            item = self.list_results.currentItem()
        
        if not item:
            self.reject()
            return
        
        data = item.data(Qt.ItemDataRole.UserRole)
        
        if isinstance(data, tuple):
            action = data[0]
            
            if action == "RENAME":
                _, new_name, new_type = data
                self._rename_info = (new_name, new_type)
                self._selected_entity = self.target_entity
                self.accept()
                
            elif action in ("CREATE", "CREATE_SPOTIFY"):
                _, name, type_name = data
                service = getattr(self.services, 'spotify_parsing_service', None)
                
                # Split logic for Spotify CamelCase
                if action == "CREATE_SPOTIFY" and service:
                    parts = service.split_camel_case(name)
                    if parts and hasattr(self.service, self.config.get_or_create_fn):
                        create_method = getattr(self.service, self.config.get_or_create_fn)
                        results = [create_method(p, type_name)[0] for p in parts]
                        self._selected_entity = results
                        self.accept()
                        return

                # Default Create
                if hasattr(self.service, self.config.get_or_create_fn):
                    create_method = getattr(self.service, self.config.get_or_create_fn)
                    self._selected_entity, _ = create_method(name, type_name)
                self.accept()
        else:
            self._selected_entity = data
            self.accept()
    
    # === Public API ===
    
    def get_selected(self) -> Any:
        """Return the selected entity."""
        return self._selected_entity
    
    def is_rename_requested(self) -> bool:
        """Check if user selected Rename action."""
        return self._rename_info is not None
    
    def get_rename_info(self):
        """Get rename details: (new_name, new_type)."""
        return self._rename_info
    
    def get_new_name(self) -> str:
        """Return the text in the search box."""
        return self.txt_search.text().strip()
    
    def get_target_type(self) -> str:
        """Return the currently selected type filter."""
        return self._current_type_filter or self.config.default_type
