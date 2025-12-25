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

    def _resolve_routing_rules(self, genre_clean: str, year_clean: str, filename: str) -> str:
        """
        Applies strict logic to determine folder structure.
        Inputs are already sanitized.
        """
        g_lower = genre_clean.lower()
        
        # Rule 1: Patriotic / Domoljubne -> Cro/Domoljubne
        # (Special case: Subgenre of Croatian)
        if g_lower in ["patriotic", "domoljubne"]:
            return os.path.join("Cro", "Domoljubne", filename)

        # Rule 2: Croatian Pop -> Cro/Year
        if g_lower == "cro pop":
            return os.path.join("Cro", year_clean, filename)

        # Rule 3: Pop -> Year only (Skip Genre folder)
        # "pop songs go only info year\file"
        if g_lower == "pop":
            return os.path.join(year_clean, filename)

        # Rule 4: Jazz -> Genre only (No Year)
        # "jazz goes into gemre\file"
        if g_lower == "jazz":
             return os.path.join(genre_clean, filename)
        
        # Default Rule: Genre/Year/File
        return os.path.join(genre_clean, year_clean, filename)

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
