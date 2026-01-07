# Logic: Artist Merging & Alias Linking

This document defines the rules for handling artist merges and alias linking in the `ArtistDetailsDialog` and `ArtistPickerDialog` workflow. The goal is to separate user-intent (Linking/Moving Names) from database reality (Merging IDs), prioritized by **User Perspective Data Loss**.

## Core Concept
The user wants to "Link Name A to Person B". The system must determine if this actions is:
1.  **Trivial:** Just adding a new string.
2.  **Redirection:** Moving a string from one person to another (Safe).
3.  **Destructive:** Destroying a distinct person's profile to merge it (Unsafe).

## Scenarios & Handling

### 1. The "Dead Alias" (Empty Shell)
**Scenario:** User adds "Ziggy Stardust". "Ziggy" exists in the DB but has 0 Songs, 0 Aliases, no Group Memberships, and no custom Notes.
*   **User Intent:** "Use this name."
*   **System State:** Independent Contributor #99 (Empty).
*   **Action:** **Silent Merge.** Absorb ID #99 into Current Artist.
*   **Data Loss:** None (Shell is disposable).
*   **UI:** No Popup. Instant success.

### 2. The "Alias Re-Link" (Stealing a Name)
**Scenario:** User searches for "The Ghost of Mixes". System finds it is currently an alias for "DJ Someone".
*   **User Intent:** "The Ghost of Mixes is actually an alias for Me, not DJ Someone."
*   **System State:** "The Ghost" is an alias string record owned by Contributor #50 ("DJ Someone").
*   **Action:** **Move Alias.** Update `ContributorAliases` to point "The Ghost" to Current Artist.
*   **Data Loss:** None. "DJ Someone" remains intact. "The Ghost" just points to a new home.
*   **UI:** " 'The Ghost' is currently linked to 'DJ Someone'. **[Move Alias]** "

### 3. The "Person with Alias" (Identity Demotion)
**Scenario:** User adds "Freddie Mercury" (ID #10). "Freddie" has an alias "Farrokh" (ID #10a). User links him to "Queen".
*   **User Intent:** "Freddie belongs to Queen." (Or "Freddie is Queen" in a merge context).
*   **System State:** Independent Contributor #10 with child data.
*   **Action:** **Merge/Absorb.** ID #10 is deleted. ID #10's songs move to "Queen". "Freddie" becomes an alias of "Queen". "Farrokh" becomes an alias of "Queen".
*   **Data Loss:** Segregation is lost. You cannot easily split them later.
*   **UI:** **Warning.** "Merging 'Freddie' will break links to his aliases. Songs will be mixed."

### 4. The "Independent Person" (Destructive Merge)
**Scenario:** User adds "David Bowie" (ID #20) to "David Jones" (ID #21). Bowie has songs, notes, and a biography.
*   **User Intent:** "These are the same person."
*   **System State:** Two distinct profiles with data.
*   **Action:** **Merge/Absorb.** ID #20 is deleted.
*   **Data Loss:** **Profile Metadata Lost** (Bio, Notes, Birthday). **Song Separation Lost** (All songs mixed into ID #21).
*   **UI:** **PERMANENT DATA LOSS WARNING.** "Merging will DELETE profile notes. Songs will be mixed and cannot be separated."

## Implementation Details

### Required Checks (`ArtistDetailsDialog._add_alias`)
1.  **Alias Check:** Did the picker return a `matched_alias` string?
    *   **Yes:** Trigger **Scenario 2 (Move Alias)**.
2.  **Impact Check:** If no alias string, check the Target Contributor object.
    *   `song_count > 0`? -> **Destructive.**
    *   `has_aliases`? -> **Destructive (Complexity).**
    *   `has_members`? -> **Destructive (Complexity).**
    *   `has_metadata` (Sort Name != Name)? -> **Destructive.**
3.  **Fallback:** If all false -> **Scenario 1 (SIlent Merge).**

### Required Methods
*   `ContributorService.move_alias(alias_name, old_owner_id, new_owner_id)`: Needed for Scenario 2.
