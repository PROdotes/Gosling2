"""
Yellberus 🐕‍🦺
The Field Registry - Single Source of Truth for Data Fields.

This module defines all available data fields in the application, their properties,
validation rules, and UI behavior. It replaces scattered constants and configurations.
"""

from dataclasses import dataclass
from typing import Optional, Callable, List, Any
from enum import Enum, auto

class FieldType(Enum):
    TEXT = auto()
    INTEGER = auto()
    REAL = auto()
    BOOLEAN = auto()
    LIST = auto()      # Comma-separated or multiple values
    DURATION = auto()  # Seconds, display as mm:ss
    DATETIME = auto()

@dataclass
class FieldDef:
    """Definition of a single data field."""
    name: str                      # Internal key (e.g., "title")
    ui_header: str                 # Column header (e.g., "Title")
    db_column: str                 # SQL column name (e.g., "MS.Name")
    field_type: FieldType = FieldType.TEXT
    zone: str = "amber"            # Semantic zone (amber, blue, green, gray)

    
    # Validation
    required: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    validation_pattern: Optional[str] = None  # Regex pattern for format validation (e.g., ISRC)
    
    # UI behavior
    visible: bool = True
    editable: bool = True
    searchable: bool = True
    ui_search: bool = False        # Link to external search (Google, Spotify)
    
    # Filter behavior
    filterable: bool = False
    strategy: str = "list"  # "list", "range", "boolean", "decade_grouper", "first_letter_grouper"
    
    # Mapping
    model_attr: Optional[str] = None  # Song model property (defaults to name)
    portable: bool = True
    
    # Query generation
    query_expression: Optional[str] = None  # Full SQL expression (for GROUP_CONCAT etc). If None, uses db_column.
    id3_tag: Optional[str] = None # Direct ID3 tag mapping (e.g. "TIT2")

# ==================== THE REGISTRY ====================

# Query parts (FROM, WHERE, GROUP BY are static; SELECT is generated from FIELDS)
QUERY_FROM = """
    FROM MediaSources MS
    JOIN Songs S ON MS.SourceID = S.SourceID
    LEFT JOIN MediaSourceContributorRoles MSCR ON MS.SourceID = MSCR.SourceID
    LEFT JOIN Contributors C ON MSCR.ContributorID = C.ContributorID
    LEFT JOIN ContributorAliases CA ON MSCR.CreditedAliasID = CA.AliasID
    LEFT JOIN ContributorAliases CA_ALL ON C.ContributorID = CA_ALL.ContributorID
    LEFT JOIN GroupMembers GM ON C.ContributorID = GM.GroupID
    LEFT JOIN Contributors MEM ON GM.MemberID = MEM.ContributorID
    LEFT JOIN ContributorAliases MA ON MEM.ContributorID = MA.ContributorID
    LEFT JOIN Roles R ON MSCR.RoleID = R.RoleID
    LEFT JOIN SongAlbums SA ON MS.SourceID = SA.SourceID
    LEFT JOIN Albums A ON SA.AlbumID = A.AlbumID
    LEFT JOIN AlbumPublishers AP ON A.AlbumID = AP.AlbumID
    LEFT JOIN Publishers P ON AP.PublisherID = P.PublisherID
    LEFT JOIN MediaSourceTags MST_G ON MS.SourceID = MST_G.SourceID
    LEFT JOIN Tags TG_G ON MST_G.TagID = TG_G.TagID AND TG_G.TagCategory = 'Genre'
    LEFT JOIN MediaSourceTags MST_M ON MS.SourceID = MST_M.SourceID
    LEFT JOIN Tags TG_M ON MST_M.TagID = TG_M.TagID AND TG_M.TagCategory = 'Mood'
    LEFT JOIN MediaSourceTags MST_S ON MS.SourceID = MST_S.SourceID
    LEFT JOIN Tags TG_S ON MST_S.TagID = TG_S.TagID AND TG_S.TagCategory = 'Status' AND TG_S.TagName = 'Unprocessed'
    LEFT JOIN Publishers P_TRK ON SA.TrackPublisherID = P_TRK.PublisherID
    LEFT JOIN RecordingPublishers RP ON MS.SourceID = RP.SourceID
    LEFT JOIN Publishers P_REC ON RP.PublisherID = P_REC.PublisherID
"""

QUERY_BASE_WHERE = "WHERE MS.IsActive = 1"

QUERY_GROUP_BY = "GROUP BY MS.SourceID"

# Helper to group years into decades
def decade_grouper(year: Any) -> str:
    try:
        y = int(year)
        return f"{y // 10 * 10}s"
    except (ValueError, TypeError):
        return "Unknown"

# Helper to group by first letter
def first_letter_grouper(value: Any) -> str:
    if not value:
        return "#"
    s = str(value).strip().upper()
    if not s:
        return "#"
    first = s[0]
    return first if first.isalpha() else "#"

# Lookup for grouping functions by strategy name
GROUPERS = {
    "decade_grouper": decade_grouper,
    "first_letter_grouper": first_letter_grouper,
}

# NOTE: The order of this list MUST match the columns in BASE_QUERY!
FIELDS: List[FieldDef] = [
    FieldDef(
        name='performers',
        ui_header='Performers',
        db_column='Performers',
        field_type=FieldType.LIST,
        id3_tag='TPE1',
        min_length=1,
        query_expression="GROUP_CONCAT(DISTINCT CASE WHEN R.RoleName = 'Performer' THEN COALESCE(CA.AliasName, C.ContributorName) END) AS Performers",
        searchable=False,
        strategy='list',
        ui_search=True,
        zone='amber',
    ),
    FieldDef(
        name='groups',
        ui_header='Groups',
        db_column='S.SongGroups',
        id3_tag='TIT1',
        searchable=False,
        visible=False,
    ),
    FieldDef(
        name='unified_artist',
        ui_header='Artist',
        db_column='UnifiedArtist',
        editable=False,
        filterable=True,
        portable=False,
        query_expression="COALESCE(NULLIF(S.SongGroups, ''), GROUP_CONCAT(DISTINCT CASE WHEN R.RoleName = 'Performer' THEN COALESCE(CA.AliasName, C.ContributorName) END)) || ' ::: ' || COALESCE(GROUP_CONCAT(DISTINCT CA_ALL.AliasName), '') || ' ' || COALESCE(GROUP_CONCAT(DISTINCT C.ContributorName), '') || ' ' || COALESCE(GROUP_CONCAT(DISTINCT MEM.ContributorName), '') || ' ' || COALESCE(GROUP_CONCAT(DISTINCT MA.AliasName), '') AS UnifiedArtist",
        strategy='list',
        zone='amber',
    ),
    FieldDef(
        name='title',
        ui_header='Title',
        db_column='MS.MediaName',
        id3_tag='TIT2',
        min_length=1,
        required=True,
        ui_search=True,
        zone='amber',
    ),
    FieldDef(
        name='album',
        ui_header='Album',
        db_column='AlbumTitle',
        field_type=FieldType.LIST,
        filterable=True,
        id3_tag='TALB',
        query_expression="GROUP_CONCAT(A.AlbumTitle, ', ') AS AlbumTitle",
        required=True,
        strategy='list',
        ui_search=True,
        zone='amber', # IDENTITY
    ),
    FieldDef(
        name='album_id',
        ui_header='Album ID',
        db_column='SA.AlbumID',
        field_type=FieldType.INTEGER,
        editable=False,
        portable=False,
        searchable=False,
        visible=False,
    ),
    FieldDef(
        name='composers',
        ui_header='Composer',
        db_column='Composers',
        field_type=FieldType.LIST,
        filterable=True,
        id3_tag='TCOM',
        min_length=1,
        query_expression="GROUP_CONCAT(DISTINCT CASE WHEN R.RoleName = 'Composer' THEN COALESCE(CA.AliasName, C.ContributorName) END) || ' ::: ' || GROUP_CONCAT(DISTINCT CA_ALL.AliasName) || ' ' || GROUP_CONCAT(DISTINCT C.ContributorName) AS Composers",
        required=True,
        strategy='list',
        ui_search=True,
        zone='amber', # ATTRIBUTE
    ),
    FieldDef(
        name='publisher',
        ui_header='Publisher',
        db_column='Publisher',
        field_type=FieldType.LIST,
        filterable=True,
        id3_tag='TPUB',
        # Logic: Track Override > Album Publisher > Recording/Archival Publisher
        query_expression='COALESCE(P_TRK.PublisherName, GROUP_CONCAT(DISTINCT P.PublisherName), GROUP_CONCAT(DISTINCT P_REC.PublisherName)) AS Publisher',
        required=True,
        strategy='list',
        ui_search=True,
        zone='amber', # IDENTITY
    ),

    FieldDef(
        name='recording_year',
        ui_header='Year',
        db_column='S.RecordingYear',
        field_type=FieldType.INTEGER,
        filterable=True,
        id3_tag='TDRC',
        min_value=1860,
        required=True,
        strategy='list',  # Flat list, not grouped by decade
        ui_search=True,
        validation_pattern=r'^\d{4}$', # Enforce 4 digits (e.g. 1999) to catch typos like "199"
        zone='amber', # ATTRIBUTE
    ),
    FieldDef(
        name='genre',
        ui_header='Genre',
        db_column='Genre',
        field_type=FieldType.LIST,
        filterable=True,
        id3_tag='TCON',
        query_expression='GROUP_CONCAT(DISTINCT TG_G.TagName) AS Genre',
        required=True,
        strategy='list',
        ui_search=True,
        zone='amber', # Warm Amber (Matches Speech/All)
    ),
    FieldDef(
        name='mood',
        ui_header='Mood',
        db_column='Mood',
        field_type=FieldType.LIST,
        filterable=True,
        id3_tag='TMOO',
        query_expression='GROUP_CONCAT(DISTINCT TG_M.TagName) AS Mood',
        required=False,
        strategy='list',
        ui_search=True,
        zone='amber',
    ),
    FieldDef(
        name='isrc',
        ui_header='ISRC',
        db_column='S.ISRC',
        id3_tag='TSRC',
        searchable=False,
        ui_search=True,
        validation_pattern='^[A-Z]{2}[A-Z0-9]{3}\\d{2}\\d{5}$',
    ),
    FieldDef(
        name='duration',
        ui_header='Duration',
        db_column='MS.SourceDuration',
        field_type=FieldType.DURATION,
        editable=False,
        id3_tag='TLEN',
        min_value=30,
        portable=False,
        required=True,
        searchable=False,
    ),
    FieldDef(
        name='producers',
        ui_header='Producer',
        db_column='Producers',
        field_type=FieldType.LIST,
        filterable=True,
        id3_tag='TIPL',
        query_expression="GROUP_CONCAT(DISTINCT CASE WHEN R.RoleName = 'Producer' THEN COALESCE(CA.AliasName, C.ContributorName) END) || ' ::: ' || GROUP_CONCAT(DISTINCT CA_ALL.AliasName) || ' ' || GROUP_CONCAT(DISTINCT C.ContributorName) AS Producers",
        strategy='list',
        ui_search=True,
        zone='amber', # ATTRIBUTE
    ),
    FieldDef(
        name='lyricists',
        ui_header='Lyricist',
        db_column='Lyricists',
        field_type=FieldType.LIST,
        filterable=True,
        id3_tag='TEXT',
        portable=False,
        query_expression="GROUP_CONCAT(DISTINCT CASE WHEN R.RoleName = 'Lyricist' THEN COALESCE(CA.AliasName, C.ContributorName) END) || ' ::: ' || GROUP_CONCAT(DISTINCT CA_ALL.AliasName) || ' ' || GROUP_CONCAT(DISTINCT C.ContributorName) AS Lyricists",
        strategy='list',
        ui_search=True,
        zone='amber', # ATTRIBUTE
    ),
    FieldDef(
        name='album_artist',
        ui_header='Album Artist',
        db_column='AlbumArtist',
        id3_tag='TPE2',
        query_expression="GROUP_CONCAT(A.AlbumArtist, ', ') AS AlbumArtist",
        strategy='list',
        visible=False,
    ),
    FieldDef(
        name='notes',
        ui_header='Notes',
        db_column='MS.SourceNotes',
        portable=False,
        searchable=False,
    ),
    FieldDef(
        name='is_done',
        ui_header='Status',
        db_column='is_done',
        field_type=FieldType.BOOLEAN,
        filterable=True,
        portable=False,
        query_expression="(CASE WHEN COUNT(DISTINCT TG_S.TagID) > 0 THEN 0 ELSE 1 END) AS is_done",
        searchable=False,
        strategy='boolean',
        zone='magenta', # Console Magenta (Matches Surgical Highlights)
    ),

    FieldDef(
        name='path',
        ui_header='Path',
        db_column='MS.SourcePath',
        editable=False,
        model_attr='source',
        portable=False,
        required=True,
        searchable=False,
        strategy='decade_grouper',
        visible=False,
    ),
    FieldDef(
        name='file_id',
        ui_header='ID',
        db_column='MS.SourceID',
        field_type=FieldType.INTEGER,
        editable=False,
        model_attr='source_id',
        portable=False,
        required=True,
        searchable=False,
        visible=False,
    ),
    FieldDef(
        name='type_id',
        ui_header='Type',
        db_column='MS.TypeID',
        field_type=FieldType.INTEGER,
        editable=False,
        portable=False,
        searchable=False,
        visible=False,
    ),
    FieldDef(
        name='bpm',
        ui_header='BPM',
        db_column='S.TempoBPM',
        field_type=FieldType.INTEGER,
        filterable=True,
        id3_tag='TBPM',
        min_value=0,
        searchable=False,
        strategy='range',
        zone='gray', # SYSTEM
    ),
    FieldDef(
        name='is_active',
        ui_header='Active',
        db_column='MS.IsActive',
        field_type=FieldType.BOOLEAN,
        filterable=True,
        portable=False,
        searchable=False,
        strategy='boolean',
        zone='gray', # SYSTEM
    ),
    FieldDef(
        name='audio_hash',
        ui_header='Audio Hash',
        db_column='MS.AudioHash',
        editable=False,
        portable=False,
        searchable=False,
        visible=False,
    ),
]

# ==================== CROSS-FIELD VALIDATION RULES ====================
# Rules that span multiple fields (can't be expressed per-field)

VALIDATION_GROUPS = [
    {
        "name": "unified_artist",
        "rule": "at_least_one",  # At least one of these fields must be populated
        "fields": ["performers", "groups"],
        "message": "Song must have at least one performer or group"
    },
]

# ==================== QUERY GENERATION ====================

def build_query_select() -> str:
    """
    Generate SELECT clause from FIELDS list.
    Uses query_expression if defined, otherwise uses db_column.
    This ensures QUERY_SELECT always matches FIELDS order.
    """
    columns = []
    for f in FIELDS:
        if f.query_expression:
            columns.append(f.query_expression)
        else:
            columns.append(f.db_column)
    return "SELECT \n        " + ",\n        ".join(columns)

# Generate QUERY_SELECT from FIELDS (single source of truth)
QUERY_SELECT = build_query_select()

# The Canonical Query (Standard Access)
BASE_QUERY = f"{QUERY_SELECT} {QUERY_FROM} {QUERY_BASE_WHERE} {QUERY_GROUP_BY}"

# ==================== HELPERS ====================

def get_field(name: str) -> Optional[FieldDef]:
    """Lookup a field by name."""
    return next((f for f in FIELDS if f.name == name), None)

def get_visible_fields() -> List[FieldDef]:
    """Get fields that should appear in the table."""
    return [f for f in FIELDS if f.visible]

def get_filterable_fields() -> List[FieldDef]:
    """Get fields that should appear in the filter sidebar."""
    return [f for f in FIELDS if f.filterable]

def get_required_fields() -> List[FieldDef]:
    """Get fields marked as required for validation."""
    return [f for f in FIELDS if f.required]

def validate_row(row_data: list) -> set:
    """
    Validate a row of data against Yellberus field definitions.
    Returns a set of field names that failed validation.
    
    Checks:
    1. Per-field: required, min_length, min_value
    2. Cross-field: rules defined in VALIDATION_GROUPS
    """
    failed_fields = set()
    field_indices = {f.name: i for i, f in enumerate(FIELDS)}
    
    # Per-field validation
    for col_idx, cell_value in enumerate(row_data):
        if col_idx >= len(FIELDS):
            break
            
        field_def = FIELDS[col_idx]
        is_valid = True
        
        # Check required
        if field_def.required:
            if cell_value is None:
                is_valid = False
            elif isinstance(cell_value, str) and not cell_value.strip():
                is_valid = False
            elif isinstance(cell_value, (list, tuple)) and len(cell_value) == 0:
                is_valid = False
        
        # Check list min_length
        if is_valid and field_def.field_type == FieldType.LIST:
            if field_def.required and not cell_value:
                is_valid = False
            elif cell_value and field_def.min_length is not None:
                items = [x.strip() for x in str(cell_value).split(',') if x.strip()]
                if len(items) < field_def.min_length:
                    is_valid = False
        
        # Check text min_length
        elif is_valid and field_def.field_type == FieldType.TEXT:
            if cell_value and field_def.min_length is not None:
                if len(str(cell_value).strip()) < field_def.min_length:
                    is_valid = False
        
        # Check numeric range (min/max)
        elif is_valid and field_def.field_type in (FieldType.INTEGER, FieldType.REAL, FieldType.DURATION):
            if cell_value is not None:
                try:
                    val_num = float(cell_value)
                    
                    if field_def.min_value is not None and val_num < field_def.min_value:
                        is_valid = False
                        
                    if field_def.max_value is not None and val_num > field_def.max_value:
                        is_valid = False
                        
                    # Dynamic Cap for Years
                    if field_def.name == 'recording_year':
                        from datetime import datetime
                        max_year = datetime.now().year + 1
                        if val_num > max_year:
                             is_valid = False
                             
                except (ValueError, TypeError):
                    pass # logic elsewhere might catch type errors, but here we just skip check
        
        if not is_valid:
            failed_fields.add(field_def.name)
    
    # Cross-field validation from VALIDATION_GROUPS
    for group in VALIDATION_GROUPS:
        rule = group.get("rule")
        fields = group.get("fields", [])
        
        if rule == "at_least_one":
            # Check if at least one of the fields has a value
            has_any = False
            for field_name in fields:
                idx = field_indices.get(field_name)
                if idx is not None and idx < len(row_data):
                    val = row_data[idx]
                    if val and str(val).strip():
                        has_any = True
                        break
            
            if not has_any:
                # Mark all fields in the group as failing
                for field_name in fields:
                    failed_fields.add(field_name)
    
    return failed_fields


# ==================== SCHEMA VALIDATION ====================

class SchemaError(Exception):
    """Raised when schema validation fails."""
    pass

def yell(message: str) -> None:
    """
    Report a schema or mapping error.
    Called by Song when it can't map a value.
    """
    from . import logger
    logger.dev_warning(f"YELLBERUS: {message}")

def validate_schema() -> None:
    """
    Cross-check FIELDS against id3_frames.json and Song model.
    Raises SchemaError if mismatches are found.
    
    Checks:
    1. Portable fields have id3_frame defined
    2. id3_frame exists in id3_frames.json with 'field' mapping
    3. JSON 'field' value has matching Song attribute (or alias)
    4. Local fields don't have id3_frame
    
    Call this at app startup or in tests to catch schema drift early.
    """
    import json
    import os
    from src.data.models.song import Song
    
    errors = []
    
    # Load id3_frames.json
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, '..', 'resources', 'id3_frames.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            id3_frames = json.load(f)
    except Exception as e:
        errors.append(f"❌ Failed to load id3_frames.json: {e}")
        id3_frames = {}
    
    # Build reverse lookup: field_name -> frame_code
    field_to_frame = {}
    for frame_code, frame_info in id3_frames.items():
        if isinstance(frame_info, dict) and 'field' in frame_info:
            field_to_frame[frame_info['field']] = frame_code
    
    # Known aliases (JSON field name -> Song attribute)
    attr_map = {
        'file_id': 'source_id',
        'path': 'source',
        'title': 'name',
    }
    
    for field in FIELDS:
        # Look up frame code from JSON using field name
        frame_code = field_to_frame.get(field.name)
        
        # Check 1: Portable fields must have a frame in JSON
        if field.portable and not frame_code:
            errors.append(f"❌ Portable field '{field.name}' has no ID3 frame mapping in id3_frames.json")
            continue
        
        # For portable fields, verify the full chain
        if field.portable and frame_code:
            frame_info = id3_frames.get(frame_code, {})
            if isinstance(frame_info, dict):
                json_field = frame_info.get('field')
                
                # Check 2: JSON field maps to Song attribute
                attr = attr_map.get(json_field, json_field)
                if attr not in Song.__dataclass_fields__ and not hasattr(Song, attr):
                    errors.append(f"❌ JSON field '{json_field}' → Song missing attribute '{attr}'")
        
        # For local fields, check Song has the attribute
        if not field.portable:
            attr = field.model_attr or field.name
            attr = attr_map.get(attr, attr)
            if attr not in Song.__dataclass_fields__ and not hasattr(Song, attr):
                errors.append(f"❌ Local field '{field.name}' → Song missing attribute '{attr}'")
    
    if errors:
        raise SchemaError("YELLBERUS SCHEMA MISMATCH:\n" + "\n".join(errors))

def row_to_tagged_tuples(row: tuple) -> list:
    """
    Convert a Yellberus query result row to tagged tuples.
    Returns: [(value, id3_frame_or_field_name), ...]
    
    For portable fields: looks up id3_frame from JSON using field name
    For local fields: uses field name prefixed with "_" (e.g., "_file_id")
    
    Song will use these to look up mappings in id3_frames.json.
    """
    import json
    import os
    
    # Load id3_frames.json to find frame codes
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, '..', 'resources', 'id3_frames.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            id3_frames = json.load(f)
    except Exception:
        id3_frames = {}
    
    # Build reverse lookup: field_name -> frame_code
    field_to_frame = {}
    for frame_code, frame_info in id3_frames.items():
        if isinstance(frame_info, dict) and 'field' in frame_info:
            field_to_frame[frame_info['field']] = frame_code
    
    result = []
    for i, field in enumerate(FIELDS):
        if i >= len(row):
            break
            
        value = row[i]
        
        # Handle list types (comma-separated strings from DB)
        if field.field_type == FieldType.LIST and value:
            value = [v.strip() for v in str(value).split(',') if v.strip()]
        
        # Look up ID3 frame from JSON
        frame_code = field_to_frame.get(field.name)
        
        if field.portable and frame_code:
            # Portable field: tag with ID3 frame code
            result.append((value, frame_code))
        else:
            # Local field or no frame found: tag with underscore-prefixed field name
            result.append((value, f"_{field.name}"))
    
    return result


def check_db_integrity(cursor) -> None:
    """
    Runtime check: Compare DB schema against FIELDS registry.
    Yells if there are orphan columns in the database.
    """
    # 1. Gather all expected columns from Yellberus
    yellberus_cols = set()
    for f in FIELDS:
        # DB column might be 'MS.Name' or 'Producers' or 'S.BPM'
        col = f.db_column
        if '.' in col:
            col = col.split('.')[1]
        yellberus_cols.add(col)
        
    # 2. Check Tables
    # Valid columns that are in DB but intentionally not in Yellberus yet
    known_ignored = {
        'Notes',  # Not yet fully implemented
    }
    
    for table in ['MediaSources', 'Songs']:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            rows = cursor.fetchall()
            if not rows:
                continue
                
            db_cols = {row[1] for row in rows}
            orphans = db_cols - yellberus_cols - known_ignored
            
            if orphans:
                for o in orphans:
                    yell(f"Orphan column in {table} detected: '{o}' (Exists in DB but not in Registry)")
                    
        except Exception as e:
            yell(f"Integrity check failed: {e}")

def cast_from_string(field_def: FieldDef, value: Any) -> Any:
    """
    Cast a string value (from UI) to the correct Python type for the model.
    Handles Lists, Integers, Reals, and Booleans based on FieldType.
    """
    if value is None:
        return None
        
    # 0. Pass-through for Lists
    if isinstance(value, (list, tuple)) and field_def.field_type == FieldType.LIST:
        return [str(v).strip() for v in value if str(v).strip()]

    # 1. Normalize to String
    s_val = str(value).strip() if value is not None else ""
    if not s_val:
        return None

    # 2. Pattern Validation (Global)
    if field_def.validation_pattern:
        import re
        if not re.match(field_def.validation_pattern, s_val):
             raise ValueError(f"'{s_val}' does not match format for {field_def.ui_header}")

    # 3. Min Length Check (Text/String based)
    if field_def.min_length is not None:
        if len(s_val) < field_def.min_length:
             raise ValueError(f"'{s_val}' is too short for {field_def.ui_header} (Min: {field_def.min_length})")

    # 4. Type Casting & Range Check
    if field_def.field_type == FieldType.LIST:
        # Check size of list items? (min_length usually applies to list count OR item length?)
        # Yellberus validate_row checks LIST COUNT.
        items = [v.strip() for v in s_val.split(',') if v.strip()]
        if field_def.min_length is not None and len(items) < field_def.min_length:
             raise ValueError(f"{field_def.ui_header} requires at least {field_def.min_length} items")
        return items
        
    elif field_def.field_type == FieldType.INTEGER:
        try:
            i_val = int(s_val)
            if field_def.min_value is not None and i_val < field_def.min_value:
                 raise ValueError(f"{field_def.ui_header} must be at least {field_def.min_value}")
            if field_def.max_value is not None and i_val > field_def.max_value:
                 raise ValueError(f"{field_def.ui_header} cannot be greater than {field_def.max_value}")
                 
            # Dynamic Cap for Years (Future-Proofing Logic)
            if field_def.name == 'recording_year':
                from datetime import datetime
                max_year = datetime.now().year + 1
                if i_val > max_year:
                     raise ValueError(f"{field_def.ui_header} cannot be in the future (Max: {max_year})")

            return i_val
        except (ValueError, TypeError):
            raise ValueError(f"'{value}' is not a valid number for {field_def.ui_header}")
            
    elif field_def.field_type == FieldType.REAL:
        try:
            f_val = float(s_val)
            if field_def.min_value is not None and f_val < field_def.min_value:
                 raise ValueError(f"{field_def.ui_header} must be at least {field_def.min_value}")
            if field_def.max_value is not None and f_val > field_def.max_value:
                 raise ValueError(f"{field_def.ui_header} cannot be greater than {field_def.max_value}")
            return f_val
        except (ValueError, TypeError):
            raise ValueError(f"'{value}' is not a valid number for {field_def.ui_header}")
            
    elif field_def.field_type == FieldType.BOOLEAN:
        return s_val.lower() in ("true", "1", "yes", "on")
        
    # Default: Text
    return s_val
