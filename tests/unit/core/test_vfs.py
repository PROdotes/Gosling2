import os
import tempfile
import zipfile
from unittest.mock import patch
import pytest
from src.core.vfs import VFS


class TestVFSLogic:
    """Level 1: Logic tests for VFS functionality (Happy Path & Basic Errors)"""

    @pytest.fixture
    def sample_zip(self):
        """Create a temporary ZIP file with test content."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            zip_path = tmp.name

        try:
            with zipfile.ZipFile(zip_path, 'w') as zf:
                # Add some test files
                zf.writestr('song1.mp3', b'fake mp3 data')
                zf.writestr('cover.jpg', b'fake image data')
                zf.writestr('info.nfo', b'fake nfo data')
                zf.writestr('readme.txt', b'fake readme data')
                # Add a directory (should be excluded)
                zf.writestr('nested/file.dat', b'nested file')
                zf.writestr('nested/', b'')  # Empty directory entry

            yield zip_path
        finally:
            if os.path.exists(zip_path):
                os.unlink(zip_path)

    def test_get_physical_members_normal_zip(self, sample_zip):
        """Test get_physical_members returns all files in a normal ZIP."""
        members = VFS.get_physical_members(sample_zip)

        expected = ['song1.mp3', 'cover.jpg', 'info.nfo', 'readme.txt', 'nested/file.dat']
        assert sorted(members) == sorted(expected)

    def test_get_physical_members_empty_zip(self):
        """Test get_physical_members with empty ZIP file."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            empty_zip = tmp.name

        try:
            # Create empty ZIP
            with zipfile.ZipFile(empty_zip, 'w'):
                pass

            members = VFS.get_physical_members(empty_zip)
            assert members == []
        finally:
            if os.path.exists(empty_zip):
                os.unlink(empty_zip)

    def test_get_physical_members_nonexistent_file(self):
        """Test get_physical_members with non-existent file."""
        members = VFS.get_physical_members('/nonexistent/file.zip')
        assert members == []

    def test_get_physical_members_not_a_zip(self):
        """Test get_physical_members with a file that's not a ZIP."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            txt_path = tmp.name

        try:
            with open(txt_path, 'w') as f:
                f.write('not a zip file')

            members = VFS.get_physical_members(txt_path)
            assert members == []
        finally:
            if os.path.exists(txt_path):
                os.unlink(txt_path)

    def test_get_physical_members_corrupt_zip(self):
        """Test get_physical_members with corrupt ZIP file."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            corrupt_zip = tmp.name

        try:
            # Write some garbage data
            with open(corrupt_zip, 'wb') as f:
                f.write(b'this is not a valid zip file')

            members = VFS.get_physical_members(corrupt_zip)
            assert members == []
        finally:
            if os.path.exists(corrupt_zip):
                os.unlink(corrupt_zip)

    def test_get_physical_members_excludes_directories(self, sample_zip):
        """Test get_physical_members excludes directory entries."""
        # Add a directory entry to the ZIP
        with zipfile.ZipFile(sample_zip, 'a') as zf:
            zf.writestr('another_dir/', b'')  # Directory entry

        members = VFS.get_physical_members(sample_zip)
        # Should not include 'another_dir/' or 'nested/'
        assert 'another_dir/' not in members
        assert 'nested/' not in members
        assert 'nested/file.dat' in members  # But should include files in directories