# Implementation Plan: Identity Resolution [GOSLING2]

## 1. Domain Model Update (`src/models/domain.py`)
Add the `Identity` model to represent the resolved entity.

```python
class Identity(DomainModel):
    id: int
    type: str  # person, group, placeholder
    display_name: str
    legal_name: Optional[str] = None
    
    # The Tree Connections
    aliases: List[str] = []        # Stage names from ArtistNames
    members: List["Identity"] = [] # If type='group', the constituent persons
    groups: List["Identity"] = []  # If type='person', the parent groups
```

## 2. Repository Implementation (`src/data/identity_repository.py`)
Create `IdentityRepository` inheriting from `BaseRepository`.

### Key Methods:
- `get_by_id(identity_id: int) -> Optional[Identity]`: Hydrate basic Identity fields.
- `resolve_full(identity_id: int) -> Optional[Identity]`:
    1. Fetch `Identity` basic info.
    2. Fetch `aliases` from `ArtistNames` WHERE `OwnerIdentityID = ?`.
    3. If `type == 'group'`: Fetch `members` (Identity objects) from `GroupMemberships` where `GroupIdentityID = ?`.
    4. If `type == 'person'`: Fetch `groups` (Identity objects) from `GroupMemberships` where `MemberIdentityID = ?`.
- `resolve_name_pool(name_ids: List[int]) -> Dict[int, Identity]`: Batch resolution for performance.

## 3. Testing Strategy (`tmp/test_identity.py`)
- **Test 1: Basic Hydration**: Verify `get_by_id` returns correct fields.
- **Test 2: Alias Resolution**: Ensure all `ArtistNames` associated with an Identity are returned.
- **Test 3: Group Expansion**: Verify `group` identity expands to its `members`.
- **Test 4: Membership Expansion**: Verify `person` identity expands to its `groups`.

## 4. Instrumentation
- Use `src.services.logger` for entry/exit logging.
- Log `resolve_full` duration and depth (staying at 1-level depth as per brain constraints).

## 5. Lookup Sync
- Update `docs/lookup/data.md` with the new repository and model.
