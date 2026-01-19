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
        # Check Rules
        # Extract genres from Unified Tags (e.g., "Genre:Rock" -> "rock")
        song_genres = []
        
        # 1. Try to get ORDERED tags from DB (Source of Truth for Primary)
        if hasattr(song, 'source_id') and song.source_id:
             try:
                 from ...business.services.tag_service import TagService
                 from ...core.registries.id3_registry import ID3Registry
                 ts = TagService()
                 db_tags = ts.get_tags_for_source(song.source_id)
                 for t in db_tags:
                     if t.category and ID3Registry.get_id3_frame(t.category) == "TCON":
                         song_genres.append(t.tag_name.lower().strip())
             except Exception:
                 pass

        # 2. Fallback for Transient Songs (No DB ID) or basic strings
        if not song_genres and hasattr(song, 'tags') and song.tags:
            from ...core.registries.id3_registry import ID3Registry
            for tag in song.tags:
                if ":" in tag:
                    cat, val = tag.split(":", 1)
                     # Check if this category is Genre (maps to TCON frame)
                    if ID3Registry.get_id3_frame(cat) == "TCON":
                        song_genres.append(val.lower().strip())
        # 2. Priority Check: Genre Tag Order
        # STRICT PRIMARY: Only check rules for the FIRST genre.
        # We use strict primary (song_genres[0]) to prevent secondary tags from hijacking the rule.
        if rules and song_genres:
            genre = song_genres[0] # Strict Primary
            for rule in rules.get("routing_rules", []):
                # Rules are implicitly genre-based via 'match_genres'
                matches = [m.lower().strip() for m in rule.get("match_genres", [])]
                if genre in matches:
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
        primary_genre = song_genres[0] if song_genres else None
        rel_path = self._resolve_pattern(pattern, song, overrides={'genre': primary_genre})
        
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

    def _resolve_pattern(self, pattern: str, song, overrides: dict = None) -> str:
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
        
        # Resolve Genre (Handle list from tags or legacy field)
        genre_name = overrides.get('genre') if overrides else None
        
        if not genre_name:
            genre_name = "Uncategorized"
            
            # 1. Try Unified Tags
            if hasattr(song, 'tags') and song.tags:
                from ...core.registries.id3_registry import ID3Registry
                for tag in song.tags:
                    if ":" in tag:
                         cat, val = tag.split(":", 1)
                         # Check if this category is Genre (maps to TCON frame)
                         if ID3Registry.get_id3_frame(cat) == "TCON":
                             genre_name = val.strip()
                             break # Take first genre as primary
        


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

    # ==================== RULES API (T-82) ====================
    
    def get_rules(self) -> dict:
        """Public API: Get current rules configuration."""
        return self._load_rules()

    def save_rules(self, rules_data: dict) -> bool:
        """Public API: Save rules configuration to JSON."""
        import json
        
        # Canonical save path: src/json/rules.json
        
        target_path = self._resolve_rules_path()
        if not target_path:
            # Fallback for new create
            base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            target_path = os.path.join(base_dir, "src", "json", "rules.json")
            
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=4)
            return True
        except Exception as e:
            from ...core import logger
            logger.error(f"Failed to save rules.json: {e}")
            return False

    def _resolve_rules_path(self) -> str:
        """Determine where rules.json lives. Canonical location: src/json/rules.json"""
        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        path = os.path.join(base_dir, "src", "json", "rules.json")
        if os.path.exists(path):
            return path
        return None

    def _load_rules(self) -> dict:
        """Load external rules from JSON."""
        import json
        
        path = self._resolve_rules_path()
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load rules.json at {path}: {e}")
        return {}



    def check_conflict(self, target_path: str) -> bool:
        """
        Returns True if target_path exists on disk.
        """
        return os.path.exists(target_path)

    def rename_song(self, song, target_path: str = None) -> tuple[bool, str]:
        """
        Executes the move. Returns (Success, Error Message).
        """
        if not target_path:
            target_path = self.calculate_target_path(song)

        # 1. Validate Constraints
        if self.check_conflict(target_path):
            return False, f"Destination already exists: {os.path.basename(target_path)}"
            
        # Extension Check check to ensure we don't do something weird
        
        try:
            from ...core.vfs import VFS
            
            # CASE A: Virtual File (Extract)
            if VFS.is_virtual(song.path):
                # 1. Ensure target directory
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # 2. Extract content (Copy)
                content = VFS.read_bytes(song.path)
                with open(target_path, 'wb') as f:
                    f.write(content)
                    
                # 3. Update Model (Link Broken)
                # Note: We do NOT delete from ZIP (expensive/risky). 
                # We leave the artifact and let Cleanup Logic handle the ZIP deletion if empty.
                song.path = target_path
                return True, None

            # CASE B: Physical File (Move)
            # Ensure source exists
            if not song.path or not os.path.exists(song.path):
                return False, f"Source file not found: {song.path}"

            # 2. Create parent directories
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # 3. Move
            shutil.move(song.path, target_path)
            
            # 4. Update Model (Caller must persist to DB)
            song.path = target_path
            return True, None
            
        except (OSError, shutil.Error, Exception) as e:
            from src.core import logger
            logger.error(f"Rename Error during file move: {e}")
            return False, f"System Error: {str(e)}"

    def _sanitize(self, component: str) -> str:
        """Internal helper to strip bad chars."""
        # Windows strict + Linux safe
        # < > : " / \ | ? *
        if not component: return ""
        bad_chars = '<>:"/\\|?*'
        clean = "".join(c for c in component if c not in bad_chars)
        # Strip trailing dots/spaces (Windows hates 'Folder. ')
        return clean.strip().strip('.')
