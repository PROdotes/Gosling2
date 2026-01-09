
import os
import zipfile
import io
from typing import Optional, Tuple, List

class VFS:
    """
    T-90: Virtual File System
    Simplifies access to files inside ZIP archives using the 'piped' syntax:
    'C:/Path/To/Archive.zip|Internal/Path/Song.mp3'
    """
    
    SEPARATOR = "|"

    @classmethod
    def is_virtual(cls, path: str) -> bool:
        """Check if the path refers to a file inside an archive."""
        return cls.SEPARATOR in path

    @classmethod
    def split_path(cls, path: str) -> Tuple[str, str]:
        """Split a virtual path into (archive_path, member_path)."""
        if cls.SEPARATOR in path:
            return path.split(cls.SEPARATOR, 1)
        return path, ""

    @classmethod
    def read_bytes(cls, path: str) -> bytes:
        """Read the raw bytes of a file (physical or virtual)."""
        if cls.is_virtual(path):
            zip_path, member_path = cls.split_path(path)
            with zipfile.ZipFile(zip_path, 'r') as zr:
                try:
                    with zr.open(member_path) as f:
                        return f.read()
                except KeyError:
                    # Case-insensitive fallback
                    # ZIP paths use forward slashes strictly
                    target = member_path.replace('\\', '/').lower()
                    for name in zr.namelist():
                        if name.lower() == target:
                            with zr.open(name) as f:
                                return f.read()
                    raise
        else:
            with open(path, 'rb') as f:
                return f.read()

    @classmethod
    def get_stream(cls, path: str) -> io.BytesIO:
        """Get a file-like stream for a path (physical or virtual)."""
        return io.BytesIO(cls.read_bytes(path))

    @classmethod
    def list_zip_contents(cls, zip_path: str, audio_only: bool = True) -> List[str]:
        """Return a list of virtual paths for all (audio) members in a ZIP."""
        if not os.path.exists(zip_path) or not zipfile.is_zipfile(zip_path):
            return []
            
        audio_exts = ('.mp3', '.wav')
        virtual_paths = []
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zr:
                for name in zr.namelist():
                    # Skip directories
                    if name.endswith('/'): continue
                    
                    if not audio_only or name.lower().endswith(audio_exts):
                        virtual_paths.append(f"{zip_path}{cls.SEPARATOR}{name}")
        except Exception:
            pass
            
        return virtual_paths
            
    @classmethod
    def get_physical_member_count(cls, zip_path: str) -> int:
        """Count total files inside the ZIP (ignoring directories)."""
        if not os.path.exists(zip_path) or not zipfile.is_zipfile(zip_path):
            return 0
        try:
            with zipfile.ZipFile(zip_path, 'r') as zr:
                # Count files (not dirs ending in /)
                return sum(1 for name in zr.namelist() if not name.endswith('/'))
        except Exception:
            return 0
