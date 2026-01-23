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
    
    def set_primary(self, child_id: int) -> bool:
        """Promote a child entity to primary status. Returns success."""
        return False
    
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
        """Add entity to field for all selected songs (Immediate DB Write)."""
        if not self.songs:
            return False
        
        # T-92: IMMEDIATE WRITE MODE
        success_any = False
        
        # 1. Album (Specific)
        if self.field_name == 'album':
             for song in self.songs:
                 if self.service.set_primary_album(song.source_id, child_id):
                     success_any = True

        # 2. Tags (Specific)
        elif self.field_name == 'tags' and hasattr(self.service, 'add_tag_to_source'):
             for song in self.songs:
                 if self.service.add_tag_to_source(song.source_id, child_id):
                     success_any = True
                     
        # 3. Publisher
        elif hasattr(self.service, 'add_publisher_to_song') and self.field_name == 'publisher':
             for song in self.songs:
                 if self.service.add_publisher_to_song(song.source_id, child_id):
                     success_any = True
        
        # 4. Roles (Generic Fallback)
        elif hasattr(self.service, 'add_song_role'):
            # Dynamic Role Mapping
            role_map = {
                'performers': 'Performer',
                'composers': 'Composer',
                'producers': 'Producer',
                'remixers': 'Remixer',
                'lyricists': 'Lyricist',
                'arrangers': 'Arranger',
                'engineers': 'Engineer',
            }
            role = role_map.get(self.field_name, self.field_name[:-1].title() if self.field_name.endswith('s') else self.field_name.title())

            for song in self.songs:
                if self.service.add_song_role(song.source_id, child_id, role):
                    success_any = True

        # 5. Fallback: Generic Staging (Raw Text Fields)
        else:
             return self._legacy_link_staged(child_id, **kwargs)
        
        self.on_data_changed()
        return success_any

    def _legacy_link_staged(self, child_id, **kwargs):
        """Original Staging Logic (Preserved for text fields)."""
        entity = self.service.get_by_id(child_id)
        if not entity: return False
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
                     if hasattr(self._stage_change, '__code__') and 'song_id' in self._stage_change.__code__.co_varnames:
                         self._stage_change(self.field_name, new_list, song_id=song.source_id)
                     else:
                         self._stage_change(self.field_name, new_list)
        return True

    def _stage(self, song_id, field, value):
        """Helper for safe staging call."""
        if hasattr(self._stage_change, '__code__') and 'song_id' in self._stage_change.__code__.co_varnames:
             self._stage_change(field, value, song_id=song_id)
        else:
             self._stage_change(field, value)
    
    def unlink(self, child_id: int) -> bool:
        """Remove entity (Immediate DB Write)."""
        if child_id == -99:
            return False # Status chip is not removable via unlink logic
        if not self.songs: return False
        
        success_any = False
        
        # 1. Album
        if self.field_name == 'album':
             for song in self.songs:
                 if self.service.remove_song_from_album(song.source_id, child_id):
                     success_any = True

        # 2. Tags
        elif self.field_name == 'tags' and hasattr(self.service, 'remove_tag_from_source'):
             for song in self.songs:
                 if self.service.remove_tag_from_source(song.source_id, child_id):
                     success_any = True
        
        # 3. Publisher
        elif hasattr(self.service, 'remove_publisher_from_song') and self.field_name == 'publisher':
             for song in self.songs:
                 if self.service.remove_publisher_from_song(song.source_id, child_id):
                     success_any = True

        # 4. Roles
        elif hasattr(self.service, 'remove_song_role'):
            role_map = {
                'performers': 'Performer',
                'composers': 'Composer',
                'producers': 'Producer',
                'remixers': 'Remixer',
                'lyricists': 'Lyricist'
            }
            role = role_map.get(self.field_name, self.field_name[:-1].title() if self.field_name.endswith('s') else self.field_name.title())
            
            for song in self.songs:
                if self.service.remove_song_role(song.source_id, child_id, role):
                    success_any = True
                     
        # 5. Fallback
        else:
             return self._legacy_unlink_staged(child_id)
             
        self.on_data_changed()
        return success_any

    def _legacy_unlink_staged(self, child_id):
        entity = self.service.get_by_id(child_id)
        if not entity: return False
        name = self._get_entity_name(entity)
        
        for song in self.songs:
            if self._get_value:
                current = self._get_value(song.source_id, self.field_name, getattr(song, self.field_name, []))
            else:
                current = getattr(song, self.field_name, [])
                 
            if not isinstance(current, list):
                current = [current] if current else []
            
            new_list = [p for p in current if p != name]
            self._stage(song_id, self.field_name, new_list)
        return True
    
    def set_primary(self, child_id: int) -> bool:
        """Promote entity to primary status (Atomic Save)."""
        if not self.songs:
            return False

        success_any = False
        
        # 1. TAGS: Reorder within category
        if self.field_name == 'tags':
            # Immediate Save Mode (Atomic)
            # We target the specific category of the requested tag
            entity = self.service.get_by_id(child_id)
            if not entity or not hasattr(entity, 'category'):
                return False
                
            category = entity.category
            for song in self.songs:
                # 1. Fetch current tags for this specific category from DB (fresh)
                current_tags = self.service.get_tags_for_source(song.source_id, category)
                # 2. Reorder
                ordered_ids = [t.tag_id for t in current_tags]
                if child_id in ordered_ids:
                    ordered_ids.remove(child_id)
                ordered_ids.insert(0, child_id)
                
                # 3. Save Atomic (Bypassing staging)
                if self.service.set_tags(song.source_id, ordered_ids, category):
                    success_any = True
        
        # 2. ALBUM: Switch Primary Album
        elif self.field_name == 'album':
            if hasattr(self.service, 'set_primary_album'):
                for song in self.songs:
                    if self.service.set_primary_album(song.source_id, child_id):
                        success_any = True

        if success_any:
            self.on_data_changed()
            
        return success_any
    
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
        return [a.alias_id for a in aliases]
    
    def get_child_data(self) -> List[tuple]:
        aliases = self.service.get_aliases(self.artist.contributor_id)
        return [
            (a.alias_id, a.alias_name, "📝", False, False, "", "amber", False)
            for a in aliases if a.alias_name.lower() != self.artist.name.lower()
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
        """Unlink (Split) an alias into its own identity."""
        if self.service.unlink_alias(child_id):
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
    """Adapter for Member <-> Group relationships."""
    
    def __init__(self, artist: Any, service: Any, refresh_fn: Callable = None, parent: Any = None):
        self.artist = artist
        self.service = service
        self._refresh = refresh_fn
        self.parent = parent # For QDialogs
    
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
            aliases = self.service.get_aliases(child_id)
            for a in aliases:
                if a.alias_name.lower() == alias_name.lower():
                    alias_id = a.alias_id
                    break

        if self.artist.type == "group":
            self.service.add_member(self.artist.contributor_id, child_id, member_alias_id=alias_id)
        else:
            self.service.add_member(child_id, self.artist.contributor_id) # Reverse direction
            
        self.on_data_changed()
        return True
    
    def unlink(self, child_id: int) -> bool:
        """Remove membership link."""
        # Safety Check: If removing an ALIAS member, warn that it removes the Person.
        name_info = self.service.get_by_id(child_id) # child_id is NameID
        if name_info and self.parent: 
             # Is it an alias? (Name != Primary Name of Identity)
             # Wait, get_by_id returns Contributor object with 'name' being the resolved name for that ID.
             # We need to know if it's acting as an alias in THIS context.
             # But 'child_id' passed from EntityListWidget is the NameID we visualized (the Alias NameID).
             
             # If the NameID is NOT a Primary Name, it is an Alias.
             is_alias = False
             # We can check name_service or infer from type. 
             # Easier: Check if Name != Identity Primary Name
             # But get_by_id logic is complex.
             
             # Let's rely on the explicit warning:
             # "You are removing 'NAME'. If this is an alias, 'REAL PERSON' will be removed."
             
             pass

        if self.artist.type == "group":
            # Check if Aliased
            member = self.service.get_by_id(child_id)
            if member and self.parent:
                from PyQt6.QtWidgets import QMessageBox
                
                # Resolving identity to see who we are really deleting
                real_person = self.service.get_by_id(child_id) 
                # Note: get_by_id(AliasID) returns the Identity info but with Alias Name?
                # Let's use internal resolution to be sure
                
                # If the displayed name (from child_id) is NOT the primary name?
                # Actually, simpler:
                # If we are in "Aliases" mode? No, this is Members.
                
                # Only warn if it LOOKS like an alias?
                # Or just warn regardless? "Remove 'Name' from group?"
                # EntityListWidget logic is silent.
                # Let's be safe.
                
                msg = f"Remove '{member.name}' from '{self.artist.name}'?"
                if member.matched_alias: 
                     # If we fetched it via get_members, it might have matched_alias set?
                     # No, get_by_id(child_id) returns a fresh object.
                     pass

                # If the ID is an ALIAS ID, get_by_id returns the properties of that NameID.
                # If we want to check for "Shadow Removal", we should check if ChildID belongs to an Identity
                # that has a DIFFERENT Primary Name.
                
                # This is getting complex to sniff.
                # User complaint: "Deleting 'Ziggy' deleted 'Freddie'".
                # So we just say: "Removing this member ('Ziggy') will remove the underlying artist ('Freddie') from the group."
                
                reply = QMessageBox.question(self.parent, "Remove Member?", 
                                             f"Are you sure you want to remove '{member.name}' from '{self.artist.name}'?\n\nThis will remove the member entirely, including any aliases.",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    return False

            self.service.remove_member(self.artist.contributor_id, child_id)
        else:
            self.service.remove_member(child_id, self.artist.contributor_id)
        self.on_data_changed()
        return True
    
    def get_parent_for_dialog(self) -> Any:
        # T-Bug: Do NOT return self.artist here.
        # This is passed to the router as 'context_entity', which maps to 'context_song'.
        # Passing an Artist as a Song context is semantically wrong and dangerous.
        return None
    
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
            
        # T-92: IMMEDIATE WRITE MODE
        # Chip interactions are direct object manipulations. Staging is removed.
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
            
        # T-92: IMMEDIATE WRITE MODE
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

        # T-92: IMMEDIATE WRITE MODE
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
            
        # T-92: IMMEDIATE WRITE MODE
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

# =============================================================================
