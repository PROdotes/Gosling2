"""
Entity Picker Configuration 🔧
Defines configuration for the universal EntityPickerDialog.

This allows TagPickerDialog's UX pattern to be reused for Artists, Publishers, etc.
Each entity type has a PickerConfig that defines:
- Type buttons (categories for Tags, types for Artists)
- Prefix syntax support
- Whether new types can be created
- Service methods for searching
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional, Any
from src.core.entity_registry import EntityType


@dataclass
class PickerConfig:
    """Configuration for EntityPickerDialog behavior."""
    
    # === Display ===
    title_add: str                      # "Add Tag" / "Add Artist"
    title_edit: str                     # "Rename Tag" / "Edit Artist"
    search_placeholder: str             # "Search or type prefix:tag..."
    
    # === Type/Category System ===
    type_buttons: List[str]             # ["Genre", "Mood", ...] or ["Person", "Group", "Alias"]
    type_icons: Dict[str, str]          # {"Genre": "🎵", "Person": "👤", ...}
    type_colors: Dict[str, str]         # Glow colors for each button
    allow_new_types: bool               # True for Tags, False for Artists
    default_type: str                   # Default selection (e.g., "Genre" or "Person")
    
    # === Prefix Parsing ===
    # Short prefixes: {"g": "Genre", "m": "Mood"} or {"p": "Person", "a": "Alias"}
    prefix_map: Dict[str, str] = field(default_factory=dict)
    
    # === Actions ===
    allow_create: bool = True
    allow_rename: bool = True
    allow_remove: bool = True
    
    # === Entity-specific Service Methods ===
    service_attr: str = ""              # "tag_service" or "contributor_service"
    
    # Method name or callable for getting all items of a type
    # Called as: service.get_all_by_type(type_name) or service.search("", type=type_name)
    get_by_type_fn: str = ""
    
    # Method name for getting entity by ID
    get_by_id_fn: str = "get_by_id"
    
    # Method name for searching (all types)
    search_fn: str = "search"
    
    # Method name for get_or_create
    get_or_create_fn: str = "get_or_create"
    
    # === Display Functions ===
    # How to get the display name from an entity
    display_fn: Callable[[Any], str] = lambda e: str(e)
    
    # How to get the ID from an entity  
    id_fn: Callable[[Any], int] = lambda e: getattr(e, 'id', 0)
    
    # How to get the type/category from an entity
    type_fn: Callable[[Any], str] = lambda e: ""
    
    # How to get the icon for an entity
    icon_fn: Callable[[Any], str] = lambda e: "📦"


# =============================================================================
# PREDEFINED CONFIGURATIONS
# =============================================================================

def get_tag_picker_config() -> PickerConfig:
    """Get configuration for Tag picker."""
    from src.core.registries.id3_registry import ID3Registry
    
    return PickerConfig(
        title_add="Add Tag",
        title_edit="Rename Tag",
        search_placeholder="Search or type prefix:tag (e.g., m:chill)",
        
        type_buttons=[],  # Will be populated dynamically from DB
        type_icons={},    # Will be populated from ID3Registry
        type_colors={},   # Will be populated from ID3Registry
        allow_new_types=True,  # Can create "vacation:beach"
        default_type="Genre",
        
        prefix_map={
            "g": "Genre", "genre": "Genre",
            "m": "Mood", "mood": "Mood",
            "s": "Status", "status": "Status",
            "c": "Custom", "custom": "Custom",
        },
        
        service_attr="tag_service",
        get_by_type_fn="get_all_by_category",
        get_by_id_fn="get_by_id",
        search_fn="search",
        get_or_create_fn="get_or_create",
        
        display_fn=lambda t: t.tag_name if hasattr(t, 'tag_name') else str(t),
        id_fn=lambda t: t.tag_id if hasattr(t, 'tag_id') else 0,
        type_fn=lambda t: t.category if hasattr(t, 'category') else "Custom",
        icon_fn=lambda t: ID3Registry.get_category_icon(
            t.category if hasattr(t, 'category') else "Custom", 
            default="📦"
        ),
    )


def get_artist_picker_config(allowed_types: Optional[List[str]] = None, default_type: Optional[str] = None) -> PickerConfig:
    """
    Get configuration for Artist/Contributor picker.
    
    Args:
        allowed_types: Optional list of types to include (e.g., ["Group"]).
                       If None, includes all ["Person", "Group", "Alias"].
        default_type: Optional default selected type.
    """
    all_types = ["Person", "Group"]
    all_icons = {"Person": "👤", "Group": "👥"}
    all_colors = {"Person": "#4FC3F7", "Group": "#81C784"}
    
    # Filter types if requested
    types = allowed_types if allowed_types is not None else all_types
    
    return PickerConfig(
        title_add="Add Artist",
        title_edit="Edit Artist",
        search_placeholder="Search or type name...",
        
        type_buttons=types,
        type_icons={k: v for k, v in all_icons.items() if k in types},
        type_colors={k: v for k, v in all_colors.items() if k in types},
        allow_new_types=False,  # Cannot invent new types
        default_type=default_type or (types[0] if len(types) == 1 else None),
        
        prefix_map={
            "p": "Person", "person": "Person",
            "g": "Group", "group": "Group",
        },
        
        service_attr="contributor_service",
        get_by_type_fn="get_all_by_type",  # T-Fix: Initial population
        get_by_id_fn="get_by_id",
        search_fn="search",
        get_or_create_fn="get_or_create",
        
        display_fn=lambda a: a.name if hasattr(a, 'name') else str(a),
        id_fn=lambda a: a.contributor_id if hasattr(a, 'contributor_id') else 0,
        type_fn=lambda a: getattr(a, 'type', 'Person'),
        icon_fn=lambda a: "👥" if getattr(a, 'type', 'person').lower() == "group" else "👤",
    )


def get_publisher_picker_config() -> PickerConfig:
    """Get configuration for Publisher picker."""
    return PickerConfig(
        title_add="Add Publisher",
        title_edit="Edit Publisher",
        search_placeholder="Search publishers...",
        
        type_buttons=[],  # Publishers don't have types
        type_icons={},
        type_colors={},
        allow_new_types=False,
        default_type="",
        
        prefix_map={},  # No prefix support for publishers
        
        service_attr="publisher_service",
        get_by_type_fn="search",
        get_by_id_fn="get_by_id",
        search_fn="search",
        get_or_create_fn="get_or_create",
        
        display_fn=lambda p: p.publisher_name if hasattr(p, 'publisher_name') else str(p),
        id_fn=lambda p: p.publisher_id if hasattr(p, 'publisher_id') else 0,
        type_fn=lambda p: "",
        icon_fn=lambda p: "🏢",
    )

def get_config_for_type(entity_type: EntityType, allowed_types: Optional[List[str]] = None) -> Optional[PickerConfig]:
    """Resolve PickerConfig for a given EntityType."""
    if entity_type == EntityType.ARTIST:
        return get_artist_picker_config(allowed_types=allowed_types)
    if entity_type == EntityType.GROUP_MEMBER:
        # Group members use the same picker as Artists (just filtered differently)
        return get_artist_picker_config(allowed_types=allowed_types)
    if entity_type == EntityType.PUBLISHER:
        return get_publisher_picker_config()
    if entity_type == EntityType.TAG:
        return get_tag_picker_config()
    return None
