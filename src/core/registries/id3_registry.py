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
        """
        if cls._data is not None:
            return
            
        try:
            import sys
            if getattr(sys, 'frozen', False):
                # If running as a PyInstaller executable, use the MEIPASS temp folder.
                # In PyInstaller, we added the src/resources folder using --add-data
                # But ID3Frames might be in src/json, we need to check if we packaged it
                # Looking at your PyInstaller command, you didn't include src/json. 
                # BUT wait, the ID3 registry gets packaged anyway? No, it's a data file.
                # Let's read from relative to the _MEIPASS root.
                base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                json_path = os.path.join(base_dir, 'src', 'json', 'id3_frames.json')
            else:
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
                
            # Cache filtered frame map (everything is a frame definition now)
            cls._frame_map_cache = {k: v for k, v in cls._data.items() if isinstance(v, (dict, str))}
                
            logger.info(f"ID3Registry loaded {len(cls._data)} frame definitions")
            
        except Exception as e:
            logger.error(f"Error loading id3_frames.json: {e}")
            cls._data = {}
            cls._frame_map_cache = {}
    
    @classmethod
    def get_frame_map(cls) -> Dict:
        """
        Get all ID3 frame definitions.
        """
        cls._load()
        return cls._frame_map_cache
    
    @classmethod
    def get_tag_categories(cls) -> Dict:
        """
        Get all items that act as tag categories.
        A category is defined as an item that has an 'icon' but no 'field' mapping.
        """
        cls._load()
        cats = {}
        for key, val in cls._data.items():
            if isinstance(val, dict) and 'icon' in val and 'field' not in val:
                # Use tag_category if present, else use the key (frame code)
                cat_name = val.get('tag_category', key)
                cats[cat_name] = val
                # Ensure the category knows its own frame if it exists
                if 'id3_frame' not in val and len(key) == 4 and key.isupper():
                    val['id3_frame'] = key
        return cats
    
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
            # If it's the frame itself acting as a category
            if d.get('tag_category') == name and frame_code == name:
                return name
        return None
    
    @classmethod
    def get_all_category_names(cls) -> List[str]:
        """
        Get list of all valid category names.
        """
        return list(cls.get_tag_categories().keys())

