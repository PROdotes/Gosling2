"""
Entity Registry 🗂️
Central mapping of entity types to their UI behaviors (dialogs, icons, services).

This module defines HOW each entity type is displayed and edited in the UI.
It is separate from Yellberus (field definitions) because:
1. Yellberus defines DATA fields, this defines ENTITY behaviors
2. Yellberus will be extracted to external config; this stays in code
3. Entities (Artist, Publisher) are not the same as fields (performers, composers)

Usage:
    from src.core.entity_registry import EntityType, ENTITY_REGISTRY
    
    config = ENTITY_REGISTRY[EntityType.ARTIST]
    dialog = config.editor_class(artist, service, ...)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Any, TYPE_CHECKING

# TYPE_CHECKING block to avoid circular imports at runtime
# Dialogs import services, services import repos, etc.
if TYPE_CHECKING:
    from src.presentation.dialogs.artist_manager_dialog import (
        ArtistDetailsDialog, ArtistPickerDialog
    )
    from src.presentation.dialogs.publisher_manager_dialog import (
        PublisherDetailsDialog, PublisherPickerDialog
    )
    from src.presentation.dialogs.album_manager_dialog import AlbumManagerDialog
    from src.presentation.dialogs.tag_picker_dialog import TagPickerDialog


class EntityType(Enum):
    """Types of entities that can be displayed in chips/lists."""
    
    ARTIST = "artist"           # Contributors (performers, composers, etc.)
    PUBLISHER = "publisher"     # Record labels, distributors
    ALBUM = "album"             # Releases
    TAG = "tag"                 # Genre, Mood, Status, Custom tags
    ALIAS = "alias"             # Artist aliases (inline edit only)
    SONG = "song"               # Media sources (future: song picker)
    GROUP_MEMBER = "group_member"  # Artist group membership


@dataclass
class EntityConfig:
    """Configuration for how an entity type behaves in the UI."""
    
    # Dialog classes (use strings to avoid circular imports, resolved at runtime)
    editor_dialog: str          # Full path: "artist_manager_dialog.ArtistDetailsDialog"
    picker_dialog: str          # Full path: "artist_manager_dialog.ArtistPickerDialog"
    
    # Service accessor (attribute name on ServiceProvider)
    service_attr: str           # e.g., "contributor_service"
    
    # Display functions
    icon_fn: Callable[[Any], str]       # Entity -> emoji icon
    display_fn: Callable[[Any], str]    # Entity -> display label
    
    # Special behavior hooks
    custom_click_handler: Optional[str] = None  # Method name for special click handling
    
    # Metadata
    supports_create: bool = True        # Can create new entities inline?
    supports_remove: bool = True        # Can remove/unlink entities?


def _get_tag_category_icon(category: str) -> str:
    """Get icon emoji for a tag category."""
    icons = {
        "Genre": "🎵",
        "Mood": "💭", 
        "Status": "📋",
        "Custom": "🏷️",
    }
    return icons.get(category, "🏷️")


# =============================================================================
# THE REGISTRY
# =============================================================================
# Maps EntityType -> EntityConfig
# 
# NOTE: Dialog classes are specified as strings to avoid circular imports.
# They are resolved at runtime by the EntityClickRouter.
# =============================================================================

ENTITY_REGISTRY: dict[EntityType, EntityConfig] = {
    
    EntityType.ARTIST: EntityConfig(
        editor_dialog="artist_manager_dialog.ArtistDetailsDialog",
        picker_dialog="artist_manager_dialog.ArtistPickerDialog",
        service_attr="contributor_service",
        icon_fn=lambda e: "👤" if getattr(e, 'type', 'person') == "person" else "👥",
        display_fn=lambda e: getattr(e, 'name', str(e)),
    ),
    
    EntityType.PUBLISHER: EntityConfig(
        editor_dialog="publisher_manager_dialog.PublisherDetailsDialog",
        picker_dialog="publisher_manager_dialog.PublisherPickerDialog",
        service_attr="publisher_service",
        icon_fn=lambda e: "🏢",
        display_fn=lambda e: getattr(e, 'publisher_name', str(e)),
        custom_click_handler="handle_publisher_click",
    ),
    
    EntityType.ALBUM: EntityConfig(
        editor_dialog="album_manager_dialog.AlbumManagerDialog",
        picker_dialog="album_manager_dialog.AlbumManagerDialog",  # Same dialog, picker mode
        service_attr="album_service",
        icon_fn=lambda e: "💿",
        display_fn=lambda e: getattr(e, 'album_title', str(e)),
        custom_click_handler="handle_album_click",
    ),
    
    EntityType.TAG: EntityConfig(
        editor_dialog="tag_picker_dialog.TagPickerDialog",
        picker_dialog="tag_picker_dialog.TagPickerDialog",
        service_attr="tag_service",
        icon_fn=lambda e: _get_tag_category_icon(getattr(e, 'category', 'Custom')),
        display_fn=lambda e: f"{getattr(e, 'category', 'Tag')}: {getattr(e, 'tag_name', str(e))}",
        custom_click_handler="handle_tag_click",  # Status tags show audit, not editor
    ),
    
    EntityType.ALIAS: EntityConfig(
        editor_dialog="artist_manager_dialog.ArtistDetailsDialog",  # Go to identity
        picker_dialog="artist_manager_dialog.ArtistPickerDialog",
        service_attr="contributor_service",
        icon_fn=lambda e: "📝",
        display_fn=lambda e: getattr(e, 'alias_name', str(e)) if hasattr(e, 'alias_name') else str(e),
        supports_create=True,
        supports_remove=True,
    ),
    
    EntityType.GROUP_MEMBER: EntityConfig(
        editor_dialog="artist_manager_dialog.ArtistDetailsDialog",
        picker_dialog="artist_manager_dialog.ArtistPickerDialog",
        service_attr="contributor_service",
        icon_fn=lambda e: "👤" if getattr(e, 'type', 'person') == "person" else "👥",
        display_fn=lambda e: getattr(e, 'name', str(e)),
    ),
    
    EntityType.SONG: EntityConfig(
        editor_dialog="",  # TODO: Future SongMetadataDialog
        picker_dialog="",  # TODO: Future SongPickerDialog
        service_attr="library_service",
        icon_fn=lambda e: "🎵",
        display_fn=lambda e: getattr(e, 'name', getattr(e, 'title', str(e))),
        supports_create=False,  # Songs are imported, not created inline
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_entity_config(entity_type: EntityType) -> EntityConfig:
    """Get configuration for an entity type."""
    if entity_type not in ENTITY_REGISTRY:
        raise ValueError(f"Unknown entity type: {entity_type}")
    return ENTITY_REGISTRY[entity_type]


def get_entity_icon(entity_type: EntityType, entity: Any) -> str:
    """Get the icon for an entity instance."""
    config = get_entity_config(entity_type)
    return config.icon_fn(entity)


def get_entity_display(entity_type: EntityType, entity: Any) -> str:
    """Get the display label for an entity instance."""
    config = get_entity_config(entity_type)
    return config.display_fn(entity)


def resolve_dialog_class(dialog_path: str):
    """
    Resolve a dialog class from its module path string.
    
    Args:
        dialog_path: e.g., "artist_manager_dialog.ArtistDetailsDialog"
    
    Returns:
        The actual dialog class
    
    This avoids circular imports by doing dynamic import at runtime.
    """
    if not dialog_path:
        return None
        
    parts = dialog_path.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid dialog path format: {dialog_path}")
    
    module_name, class_name = parts
    
    # Import from presentation.dialogs
    import importlib
    module = importlib.import_module(f"src.presentation.dialogs.{module_name}")
    return getattr(module, class_name)
