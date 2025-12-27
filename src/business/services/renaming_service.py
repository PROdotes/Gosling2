import os
import shutil

class RenamingService:
    def __init__(self, settings_manager):
        self.settings = settings_manager

    def calculate_target_path(self, song) -> str:
        """
        Generates the ideal absolute path based on song metadata and strict patterns.
        - Pattern: {Genre}/{Year}/{Artist} - {Title}.mp3
        """
        root = self.settings.get_root_directory()
        if not root:
            # Fallback if no root set (shouldn't happen in prod, but safe for tests)
            root = os.path.dirname(song.path) if song.path else "."

        # Extract and Sanitize Components
        genre = self._sanitize(song.genre) if song.genre else "Uncategorized"
        year = self._sanitize(str(song.year)) if song.year else "Unknown Year"
        
        # Unified Artist vs Performer fallback
        # Check unified_artist, then first performer, then Unknown
        artist_raw = getattr(song, 'unified_artist', None)
        if not artist_raw and hasattr(song, 'performers') and song.performers:
             artist_raw = song.performers[0]
        
        artist = self._sanitize(str(artist_raw or "Unknown Artist"))
        
        title = self._sanitize(song.title) if song.title else "Unknown Title"
        
        # Construct Filename
        filename = f"{artist} - {title}.mp3"
        
        # Calculate Folder Structure based on Business Rules
        rel_path = self._resolve_routing_rules(genre, year, filename)
        
        # Build Absolute Path
        return os.path.join(root, rel_path)

    def _load_rules(self) -> dict:
        """Load external rules from JSON. Fallback to hardcoded defaults if missing."""
        import json
        # Location mapping - eventually moved to SettingsManager
        rules_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "design", "configs", "rules.json")
        rules_path = os.path.normpath(rules_path)
        
        try:
            if os.path.exists(rules_path):
                with open(rules_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load rules.json: {e}")
        
        # Absolute minimal fallback
        return {
            "routing_rules": [],
            "default_rule": "{genre}/{year}/{filename}"
        }

    def _resolve_routing_rules(self, genre_clean: str, year_clean: str, filename: str) -> str:
        """
        Applies rules from JSON to determine folder structure.
        """
        rules = self._load_rules()
        g_lower = genre_clean.lower()
        
        for rule in rules.get("routing_rules", []):
            matches = [m.lower() for m in rule.get("match_genres", [])]
            if g_lower in matches:
                target = rule.get("target_path", "")
                return target.format(
                    genre=genre_clean,
                    year=year_clean,
                    filename=filename
                )

        # Default Rule
        default = rules.get("default_rule", "{genre}/{year}/{filename}")
        return default.format(
            genre=genre_clean,
            year=year_clean,
            filename=filename
        )

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
            # Log error? For now just fail safe.
            print(f"Rename Error: {e}")
            return False

    def _sanitize(self, component: str) -> str:
        """Internal helper to strip bad chars."""
        # Windows strict + Linux safe
        # < > : " / \ | ? *
        if not component: return ""
        bad_chars = '<>:"/\\|?*'
        clean = "".join(c for c in component if c not in bad_chars)
        return clean.strip()
