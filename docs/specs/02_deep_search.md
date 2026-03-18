# Implementation Plan: Deep Search & Identity Resolution [GOSLING2]

## 1. Requirement
Searching for a string (e.g. "Grohl") should return:
- Songs with "Grohl" in the title.
- Songs credited to "Dave Grohl", "Grohlton", etc.
- Songs credited to "Nirvana" or "Foo Fighters" (if the Identity resolution identifies the link).

## 2. Technical Approach: The "UNION Search"
Instead of a massive JOIN that creates N+1 row explosions, we use a UNION of three distinct discovery paths to gather Song IDs, then hydrate the winners.

### Path A: Title Match
Direct search on `MediaSources.MediaName`.

### Path B: Credit Match (Surface)
Search for the string in `ArtistNames.DisplayName`.
This handles "Grohlton" -> Dave Grohl songs.

### Path C: Identity Match (Deep)
1. Find Identities matching the query (DisplayName or LegalName).
2. Resolve those Identities (Aliases/Groups/Members).
3. Gather all `ArtistNames` for those Identities.
4. Find all Songs credited to those `ArtistNames`.

## 3. Implementation Steps

### 3.1 `SongRepository.search_deep(query: str, limit: int = 50)`
Implement a single efficient SQL query using `UNION` and `IN` clauses.

```sql
SELECT {self._COLUMNS} {self._JOIN}
WHERE m.SourceID IN (
    -- Path A: Title
    SELECT SourceID FROM MediaSources WHERE MediaName LIKE ?
    UNION
    -- Path B: Direct Credit
    SELECT sc.SourceID 
    FROM SongCredits sc 
    JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
    WHERE an.DisplayName LIKE ?
    UNION
    -- Path C: Identity Membership (The Grohlton Check)
    SELECT sc.SourceID
    FROM SongCredits sc
    JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
    JOIN Identities i ON an.OwnerIdentityID = i.IdentityID
    WHERE i.IdentityID IN (
        -- Recursive check for Groups the person is in, or Persons in the group
        SELECT GroupIdentityID FROM GroupMemberships WHERE MemberIdentityID = (SELECT IdentityID FROM Identities WHERE DisplayName LIKE ?)
        UNION
        SELECT MemberIdentityID FROM GroupMemberships WHERE GroupIdentityID = (SELECT IdentityID FROM Identities WHERE DisplayName LIKE ?)
    )
)
LIMIT ?
```

### 3.2 `CatalogService.search_songs(query: str)`
Update to call `repo.search_deep`.

## 4. Testing
- Verify searching for a person returns their group's songs.
- Verify searching for a group returns its members' solo songs (Optional - check brain: "Person-type identities expand to their Groups, but Group-type identities do NOT expand to their members").
- I will stick to the brain's "Person -> Groups" expansion for deep search.
