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
    max_length: Optional[int] = None
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

    def is_valid(self, value: Any) -> bool:
        """
        Check if a value satisfies this field's constraints.
        Does NOT throw, just returns True/False.
        """
        # 1. Required Check
        if self.required:
            if value is None: return False
            if isinstance(value, str) and not value.strip(): return False
            if isinstance(value, (list, tuple)) and not value: return False
            
        if value is None:
            return True # If not required, None is valid
            
        # 2. String-based Checks (Length / Regex)
        if self.field_type in (FieldType.TEXT, FieldType.LIST): # List check applies to items or count... 
            # Current policy: min_length on List means "Number of Items"
            if self.field_type == FieldType.LIST:
                if isinstance(value, (list, tuple)):
                    if self.min_length is not None and len(value) < self.min_length:
                        return False
                elif isinstance(value, str):
                    items = [x.strip() for x in value.split(',') if x.strip()]
                    if self.min_length is not None and len(items) < self.min_length:
                        return False
                    if self.max_length is not None and len(items) > self.max_length:
                        return False
            else:
                s_val = str(value).strip()
                if self.min_length is not None and len(s_val) < self.min_length:
                    return False
                if self.max_length is not None and len(s_val) > self.max_length:
                    return False
                if self.validation_pattern:
                    import re
                    if not re.match(self.validation_pattern, s_val):
                        return False
                        
        # 3. Numeric Range Checks
        if self.field_type in (FieldType.INTEGER, FieldType.REAL, FieldType.DURATION):
            try:
                num_val = float(value)
                if self.min_value is not None and num_val < self.min_value:
                    return False
                if self.max_value is not None and num_val > self.max_value:
                    return False
                
                # Dynamic Future-Proofing for Year
                if self.name == 'recording_year':
                    from datetime import datetime
                    if num_val > datetime.now().year + 5:
                        return False
            except (ValueError, TypeError):
                return False
                
        return True

# ==================== THE REGISTRY ====================

# Query parts (FROM, WHERE, GROUP BY are static; SELECT is generated from FIELDS)
QUERY_FROM = """
    FROM MediaSources MS
    JOIN Songs S ON MS.SourceID = S.SourceID
"""

QUERY_BASE_WHERE = "WHERE 1=1"

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
        query_expression="(SELECT GROUP_CONCAT(AN_SUB.DisplayName, ', ') FROM SongCredits SC_SUB JOIN ArtistNames AN_SUB ON SC_SUB.CreditedNameID = AN_SUB.NameID JOIN Roles R_SUB ON SC_SUB.RoleID = R_SUB.RoleID WHERE SC_SUB.SourceID = MS.SourceID AND R_SUB.RoleName = 'Performer') AS Performers",
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
        query_expression="""
            COALESCE(NULLIF(S.SongGroups, ''), 
            (SELECT GROUP_CONCAT(AN_SUB.DisplayName, ', ') 
             FROM SongCredits SC_SUB 
             JOIN ArtistNames AN_SUB ON SC_SUB.CreditedNameID = AN_SUB.NameID 
             JOIN Roles R_SUB ON SC_SUB.RoleID = R_SUB.RoleID 
             WHERE SC_SUB.SourceID = MS.SourceID AND R_SUB.RoleName = 'Performer')) 
            AS UnifiedArtist
        """,
        strategy='list',
        zone='amber',
    ),
    FieldDef(
        name='title',
        ui_header='Title',
        db_column='MS.MediaName',
        id3_tag='TIT2',
        min_length=1,
        max_length=1000,
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
        query_expression="(SELECT GROUP_CONCAT(A_SUB.AlbumTitle, '|||') FROM SongAlbums SA_SUB JOIN Albums A_SUB ON SA_SUB.AlbumID = A_SUB.AlbumID WHERE SA_SUB.SourceID = MS.SourceID ORDER BY SA_SUB.IsPrimary DESC) AS AlbumTitle",
        required=True,
        strategy='list',
        ui_search=True,
        zone='amber', # IDENTITY
    ),
    FieldDef(
        name='album_id',
        ui_header='Album ID',
        db_column='AlbumID',
        field_type=FieldType.INTEGER,
        editable=False,
        portable=False,
        query_expression="(SELECT SA_SUB.AlbumID FROM SongAlbums SA_SUB WHERE SA_SUB.SourceID = MS.SourceID AND SA_SUB.IsPrimary = 1 LIMIT 1) AS AlbumID",
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
        query_expression="(SELECT GROUP_CONCAT(AN_SUB.DisplayName, ', ') FROM SongCredits SC_SUB JOIN ArtistNames AN_SUB ON SC_SUB.CreditedNameID = AN_SUB.NameID JOIN Roles R_SUB ON SC_SUB.RoleID = R_SUB.RoleID WHERE SC_SUB.SourceID = MS.SourceID AND R_SUB.RoleName = 'Composer') AS Composers",
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
        query_expression="""
            COALESCE(
                (SELECT P_SUB.PublisherName FROM SongAlbums SA_SUB JOIN Publishers P_SUB ON SA_SUB.TrackPublisherID = P_SUB.PublisherID WHERE SA_SUB.SourceID = MS.SourceID AND SA_SUB.IsPrimary = 1),
                (SELECT GROUP_CONCAT(P_SUB.PublisherName, '|||') FROM SongAlbums SA_SUB JOIN AlbumPublishers AP_SUB ON SA_SUB.AlbumID = AP_SUB.AlbumID JOIN Publishers P_SUB ON AP_SUB.PublisherID = P_SUB.PublisherID WHERE SA_SUB.SourceID = MS.SourceID AND SA_SUB.IsPrimary = 1),
                (SELECT GROUP_CONCAT(P_SUB.PublisherName, '|||') FROM RecordingPublishers RP_SUB JOIN Publishers P_SUB ON RP_SUB.PublisherID = P_SUB.PublisherID WHERE RP_SUB.SourceID = MS.SourceID)
            ) AS Publisher
        """,
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
        name='tags',
        ui_header='Tags',
        db_column='AllTags',
        field_type=FieldType.LIST,
        filterable=True,
        portable=False,  # Virtual container for TCON/TMOO
        query_expression="(SELECT GROUP_CONCAT(TG.TagCategory || ':' || TG.TagName, '|||') FROM MediaSourceTags MST JOIN Tags TG ON MST.TagID = TG.TagID WHERE MST.SourceID = MS.SourceID) AS AllTags",
        strategy='list',
        zone='gray',
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
        query_expression="(SELECT GROUP_CONCAT(AN_SUB.DisplayName, ', ') FROM SongCredits SC_SUB JOIN ArtistNames AN_SUB ON SC_SUB.CreditedNameID = AN_SUB.NameID JOIN Roles R_SUB ON SC_SUB.RoleID = R_SUB.RoleID WHERE SC_SUB.SourceID = MS.SourceID AND R_SUB.RoleName = 'Producer') AS Producers",
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
        query_expression="(SELECT GROUP_CONCAT(AN_SUB.DisplayName, ', ') FROM SongCredits SC_SUB JOIN ArtistNames AN_SUB ON SC_SUB.CreditedNameID = AN_SUB.NameID JOIN Roles R_SUB ON SC_SUB.RoleID = R_SUB.RoleID WHERE SC_SUB.SourceID = MS.SourceID AND R_SUB.RoleName = 'Lyricist') AS Lyricists",
        strategy='list',
        ui_search=True,
        zone='amber', # ATTRIBUTE
    ),
    FieldDef(
        name='album_artist',
        ui_header='Album Artist',
        db_column='AlbumArtist',
        id3_tag='TPE2',
        query_expression="(SELECT A_SUB.AlbumArtist FROM SongAlbums SA_SUB JOIN Albums A_SUB ON SA_SUB.AlbumID = A_SUB.AlbumID WHERE SA_SUB.SourceID = MS.SourceID AND SA_SUB.IsPrimary = 1 LIMIT 1) AS AlbumArtist",
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
        query_expression="(CASE WHEN EXISTS (SELECT 1 FROM MediaSourceTags MST_SUB JOIN Tags TG_SUB ON MST_SUB.TagID = TG_SUB.TagID WHERE MST_SUB.SourceID = MS.SourceID AND TG_SUB.TagCategory = 'Status' AND TG_SUB.TagName = 'Unprocessed') THEN 0 ELSE 1 END) AS is_done",
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
        ui_header='TOGGLE LIVE',
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

def get_field(name: str) -> Optional[FieldDef]:
    """Retrieve field definition by internal name."""
    return next((f for f in FIELDS if f.name == name), None)


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
        if not field_def.is_valid(cell_value):
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
    from src.data.models.song import Song
    from .registries.id3_registry import ID3Registry
    
    errors = []
    
    # Load ID3 frames from registry
    id3_frames = ID3Registry.get_frame_map()
    
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
        
        # For local fields, check Song has the attribute (unless virtual/unified)
        if not field.portable:
            attr = field.model_attr or field.name
            attr = attr_map.get(attr, attr)
            
            # Unified fields live in the 'tags' list, not as direct attributes
            if field.name == 'is_done':
                continue
                
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
    from .registries.id3_registry import ID3Registry
    
    # Load ID3 frames from registry
    id3_frames = ID3Registry.get_frame_map()
    
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
        
        # Handle list types (aggregated strings from DB)
        if field.field_type == FieldType.LIST and value:
            # T-70: Support both standard comma and the '|||' separator used for tags
            if '|||' in str(value):
                value = [v.strip() for v in str(value).split('|||') if v.strip()]
            else:
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
        'SongIsDone', # Legacy column, replaced by virtual is_done
        'IsDone', # Variant? To be safe.
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

    # 2. Validation
    if not field_def.is_valid(s_val):
         # Try to be helpful with the error message
         if field_def.required and not s_val:
             raise ValueError(f"{field_def.ui_header} is required")
         if field_def.min_length is not None:
             # Text or List?
             if field_def.field_type == FieldType.LIST:
                 raise ValueError(f"{field_def.ui_header} requires at least {field_def.min_length} items")
             else:
                 raise ValueError(f"'{s_val}' is too short for {field_def.ui_header}")
         if field_def.min_value is not None:
             raise ValueError(f"{field_def.ui_header} must be at least {field_def.min_value}")
         if field_def.validation_pattern:
             raise ValueError(f"'{s_val}' does not match format for {field_def.ui_header}")
             
         raise ValueError(f"Invalid value for {field_def.ui_header}: '{s_val}'")

    # 3. Type Casting
    if field_def.field_type == FieldType.LIST:
        return [v.strip() for v in s_val.split(',') if v.strip()]
        
    elif field_def.field_type == FieldType.INTEGER:
        return int(s_val)
            
    elif field_def.field_type == FieldType.REAL:
        return float(s_val)
            
    elif field_def.field_type == FieldType.BOOLEAN:
        return s_val.lower() in ("true", "1", "yes", "on")
        
    # Default: Text
    return s_val
