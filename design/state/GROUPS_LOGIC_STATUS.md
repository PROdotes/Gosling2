# Groups Logic Status (Dec 22 Update)

## 1. The Core Conflict: ID3 (Flat) vs Database (Relational)

We are bridging two worlds:
1.  **ID3 Tags (Legacy/Flat)**:
    *   `TPE1` (Lead Performer): A string list (e.g., "Nirvana").
    *   `TIT1` (Content Group): A grouping string (e.g., "Disc 1").
    *   *Constraint*: ID3 has no concept of "Dave Grohl is in Nirvana".

2.  **Database (Gosling 2/Relational)**:
    *   **Entities**: `Contributors` table distinguishes `Type` ('person' vs 'group').
    *   **Relationships**: `GroupMembers` table links Persons to Groups.
    *   **Roles**: `MediaSourceContributorRoles` links Entities to Songs (as 'Performer', 'Composer', etc).

## 2. The "Zombie" Column (`S.Groups`)
*   **Status**: **DEAD / DISABLED**.
*   **Why**: It was a failed attempt to map `TIT1` directly to a conceptual "Group".
*   **Directive**: Do not use `S.Groups`. It remains in the schema only for extreme legacy compatibility.

## 3. The Current Architecture (Hybrid)
*   **Storage**:
    *   "Nirvana" is stored as a **Contributor**.
    *   `Type` should be `'group'` (Currently unenforced logic, strictly manual).
    *   "Nirvana" is linked to "Lithium" via `Role='Performer'`.
    *   "Dave Grohl" is linked to "Nirvana" via `GroupMembers` (Manual only).
*   **Missing Logic**:
    *   There is no **Service Layer** enforcement to ensure `GroupMembers` only links Groups to People.
    *   There is no **UI** to toggle `Type` ('person'/'group').
    *   The **Search Logic** (`get_by_unified_artists`) is currently simplistic and does not traverse the Group/Member graph (partially mitigated by Service layer).

## 4. UI/Filter Requirements
The "Unified Artist" filter list (`unified_artist` field) MUST populate with:
1.  **Performers**: All Contributors link to songs with `Role='Performer'` (includes Groups and People).
2.  **Groups**: All Contributors with `Type='group'` (even if not linked to a song directly).
3.  **Aliases**: All entries in `ContributorAliases` (e.g., "Dale Nixon").

User Expectation: Searching/Filtering for an alias (e.g. "Dale Nixon") must show songs by the resolved entity ("Dave Grohl") and their groups ("Nirvana").

## 4. The Gap (Technical Debt)
*   **Danger**: Because `Type` is unenforced, we could accidentally link two people as "members" of each other.
*   **Future Plan**:
    1.  Implement `ContributorService` to enforce `Type`.
    2.  Update `SongRepository` search to traverse the graph (Person -> Group -> Song).
    3.  Build UI for managing relationships.

## 5. Summary
The **Schema** is sound and ready for complex relations.
The **Application Logic** is currently primitive and treats everything as flat Performers.
**Legacy Sync (T-06)** can proceed independently of this feature.
