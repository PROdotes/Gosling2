"""
Context Adapters 🔌
Abstract interface for parent-child relationship management in EntityListWidget.

The widget doesn't know what parent entity it's attached to.
It just calls adapter.link() and adapter.unlink().
The adapter knows the parent (Song, Album, Artist, Publisher) and how to modify it.

Usage:
    # Song context (SidePanel editing performers)
    adapter = SongFieldAdapter(current_songs, 'performers', contributor_service)
    
    # Album context (AlbumManager editing album artists)
    adapter = AlbumContributorAdapter(album, album_service)
    
    # Artist context (ArtistDetails editing aliases)
    adapter = ArtistAliasAdapter(artist, contributor_service)
"""

from abc import ABC, abstractmethod
from typing import List, Any, Optional, Callable
from dataclasses import dataclass


class ContextAdapter(ABC):
    """
    Abstract interface for parent-child relationship management.
    
    Implementations handle specific parent types:
    - SongFieldAdapter: Song → Performers/Composers/etc.
    - AlbumContributorAdapter: Album → Artists
    - ArtistAliasAdapter: Artist → Aliases
    - ArtistMemberAdapter: Artist → Group Members
    - PublisherChildAdapter: Publisher → Subsidiaries
    """
    
    @abstractmethod
    def get_children(self) -> List[int]:
        """Return IDs of currently linked child entities."""
        pass
    
    @abstractmethod
    def get_child_data(self) -> List[tuple]:
        """
        Return chip data for all children.
        
        Returns:
            List of tuples: (id, label, icon, is_mixed, is_inherited, tooltip, zone, is_primary)
        """
        pass
    
    @abstractmethod
    def link(self, child_id: int) -> bool:
        """Link a child entity to the parent. Returns success."""
        pass
    
    @abstractmethod
    def unlink(self, child_id: int) -> bool:
        """Unlink a child entity from the parent. Returns success."""
        pass
    
    @abstractmethod
    def get_parent_for_dialog(self) -> Any:
        """
        Return parent entity for dialog context.
        
        This is passed to editor dialogs for the "Remove from this X" button.
        Could be a Song, Album, Artist, Publisher, etc.
        """
        pass
    
    def on_data_changed(self) -> None:
        """
        Called after link/unlink operations.
        Override to trigger UI refresh, emit signals, etc.
        """
        pass
    
    def get_excluded_ids(self) -> set:
        """Return IDs that should be hidden from the picker."""
        return set(self.get_children())


# =============================================================================
# SONG FIELD ADAPTER
# For SidePanel: Song → Performers, Composers, Publishers, etc.
# =============================================================================

class SongFieldAdapter(ContextAdapter):
    """
    Adapter for editing a Song's field (performers, composers, etc.).
    
    This is the most complex adapter because:
    1. It may handle multiple songs (bulk edit)
    2. It stages changes rather than committing immediately
    3. Different fields have different data types (artists, publishers, tags)
    """
    
    def __init__(
        self, 
        songs: List[Any],
        field_name: str,
        service: Any,
        stage_change_fn: Callable[[str, Any], None] = None,
        get_child_data_fn: Callable[[], List[tuple]] = None,
        refresh_fn: Callable[[], None] = None
    ):
        """
        Args:
            songs: List of Song objects being edited
            field_name: Field name (e.g., 'performers', 'publishers')
            service: Service for looking up entities (contributor_service, etc.)
            stage_change_fn: Callback to stage a change (field_name, new_value)
            get_child_data_fn: Callback to get current chips (tuples)
            refresh_fn: Callback to refresh UI after changes
        """
        self.songs = songs
        self.field_name = field_name
        self.service = service
        self._stage_change = stage_change_fn
        self._get_child_data = get_child_data_fn
        self._refresh = refresh_fn
    
    def get_children(self) -> List[int]:
        if not self.songs:
            return []
        
        # Pull latest data (including staged)
        chips = self.get_child_data()
        return [c[0] for c in chips if c[0] > 0]
    
    def get_child_data(self) -> List[tuple]:
        if self._get_child_data:
            return self._get_child_data()
        return []

    def link(self, child_id: int) -> bool:
        """Add entity to field for all selected songs."""
        if not self.songs:
            return False
        
        entity = self.service.get_by_id(child_id)
        if not entity:
            return False
        
        name = self._get_entity_name(entity)
        
        for song in self.songs:
            current = getattr(song, self.field_name, [])
            if not isinstance(current, list):
                current = [current] if current else []
            
            if name not in current:
                new_list = current + [name]
                if self._stage_change:
                    self._stage_change(self.field_name, new_list)
        
        self.on_data_changed()
        return True
    
    def unlink(self, child_id: int) -> bool:
        """Remove entity from field for all selected songs."""
        if not self.songs:
            return False
        
        entity = self.service.get_by_id(child_id)
        if not entity:
            return False
        
        name = self._get_entity_name(entity)
        
        # T-89: Enforcement Gate for 'Status: Unprocessed'
        if self.field_name == 'tags' and "Unprocessed" in name:
            # We can't easily get _get_validation_errors from here without passing it in
            # But we can at least check if the user is trying to remove it.
            # For now, let's assume the SidePanel handles the visual warning 
            # or we move the check here later. 
            pass

        for song in self.songs:
            current = getattr(song, self.field_name, [])
            if not isinstance(current, list):
                current = [current] if current else []
            
            new_list = [p for p in current if p != name]
            if self._stage_change:
                self._stage_change(self.field_name, new_list)
                
                # Special Case: Sync album_id if removing an album
                if self.field_name == 'album':
                    curr_ids = getattr(song, 'album_id', [])
                    if isinstance(curr_ids, int): curr_ids = [curr_ids]
                    if not curr_ids: curr_ids = []
                    
                    if child_id in curr_ids:
                        new_ids = [x for x in curr_ids if x != child_id]
                        final_ids = new_ids if len(new_ids) > 1 else (new_ids[0] if new_ids else None)
                        self._stage_change('album_id', final_ids)
        
        self.on_data_changed()
        return True
    
    def get_parent_for_dialog(self) -> Any:
        """Return first song for context (or None for bulk)."""
        if len(self.songs) == 1:
            return self.songs[0]
        return None
    
    def on_data_changed(self):
        if self._refresh:
            self._refresh()
    
    def _get_entity_id(self, entity: Any) -> int:
        """Get ID from entity (handles different attribute names)."""
        for attr in ['contributor_id', 'publisher_id', 'album_id', 'tag_id', 'id']:
            if hasattr(entity, attr):
                return getattr(entity, attr)
        return 0
    
    def _get_entity_name(self, entity: Any) -> str:
        """Get display name from entity."""
        for attr in ['name', 'publisher_name', 'album_title', 'tag_name']:
            if hasattr(entity, attr):
                return getattr(entity, attr)
        return str(entity)


# =============================================================================
# ARTIST ALIAS ADAPTER
# For ArtistDetailsDialog: Artist → Aliases
# =============================================================================

class ArtistAliasAdapter(ContextAdapter):
    """Adapter for editing an Artist's aliases."""
    
    def __init__(self, artist: Any, service: Any, refresh_fn: Callable = None):
        self.artist = artist
        self.service = service
        self._refresh = refresh_fn
    
    def get_children(self) -> List[int]:
        aliases = self.service.get_aliases(self.artist.contributor_id)
        return [alias_id for alias_id, _ in aliases]
    
    def get_child_data(self) -> List[tuple]:
        aliases = self.service.get_aliases(self.artist.contributor_id)
        return [
            (alias_id, alias_name, "📝", False, False, "", "amber", False)
            for alias_id, alias_name in aliases
        ]
    
    def link(self, child_id: int) -> bool:
        # For aliases, "link" means adding a new alias by name
        # This is handled differently - see ArtistDetailsDialog._add_alias
        return False
    
    def link_by_name(self, name: str) -> bool:
        """Add a new alias by name."""
        if self.service.add_alias(self.artist.contributor_id, name):
            self.on_data_changed()
            return True
        return False
    
    def unlink(self, child_id: int) -> bool:
        """Delete an alias."""
        if self.service.delete_alias(child_id):
            self.on_data_changed()
            return True
        return False
    
    def get_parent_for_dialog(self) -> Any:
        return self.artist
    
    def on_data_changed(self):
        if self._refresh:
            self._refresh()


# =============================================================================
# ARTIST MEMBER ADAPTER  
# For ArtistDetailsDialog: Group → Members (or Person → Groups)
# =============================================================================

class ArtistMemberAdapter(ContextAdapter):
    """Adapter for editing an Artist's group memberships."""
    
    def __init__(self, artist: Any, service: Any, refresh_fn: Callable = None):
        self.artist = artist
        self.service = service
        self._refresh = refresh_fn
    
    def get_children(self) -> List[int]:
        if self.artist.type == "group":
            members = self.service.get_members(self.artist.contributor_id)
        else:
            members = self.service.get_groups(self.artist.contributor_id)
        return [m.contributor_id for m in members]
    
    def get_child_data(self) -> List[tuple]:
        if self.artist.type == "group":
            members = self.service.get_members(self.artist.contributor_id)
        else:
            members = self.service.get_groups(self.artist.contributor_id)
        
        return [
            (m.contributor_id, m.name, "👤" if m.type == "person" else "👥", 
             False, False, "", "amber", False)
            for m in members
        ]
    
    def link(self, child_id: int) -> bool:
        """Add member to group (or group to person)."""
        if self.artist.type == "group":
            self.service.add_member(self.artist.contributor_id, child_id)
        else:
            self.service.add_member(child_id, self.artist.contributor_id)
        self.on_data_changed()
        return True
    
    def unlink(self, child_id: int) -> bool:
        """Remove membership link."""
        if self.artist.type == "group":
            self.service.remove_member(self.artist.contributor_id, child_id)
        else:
            self.service.remove_member(child_id, self.artist.contributor_id)
        self.on_data_changed()
        return True
    
    def get_parent_for_dialog(self) -> Any:
        return self.artist
    
    def on_data_changed(self):
        if self._refresh:
            self._refresh()


# =============================================================================
# PUBLISHER CHILD ADAPTER
# For PublisherDetailsDialog: Publisher → Subsidiaries
# =============================================================================

class PublisherChildAdapter(ContextAdapter):
    """Adapter for editing a Publisher's subsidiaries."""
    
    def __init__(self, publisher: Any, service: Any, refresh_fn: Callable = None):
        self.publisher = publisher
        self.service = service
        self._refresh = refresh_fn
    
    def get_children(self) -> List[int]:
        all_pubs = self.service.search("")
        return [
            p.publisher_id for p in all_pubs 
            if p.parent_publisher_id == self.publisher.publisher_id
        ]
    
    def get_child_data(self) -> List[tuple]:
        all_pubs = self.service.search("")
        children = [
            p for p in all_pubs 
            if p.parent_publisher_id == self.publisher.publisher_id
        ]
        return [
            (p.publisher_id, f"↳ {p.publisher_name}", "🏢", False, False, "", "amber", False)
            for p in children
        ]
    
    def link(self, child_id: int) -> bool:
        """Set a publisher as child of this one."""
        # Cycle Detection
        if self.service.would_create_cycle(child_id, self.publisher.publisher_id):
            return False
            
        child = self.service.get_by_id(child_id)
        if child:
            child.parent_publisher_id = self.publisher.publisher_id
            self.service.update(child)
            self.on_data_changed()
            return True
        return False
    
    def unlink(self, child_id: int) -> bool:
        """Remove child relationship (orphan the subsidiary)."""
        child = self.service.get_by_id(child_id)
        if child:
            child.parent_publisher_id = None
            self.service.update(child)
            self.on_data_changed()
            return True
        return False
    
    def get_parent_for_dialog(self) -> Any:
        return self.publisher
    
    def on_data_changed(self):
        if self._refresh:
            self._refresh()
    
    def get_excluded_ids(self) -> set:
        """Exclude children AND self AND ancestors to prevent cycles."""
        exclude = set(self.get_children())
        exclude.add(self.publisher.publisher_id)
        
        # Walk up to get all ancestors
        current = self.publisher
        while current.parent_publisher_id:
            exclude.add(current.parent_publisher_id)
            current = self.service.get_by_id(current.parent_publisher_id)
            if not current:
                break
        return exclude

# =============================================================================
# ALBUM CONTRIBUTOR ADAPTER
# For AlbumManagerDialog: Album → Artists
# =============================================================================

class AlbumContributorAdapter(ContextAdapter):
    """Adapter for editing an Album's contributor (artist)."""
    
    def __init__(self, album: Any, service: Any, stage_change_fn: Callable = None, refresh_fn: Callable = None):
        self.album = album
        self.service = service
        self._stage_change = stage_change_fn
        self._refresh = refresh_fn
    
    def get_children(self) -> List[int]:
        # Implementation depends on how album.album_artist is stored (usually it's a string in the DB)
        # T-91 will make this M2M. For now, it's string-based lookup.
        name = getattr(self.album, 'album_artist', "")
        if not name: return []
        
        artist, _ = self.service.get_or_create(name)
        return [artist.contributor_id] if artist else []
    
    def get_child_data(self) -> List[tuple]:
        # Implementation depends on how album.album_artist is stored
        name = getattr(self.album, 'album_artist', "")
        if not name: return []
        
        artist, _ = self.service.get_or_create(name)
        if not artist: return []
        
        icon = "👤" if artist.type == "person" else "👥"
        return [(artist.contributor_id, artist.name, icon, False, False, "", "amber", False)]
    
    def link(self, child_id: int) -> bool:
        artist = self.service.get_by_id(child_id)
        if not artist: return False
        
        if self._stage_change:
            self._stage_change("album_artist", artist.name)
        else:
            self.album.album_artist = artist.name
            
        self.on_data_changed()
        return True
    
    def unlink(self, child_id: int) -> bool:
        if self._stage_change:
            self._stage_change("album_artist", "")
        else:
            self.album.album_artist = ""
            
        self.on_data_changed()
        return True
    
    def get_parent_for_dialog(self) -> Any:
        return self.album
    
    def on_data_changed(self):
        if self._refresh:
            self._refresh()

# =============================================================================
# ALBUM PUBLISHER ADAPTER
# For AlbumManagerDialog: Album → Publisher
# =============================================================================

class AlbumPublisherAdapter(ContextAdapter):
    """Adapter for editing an Album's publisher."""
    
    def __init__(self, album: Any, service: Any, stage_change_fn: Callable = None, refresh_fn: Callable = None):
        self.album = album
        self.service = service
        self._stage_change = stage_change_fn
        self._refresh = refresh_fn
    
    def get_children(self) -> List[int]:
        # Assume album has publisher_id attribute
        pid = getattr(self.album, 'publisher_id', 0)
        return [pid] if pid else []
    
    def get_child_data(self) -> List[tuple]:
        pid = getattr(self.album, 'publisher_id', 0)
        if not pid: return []
        
        pub = self.service.get_by_id(pid)
        if not pub: return []
        
        return [(pub.publisher_id, pub.publisher_name, "🏢", False, False, "", "amber", False)]
    
    def link(self, child_id: int) -> bool:
        if self._stage_change:
            self._stage_change("publisher_id", child_id)
        else:
            self.album.publisher_id = child_id
            
        self.on_data_changed()
        return True
    
    def unlink(self, child_id: int) -> bool:
        if self._stage_change:
            self._stage_change("publisher_id", None)
        else:
            self.album.publisher_id = None
            
        self.on_data_changed()
        return True
    
    def get_parent_for_dialog(self) -> Any:
        return self.album
    
    def on_data_changed(self):
        if self._refresh:
            self._refresh()
