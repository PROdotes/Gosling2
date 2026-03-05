# [GOSLING3] Identity & Lookup Specification

This document defines the authoritative logic for the **Linked Identity Model** and the **High-Performance Search Engine**. It bridges the gap between human identities, artist aliases, and complex collaboration graphs.

## 1. Core Data Entities

| Entity | Purpose | Example |
| :--- | :--- | :--- |
| **Identity** | The persistent human or group entity. | `ID: 50` (Person: Farrokh Bulsara) |
| **ArtistName** | A specific "Sticker" (alias) owned by an Identity. | `NameID: 7` ("Freddie Mercury") |
| **Relationship** | A membership link between two Identities. | `ID: 50` is a member of `ID: 90` (Queen) |
| **SongCredit** | Links a `Song` to an `ArtistName` and a `Role`. | `Song: 101` -> `Name: 7` (Role: Performer) |

---

## 2. The Identity Resolution Protocol (The "Ghost" Bridge)

To handle 60k+ songs and complex aliases, we use an **ID-First Resolution** rather than string-matching.

### Step 1: Resolve the "Active Identity Set"
When a song is selected (for Playback or Search), the system resolves the **Active Set**:
1.  **Resolve Alias**: Map the credited `NameID` to its `OwnerIdentityID`.
2.  **Horizontal Expansion**: Find all members if the Identity is a **Group**.
3.  **Vertical Expansion**: Find all groups if the Identity is a **Person**.
4.  **Result**: A `Set[int]` of all Identities "in the room."

### Step 2: The Song Discovery Logic (Two-Pass)
To find all songs for "Dave Grohl" (Nirvana, Foo Fighters, etc.):
1.  **Identity Pass**: Resolve the Active Set `{Dave, Nirvana, Foo Fighters}`.
2.  **Name Pass**: Find every `NameID` owned by **any** Identity in that set.
3.  **Credit Pass**: Select all `SongIDs` from `SongCredits` where `NameID` is in that name set.
    - *Scale Note*: This uses indexed integer lookups. It handles 100k songs in <5ms.

---

## 3. High-Performance Search UI (The "Jazler Pattern")

To prevent "Search Lag" while typing, the Studio Client implements the **Staged Debounce**.

### Tier 1: Surface Discovery (Debounce: 50ms)
- **Scope**: Simple text match on `ArtistNames`. No graph expansion.
- **Limit**: **Top 20 results** (The Jazler Gate).
- **UX**: Instant feedback for typos. Shows names like "Bob Dylan" or "The Beatles."

### Tier 2: Deep Resolution (Debounce: 250ms)
- **Trigger**: User stops typing (Intent established).
- **Scope**: Full Identity expansion (Grohlton Expansion).
- **Limit**: **Unlimited**. Populate the full library view.
- **Visuals**: Primary results appear first; related group tracks pop in milliseconds later via the async resolve.

---

## 4. Scalability: The ID-Skeleton Architecture

For 100k+ libraries, we implement the **YouTube Preload Hack**:

1.  **RAM Skeleton**: At startup, load all `SongIDs` into a sorted Python list (~1MB RAM for 100k songs).
2.  **Virtual View**: The UI Table says it has 100,000 rows, but only creates UI objects for the ~30 visible rows.
3.  **Zone Fetching**: As the user scrolls (even at "Speed Hack" velocities), the Model fetches metadata in chunks of 100 based on the IDs in the RAM Skeleton.
4.  **Async Refresh**: The UI never blocks on the DB. If data isn't ready for a row, show a placeholder. Once the indexed DB query returns, "pop" the text in.

---

## 5. Summary of Anti-Spaghetti Laws
1.  **No Direct Identity-on-Song**: Songs point to Names. Names point to Identities. This preserves historical accuracy (Cat Stevens vs. Yusuf Islam).
2.  **Zero-Join Limit**: Never write a JOIN deeper than 3 tables. Perform graph expansion in the `IdentityService` using Python and fast, separate SQL hits.
3.  **Atomic Identities**: Adding a new alias for an artist (e.g., Oliver Dragojevic) touches **one row** in `ArtistNames`. It never requires updating thousands of tracks.
