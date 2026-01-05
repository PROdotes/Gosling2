"""
Unit tests for ID3Registry

Tests the centralized ID3 frame and tag category registry.
"""

import pytest
from src.core.registries.id3_registry import ID3Registry


class TestID3Registry:
    """Test ID3Registry functionality."""
    
    def setup_method(self):
        """Clear cache before each test."""
        ID3Registry.clear_cache()
    
    def test_loads_frame_map(self):
        """Test that frame map loads successfully."""
        frame_map = ID3Registry.get_frame_map()
        
        assert isinstance(frame_map, dict)
        assert len(frame_map) > 0
        
        # Should have common frames
        assert 'TIT2' in frame_map  # Title
        assert 'TPE1' in frame_map  # Performers
        assert 'TCON' in frame_map  # Genre
        assert 'TMOO' in frame_map  # Mood
    
    def test_frame_map_excludes_tag_categories(self):
        """Test that frame map doesn't include tag_categories section."""
        frame_map = ID3Registry.get_frame_map()
        
        assert 'tag_categories' not in frame_map
    
    def test_get_tag_categories(self):
        """Test getting tag categories."""
        categories = ID3Registry.get_tag_categories()
        
        # Should return dict with our defined categories
        assert isinstance(categories, dict)
        
        # Verify expected categories exist
        assert "Genre" in categories
        assert "Mood" in categories
        assert "Status" in categories
        assert "Custom" in categories
        
        # Verify Genre category structure
        genre = categories["Genre"]
        assert genre["id3_frame"] == "TCON"
        assert genre["icon"] == "🏷️"
        assert genre["color"] == "#FFB84D"
        assert "description" in genre
        
        # Verify Mood category structure
        mood = categories["Mood"]
        assert mood["id3_frame"] == "TMOO"
        assert mood["icon"] == "✨"
        assert mood["color"] == "#32A8FF"

    
    def test_get_category_icon(self):
        """Test getting category icon."""
        # Test real categories
        assert ID3Registry.get_category_icon("Genre") == "🏷️"
        assert ID3Registry.get_category_icon("Mood") == "✨"
        assert ID3Registry.get_category_icon("Status") == "📋"
        
        # Test default fallback
        icon = ID3Registry.get_category_icon("NonExistent", default="🎵")
        assert icon == "🎵"
    
    def test_get_category_color(self):
        """Test getting category color."""
        # Test real categories
        assert ID3Registry.get_category_color("Genre") == "#FFB84D"
        assert ID3Registry.get_category_color("Mood") == "#32A8FF"
        assert ID3Registry.get_category_color("Status") == "#888888"
        
        # Test default fallback
        color = ID3Registry.get_category_color("NonExistent", default="#FF0000")
        assert color == "#FF0000"
    
    def test_get_id3_frame_for_category(self):
        """Test getting ID3 frame for a category."""
        # Test real mappings
        assert ID3Registry.get_id3_frame("Genre") == "TCON"
        assert ID3Registry.get_id3_frame("Mood") == "TMOO"
        assert ID3Registry.get_id3_frame("Status") is None  # Internal only
        assert ID3Registry.get_id3_frame("Custom") is None  # No ID3 mapping
        
        # Non-existent category
        assert ID3Registry.get_id3_frame("NonExistent") is None

    
    def test_get_all_category_names(self):
        """Test getting all category names."""
        names = ID3Registry.get_all_category_names()
        
        assert isinstance(names, list)
        assert len(names) == 4  # Genre, Mood, Status, Custom
        assert "Genre" in names
        assert "Mood" in names
        assert "Status" in names
        assert "Custom" in names
    
    def test_is_valid_category(self):
        """Test category validation."""
        # Valid categories
        assert ID3Registry.is_valid_category("Genre") is True
        assert ID3Registry.is_valid_category("Mood") is True
        assert ID3Registry.is_valid_category("Status") is True
        assert ID3Registry.is_valid_category("Custom") is True
        
        # Invalid category
        assert ID3Registry.is_valid_category("NonExistent") is False

    
    def test_get_frame_for_field(self):
        """Test getting frame code for field name."""
        # Title field should map to TIT2
        frame = ID3Registry.get_frame_for_field("title")
        assert frame == "TIT2"
        
        # Performers should map to TPE1
        frame = ID3Registry.get_frame_for_field("performers")
        assert frame == "TPE1"
        
        # Non-existent field
        frame = ID3Registry.get_frame_for_field("nonexistent_field")
        assert frame is None
    
    def test_get_field_for_frame(self):
        """Test getting field name for frame code."""
        # TIT2 should map to title
        field = ID3Registry.get_field_for_frame("TIT2")
        assert field == "title"
        
        # TPE1 should map to performers
        field = ID3Registry.get_field_for_frame("TPE1")
        assert field == "performers"
        
        # Non-existent frame
        field = ID3Registry.get_field_for_frame("XXXX")
        assert field is None
    
    def test_caching(self):
        """Test that data is cached after first load."""
        # First call loads data
        frame_map1 = ID3Registry.get_frame_map()
        
        # Second call should return cached data (same object)
        frame_map2 = ID3Registry.get_frame_map()
        
        assert frame_map1 is frame_map2
    
    def test_clear_cache(self):
        """Test cache clearing."""
        # Load data
        ID3Registry.get_frame_map()
        assert ID3Registry._data is not None
        
        # Clear cache
        ID3Registry.clear_cache()
        assert ID3Registry._data is None
        
        # Should reload on next access
        frame_map = ID3Registry.get_frame_map()
        assert ID3Registry._data is not None
