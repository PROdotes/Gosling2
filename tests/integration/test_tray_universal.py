
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from src.presentation.widgets.side_panel_widget import SidePanelWidget
from src.presentation.dialogs.album_manager_dialog import AlbumManagerDialog
from src.presentation.dialogs.artist_manager_dialog import ArtistDetailsDialog
from src.presentation.dialogs.publisher_manager_dialog import PublisherDetailsDialog
from src.data.models.song import Song
from src.data.models.tag import Tag
from src.data.models.contributor import Contributor
from src.data.models.album import Album
from src.data.models.publisher import Publisher

@pytest.fixture
def mock_songs():
    s1 = Song(source_id=1, name="Song 1")
    s1.performers = ["Artist 1", "Artist 2"]
    s1.tags = ["Genre:Rock", "Mood:Happy"]
    s1.album = ["Album 1"]
    
    s2 = Song(source_id=2, name="Song 2")
    s2.performers = ["Artist 1", "Artist 3"]
    s2.tags = ["Genre:Rock", "Mood:Sad"]
    s2.album = ["Album 2"]
    
    return [s1, s2]

@pytest.fixture
def side_panel(qtbot, mock_widget_deps):
    deps = mock_widget_deps
    # Ensure tag service returns expected mock tags
    deps['library_service'].tag_service = MagicMock()
    deps['library_service'].tag_service.get_tags_for_source.side_effect = lambda sid: [
        Tag(101, "Rock", "Genre"), Tag(102, "Happy", "Mood")
    ] if sid == 1 else [
        Tag(101, "Rock", "Genre"), Tag(103, "Sad", "Mood")
    ]
    deps['library_service'].tag_service.find_by_name.side_effect = lambda n, c: {
        ("Rock", "Genre"): Tag(101, "Rock", "Genre"),
        ("Happy", "Mood"): Tag(102, "Happy", "Mood"),
        ("Sad", "Mood"): Tag(103, "Sad", "Mood")
    }.get((n, c))

    panel = SidePanelWidget(
        deps['library_service'],
        deps['metadata_service'],
        deps['settings_manager'],
        deps['renaming_service'],
        deps['duplicate_scanner']
    )
    qtbot.addWidget(panel)
    return panel

def test_side_panel_multi_edit_tray_logic(qtbot, side_panel, mock_songs):
    """VERIFY: Side Panel Tray handles multi-edit intersection and differential removal."""
    side_panel.set_songs(mock_songs)
    
    # 1. Verify Performers (Artists) Intersection
    artist_tray = side_panel._field_widgets['performers']
    # Common artist is "Artist 1"
    names = artist_tray.get_names()
    assert "Artist 1" in names
    assert "Artist 2" not in names
    
    # 2. Verify Tags Intersection
    tag_tray = side_panel._field_widgets['tags']
    # Common tag is "Genre: Rock"
    tag_names = tag_tray.get_names()
    assert any("Rock" in n for n in tag_names)
    assert not any("Happy" in n for n in tag_names)
    
    # Verify "Mixed" chip for tags
    # [ (101, 'Genre: Rock', ...), (-1, '1 Mixed', '🔀', ...) ]
    assert any("Mixed" in n for n in tag_names)

    # 3. Test Differential Removal (Artist)
    # Remove common "Artist 1" from both songs
    adapter = artist_tray.context_adapter
    # Mock contributor service to resolve "Artist 1" (ID 1)
    side_panel.contributor_service.get_by_id.return_value = Contributor(1, "Artist 1")
    
    adapter.unlink(1) # Unlink Artist 1
    
    # Verify Staging: S1 should have ["Artist 2"], S2 should have ["Artist 3"]
    assert side_panel._staged_changes[1]['performers'] == ["Artist 2"]
    assert side_panel._staged_changes[2]['performers'] == ["Artist 3"]
    
    # Verify tray reflected change (Artist 1 gone)
    assert "Artist 1" not in artist_tray.get_names()

    # 4. Test Differential Removal (Tag)
    # Remove common "Genre:Rock" (ID 101)
    tag_adapter = tag_tray.context_adapter
    side_panel.tag_service.get_by_id.return_value = Tag(101, "Rock", "Genre")
    
    tag_adapter.unlink(101)
    
    # Verify Staging: S1 should have ["Mood:Happy"], S2 should have ["Mood:Sad"]
    assert side_panel._staged_changes[1]['tags'] == ["Mood:Happy"]
    assert side_panel._staged_changes[2]['tags'] == ["Mood:Sad"]

def test_album_manager_tray_integration(qtbot, mock_widget_deps):
    """VERIFY: Album Manager uses the new unified trays and allows additions."""
    deps = mock_widget_deps
    album = Album(50, "Test Album", "Artist X", 2024, "Album")
    deps['library_service'].album_service.get_by_id.return_value = album
    
    # Mock contributor/publisher services
    contributor_service = deps['library_service'].contributor_service
    publisher_service = deps['library_service'].publisher_service
    album_service = deps['library_service'].album_service

    dialog = AlbumManagerDialog(album_service, publisher_service, contributor_service, initial_data={'album_id': 50})
    qtbot.addWidget(dialog)
    
    # Ensure trays are initialized
    assert dialog.tray_artist.allow_add is True
    assert dialog.tray_publisher.allow_add is True
    
    # Test Adding via Tray's internal button
    new_artist = Contributor(99, "New Artist")
    
    with patch('src.presentation.widgets.entity_list_widget.EntityClickRouter.open_picker', return_value=new_artist):
        # Trigger the add logic
        dialog.tray_artist._on_add_clicked()
        
    # Verify the artist was linked to the album and shown in tray
    assert "New Artist" in dialog.tray_artist.get_names()

def test_artist_details_alias_relay(qtbot, mock_widget_deps):
    """VERIFY: Artist Details uses chips for aliases and handles renaming/refresh."""
    deps = mock_widget_deps
    artist = Contributor(1, "Main Artist")
    service = deps['library_service'].contributor_service
    service.get_aliases.return_value = [Contributor(2, "Alias 1")]
    
    dialog = ArtistDetailsDialog(artist, service)
    qtbot.addWidget(dialog)
    
    # Verify alias tray (list_aliases)
    assert dialog.list_aliases.layout_mode.__class__.__name__ == 'LayoutMode' # Check it's CLOUD or STACK
    # ArtistDetails uses CLOUD for aliases now
    assert "Alias 1" in dialog.list_aliases.get_names()
    
    # Test unlinking
    with patch.object(service, 'unlink_alias', return_value=True):
         # Simulate unlinking ID 2
         dialog.list_aliases._do_remove(2)
         service.unlink_alias.assert_called_with(1, 2)

def test_publisher_details_subsidiary_chips(qtbot, mock_widget_deps):
    """VERIFY: Publisher Details uses chips for subsidiaries."""
    deps = mock_widget_deps
    pub = Publisher(1, "Big Label")
    service = deps['library_service'].publisher_service
    service.get_children.return_value = [Publisher(2, "Small Label")]
    
    dialog = PublisherDetailsDialog(pub, service)
    qtbot.addWidget(dialog)
    
    # Verify subsidiaries (list_children) uses chips
    assert "Small Label" in dialog.list_children.get_names()
    
    # Test adding subsidiary
    new_sub = Publisher(3, "Sub Label")
    with patch('src.presentation.widgets.entity_list_widget.EntityClickRouter.open_picker', return_value=new_sub):
        dialog.list_children._on_add_clicked()
        # Ensure service was called
        service.set_parent.assert_called_with(3, 1)
