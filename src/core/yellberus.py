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
    
    # Validation
    required: bool = False
    min_value: Optional[float] = None
    min_length: Optional[int] = None
    
    # UI behavior
    visible: bool = True
    editable: bool = True
    sortable: bool = True
    searchable: bool = True
    
    # Filter behavior
    filterable: bool = False
    filter_type: str = "list"         # "list", "range", "boolean"
    grouping_function: Optional[Callable[[Any], str]] = None # Logic for branches (e.g. 1984 -> "1980s")
    
    # Mapping
    model_attr: Optional[str] = None  # Song model property (defaults to name)
    portable: bool = True
    
    # Query generation
    query_expression: Optional[str] = None  # Full SQL expression (for GROUP_CONCAT etc). If None, uses db_column.

# ==================== THE REGISTRY ====================

# Query parts (FROM, WHERE, GROUP BY are static; SELECT is generated from FIELDS)
QUERY_FROM = """
    FROM MediaSources MS
    JOIN Songs S ON MS.SourceID = S.SourceID
    LEFT JOIN MediaSourceContributorRoles MSCR ON MS.SourceID = MSCR.SourceID
    LEFT JOIN Contributors C ON MSCR.ContributorID = C.ContributorID
    LEFT JOIN Roles R ON MSCR.RoleID = R.RoleID
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

# NOTE: The order of this list MUST match the columns in BASE_QUERY!
FIELDS: List[FieldDef] = [
    FieldDef(
        name="path",
        ui_header="Path",
        db_column="MS.Source",
        visible=False,
        editable=False,
        filterable=False,
        searchable=False,
        required=True,
        portable=False,
        model_attr="source",
    ),
    FieldDef(
        name="file_id",
        ui_header="ID",
        db_column="MS.SourceID",
        field_type=FieldType.INTEGER,
        visible=False,
        editable=False,
        filterable=False,
        searchable=False,
        required=True,
        portable=False,
        model_attr="source_id",
    ),
    FieldDef(
        name="type_id",
        ui_header="Type",
        db_column="MS.TypeID",
        field_type=FieldType.INTEGER,
        visible=False,
        editable=False,
        filterable=False,
        searchable=False,
        required=False,
        portable=False,
    ),
    FieldDef(
        name="notes",
        ui_header="Notes",
        db_column="MS.Notes",
        visible=True,
        editable=True,
        filterable=False,
        searchable=True,
        required=False,
        portable=False,
    ),
    FieldDef(
        name="isrc",
        ui_header="ISRC",
        db_column="S.ISRC",
        visible=True,
        editable=True,
        filterable=False,
        searchable=True,
        required=False,
        portable=True,
    ),
    FieldDef(
        name="is_active",
        ui_header="Active",
        db_column="MS.IsActive",
        field_type=FieldType.BOOLEAN,
        visible=True,
        editable=True,
        filterable=True,
        searchable=False,
        required=False,
        portable=False,
    ),
    FieldDef(
        name="producers",
        ui_header="Producer",
        db_column="Producers",
        field_type=FieldType.LIST,
        visible=True,
        editable=True,
        filterable=True,
        searchable=True,
        required=False,
        portable=True,
        query_expression="GROUP_CONCAT(CASE WHEN R.Name = 'Producer' THEN C.Name END, ', ') AS Producers",
    ),
    FieldDef(
        name="lyricists",
        ui_header="Lyricist",
        db_column="Lyricists",
        field_type=FieldType.LIST,
        visible=True,
        editable=True,
        filterable=True,
        searchable=True,
        required=False,
        portable=True,
        query_expression="GROUP_CONCAT(CASE WHEN R.Name = 'Lyricist' THEN C.Name END, ', ') AS Lyricists",
    ),
    FieldDef(
        name="duration",
        ui_header="Duration",
        db_column="MS.Duration",
        field_type=FieldType.DURATION,
        visible=True,
        editable=True,
        filterable=False,
        searchable=False,
        required=True,
        portable=False,
        min_value=30,
    ),
    FieldDef(
        name="title",
        ui_header="Title",
        db_column="MS.Name",
        visible=True,
        editable=True,
        filterable=False,
        searchable=True,
        required=True,
        portable=True,
        min_length=1,
    ),
    FieldDef(
        name="is_done",
        ui_header="Status",
        db_column="S.IsDone",
        field_type=FieldType.BOOLEAN,
        visible=True,
        editable=True,
        filterable=True,
        searchable=False,
        required=False,
        portable=False,
        filter_type="boolean",
    ),
    FieldDef(
        name="bpm",
        ui_header="BPM",
        db_column="S.TempoBPM",
        field_type=FieldType.INTEGER,
        visible=True,
        editable=True,
        filterable=True,
        searchable=False,
        required=False,
        portable=True,
        min_value=0,
        filter_type="range",
    ),
    FieldDef(
        name="recording_year",
        ui_header="Year",
        db_column="S.RecordingYear",
        field_type=FieldType.INTEGER,
        visible=True,
        editable=True,
        filterable=True,
        searchable=True,
        required=True,
        portable=True,
        grouping_function=decade_grouper,
    ),
    FieldDef(
        name="performers",
        ui_header="Artist",
        db_column="Performers",
        field_type=FieldType.LIST,
        visible=True,
        editable=True,
        filterable=True,
        searchable=True,
        required=True,
        portable=True,
        min_length=1,
        query_expression="GROUP_CONCAT(CASE WHEN R.Name = 'Performer' THEN C.Name END, ', ') AS Performers",
    ),
    FieldDef(
        name="composers",
        ui_header="Composer",
        db_column="Composers",
        field_type=FieldType.LIST,
        visible=True,
        editable=True,
        filterable=True,
        searchable=True,
        required=True,
        portable=True,
        min_length=1,
        query_expression="GROUP_CONCAT(CASE WHEN R.Name = 'Composer' THEN C.Name END, ', ') AS Composers",
    ),
    FieldDef(
        name="groups",
        ui_header="Groups",
        db_column="S.Groups",
        visible=True,
        editable=True,
        filterable=True,
        searchable=True,
        required=False,
        portable=True,
    ),
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
