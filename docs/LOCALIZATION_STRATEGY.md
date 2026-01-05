# Localization Strategy for Gosling2

## Overview
This document outlines a game-style localization system where all user-facing text is externalized to JSON files, making translation and customization easy without touching code.

## Architecture

### File Structure
```
src/resources/
  locales/
    en.json          # English (default/fallback)
    hr.json          # Croatian
    es.json          # Spanish
    ja.json          # Japanese
    de.json          # German
    fr.json          # French
    custom.json      # User overrides (optional)
```

### Locale File Format
Each locale file contains **all** user-facing strings organized by context:

```json
{
  "locale": {
    "code": "en",
    "name": "English",
    "direction": "ltr"
  },
  
  "ui": {
    "buttons": {
      "save": "Save",
      "cancel": "Cancel",
      "delete": "Delete",
      "add": "Add",
      "edit": "Edit",
      "search": "Search"
    },
    "labels": {
      "title": "Title",
      "artist": "Artist",
      "album": "Album",
      "year": "Year",
      "duration": "Duration"
    },
    "messages": {
      "save_success": "Changes saved successfully",
      "save_error": "Failed to save changes: {error}",
      "confirm_delete": "Are you sure you want to delete {item}?",
      "no_selection": "No Selection",
      "multiple_selected": "{count} Songs Selected"
    },
    "dialogs": {
      "add_tag": "Add Tag",
      "rename_tag": "Rename Tag",
      "album_manager": "Album Manager",
      "artist_details": "Artist Details"
    }
  },
  
  "tag_categories": {
    "Genre": {
      "name": "Genre",
      "description": "Musical genre classification",
      "aliases": ["genre", "style", "type"]
    },
    "Mood": {
      "name": "Mood",
      "description": "Emotional mood or atmosphere",
      "aliases": ["mood", "vibe", "feeling"]
    },
    "Status": {
      "name": "Status",
      "description": "Internal workflow status",
      "aliases": ["status", "state"]
    }
  },
  
  "fields": {
    "title": "Title",
    "performers": "Performers",
    "album": "Album",
    "composers": "Composer",
    "publisher": "Publisher",
    "recording_year": "Year",
    "isrc": "ISRC",
    "bpm": "BPM",
    "notes": "Notes"
  },
  
  "validation": {
    "required": "{field} is required",
    "min_length": "{field} must be at least {min} characters",
    "max_length": "{field} cannot exceed {max} characters",
    "invalid_format": "Invalid format for {field}",
    "invalid_year": "Year must be between {min} and {max}"
  },
  
  "errors": {
    "file_not_found": "File not found: {path}",
    "database_error": "Database error: {error}",
    "network_error": "Network error: {error}",
    "permission_denied": "Permission denied"
  }
}
```

### Croatian Example (hr.json)
```json
{
  "locale": {
    "code": "hr",
    "name": "Hrvatski",
    "direction": "ltr"
  },
  
  "ui": {
    "buttons": {
      "save": "Spremi",
      "cancel": "Odustani",
      "delete": "Obriši",
      "add": "Dodaj",
      "edit": "Uredi",
      "search": "Traži"
    },
    "labels": {
      "title": "Naslov",
      "artist": "Izvođač",
      "album": "Album",
      "year": "Godina",
      "duration": "Trajanje"
    }
  },
  
  "tag_categories": {
    "Genre": {
      "name": "Žanr",
      "description": "Klasifikacija glazbenog žanra",
      "aliases": ["žanr", "stil", "vrsta"]
    },
    "Mood": {
      "name": "Raspoloženje",
      "description": "Emocionalno raspoloženje ili atmosfera",
      "aliases": ["raspoloženje", "vibra", "osjećaj"]
    }
  }
}
```

## Implementation

### 1. LocaleManager Service
```python
# src/core/locale_manager.py

import json
import os
from typing import Dict, Any, Optional

class LocaleManager:
    """Centralized locale/translation manager."""
    
    _instance = None
    _current_locale = "en"
    _locales: Dict[str, Dict] = {}
    _fallback_locale = "en"
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = LocaleManager()
        return cls._instance
    
    def __init__(self):
        self._load_locales()
    
    def _load_locales(self):
        """Load all available locale files."""
        locale_dir = os.path.join(
            os.path.dirname(__file__), 
            '..', 'resources', 'locales'
        )
        
        if not os.path.exists(locale_dir):
            return
        
        for filename in os.listdir(locale_dir):
            if filename.endswith('.json'):
                locale_code = filename[:-5]  # Remove .json
                filepath = os.path.join(locale_dir, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self._locales[locale_code] = json.load(f)
                except Exception as e:
                    print(f"Failed to load locale {locale_code}: {e}")
    
    def set_locale(self, locale_code: str):
        """Set the current active locale."""
        if locale_code in self._locales:
            self._current_locale = locale_code
        else:
            print(f"Locale {locale_code} not found, using {self._fallback_locale}")
    
    def get(self, key: str, **kwargs) -> str:
        """
        Get translated string by dot-notation key.
        
        Examples:
            get("ui.buttons.save")
            get("ui.messages.save_success")
            get("validation.required", field="Title")
        """
        # Try current locale
        value = self._get_nested(self._locales.get(self._current_locale, {}), key)
        
        # Fallback to English
        if value is None and self._current_locale != self._fallback_locale:
            value = self._get_nested(self._locales.get(self._fallback_locale, {}), key)
        
        # Return key if not found
        if value is None:
            return key
        
        # Format with kwargs if provided
        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return value
    
    def _get_nested(self, data: Dict, key: str) -> Optional[str]:
        """Get nested dictionary value using dot notation."""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def get_available_locales(self) -> list:
        """Get list of available locale codes."""
        return list(self._locales.keys())
    
    def get_locale_name(self, locale_code: str) -> str:
        """Get display name for a locale."""
        locale_data = self._locales.get(locale_code, {})
        return locale_data.get('locale', {}).get('name', locale_code)


# Convenience function
def t(key: str, **kwargs) -> str:
    """Shorthand for LocaleManager.get_instance().get()"""
    return LocaleManager.get_instance().get(key, **kwargs)
```

### 2. Usage in Code

**Before:**
```python
self.btn_save = GlowButton("Save")
self.lbl_title = QLabel("Title")
QMessageBox.warning(self, "Error", "Failed to save changes")
```

**After:**
```python
from src.core.locale_manager import t

self.btn_save = GlowButton(t("ui.buttons.save"))
self.lbl_title = QLabel(t("fields.title"))
QMessageBox.warning(
    self, 
    t("ui.dialogs.error"), 
    t("ui.messages.save_error", error=str(e))
)
```

### 3. Tag Category Localization

**ID3Registry Enhancement:**
```python
@classmethod
def get_category_name(cls, category: str, locale: Optional[str] = None) -> str:
    """Get localized category name."""
    from .locale_manager import LocaleManager
    
    if locale is None:
        locale = LocaleManager.get_instance()._current_locale
    
    # Try localized name
    key = f"tag_categories.{category}.name"
    localized = LocaleManager.get_instance().get(key)
    
    # Fallback to category key
    return localized if localized != key else category

@classmethod
def resolve_category_alias(cls, alias: str) -> Optional[str]:
    """
    Resolve a category alias to canonical name.
    Works across all loaded locales.
    """
    from .locale_manager import LocaleManager
    lm = LocaleManager.get_instance()
    
    alias_lower = alias.lower()
    
    # Check all locales for alias matches
    for locale_code, locale_data in lm._locales.items():
        categories = locale_data.get('tag_categories', {})
        
        for cat_key, cat_data in categories.items():
            # Check canonical name
            if cat_data.get('name', '').lower() == alias_lower:
                return cat_key
            
            # Check aliases
            aliases = cat_data.get('aliases', [])
            if alias_lower in [a.lower() for a in aliases]:
                return cat_key
    
    return None
```

## Migration Path

### Phase 1: Infrastructure
1. Create `LocaleManager` service
2. Create `locales/en.json` with current English strings
3. Add locale selection to settings

### Phase 2: Gradual Adoption
1. Start with new features (use `t()` from day 1)
2. Refactor existing dialogs one at a time
3. Create helper script to extract hardcoded strings

### Phase 3: Community Translations
1. Provide template `en.json` to translators
2. Accept community contributions
3. Validate JSON structure automatically

## Benefits

✅ **Easy Translation**: Translators only need to edit JSON  
✅ **No Code Changes**: Add new languages without touching Python  
✅ **User Customization**: Users can override any string via `custom.json`  
✅ **Consistency**: All strings in one place per language  
✅ **Fallback Chain**: Missing translations fall back to English  
✅ **Format Strings**: Support for dynamic values (`{field}`, `{count}`)  
✅ **Context Aware**: Organized by UI context (buttons, labels, errors)

## Future Enhancements

- **Pluralization**: Handle singular/plural forms
- **RTL Support**: Right-to-left languages (Arabic, Hebrew)
- **Date/Number Formatting**: Locale-specific formatting
- **Hot Reload**: Change language without restart
- **Translation Coverage**: Report missing translations

## Example: Tag Picker Dialog

**Before:**
```python
self.setWindowTitle("Add Tag")
lbl = QLabel("RENAME TAG" if self.target_tag else "ADD TAG")
self.txt_search.setPlaceholderText("Search or type prefix:tag (e.g., m:chill)")
```

**After:**
```python
from src.core.locale_manager import t

title_key = "ui.dialogs.rename_tag" if self.target_tag else "ui.dialogs.add_tag"
self.setWindowTitle(t(title_key))

label_key = "ui.labels.rename_tag" if self.target_tag else "ui.labels.add_tag"
lbl = QLabel(t(label_key))

self.txt_search.setPlaceholderText(t("ui.placeholders.tag_search"))
```

## Notes

- Keep keys descriptive: `ui.buttons.save` not `btn1`
- Group related strings: All buttons under `ui.buttons`
- Use format strings for dynamic content: `{field}`, `{count}`, `{error}`
- Maintain key consistency across all locale files
- Consider context: "Save" button vs "Save changes?" message
