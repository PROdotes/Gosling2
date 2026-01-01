"""
Level 1 Logic Tests for Artist Manager Dialogs.
Per TESTING.md: Tests the happy path and polite failures.
"""
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox

from src.presentation.dialogs.artist_manager_dialog import (
    ArtistCreatorDialog,
    ArtistPickerDialog,
    ArtistDetailsDialog
)
from src.data.models.contributor import Contributor


class TestArtistCreatorDialog:
    """Tests for the quick artist creation dialog."""

    def test_initialization(self, qtbot):
        """Test dialog initializes with empty fields."""
        dialog = ArtistCreatorDialog()
        qtbot.addWidget(dialog)
        
        assert dialog.inp_name.text() == ""
        assert dialog.windowTitle() == "New Artist"

    def test_initialization_with_name(self, qtbot):
        """Test dialog initializes with pre-filled name."""
        dialog = ArtistCreatorDialog(initial_name="John Doe")
        qtbot.addWidget(dialog)
        
        assert dialog.inp_name.text() == "John Doe"

    def test_get_data_person(self, qtbot):
        """Test getting data with Person type selected."""
        dialog = ArtistCreatorDialog()
        qtbot.addWidget(dialog)
        
        dialog.inp_name.setText("Solo Artist")
        dialog.radio_person.setChecked(True)
        
        name, artist_type = dialog.get_data()
        
        assert name == "Solo Artist"
        assert artist_type == "person"

    def test_get_data_group(self, qtbot):
        """Test getting data with Group type selected."""
        dialog = ArtistCreatorDialog()
        qtbot.addWidget(dialog)
        
        dialog.inp_name.setText("The Band")
        dialog.radio_group.setChecked(True)
        
        name, artist_type = dialog.get_data()
        
        assert name == "The Band"
        assert artist_type == "group"

    def test_default_type_is_person(self, qtbot):
        """Test that Person is the default type selection."""
        dialog = ArtistCreatorDialog()
        qtbot.addWidget(dialog)
        
        assert dialog.radio_person.isChecked()
        assert not dialog.radio_group.isChecked()


class TestArtistPickerDialog:
    """Tests for the artist selection dialog."""

    @pytest.fixture
    def mock_repo(self):
        """Mock contributor repository."""
        repo = MagicMock()
        # search is called in _populate, not get_all
        mock_artists = [
            MagicMock(contributor_id=1, name="Artist One", type="person"),
            MagicMock(contributor_id=2, name="Band Two", type="group"),
            MagicMock(contributor_id=3, name="Artist Three", type="person"),
        ]
        repo.search.return_value = mock_artists
        return repo

    def test_initialization(self, qtbot, mock_repo):
        """Test picker initializes and populates list."""
        dialog = ArtistPickerDialog(repo=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.windowTitle() == "Select Artist"
        # search("") is called in _populate
        mock_repo.search.assert_called_once_with("")

    def test_filter_by_type(self, qtbot, mock_repo):
        """Test picker can filter by artist type."""
        dialog = ArtistPickerDialog(repo=mock_repo, filter_type="person")
        qtbot.addWidget(dialog)
        
        # The repo.search is called; filtering happens client-side
        assert dialog.filter_type == "person"

    def test_exclude_ids(self, qtbot, mock_repo):
        """Test picker excludes specified IDs."""
        exclude = {1, 2}
        dialog = ArtistPickerDialog(repo=mock_repo, exclude_ids=exclude)
        qtbot.addWidget(dialog)
        
        assert dialog.exclude_ids == exclude

    def test_get_selected_returns_none_before_selection(self, qtbot, mock_repo):
        """Test get_selected returns None when nothing selected."""
        dialog = ArtistPickerDialog(repo=mock_repo)
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
        dialog = ArtistDetailsDialog(artist=mock_artist, repo=mock_repo)
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
        
        dialog = ArtistDetailsDialog(artist=group_artist, repo=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.txt_name.text() == "The Band"
        assert dialog.radio_group.isChecked()
        assert dialog.lbl_member.text() == "GROUP MEMBERS"

    def test_add_alias(self, qtbot, mock_artist, mock_repo):
        """Test adding an alias to artist."""
        dialog = ArtistDetailsDialog(artist=mock_artist, repo=mock_repo)
        qtbot.addWidget(dialog)
        
        # Mock the ArtistCreatorDialog to return name without showing
        with patch('src.presentation.dialogs.artist_manager_dialog.ArtistCreatorDialog') as MockCreator:
            mock_dlg = MagicMock()
            mock_dlg.exec.return_value = True
            mock_dlg.get_data.return_value = ("Stage Name", "person")
            MockCreator.return_value = mock_dlg
            
            # Mock validation to pass
            mock_repo.validate_identity.return_value = (False, "")
            
            dialog._add_alias()
        
        mock_repo.add_alias.assert_called_once()

    def test_add_alias_cancelled(self, qtbot, mock_artist, mock_repo):
        """Test cancelling alias addition."""
        dialog = ArtistDetailsDialog(artist=mock_artist, repo=mock_repo)
        qtbot.addWidget(dialog)
        
        # Mock the ArtistCreatorDialog to simulate cancel
        with patch('src.presentation.dialogs.artist_manager_dialog.ArtistCreatorDialog') as MockCreator:
            mock_dlg = MagicMock()
            mock_dlg.exec.return_value = False  # User cancelled
            MockCreator.return_value = mock_dlg
            
            dialog._add_alias()
        
        mock_repo.add_alias.assert_not_called()

    def test_save_updates_name(self, qtbot, mock_artist, mock_repo):
        """Test saving updates the artist name."""
        dialog = ArtistDetailsDialog(artist=mock_artist, repo=mock_repo)
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
        dialog = ArtistDetailsDialog(artist=mock_artist, repo=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.lbl_member.text() == "BELONGS TO GROUPS"
