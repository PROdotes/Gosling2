import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.repositories.song_repository import SongRepository

"""
Fixture Injector for Test Songs.
Reads `tests/fixtures/test_songs.json` and populates the database.

JSON Schema (All fields strictly required by current logic):
[
  {
    "path": "C:\\Path\\To.mp3",       # Unique Key (Required)
    "title": "Song Title",            # (Required)
    "artist": "Artist Name",          # (Required) -> Maps to unified_artist
    "year": 1999,                     # (Required) -> Maps to recording_year
    "album": "Album Name"             # (Required) -> Triggers Album Sync
  }
]
"""

def inject():
    fixture_path = project_root / 'tests/fixtures/test_songs.json'
    contrib_path = project_root / 'tests/fixtures/contributors.json'
    
    with open(fixture_path, 'r') as f:
        songs_data = json.load(f)

    import logging
    logging.basicConfig(level=logging.DEBUG)
    from src.core import logger
    
    # Force Logger to DEBUG
    log_instance = logger.get()
    log_instance.setLevel(logging.DEBUG)
    for handler in log_instance.handlers:
        handler.setLevel(logging.DEBUG)

    # 1. Boot Repos
    repo = SongRepository()
    print(f"DB Path: {repo.db_path}")
    from src.data.repositories.contributor_repository import ContributorRepository
    crepo = ContributorRepository()
    
    # 2. THE NUKE: Clear existing data for a clean fixture state
    print("Nuking existing library data...")
    with repo.get_connection() as conn:
        conn.execute("DELETE FROM MediaSourceContributorRoles")
        conn.execute("DELETE FROM SongAlbums")
        conn.execute("DELETE FROM AlbumPublishers")
        conn.execute("DELETE FROM AlbumContributors")
        conn.execute("DELETE FROM Albums")
        conn.execute("DELETE FROM Publishers")
        conn.execute("DELETE FROM GroupMembers")
        conn.execute("DELETE FROM ContributorAliases")
        conn.execute("DELETE FROM Contributors")
        conn.execute("DELETE FROM MediaSourceTags")
        conn.execute("DELETE FROM Tags")
        conn.execute("DELETE FROM Songs")
        conn.execute("DELETE FROM MediaSources")
        conn.commit()

    # 3. Inject Contributors (Complex Identities)
    from src.business.services.contributor_service import ContributorService
    c_service = ContributorService()
    
    if os.path.exists(contrib_path):
        with open(contrib_path, 'r') as f:
            contrib_data = json.load(f)
        
        print(f"Injecting {len(contrib_data)} complex artist identities...")
        for c in contrib_data:
            # 1. Create Core Identity + Primary Name
            # Use get_by_name to check existence first (legacy safe)
            existing = c_service.get_by_name(c['name'])
            if not existing:
                artist = c_service.create(c['name'], c.get('type', 'person'))
                created = True
            else:
                artist = existing
                created = False
            
            # Aliases
            for alias in c.get('aliases', []):
                c_service.add_alias(artist.contributor_id, alias)
            
            # Members (Requires IDs, we resolve by name)
            for m_name in c.get('members', []):
                member_obj = c_service.get_by_name(m_name)
                if not member_obj:
                    member_obj = c_service.create(m_name, 'person')
                
                c_service.add_member(artist.contributor_id, member_obj.contributor_id) # Group, Member
        print("[OK] Artist identities established.")

    print(f"Processing {len(songs_data)} songs from fixture...")
    
    count = 0
    seen_paths = set()  # Track processed songs for M2M support
    
    for data in songs_data:
        # Normalize path
        raw_path = data['path']
        path = os.path.normcase(os.path.abspath(raw_path))
        
        # 1. Ensure Insert (Skip if already handled in this run)
        if path not in seen_paths:
            source_id = repo.insert(path)
            if not source_id:
                print(f"Failed to insert {path}")
                continue
            seen_paths.add(path)
        
        # 2. Fetch and Update Metadata
        # 2. Fetch and Update Metadata
        # Use source_id from insert if available, otherwise fetch by path
        if 'source_id' in locals() and source_id:
            print(f"DEBUG: Fetching by ID {source_id}")
            song = repo.get_by_id(source_id)
        else:
            print(f"DEBUG: Fetching by path {path}")
            song = repo.get_by_path(path)
            
        if not song:
             print(f"[FAIL] Could not retrieve song object for {path} (ID: {source_id if 'source_id' in locals() else 'Unknown'})")
             # DEBUG: Check DB content directly
             if 'source_id' in locals() and source_id:
                 with repo.get_connection() as conn:
                     cur = conn.cursor()
                     cur.execute(f"SELECT * FROM MediaSources WHERE SourceID={source_id}")
                     print(f"  MediaSources Row: {dict(cur.fetchone())}")
                     cur.execute(f"SELECT * FROM Songs WHERE SourceID={source_id}")
                     print(f"  Songs Row: {dict(cur.fetchone())}")
             continue
             
        song.title = data['title']
        
        # Split performers if delimited (legacy support)
        p_raw = data['artist']
        if isinstance(p_raw, str) and ',' in p_raw:
            song.performers = [p.strip() for p in p_raw.split(',')]
        else:
            song.performers = [p_raw]
            
        song.recording_year = data['year']
        song.album = data.get('album')  # Optional - None triggers "Single Paradox"
        song.album_artist = data.get('album_artist', data['artist'])  # Default to artist if not specified
        song.publisher = data.get('publisher')  # Optional
        # Handle Tags (Unified Category:Name)
        tags = []
        if data.get('genre'):
            genres = [g.strip() for g in str(data['genre']).split(',') if g.strip()]
            tags.extend([f"Genre:{g}" for g in genres])
        if data.get('mood'):
            moods = [m.strip() for m in str(data['mood']).split(',') if m.strip()]
            tags.extend([f"Mood:{m}" for m in moods])
        song.tags = tags

        # T-70: Role Splitting logic
        delims = r',|;| & '
        
        # Composers
        c_raw = data.get('composers', [])
        if isinstance(c_raw, str):
            import re
            song.composers = [p.strip() for p in re.split(delims + r'|/', c_raw) if p.strip()]
        else:
            song.composers = c_raw if isinstance(c_raw, list) else ([c_raw] if c_raw else [])

        # Producers
        pr_raw = data.get('producers', [])
        if isinstance(pr_raw, str):
            import re
            song.producers = [p.strip() for p in re.split(delims + r'|/', pr_raw) if p.strip()]
        else:
            song.producers = pr_raw if isinstance(pr_raw, list) else ([pr_raw] if pr_raw else [])

        # Lyricists
        l_raw = data.get('lyricists', [])
        if isinstance(l_raw, str):
            import re
            song.lyricists = [p.strip() for p in re.split(delims, l_raw) if p.strip()]
        else:
            song.lyricists = l_raw if isinstance(l_raw, list) else ([l_raw] if l_raw else [])
        
        # 3. Save (Triggers album/publisher/contributor sync)
        if repo.update(song):
            pub_str = f" | Publisher: {song.publisher}" if song.publisher else ""
            print(f"[OK] Injected: {song.title} -> Album: {song.album}{pub_str}")
            count += 1
        else:
            print(f"[FAIL] Failed to update: {song.title}")

    print(f"\n--- Injection Complete ({count}/{len(songs_data)}) ---")
    
    # 4. Post-Injection: Establishing Hierarchy (User Req: Northern Songs -> Sony)
    print("\n[HIERARCHY] Setting up Publisher Relationships...")
    from src.data.repositories.publisher_repository import PublisherRepository
    pub_repo = PublisherRepository()
    
    hierarchy = {
        "Sony": ["Northern Songs", "EMI", "Parlophone"],
        "Universal Music Group": ["DGC Records", "Capitol Records", "Polar Music"]
    }
    
    for parent_name, children in hierarchy.items():
        parent, _ = pub_repo.get_or_create(parent_name)
        for child_name in children:
            child, _ = pub_repo.get_or_create(child_name)
            if not child.parent_publisher_id:
                child.parent_publisher_id = parent.publisher_id
                pub_repo.update(child)
                print(f"  [LINK] {child_name} -> {parent_name}")
    
    # 5. Post-Injection: Multi-Album Links (Testing M:M)
    print("\n[MULTI-ALBUM] Linking songs to additional albums...")
    from src.data.repositories.album_repository import AlbumRepository
    album_repo = AlbumRepository()
    
    # Link "Dancing Queen" (ABBA Greatest Hits) to also appear on "Gold: Greatest Hits"
    with repo.get_connection() as conn:
        # Find Dancing Queen's SourceID
        cursor = conn.execute("SELECT MS.SourceID FROM MediaSources MS WHERE MS.MediaName = 'Dancing Queen'")
        row = cursor.fetchone()
        if row:
            source_id = row[0]
            # Create the second album
            cursor.execute(
                "INSERT INTO Albums (AlbumTitle, AlbumArtist, AlbumType, ReleaseYear) VALUES (?, ?, 'Compilation', ?)",
                ("Gold: Greatest Hits", "ABBA", 1992)
            )
            second_album_id = cursor.lastrowid
            
            # T-91: Link ABBA to Gold Greatest Hits via M2M
            # Resolve name to NameID in ArtistNames
            abba = c_service.get_by_name("ABBA")
            if abba:
                abba_id = abba.contributor_id
                cursor.execute(
                    "INSERT OR IGNORE INTO AlbumCredits (AlbumID, CreditedNameID, RoleID) VALUES (?, ?, (SELECT RoleID FROM Roles WHERE RoleName = 'Performer'))",
                    (second_album_id, abba_id)
                )

            # Link song to second album (non-primary)
            cursor.execute(
                "INSERT OR IGNORE INTO SongAlbums (SourceID, AlbumID, IsPrimary) VALUES (?, ?, 0)",
                (source_id, second_album_id)
            )
            conn.commit()
            print(f"  [M:M] 'Dancing Queen' now appears on 2 albums")
    
    # 6. Post-Injection: Album Publishers (Level 2 - Testing Inheritance)
    print("\n[ALBUM-PUBLISHERS] Setting up album-level publishers for Waterfall testing...")
    with repo.get_connection() as conn:
        # Get publisher IDs
        pubs = {}
        for name in ['Polar Music', 'EMI', 'DGC Records', 'Northern Songs', 'Parlophone', 'Queen Productions Ltd']:
            cur = conn.execute("SELECT PublisherID FROM Publishers WHERE PublisherName = ?", (name,))
            row = cur.fetchone()
            if row:
                pubs[name] = row[0]
        
        # Get album IDs
        albums = {}
        cur = conn.execute("SELECT AlbumID, AlbumTitle, AlbumArtist FROM Albums")
        for row in cur.fetchall():
            key = f"{row[1]} ({row[2] or 'N/A'})"
            albums[key] = row[0]
        
        # --- TEST CASE: Level 2 (Album Publisher) ---
        # ABBA's Greatest Hits should have "Polar Music" as album publisher
        abba_gh = albums.get("Greatest Hits (ABBA)")
        if abba_gh and 'Polar Music' in pubs:
            conn.execute("INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)",
                        (abba_gh, pubs['Polar Music']))
            print(f"  [L2] ABBA 'Greatest Hits' -> Polar Music (Album Label)")
        
        # Gold: Greatest Hits also gets Polar Music
        gold_gh = albums.get("Gold: Greatest Hits (ABBA)")
        if gold_gh and 'Polar Music' in pubs:
            conn.execute("INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)",
                        (gold_gh, pubs['Polar Music']))
            print(f"  [L2] ABBA 'Gold: Greatest Hits' -> Polar Music (Album Label)")
        
        # --- TEST CASE: Multi-Publisher Album (Joint Venture) ---
        # Queen's Greatest Hits has 3 labels (from fixture data)
        queen_gh = albums.get("Greatest Hits (Queen)")
        if queen_gh:
            for pub_name in ['EMI', 'Queen Productions Ltd', 'Parlophone']:
                if pub_name in pubs:
                    conn.execute("INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)",
                                (queen_gh, pubs[pub_name]))
            print(f"  [L2] Queen 'Greatest Hits' -> EMI, Queen Productions Ltd, Parlophone (Multi-Label)")
        
        # Nirvana's Nevermind gets DGC Records
        nevermind = albums.get("Nevermind (Nirvana)")
        if nevermind and 'DGC Records' in pubs:
            conn.execute("INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)",
                        (nevermind, pubs['DGC Records']))
            print(f"  [L2] Nirvana 'Nevermind' -> DGC Records (Album Label)")
        
        # Beatles Help! gets Northern Songs (which has parent Sony)
        help_album = albums.get("Help! (The Beatles)")
        if help_album and 'Northern Songs' in pubs:
            conn.execute("INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)",
                        (help_album, pubs['Northern Songs']))
            print(f"  [L2] Beatles 'Help!' -> Northern Songs [Sony] (Parent Chain)")
        
        conn.commit()
    
    # 7. Clear TrackPublisherID for songs that should INHERIT from album (pure Level 2 test)
    print("\n[WATERFALL-CLEANUP] Clearing track overrides for inheritance test...")
    with repo.get_connection() as conn:
        # Clear TrackPublisherID for Dancing Queen so it inherits from album
        conn.execute("""
            UPDATE SongAlbums SET TrackPublisherID = NULL 
            WHERE SourceID IN (SELECT SourceID FROM MediaSources WHERE MediaName = 'Dancing Queen')
        """)
        # Clear for Nirvana songs too
        conn.execute("""
            UPDATE SongAlbums SET TrackPublisherID = NULL 
            WHERE SourceID IN (SELECT SourceID FROM MediaSources WHERE MediaName IN ('Lithium', 'Polly', 'In Bloom'))
        """)
        # Keep "Radio Ga Ga" with its TrackPublisherID (Special License Corp) for override test
        conn.commit()
        print("  [OK] Dancing Queen, Lithium, Polly, In Bloom now inherit from album (Level 2)")
        print("  [OK] Radio Ga Ga keeps TrackPublisherID override (Level 1)")
    
    # Report on Albums
    with repo.get_connection() as conn:
        cursor = conn.execute("SELECT AlbumID, AlbumTitle, AlbumArtist, ReleaseYear FROM Albums")
        albums = cursor.fetchall()
        print(f"\nCreated {len(albums)} Albums in DB:")
        for alb in albums:
            c2 = conn.execute("SELECT COUNT(*) FROM SongAlbums WHERE AlbumID=?", (alb[0],))
            song_count = c2.fetchone()[0]
            # Get album publishers
            c3 = conn.execute("""
                SELECT GROUP_CONCAT(P.PublisherName, ', ') 
                FROM AlbumPublishers AP 
                JOIN Publishers P ON AP.PublisherID = P.PublisherID 
                WHERE AP.AlbumID = ?
            """, (alb[0],))
            pub_row = c3.fetchone()
            pub_str = f" | Labels: {pub_row[0]}" if pub_row and pub_row[0] else ""
            artist_str = f" by {alb[2]}" if alb[2] else ""
            print(f"[ALBUM] ID {alb[0]}: '{alb[1]}'{artist_str} ({alb[3]}) - {song_count} Songs{pub_str}")

if __name__ == "__main__":
    inject()
