import os
import shutil

class RenamingService:
    def __init__(self, settings_manager):
        self.settings = settings_manager

    def calculate_target_path(self, song) -> str:
        """
        Generates the ideal absolute path based on SettingsManager patterns.
        Pattern example: "{Artist}/{Album}/{Title}"
        """
        # 1. Get Root
        root = self.settings.get_root_directory()
        if not root:
             root = os.path.dirname(song.path) if song.path else "."
             
        # 2. Resolve Pattern (Priority: Rules > Settings)
        # Load rules
        rules = self._load_rules()
        pattern = None
        
        # Check Rules
        if rules and song.genre:
            g_lower = song.genre.lower().strip()
            for rule in rules.get("routing_rules", []):
                matches = [m.lower() for m in rule.get("match_genres", [])]
                if g_lower in matches:
                    pattern = rule.get("target_path", "")
                    break
        
        # 3. Fallback to Rules Default (Missing Link)
        if not pattern and rules:
            pattern = rules.get("default_rule")

        # 4. Fallback to Settings
        if not pattern:
            pattern = self.settings.get_rename_pattern()
            
        if not pattern:
            # Absolute fallback
            pattern = "{Artist}/{Album}/{Title}"
            
        # 3. Resolve components
        rel_path = self._resolve_pattern(pattern, song)
        
        # 4. Attach extension (preserve original if possible, else mp3)
        ext = ".mp3"
        if song.path:
            _, orig_ext = os.path.splitext(song.path)
            if orig_ext:
                ext = orig_ext
        
        # Check if pattern already includes extension
        if not rel_path.lower().endswith(ext.lower()):
            rel_path += ext
            
        return os.path.join(root, rel_path)

    def _resolve_pattern(self, pattern: str, song) -> str:
        """Replace tokens {Artist}, {Genre}, {Year}, etc."""
        # Data Preparation
        artist = getattr(song, 'unified_artist', None)
        if not artist and hasattr(song, 'performers') and song.performers:
             artist = song.performers[0]
        artist_clean = self._sanitize(artist or "Unknown Artist")
        title_clean = self._sanitize(song.title or "Unknown Title")
        
        data = {
            # Standard TitleCase
            "Artist": artist_clean,
            "Title": title_clean,
            "Album": self._sanitize(song.album or "Unknown Album"),
            "Genre": self._sanitize(song.genre or "Uncategorized"),
            "Year": self._sanitize(str(song.year) if song.year else "0000"),
            "BPM": self._sanitize(str(song.bpm) if hasattr(song, 'bpm') and song.bpm else "0"),
            
            # Lowercase variants (for JSON compatibility)
            "artist": artist_clean,
            "title": title_clean,
            "album": self._sanitize(song.album or "Unknown Album"),
            "genre": self._sanitize(song.genre or "Uncategorized"),
            "year": self._sanitize(str(song.year) if song.year else "0000"),
            
            # Special tokens
            "filename": f"{artist_clean} - {title_clean}"
        }
        
        # Replacement
        result = pattern
        for key, val in data.items():
            result = result.replace(f"{{{key}}}", val)
            
        return result

    def _load_rules(self) -> dict:
        """Load external rules from JSON."""
        import json
        # Location mapping - eventually moved to SettingsManager
        rules_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "design", "configs", "rules.json"))
        
        try:
            if os.path.exists(rules_path):
                with open(rules_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load rules.json: {e}")
        return {}



    def check_conflict(self, target_path: str) -> bool:
        """
        Returns True if target_path exists on disk.
        """
        return os.path.exists(target_path)

    def rename_song(self, song, target_path: str = None) -> bool:
        """
        Executes the move.
        """
        if not target_path:
            target_path = self.calculate_target_path(song)

        # 1. Validate Constraints
        if self.check_conflict(target_path):
            return False
            
        # Ensure source exists
        if not song.path or not os.path.exists(song.path):
            return False

        try:
            # 2. Create parent directories
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # 3. Move
            shutil.move(song.path, target_path)
            
            # 4. Update Model (Caller must persist to DB)
            song.path = target_path
            return True
            
        except (OSError, shutil.Error) as e:
            from src.core import logger
            logger.error(f"Rename Error during file move: {e}")
            return False

    def _sanitize(self, component: str) -> str:
        """Internal helper to strip bad chars."""
        # Windows strict + Linux safe
        # < > : " / \ | ? *
        if not component: return ""
        bad_chars = '<>:"/\\|?*'
        clean = "".join(c for c in component if c not in bad_chars)
        # Strip trailing dots/spaces (Windows hates 'Folder. ')
        return clean.strip().strip('.')
