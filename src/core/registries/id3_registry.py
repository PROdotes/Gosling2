"""
ID3 Frame Registry

Centralized registry for ID3 frame mappings and tag categories.
Loads from id3_frames.json once and caches in memory.

This is the single source of truth for:
- ID3 frame definitions and field mappings
- Tag category metadata (icons, colors, ID3 frames)
"""

import json
import os
from typing import Optional, Dict, List
from ...core import logger


class ID3Registry:
    """
    Centralized registry for ID3 frame mappings and tag categories.
    
    All methods are class methods to provide a singleton-like interface
    with lazy loading and caching.
    """
    
    _data: Optional[Dict] = None
    _frame_map_cache: Optional[Dict] = None
    
    @classmethod
    def _load(cls) -> None:
        """
        Load and cache id3_frames.json.
        
        Path resolution works from this file's location:
        src/core/registries/id3_registry.py -> src/resources/id3_frames.json
        """
        if cls._data is not None:
            return
            
        try:
            # Resolve path: src/core/registries/ -> src/resources/
            base_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(base_dir, '..', '..', 'json', 'id3_frames.json')
            json_path = os.path.normpath(json_path)
            
            if not os.path.exists(json_path):
                logger.error(f"ID3 frames JSON not found at: {json_path}")
                cls._data = {}
                cls._frame_map_cache = {}
                return
                
            with open(json_path, 'r', encoding='utf-8') as f:
                cls._data = json.load(f)
                
            # Cache filtered frame map
            cls._frame_map_cache = {k: v for k, v in cls._data.items() if k != 'tag_categories'}
                
            logger.info(f"ID3Registry loaded {len(cls._data)} frame definitions")
            
        except Exception as e:
            logger.error(f"Error loading id3_frames.json: {e}")
            cls._data = {}
            cls._frame_map_cache = {}
    
    @classmethod
    def get_frame_map(cls) -> Dict:
        """
        Get all ID3 frame definitions (excludes tag_categories).
        
        Returns:
            Dictionary mapping frame codes to their definitions.
            Example: {"TCON": {"description": "Genre", "tag_category": "Genre", ...}}
        """
        cls._load()
        return cls._frame_map_cache
    
    @classmethod
    def get_tag_categories(cls) -> Dict:
        """
        Get all tag category definitions.
        
        Returns:
            Dictionary of category metadata.
            Example: {"Genre": {"id3_frame": "TCON", "icon": "🏷️", ...}}
        """
        cls._load()
        return cls._data.get('tag_categories', {})
    
    @classmethod
    def get_category_icon(cls, category: str, default: str = "📦") -> str:
        """Get icon emoji for a tag category (Case-insensitive)."""
        cats = cls.get_tag_categories()
        # Case-insensitive lookup
        cat_map = {k.lower(): v for k, v in cats.items()}
        return cat_map.get(category.lower(), {}).get('icon', default)
    
    @classmethod
    def get_category_color(cls, category: str, default: str = "#888888") -> str:
        """Get hex color for a tag category (Case-insensitive)."""
        cats = cls.get_tag_categories()
        # Case-insensitive lookup
        cat_map = {k.lower(): v for k, v in cats.items()}
        return cat_map.get(category.lower(), {}).get('color', default)
    
    @classmethod
    def get_id3_frame(cls, category: str) -> Optional[str]:
        """
        Get ID3 frame code for a tag category.
        
        Args:
            category: Category name (e.g., "Genre", "Mood")
            
        Returns:
            Frame code (e.g., "TCON") or None if no mapping exists
        """
        cats = cls.get_tag_categories()
        return cats.get(category, {}).get('id3_frame')
    
    @classmethod
    def get_category_for_frame(cls, frame_code: str) -> Optional[str]:
        """
        Find the category name associated with an ID3 frame (e.g., 'TCON' -> 'Genre').
        """
        cats = cls.get_tag_categories()
        for name, d in cats.items():
            if d.get('id3_frame') == frame_code:
                return name
        return None
    
    @classmethod
    def get_all_category_names(cls) -> List[str]:
        """
        Get list of all valid category names.
        
        Returns:
            List of category names (e.g., ["Genre", "Mood", "Status"])
        """
        return list(cls.get_tag_categories().keys())
    
    @classmethod
    def is_valid_category(cls, category: str) -> bool:
        """
        Check if a category exists in the registry.
        
        Args:
            category: Category name to check
            
        Returns:
            True if category exists, False otherwise
        """
        return category in cls.get_tag_categories()
    
    @classmethod
    def get_frame_for_field(cls, field_name: str) -> Optional[str]:
        """
        Get ID3 frame code for a field name.
        
        Args:
            field_name: Field name (e.g., "title", "performers")
            
        Returns:
            Frame code (e.g., "TIT2") or None if no mapping exists
        """
        frame_map = cls.get_frame_map()
        for frame_code, frame_def in frame_map.items():
            if isinstance(frame_def, dict) and frame_def.get('field') == field_name:
                return frame_code
        return None
    
    @classmethod
    def get_field_for_frame(cls, frame_code: str) -> Optional[str]:
        """
        Get field name for an ID3 frame code.
        
        Args:
            frame_code: Frame code (e.g., "TIT2", "TCON")
            
        Returns:
            Field name (e.g., "title") or None if no mapping exists
        """
        frame_map = cls.get_frame_map()
        frame_def = frame_map.get(frame_code)
        if isinstance(frame_def, dict):
            return frame_def.get('field')
        return None
    
    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the cached data (useful for testing).
        """
        cls._data = None
        cls._frame_map_cache = None
