"""
EntityListWidget 🎛️
Unified chip/list widget that knows how to handle its own entities.

Replaces scattered ChipTrayWidget + handler boilerplate across dialogs.
Works in two modes:
- CLOUD: Horizontal flow of chips (for Tags, Artists, Publishers in SidePanel)
- STACK: Vertical list with QListWidget (for Aliases, Members, Subsidiaries)

Usage:
    from src.presentation.widgets.entity_list_widget import EntityListWidget, LayoutMode
    from src.core.entity_registry import EntityType
    from src.core.context_adapters import ArtistAliasAdapter
    
    # In dialog:
    self.tray_aliases = EntityListWidget(
        service_provider=self.services,
        entity_type=EntityType.ALIAS,
        layout_mode=LayoutMode.STACK,
        context_adapter=ArtistAliasAdapter(self.artist, self.service, self._refresh_data)
    )
"""

from enum import Enum
from typing import Any, Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QMenu, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from .chip_tray_widget import ChipTrayWidget
from .glow_factory import GlowButton

from src.core.entity_registry import (
    EntityType, 
    get_entity_config,
    get_entity_icon,
    get_entity_display
)
from src.core.entity_click_router import EntityClickRouter, ClickAction
from src.core.context_adapters import ContextAdapter


class LayoutMode(Enum):
    """Display mode for the entity list."""
    CLOUD = "cloud"  # Horizontal flow of chips (ChipTrayWidget)
    STACK = "stack"  # Vertical list (QListWidget)


class EntityListWidget(QWidget):
    """
    Smart widget for displaying and editing entity lists.
    
    Handles:
    - Click → Opens appropriate editor dialog via EntityClickRouter
    - Add → Opens picker dialog, links via ContextAdapter
    - Remove → Unlinks via ContextAdapter
    - Display → Uses EntityConfig for icons and labels
    
    Signals:
        data_changed: Emitted when entities are added/removed/edited
    """
    
    data_changed = pyqtSignal()
    chip_context_menu_requested = pyqtSignal(int, str, object) # entity_id, label, global_pos
    
    def __init__(
        self,
        service_provider: Any,
        entity_type: EntityType,
        layout_mode: LayoutMode = LayoutMode.CLOUD,
        context_adapter: Any = None,
        allow_add: bool = True,
        allow_remove: bool = True,
        allow_edit: bool = True,
        add_tooltip: str = "Add",
        confirm_removal: bool = True,
        parent: QWidget = None
    ):
        """
        Args:
            service_provider: Object with service attributes (contributor_service, etc.)
            entity_type: Type of entities to display (ARTIST, TAG, etc.)
            layout_mode: CLOUD for chips, STACK for vertical list
            context_adapter: ContextAdapter for link/unlink operations
            allow_add: Show the add button
            allow_remove: Allow removing items
            allow_edit: Allow clicking to edit items
            add_tooltip: Tooltip for the add button
            confirm_removal: Show confirmation before removal
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.services = service_provider
        self.entity_type = entity_type
        self.layout_mode = layout_mode
        self.context_adapter = context_adapter
        self.allow_add = allow_add
        self.allow_remove = allow_remove
        self.allow_edit = allow_edit
        self.confirm_removal = confirm_removal
        
        # Optional: Callback to get filter_type for picker at runtime
        # e.g., lambda: "person" if artist.type == "group" else "group"
        self._picker_filter_fn: Optional[Callable[[], str]] = None
        self._custom_add_handler: Optional[Callable[[], None]] = None

        # Get entity config from registry
        self.entity_config = get_entity_config(entity_type)
        
        # Click router for opening dialogs
        self.click_router = EntityClickRouter(service_provider, parent=self)
        
        # Internal widget (ChipTrayWidget or QListWidget)
        self._inner_widget = None
        
        self._init_ui(add_tooltip)
    
    @property
    def tray(self) -> Optional['ChipTrayWidget']:
        """
        Public accessor for the internal ChipTrayWidget (Cloud Mode).
        Returns None if in Stack Mode.
        """
        if self.layout_mode == LayoutMode.CLOUD:
            return self._inner_widget
        return None

    def set_picker_filter(self, filter_fn: Callable[[], str]):
        """
        Set a callback to determine filter_type for the picker dialog.
        
        Example:
            widget.set_picker_filter(lambda: "person" if self.artist.type == "group" else "group")
        """
        self._picker_filter_fn = filter_fn
    
    def _init_ui(self, add_tooltip: str):
        """Build the UI based on layout mode."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        if self.layout_mode == LayoutMode.CLOUD:
            self._init_cloud_mode(layout, add_tooltip)
        else:
            self._init_stack_mode(layout, add_tooltip)
    
    def _init_cloud_mode(self, layout: QVBoxLayout, add_tooltip: str):
        """Initialize horizontal chip flow mode."""
        self._inner_widget = ChipTrayWidget(
            confirm_removal=self.confirm_removal,
            add_tooltip=add_tooltip,
            show_add=self.allow_add,
            parent=self
        )
        
        # Connect signals
        if self.allow_edit:
            self._inner_widget.chip_clicked.connect(self._on_item_clicked, Qt.ConnectionType.UniqueConnection)
            
        # Context menu handler (Intercept for smart actions)
        self._inner_widget.chip_context_menu_requested.connect(self._show_cloud_context_menu)
        
        if self.allow_remove:
            self._inner_widget.chip_remove_requested.connect(self._on_item_remove_requested)
        if self.allow_add:
            self._inner_widget.add_requested.connect(self._on_add_clicked)
        
        layout.addWidget(self._inner_widget)
    
    def _init_stack_mode(self, layout: QVBoxLayout, add_tooltip: str):
        """Initialize vertical list mode using QListWidget."""
        # Header with add button
        if self.allow_add:
            header = QHBoxLayout()
            header.setContentsMargins(0, 0, 0, 4)
            header.addStretch()
            
            self.btn_add = GlowButton("")
            self.btn_add.setObjectName("AddInlineButton")
            self.btn_add.setToolTip(add_tooltip)
            self.btn_add.clicked.connect(self._on_add_clicked)
            header.addWidget(self.btn_add)
            
            layout.addLayout(header)
        
        # QListWidget for performance with large lists
        self._inner_widget = QListWidget()
        self._inner_widget.setObjectName("EntityListStack")
        
        # Connect signals
        if self.allow_edit:
            self._inner_widget.itemDoubleClicked.connect(
                lambda item: self._on_item_clicked(
                    item.data(Qt.ItemDataRole.UserRole), 
                    item.text()
                )
            )
        
        # Context menu for removal
        if self.allow_remove:
            self._inner_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self._inner_widget.customContextMenuRequested.connect(self._show_stack_context_menu)
        
        layout.addWidget(self._inner_widget)
    
    def set_items(self, items: list):
        """
        Set the items to display.
        
        Args:
            items: List of entity objects OR list of tuples:
                   (id, label, icon, is_mixed, is_inherited, tooltip, zone, is_primary)
        """
        if self.layout_mode == LayoutMode.CLOUD:
            self._set_cloud_items(items)
        else:
            self._set_stack_items(items)
    
    def _set_cloud_items(self, items: list):
        """Set items in chip tray mode."""
        chips = []
        for item in items:
            if isinstance(item, tuple):
                # Already in chip format
                chips.append(item)
            else:
                # Convert entity to chip tuple
                entity_id = self._get_entity_id(item)
                label = get_entity_display(self.entity_type, item)
                icon = get_entity_icon(self.entity_type, item)
                chips.append((entity_id, label, icon, False, False, "", "amber", False))
        
        self._inner_widget.set_chips(chips)
    
    def _set_stack_items(self, items: list):
        """Set items in list mode."""
        self._inner_widget.clear()
        
        for item in items:
            if isinstance(item, tuple):
                entity_id, label, icon, *rest = item
            else:
                entity_id = self._get_entity_id(item)
                label = get_entity_display(self.entity_type, item)
                icon = get_entity_icon(self.entity_type, item)
            
            list_item = QListWidgetItem(f"{icon} {label}")
            list_item.setData(Qt.ItemDataRole.UserRole, entity_id)
            self._inner_widget.addItem(list_item)
    
    def set_context_adapter(self, adapter: ContextAdapter):
        """Update the context adapter dynamically."""
        self.context_adapter = adapter
        self.refresh_from_adapter()

    def refresh_from_adapter(self):
        """Refresh items from the context adapter."""
        if self.context_adapter:
            data = self.context_adapter.get_child_data()
            self.set_items(data)
        else:
            # Clear if no adapter
            self.set_items([])
    
    def _on_item_clicked(self, entity_id: int, label: str):
        """Handle click on an item - open editor dialog."""
        print(f"DEBUG: EntityListWidget clicked: ID={entity_id}, Label={label}, Type={self.entity_type}")
        if not self.allow_edit:
            return
        
        # Get context for dialog
        context_entity = None
        if self.context_adapter:
            context_entity = self.context_adapter.get_parent_for_dialog()
        
        # Route to appropriate dialog
        result = self.click_router.route_click(
            self.entity_type,
            entity_id,
            label,
            context_entity=context_entity,
            allow_remove=self.allow_remove
        )
        
        # Handle result
        if result.action == ClickAction.REMOVED:
            self._do_remove(entity_id)
        elif result.action in (ClickAction.UPDATED, ClickAction.DATA_CHANGED):
            self.refresh_from_adapter()
            self.data_changed.emit()
    
    def _on_item_remove_requested(self, entity_id: int, label: str):
        """Handle remove request from chip."""
        self._do_remove(entity_id)
    
    def _do_remove(self, entity_id: int):
        """Perform the actual removal via adapter."""
        if self.context_adapter:
            if self.context_adapter.unlink(entity_id):
                self.refresh_from_adapter()
                self.data_changed.emit()
    
    def add_item_interactive(self):
        """Public slot to trigger the add item flow (picker)."""
        self._on_add_clicked()

    def set_custom_add_handler(self, handler: Callable[[], None]):
        """Override the default add/picker behavior with a custom callback."""
        self._custom_add_handler = handler

    def _on_add_clicked(self):
        """Handle add button click - open picker dialog."""
        if not self.allow_add:
            return
            
        if self._custom_add_handler:
            self._custom_add_handler()
            return
        
        # Get current IDs to exclude
        exclude_ids = set()
        if self.context_adapter:
            exclude_ids = self.context_adapter.get_excluded_ids()
        
        # Get filter type if callback is set
        filter_type = None
        if self._picker_filter_fn:
            filter_type = self._picker_filter_fn()
        
        # Open picker
        selected = self.click_router.open_picker(
            self.entity_type,
            exclude_ids=exclude_ids,
            filter_type=filter_type
        )
        
        if selected:
            # Handle list result (some pickers return multiple)
            if isinstance(selected, list):
                for item in selected:
                    self._do_add(item)
            else:
                self._do_add(selected)
    
    def _do_add(self, entity: Any):
        """Perform the actual add via adapter."""
        if self.context_adapter:
            entity_id = self._get_entity_id(entity)
            
            # Check for Alias Match to pass to adapter (important for Group Members)
            kwargs = {}
            if hasattr(entity, 'matched_alias') and entity.matched_alias:
                 kwargs['matched_alias'] = entity.matched_alias

            if self.context_adapter.link(entity_id, **kwargs):
                # T-Polish: Use "Append Mode" for additive types to prevent sorting jumps
                # Albums are usually exclusive/replacing, so they need full refresh.
                if self.entity_type != EntityType.ALBUM:
                    self._append_local_item(entity)
                else:
                    self.refresh_from_adapter()
                
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Action Failed", 
                                   "Could not complete the link. This might be due to a circular relationship or validation error.")
    
    def _append_local_item(self, entity: Any):
        """Manually append a new item to avoid resort."""
        entity_id = self._get_entity_id(entity)
        label = get_entity_display(self.entity_type, entity)
        icon = get_entity_icon(self.entity_type, entity)
        
        # Determine defaults for new item
        is_mixed = False
        is_inherited = False
        tooltip = ""
        zone = "amber"
        is_primary = False
        
        if self.layout_mode == LayoutMode.CLOUD:
             # Append to end (index=-1)
             self._inner_widget.add_chip(entity_id, label, icon, is_mixed, is_inherited, tooltip, 
                                         move_add_button=True, zone=zone, is_primary=is_primary)
        else:
             # Stack Mode - Append
             full_label = f"{icon} {label}"
             list_item = QListWidgetItem(full_label)
             list_item.setData(Qt.ItemDataRole.UserRole, entity_id)
             self._inner_widget.addItem(list_item)
    
    def _show_stack_context_menu(self, pos):
        """Show context menu for stack mode items."""
        item = self._inner_widget.itemAt(pos)
        if not item:
            return
        
        entity_id = item.data(Qt.ItemDataRole.UserRole)
        label = item.text()
        
        # Unwrap icon from label if present
        # List items are "Icon Label", we want just logic on label?
        # Actually label passed to _fix_case should be the clean name.
        # But item.text() includes icon. item.data() has raw entity? No.
        # We need to rely on the fact that ContextAdapter refreshes...
        # Wait, get_names() returns clean names?
        # Let's just fix Cloud Mode first where label is clean.
        # For stack mode logic we might need to fetch the entity name again.
        
        menu = QMenu(self)
        
        if self.allow_edit:
            edit_action = menu.addAction("Edit...")
            edit_action.triggered.connect(
                lambda: self._on_item_clicked(entity_id, label)
            )
            
            # Smart Fix (experimental for stack)
            # Need to clean label first (remove emoji)
            # clean_label = ... (Skip for now to avoid complexity, focusing on SidePanel Cloud)

        if self.allow_remove:
            menu.addSeparator()
            remove_action = menu.addAction("Remove")
            remove_action.triggered.connect(
                lambda: self._do_remove(entity_id)
            )
        
        menu.exec(self._inner_widget.mapToGlobal(pos))
        
    def _show_cloud_context_menu(self, entity_id: int, label: str, global_pos):
        """Show context menu for chips (SidePanel)."""
        menu = QMenu(self)
        
        # Priority Actions (Restore "Set Primary" functionality)
        if hasattr(self.context_adapter, 'set_primary'):
            # Only relevant for Genres/Albums usually
            # We can check if it's already primary? 
            # ChipTray knows, but we are here.
            # Just offer it.
            menu.addAction("Set as Primary ★").triggered.connect(lambda: self._set_primary_internal(entity_id))
            menu.addSeparator()
        
        # Edit
        if self.allow_edit:
             menu.addAction("Edit...").triggered.connect(lambda: self._on_item_clicked(entity_id, label))
        
        # Smart Fixes (Title Case)
        # Only show if case conversion changes something
        if self.allow_edit and label != label.title():
             menu.addAction(f"Fix Case: {label.title()}").triggered.connect(lambda: self._fix_case(entity_id, label))

        if self.allow_remove:
            menu.addSeparator()
            menu.addAction("Remove").triggered.connect(lambda: self._do_remove(entity_id))
            
        menu.exec(global_pos)
        
    def _set_primary_internal(self, entity_id: int):
        """Handle Set Primary request via Adapter."""
        if self.context_adapter and hasattr(self.context_adapter, 'set_primary'):
            if self.context_adapter.set_primary(entity_id):
                self.refresh_from_adapter()
                self.data_changed.emit()

    def _fix_case(self, entity_id: int, label: str):
        """Updates the entity name to Title Case."""
        new_name = label.title()
        if new_name == label: return
        
        success = False
        try:
            if self.entity_type == EntityType.ARTIST:
                 svc = self.services.contributor_service
                 c = svc.get_by_id(entity_id)
                 if c:
                     c.name = new_name
                     # update() now handles smart merging and case fixes
                     success = svc.update(c)
            elif self.entity_type == EntityType.PUBLISHER:
                  svc = self.services.publisher_service
                  p = svc.get_by_id(entity_id)
                  if p:
                      p.publisher_name = new_name
                      success = svc.update(p)
            elif self.entity_type == EntityType.ALBUM:
                  svc = self.services.album_service
                  a = svc.get_by_id(entity_id)
                  if a:
                      a.title = new_name
                      success = svc.update(a)
            elif self.entity_type == EntityType.TAG:
                 svc = self.services.tag_service
                 t = svc.get_by_id(entity_id)
                 if t:
                     # rename_tag handles merges
                     success = svc.rename_tag(t.tag_name, new_name, t.category)
                     
            if success:
                 self.refresh_from_adapter()
                 self.data_changed.emit()
            else:
                 QMessageBox.warning(self, "Update Failed", f"Could not rename to '{new_name}'. Name strictly taken?")
                 
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error fixing case: {e}")

    def _get_entity_id(self, entity: Any) -> int:
        """Get ID from entity object or dictionary."""
        # Handle Dictionary
        if isinstance(entity, dict):
            for key in ['contributor_id', 'publisher_id', 'album_id', 'tag_id', 'id']:
                if key in entity:
                    return entity[key]
            return 0
            
        # Handle Object
        for attr in ['contributor_id', 'publisher_id', 'album_id', 'tag_id', 'id']:
            if hasattr(entity, attr):
                return getattr(entity, attr)
        return 0
    
    # =========================================================================
    # PASS-THROUGH METHODS for ChipTrayWidget compatibility
    # =========================================================================
    
    def add_chip(self, *args, **kwargs):
        """Pass-through for ChipTrayWidget.add_chip()."""
        if self.layout_mode == LayoutMode.CLOUD and self._inner_widget:
            self._inner_widget.add_chip(*args, **kwargs)
    
    def remove_chip(self, entity_id: int):
        """Pass-through for ChipTrayWidget.remove_chip()."""
        if self.layout_mode == LayoutMode.CLOUD and self._inner_widget:
            self._inner_widget.remove_chip(entity_id)
    
    def clear(self):
        """Clear all items."""
        if self._inner_widget:
            self._inner_widget.clear()
    
    def get_names(self) -> list:
        """Get list of item labels."""
        if self.layout_mode == LayoutMode.CLOUD and hasattr(self._inner_widget, 'get_names'):
            return self._inner_widget.get_names()
        elif self.layout_mode == LayoutMode.STACK:
            return [
                self._inner_widget.item(i).text() 
                for i in range(self._inner_widget.count())
            ]
        return []
