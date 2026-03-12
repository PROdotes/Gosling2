# [GOSLING3] v3core Model Specification

This spec defines the strictly-typed data structures for the Core layer. These models are Pydantic-based for automatic JSON serialization (Engine API) and validation.

## 1. Identity Models

### `Identity`
The persistent human or group entity.
```python
class Identity(BaseModel):
    identity_id: int
    identity_type: Literal['person', 'group', 'placeholder']
    legal_name: Optional[str] = None
    biography: Optional[str] = None
    # No "ArtistName" logic here. Identity is the "Ghost in the Machine".
```

### `ArtistName`
The "Face" of an identity.
```python
class ArtistName(BaseModel):
    name_id: int
    owner_identity_id: int
    display_name: str
    sort_name: Optional[str] = None
    is_primary: bool = False
```

### `IdentityRelation`
The temporal or structural link between two identities (e.g. Person X is a member of Group Y).
```python
class IdentityRelation(BaseModel):
    parent_id: int  # The Group / Collective
    child_id: int   # The Person / Member
    role_name: Optional[str] = "member"
    # Note: This is an Identity-to-Identity link, NOT a Name link.
```

## 2. The Credit Model

### `SongCredit`
The link between a song and an actor.
```python
class SongCredit(BaseModel):
    source_id: int
    name_id: int
    role_id: int
    # Logic: 
    # 1. Track -> NameID (The "Sticker" on the record)
    # 2. NameID -> IdentityID (The "Actor" behind the name)
    # 3. IdentityID -> IdentityRelation -> Other Identities (The "Entanglement")
```

## 3. The Song "View" Model
The unified object used by the Engine and Studio.

### `Song`
```python
class Song(BaseModel):
    source_id: int
    media_name: str  # The Title
    path: str
    duration: float
    type_id: int
    
    # Nested Data (Resolved by Repository)
    credits: List[SongCredit]
    albums: List[SongAlbum]  # M2M: Each bridge contains context (Track#, Disc#, IsPrimary)
    tags: Set[str] = Field(default_factory=set)
    primary_genre: Optional[str] = None
    
    # Metadata
    bpm: Optional[int] = None
    year: Optional[int] = None
    isrc: Optional[str] = None
    
    # State
    processing_status: int = 1
    is_active: bool = True
```

### `SongAlbum`
The temporal/contextual link between a song and an album.
```python
class SongAlbum(BaseModel):
    source_id: int
    album_id: int
    is_primary: bool = True
    track_number: Optional[int] = None
    disc_number: Optional[int] = 1
    
    # Resolved Metadata
    album_title: str
    album_type: Optional[str] = None
    publishers: List[str] = []
```
```

## 4. Why this prevents Spaghetti?
1.  **Immutability**: Models are typically loaded from the DB and passed through the Engine API. Changes require a explicit `Repository.update()` call with a fresh DTO.
2.  **No Logic**: A `Song` object cannot "calculate its own identity set". That is the job of the `IdentityService`.
3.  **Strict Serializing**: Because these are Pydantic, the Engine doesn't have to manually build JSON. `song.model_dump_json()` just works.
