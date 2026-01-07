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
    def link(self, child_id: int, **kwargs) -> bool:
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
        get_value_fn: Callable[[int, str, Any], Any] = None,
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
        self._get_value = get_value_fn
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

    def link(self, child_id: int, **kwargs) -> bool:
        """Add entity to field for all selected songs."""
        if not self.songs:
            return False
        
        entity = self.service.get_by_id(child_id)
        if not entity:
            return False
        
        name = self._get_entity_name(entity)
        
        for song in self.songs:
            # Get current value (prioritize staging)
            if self._get_value:
                current = self._get_value(song.source_id, self.field_name, getattr(song, self.field_name, []))
            else:
                current = getattr(song, self.field_name, [])
            
            if not isinstance(current, list):
                current = [current] if current else []
            
            if name not in current:
                new_list = current + [name]
                if self._stage_change:
                    # Differential Stage if supported by callback
                    if hasattr(self._stage_change, '__code__') and 'song_id' in self._stage_change.__code__.co_varnames:
                        self._stage_change(self.field_name, new_list, song_id=song.source_id)
                    else:
                        self._stage_change(self.field_name, new_list)
                    
                    # Sync album_id if adding an album
                    if self.field_name == 'album':
                        curr_ids = self._get_value(song.source_id, 'album_id', getattr(song, 'album_id', [])) if self._get_value else getattr(song, 'album_id', [])
                        if isinstance(curr_ids, int): curr_ids = [curr_ids]
                        if not curr_ids: curr_ids = []
                        
                        if child_id not in curr_ids:
                             new_ids = curr_ids + [child_id]
                             if hasattr(self._stage_change, '__code__') and 'song_id' in self._stage_change.__code__.co_varnames:
                                 self._stage_change('album_id', new_ids, song_id=song.source_id)
                             else:
                                 self._stage_change('album_id', new_ids)
        
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
        
        for song in self.songs:
            # Get current value (prioritize staging)
            if self._get_value:
                current = self._get_value(song.source_id, self.field_name, getattr(song, self.field_name, []))
            else:
                current = getattr(song, self.field_name, [])
                 
            if not isinstance(current, list):
                current = [current] if current else []
            
            new_list = [p for p in current if p != name]
            if self._stage_change:
                # Differential Stage if supported by callback
                if hasattr(self._stage_change, '__code__') and 'song_id' in self._stage_change.__code__.co_varnames:
                    self._stage_change(self.field_name, new_list, song_id=song.source_id)
                else:
                    self._stage_change(self.field_name, new_list)
                
                # Sync album_id if removing an album
                if self.field_name == 'album':
                    curr_ids = self._get_value(song.source_id, 'album_id', getattr(song, 'album_id', [])) if self._get_value else getattr(song, 'album_id', [])
                    if isinstance(curr_ids, int): curr_ids = [curr_ids]
                    if not curr_ids: curr_ids = []
                    
                    if child_id in curr_ids:
                        new_ids = [x for x in curr_ids if x != child_id]
                        final_ids = new_ids if len(new_ids) > 1 else (new_ids[0] if new_ids else None)
                        if hasattr(self._stage_change, '__code__') and 'song_id' in self._stage_change.__code__.co_varnames:
                            self._stage_change('album_id', final_ids, song_id=song.source_id)
                        else:
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
        if self.field_name == 'tags' and hasattr(entity, 'tag_name'):
             # Special Case: Unified tag format for internal logic (Category:Name)
             cat = getattr(entity, 'category', 'Genre') # Default to Genre if None
             return f"{cat}:{entity.tag_name}"
             
        for attr in ['name', 'title', 'publisher_name', 'album_title', 'tag_name']:
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
    
    def link(self, child_id: int, **kwargs) -> bool:
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
    
    def link(self, child_id: int, **kwargs) -> bool:
        """Add member to group (or group to person)."""
        alias_name = kwargs.get('matched_alias')
        alias_id = None
        
        if alias_name:
            # Resolve Alias Name to ID for the target contributor
            aliases = self.service.get_aliases(child_id)
            for a_id, a_name in aliases:
                if a_name.lower() == alias_name.lower():
                    alias_id = a_id
                    break

        if self.artist.type == "group":
            self.service.add_member(self.artist.contributor_id, child_id, member_alias_id=alias_id)
        else:
            self.service.add_member(child_id, self.artist.contributor_id) # Reverse direction
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
    
    def link(self, child_id: int, **kwargs) -> bool:
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
        if not self.album:
            return []
        
        # If we have staged changes, use them
        if hasattr(self.album, '_staged_contributors'):
            return [c.contributor_id for c in self.album._staged_contributors]

        if not self.album.album_id:
            return []
        
        # M2M support via repository fallback (if no staged)
        from src.data.repositories.album_repository import AlbumRepository
        repo = AlbumRepository()
        contributors = repo.get_contributors_for_album(self.album.album_id)
        return [c.contributor_id for c in contributors]
    
    def get_child_data(self) -> List[tuple]:
        if not self.album:
            return []
            
        contributors = []
        if hasattr(self.album, '_staged_contributors'):
            contributors = self.album._staged_contributors
        elif self.album.album_id:
            from src.data.repositories.album_repository import AlbumRepository
            repo = AlbumRepository()
            contributors = repo.get_contributors_for_album(self.album.album_id)
        
        results = []
        seen_ids = set()
        for c in contributors:
            if c.contributor_id in seen_ids:
                continue
            seen_ids.add(c.contributor_id)
            icon = "👤" if c.type == "person" else "👥"
            results.append((c.contributor_id, c.name, icon, False, False, "", "amber", False))
        return results
    
    def link(self, child_id: int, **kwargs) -> bool:
        if not self.album:
            return False
            
        contributor = self.service.get_by_id(child_id)
        if not contributor:
            return False

        # If we have a staging function, use it
        if self._stage_change:
            current = []
            if hasattr(self.album, '_staged_contributors'):
                current = self.album._staged_contributors
            elif self.album.album_id:
                from src.data.repositories.album_repository import AlbumRepository
                current = AlbumRepository().get_contributors_for_album(self.album.album_id)
            
            if child_id not in [c.contributor_id for c in current]:
                new_list = current + [contributor]
                self._stage_change('contributors', new_list)
                self.album._staged_contributors = new_list
                self.on_data_changed()
                return True
            return False

        # Immediate Save (Legacy)
        if not self.album.album_id:
            return False
            
        from src.data.repositories.album_repository import AlbumRepository
        repo = AlbumRepository()
        success = repo.add_contributor_to_album(self.album.album_id, child_id)
        
        if success:
            self.on_data_changed()
        return success
    
    def unlink(self, child_id: int) -> bool:
        if not self.album:
            return False
            
        # If we have a staging function, use it
        if self._stage_change:
            current = []
            if hasattr(self.album, '_staged_contributors'):
                current = self.album._staged_contributors
            elif self.album.album_id:
                from src.data.repositories.album_repository import AlbumRepository
                current = AlbumRepository().get_contributors_for_album(self.album.album_id)
            
            new_list = [c for c in current if c.contributor_id != child_id]
            self._stage_change('contributors', new_list)
            self.album._staged_contributors = new_list
            self.on_data_changed()
            return True

        # Immediate Save (Legacy)
        if not self.album.album_id:
            return False
            
        from src.data.repositories.album_repository import AlbumRepository
        repo = AlbumRepository()
        success = repo.remove_contributor_from_album(self.album.album_id, child_id)
        
        if success:
            self.on_data_changed()
        return success
    
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
        if not self.album:
            return []
        
        # If we have staged changes, use them
        if hasattr(self.album, '_staged_publishers'):
            return [p.publisher_id for p in self.album._staged_publishers]

        if not self.album.album_id:
            return []
        
        from src.data.repositories.album_repository import AlbumRepository
        repo = AlbumRepository()
        publishers = repo.get_publishers_for_album(self.album.album_id)
        return [p.publisher_id for p in publishers]
    
    def get_child_data(self) -> List[tuple]:
        if not self.album:
            return []
            
        publishers = []
        if hasattr(self.album, '_staged_publishers'):
            publishers = self.album._staged_publishers
        elif self.album.album_id:
            from src.data.repositories.album_repository import AlbumRepository
            repo = AlbumRepository()
            publishers = repo.get_publishers_for_album(self.album.album_id)
        
        results = []
        seen_ids = set()
        for p in publishers:
            if p.publisher_id in seen_ids:
                continue
            seen_ids.add(p.publisher_id)
            results.append((p.publisher_id, p.publisher_name, "🏢", False, False, "", "amber", False))
        return results
    
    def link(self, child_id: int, **kwargs) -> bool:
        if not self.album:
            return False
            
        pub = self.service.get_by_id(child_id)
        if not pub: return False

        # If we have a staging function, use it
        if self._stage_change:
            current = []
            if hasattr(self.album, '_staged_publishers'):
                current = self.album._staged_publishers
            elif self.album.album_id:
                from src.data.repositories.album_repository import AlbumRepository
                current = AlbumRepository().get_publishers_for_album(self.album.album_id)
            
            if child_id not in [p.publisher_id for p in current]:
                new_list = current + [pub]
                self._stage_change('publishers', new_list)
                self.album._staged_publishers = new_list
                self.on_data_changed()
                return True
            return False

        # Immediate Save (Legacy)
        if not self.album.album_id:
            return False
            
        from src.data.repositories.album_repository import AlbumRepository
        repo = AlbumRepository()
        success = repo.add_publisher_to_album(self.album.album_id, pub.publisher_name)
        
        if success:
            self.on_data_changed()
        return success
    
    def unlink(self, child_id: int) -> bool:
        if not self.album:
            return False
            
        # If we have a staging function, use it
        if self._stage_change:
            current = []
            if hasattr(self.album, '_staged_publishers'):
                current = self.album._staged_publishers
            elif self.album.album_id:
                from src.data.repositories.album_repository import AlbumRepository
                current = AlbumRepository().get_publishers_for_album(self.album.album_id)
            
            new_list = [p for p in current if p.publisher_id != child_id]
            self._stage_change('publishers', new_list)
            self.album._staged_publishers = new_list
            self.on_data_changed()
            return True

        # Immediate Save (Legacy)
        if not self.album.album_id:
            return False
            
        from src.data.repositories.album_repository import AlbumRepository
        repo = AlbumRepository()
        success = repo.remove_publisher_from_album(self.album.album_id, child_id)
        
        if success:
            self.on_data_changed()
        return success
    
    def get_parent_for_dialog(self) -> Any:
        return self.album
    
    def on_data_changed(self):
        if self._refresh:
            self._refresh()
