"""
Entity Click Router 🔀
Routes entity clicks to appropriate dialogs without duplicating handler code.

This replaces the scattered _on_*_chip_clicked handlers across dialogs.
Instead of each dialog knowing how to open ArtistDetailsDialog, PublisherDetailsDialog, etc.,
they call the router and it handles everything.

Usage:
    from src.core.entity_click_router import EntityClickRouter
    
    # In dialog __init__:
    self.click_router = EntityClickRouter(self.services, parent=self)
    
    # In chip click handler:
    result = self.click_router.route_click(EntityType.ARTIST, artist_id)
    if result.action == ClickResult.REMOVED:
        self._handle_removal(...)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Callable

from PyQt6.QtWidgets import QWidget

from .entity_registry import (
    EntityType, 
    EntityConfig, 
    ENTITY_REGISTRY, 
    get_entity_config,
    resolve_dialog_class
)


class ClickAction(Enum):
    """Result of a click action."""
    CANCELLED = 0       # User cancelled the dialog
    UPDATED = 1         # Entity was updated (standard accept)
    REMOVED = 2         # User requested removal from context
    DATA_CHANGED = 3    # Data changed, sync required (merge, rename, etc.)


@dataclass
class ClickResult:
    """Result of routing a click."""
    action: ClickAction
    entity_id: int
    entity: Any = None      # The updated entity, if applicable
    merged_into: Any = None # If merged, the target entity


class EntityClickRouter:
    """
    Routes entity clicks to appropriate dialogs.
    
    This class encapsulates the "what dialog to open for this entity" logic
    that was previously duplicated across SidePanelWidget, AlbumManagerDialog,
    ArtistDetailsDialog, etc.
    """
    
    def __init__(self, service_provider, parent: QWidget = None):
        """
        Args:
            service_provider: Object with service attributes (contributor_service, etc.)
            parent: Parent widget for dialogs
        """
        self.services = service_provider
        self.parent = parent
        
        # Custom click handlers (for special cases like Status tags)
        self._custom_handlers: dict[str, Callable] = {}
    
    def register_custom_handler(self, handler_name: str, handler_fn: Callable):
        """
        Register a custom click handler for special cases.
        
        Args:
            handler_name: Name matching EntityConfig.custom_click_handler
            handler_fn: Callable(entity_id, label) -> bool (True if handled)
        """
        self._custom_handlers[handler_name] = handler_fn
    
    def route_click(
        self, 
        entity_type: EntityType, 
        entity_id: int, 
        label: str = "",
        context_entity: Any = None,
        allow_remove: bool = True
    ) -> ClickResult:
        """
        Route a click to the appropriate editor dialog.
        
        Args:
            entity_type: Type of entity clicked
            entity_id: ID of the clicked entity
            label: Display label (for custom handlers)
            context_entity: Parent entity for "Remove from X" button (Song, Album, etc.)
            allow_remove: Whether to show the remove button
        
        Returns:
            ClickResult with the action taken
        """
        config = get_entity_config(entity_type)
        
        # Check for custom click handler (e.g., Status tags show audit)
        if config.custom_click_handler:
            handler = self._custom_handlers.get(config.custom_click_handler)
            if handler and handler(entity_id, label):
                return ClickResult(ClickAction.CANCELLED, entity_id)
        
        # Get the service for this entity type
        service = getattr(self.services, config.service_attr, None)
        if not service:
            raise ValueError(f"Service not found: {config.service_attr}")
        
        # Fetch the entity
        entity = service.get_by_id(entity_id)
        if not entity:
            return ClickResult(ClickAction.CANCELLED, entity_id)
        
        # Resolve and open the dialog
        dialog_class = resolve_dialog_class(config.editor_dialog)
        if not dialog_class:
            return ClickResult(ClickAction.CANCELLED, entity_id)
        
        # Build dialog kwargs based on what the dialog expects
        dialog_kwargs = self._build_dialog_kwargs(
            entity_type, entity, service, context_entity, allow_remove
        )
        
        dialog = dialog_class(**dialog_kwargs)
        result_code = dialog.exec()
        
        return self._interpret_result(result_code, entity_id, entity, dialog)
    
    def _build_dialog_kwargs(
        self, 
        entity_type: EntityType,
        entity: Any,
        service: Any,
        context_entity: Any,
        allow_remove: bool
    ) -> dict:
        """
        Build keyword arguments for dialog construction.
        
        Different dialogs have different constructor signatures, so we need
        to map our generic parameters to what each dialog expects.
        """
        kwargs = {"parent": self.parent}
        
        if entity_type == EntityType.ARTIST:
            kwargs["artist"] = entity
            kwargs["service"] = service
            kwargs["context_song"] = context_entity
            kwargs["allow_remove_from_context"] = allow_remove
            
        elif entity_type == EntityType.PUBLISHER:
            kwargs["publisher"] = entity
            kwargs["service"] = service
            kwargs["allow_remove_from_context"] = allow_remove
            
        elif entity_type == EntityType.ALBUM:
            # AlbumManagerDialog has a different signature
            kwargs["album_service"] = service
            kwargs["publisher_service"] = getattr(self.services, "publisher_service", None)
            kwargs["contributor_service"] = getattr(self.services, "contributor_service", None)
            kwargs["initial_data"] = {"albums": [entity]}
            
        elif entity_type == EntityType.TAG:
            kwargs["tag_service"] = service
            kwargs["target_tag"] = entity
            
        elif entity_type in (EntityType.ALIAS, EntityType.GROUP_MEMBER):
            # These use ArtistDetailsDialog for the linked artist
            kwargs["artist"] = entity
            kwargs["service"] = service
            kwargs["context_song"] = context_entity
            kwargs["allow_remove_from_context"] = allow_remove
        
        return kwargs
    
    def _interpret_result(
        self, 
        result_code: int, 
        entity_id: int, 
        entity: Any,
        dialog: Any
    ) -> ClickResult:
        """
        Interpret dialog result code into ClickResult.
        
        Most dialogs use:
        - 0: Cancelled (reject)
        - 1: Accepted (saved changes)
        - 2: Remove requested
        - 3: Data changed (merge, needs sync)
        """
        if result_code == 0:
            return ClickResult(ClickAction.CANCELLED, entity_id, entity)
        elif result_code == 1:
            return ClickResult(ClickAction.UPDATED, entity_id, entity)
        elif result_code == 2:
            return ClickResult(ClickAction.REMOVED, entity_id, entity)
        elif result_code == 3:
            # Check if dialog has merge info
            merged_into = getattr(dialog, 'merged_target', None)
            return ClickResult(ClickAction.DATA_CHANGED, entity_id, entity, merged_into)
        else:
            # Unknown code, treat as cancelled
            return ClickResult(ClickAction.CANCELLED, entity_id, entity)
    
    def open_picker(
        self,
        entity_type: EntityType,
        exclude_ids: set = None,
        filter_type: str = None
    ) -> Optional[Any]:
        """
        Open a picker dialog for selecting/creating an entity.
        
        Args:
            entity_type: Type of entity to pick
            exclude_ids: IDs to exclude from the list
            filter_type: Optional type filter (e.g., "person" for artists)
        
        Returns:
            Selected entity, or None if cancelled
        """
        config = get_entity_config(entity_type)
        
        service = getattr(self.services, config.service_attr, None)
        if not service:
            return None
        
        dialog_class = resolve_dialog_class(config.picker_dialog)
        if not dialog_class:
            return None
        
        # Build picker kwargs
        kwargs = {"parent": self.parent}
        
        if entity_type == EntityType.ARTIST:
            kwargs["service"] = service
            kwargs["exclude_ids"] = exclude_ids or set()
            if filter_type:
                kwargs["filter_type"] = filter_type
                
        elif entity_type == EntityType.PUBLISHER:
            kwargs["service"] = service
            kwargs["exclude_ids"] = exclude_ids or set()
            
        elif entity_type == EntityType.TAG:
            kwargs["tag_service"] = service
        
        dialog = dialog_class(**kwargs)
        if dialog.exec():
            return dialog.get_selected()
        return None
