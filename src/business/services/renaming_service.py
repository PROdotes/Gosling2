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
            # song.genre could be a list (from Yellberus) or a comma-string
            if isinstance(song.genre, list):
                song_genres = [g.lower().strip() for g in song.genre]
            else:
                song_genres = [g.strip().lower() for g in str(song.genre).split(',') if g.strip()]
                
            for rule in rules.get("routing_rules", []):
                matches = [m.lower().strip() for m in rule.get("match_genres", [])]
                if any(g in matches for g in song_genres):
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
        
        # 1. Resolve Artist (Priority: performers list > unified_artist string)
        artist = ""
        performers = getattr(song, 'performers', [])
        if performers and isinstance(performers, list):
            # Join multiple performers with &
            artist = " & ".join(performers)
        else:
            artist = getattr(song, 'unified_artist', None)
            if not artist:
                artist = getattr(song, 'artist', "Unknown Artist")
        
        # Clean search payload (e.g. "ABBA ::: Ella Marenee" -> "ABBA")
        if isinstance(artist, str) and " ::: " in artist:
            artist = artist.split(" ::: ")[0]
            
        artist_clean = self._sanitize(artist or "Unknown Artist")
        title_clean = self._sanitize(song.title or "Unknown Title")
        
        # Resolve Album (Handle potential list/comma string)
        album = getattr(song, 'album', "Unknown Album")
        if isinstance(album, str) and "," in album:
            # Multi-album detection: take the first one or leave as is?
            # Users usually want a clean folder. Let's take the first one if it's a list.
            album = album.split(",")[0].strip()
        elif isinstance(album, list) and album:
            album = album[0]
        
        # Resolve Genre (Handle list)
        genre_val = getattr(song, 'genre', "Uncategorized")
        if isinstance(genre_val, list) and genre_val:
            genre_name = genre_val[0]
        elif isinstance(genre_val, str) and "," in genre_val:
            genre_name = genre_val.split(",")[0].strip()
        else:
            genre_name = str(genre_val) if genre_val else "Uncategorized"

        # Resolve Composers
        composers = getattr(song, 'composers', [])
        if isinstance(composers, list) and composers:
            composer_str = " & ".join(composers)
        else:
            composer_str = str(composers) if composers else ""
        
        data = {
            # Standard TitleCase
            "Artist": artist_clean,
            "Title": title_clean,
            "Album": self._sanitize(album or "Unknown Album"),
            "Composers": self._sanitize(composer_str),
            "Genre": self._sanitize(genre_name),
            "Year": self._sanitize(str(song.year) if song.year else "0000"),
            "BPM": self._sanitize(str(song.bpm) if hasattr(song, 'bpm') and song.bpm else "0"),
            
            # Lowercase variants (for JSON compatibility)
            "artist": artist_clean,
            "title": title_clean,
            "album": self._sanitize(album or "Unknown Album"),
            "genre": self._sanitize(genre_name),
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
        # Primary: docs/configs/rules.json (As per user location)
        # Secondary: design/configs/rules.json (Legacy fallback)
        
        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        paths = [
            os.path.join(base_dir, "docs", "configs", "rules.json"),
            os.path.join(base_dir, "design", "configs", "rules.json")
        ]
        
        for rules_path in paths:
            try:
                if os.path.exists(rules_path):
                    with open(rules_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load rules.json at {rules_path}: {e}")
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
