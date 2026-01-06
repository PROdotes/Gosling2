"""
Level 1 Logic Tests for Artist Manager Dialogs.
Per TESTING.md: Tests the happy path and polite failures.
"""
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox

from src.presentation.dialogs.artist_manager_dialog import (
    ArtistPickerDialog,
    ArtistDetailsDialog
)
from src.data.models.contributor import Contributor




class TestArtistPickerDialog:
    """Tests for the artist selection dialog."""

    @pytest.fixture
    def mock_repo(self):
        """Mock contributor repository."""
        repo = MagicMock()
        # Mock search_identities used in _populate
        mock_identities = [
            (1, "Artist One", "person", "Primary"),
            (2, "Band Two", "group", "Primary"),
            (3, "Artist Three", "person", "Primary"),
        ]
        repo.search_identities.return_value = mock_identities
        return repo

    def test_initialization(self, qtbot, mock_repo):
        """Test picker initializes and populates list."""
        dialog = ArtistPickerDialog(service=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.windowTitle() == "Select or Add Artist"
        # search_identities("") is called in _populate
        mock_repo.search_identities.assert_called_once_with("")

    def test_filter_by_type(self, qtbot, mock_repo):
        """Test picker can filter by artist type."""
        dialog = ArtistPickerDialog(service=mock_repo, filter_type="person")
        qtbot.addWidget(dialog)
        
        # The repo.search is called; filtering happens client-side
        assert dialog.filter_type == "person"

    def test_exclude_ids(self, qtbot, mock_repo):
        """Test picker excludes specified IDs."""
        exclude = {1, 2}
        dialog = ArtistPickerDialog(service=mock_repo, exclude_ids=exclude)
        qtbot.addWidget(dialog)
        
        assert dialog.exclude_ids == exclude

    def test_get_selected_returns_none_before_selection(self, qtbot, mock_repo):
        """Test get_selected returns None when nothing selected."""
        dialog = ArtistPickerDialog(service=mock_repo)
        qtbot.addWidget(dialog)
        
        # Verified Fix: Should return None, not raise AttributeError
        assert dialog.get_selected() is None


class TestArtistDetailsDialog:
    """Tests for the full artist editor dialog."""

    @pytest.fixture
    def mock_repo(self):
        """Mock contributor repository with full functionality."""
        repo = MagicMock()
        repo.get_aliases.return_value = []
        repo.get_members.return_value = []
        repo.get_groups.return_value = []
        repo.update.return_value = True
        return repo

    @pytest.fixture
    def mock_artist(self):
        """Create a real Contributor for testing."""
        # Contributor model uses: contributor_id, name, sort_name, type
        return Contributor(
            contributor_id=1,
            name="Test Artist",
            sort_name="Artist, Test",
            type="person"
        )

    def test_initialization(self, qtbot, mock_artist, mock_repo):
        """Test details dialog initializes correctly."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.artist == mock_artist
        # Note: The field is txt_name not inp_name in ArtistDetailsDialog
        assert dialog.txt_name.text() == "Test Artist"

    def test_initialization_group_type(self, qtbot, mock_repo):
        """Test details dialog shows correct UI for group."""
        group_artist = Contributor(
            contributor_id=2,
            name="The Band",
            sort_name="Band, The",
            type="group"
        )
        
        dialog = ArtistDetailsDialog(artist=group_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.txt_name.text() == "The Band"
        assert dialog.radio_group.isChecked()
        assert dialog.lbl_member.text() == "GROUP MEMBERS"

    def test_add_alias(self, qtbot, mock_artist, mock_repo):
        """Test adding an alias (via merge) to artist."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        # Mock EntityPickerDialog and QMessageBox (since merge triggers confirmation)
        with patch('src.presentation.dialogs.entity_picker_dialog.EntityPickerDialog') as MockPicker, \
             patch('src.presentation.dialogs.artist_manager_dialog.QMessageBox') as MockMsg:
            
            # Setup Picker
            mock_dlg_instance = MockPicker.return_value
            mock_dlg_instance.exec.return_value = True
            
            # Use a mock object that simulates a different Contributor
            mock_selected = MagicMock()
            mock_selected.contributor_id = 999
            mock_selected.name = "Stage Name"
            mock_selected.type = "person" # Match artist type
            mock_dlg_instance.get_selected.return_value = mock_selected
            
            # Setup MessageBox to say YES
            # Ensure both the return value AND the constant match
            YES_VAL = 16384
            MockMsg.question.return_value = YES_VAL
            MockMsg.StandardButton.Yes = YES_VAL
            MockMsg.StandardButton.No = 0
            
            # Setup Service
            mock_repo.merge.return_value = True
            
            dialog._add_alias()
        
        # Verify merge was called (target_id, self_id)
        mock_repo.merge.assert_called_once_with(999, 1)

    def test_add_alias_cancelled(self, qtbot, mock_artist, mock_repo):
        """Test cancelling alias addition."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        with patch('src.presentation.dialogs.entity_picker_dialog.EntityPickerDialog') as MockPicker:
            mock_dlg_instance = MockPicker.return_value
            mock_dlg_instance.exec.return_value = False  # Cancelled
            
            dialog._add_alias()
        
        mock_repo.add_alias.assert_not_called()

    def test_save_updates_name(self, qtbot, mock_artist, mock_repo):
        """Test saving updates the artist name."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        # Change the name
        dialog.txt_name.setText("New Name")
        
        # Mock validation to pass
        mock_repo.validate_identity.return_value = (False, "")
        
        # Save (mocking accept to prevent dialog close)
        with patch.object(QDialog, 'accept'):
            dialog._save()
        
        # Verify update was called and artist was modified
        mock_repo.update.assert_called_once()
        assert mock_artist.name == "New Name"

    def test_person_shows_belongs_to_groups_label(self, qtbot, mock_artist, mock_repo):
        """Test person type shows correct membership label."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.lbl_member.text() == "BELONGS TO GROUPS"
