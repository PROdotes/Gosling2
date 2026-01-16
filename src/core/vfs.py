
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

    @classmethod
    def update_file_in_zip(cls, virtual_path: str, new_data: bytes) -> bool:
        """
        Update a single file inside a ZIP archive.
        NOTE: ZIP structure is immutable. This creates a temporary ZIP, 
        copies all other files, replaces the target, and then overwrites the original.
        """
        if not cls.is_virtual(virtual_path):
            return False
            
        zip_path, member_path = cls.split_path(virtual_path)
        
        if not os.path.exists(zip_path):
            return False
            
        # Use a temp file for the rewrite
        temp_zip_path = zip_path + ".tmp"
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zin:
                with zipfile.ZipFile(temp_zip_path, 'w') as zout:
                    # Iterate through all items
                    # We need to find the specific member to replace
                    # Handle case-insensitive matching if needed (like read_bytes)
                    target_member = member_path
                    
                    found = False
                    # Check exact match first, then lenient
                    if target_member in zin.namelist():
                        found = True
                    else:
                        # Try to resolve case-insensitive
                        target_lower = target_member.replace('\\', '/').lower()
                        for name in zin.namelist():
                            if name.lower() == target_lower:
                                target_member = name
                                found = True
                                break
                    
                    for item in zin.infolist():
                        if found and item.filename == target_member:
                            # Write new data
                            zout.writestr(target_member, new_data)
                        else:
                            # Copy existing data
                            zout.writestr(item, zin.read(item.filename))
                            
            # Atomic Swap
            os.replace(temp_zip_path, zip_path)
            return True
            
        except Exception as e:
            from ..core import logger
            try:
                logger.error(f"VFS Update Failed for {virtual_path}: {e}")
            except:
                pass # Avoid circular imports if logger fails
                
            if os.path.exists(temp_zip_path):
                try: os.remove(temp_zip_path)
                except: pass
            return False

    @classmethod
    def update_file_in_zip(cls, virtual_path: str, new_data: bytes) -> bool:
        """
        Update a single file inside a ZIP archive.
        NOTE: ZIP structure is immutable. This creates a temporary ZIP, 
        copies all other files, replaces the target, and then overwrites the original.
        """
        if not cls.is_virtual(virtual_path):
            return False
            
        zip_path, member_path = cls.split_path(virtual_path)
        
        if not os.path.exists(zip_path):
            return False
            
        # Use a temp file for the rewrite
        temp_zip_path = zip_path + ".tmp"
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zin:
                with zipfile.ZipFile(temp_zip_path, 'w') as zout:
                    # Iterate through all items
                    # We need to find the specific member to replace
                    # Handle case-insensitive matching if needed (like read_bytes)
                    target_member = member_path
                    
                    found = False
                    # Check exact match first, then lenient
                    if target_member in zin.namelist():
                        found = True
                    else:
                        # Try to resolve case-insensitive
                        target_lower = target_member.replace('\\', '/').lower()
                        for name in zin.namelist():
                            if name.lower() == target_lower:
                                target_member = name
                                found = True
                                break
                    
                    for item in zin.infolist():
                        if found and item.filename == target_member:
                            # Write new data
                            zout.writestr(target_member, new_data)
                        else:
                            # Copy existing data
                            zout.writestr(item, zin.read(item.filename))
                            
            # Atomic Swap
            os.replace(temp_zip_path, zip_path)
            return True
            
        except Exception as e:
            from ..core import logger
            logger.error(f"VFS Update Failed for {virtual_path}: {e}")
            if os.path.exists(temp_zip_path):
                try: os.remove(temp_zip_path)
                except: pass
            return False
