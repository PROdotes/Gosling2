# Logic: Artist Merging & Alias Linking

This document defines the rules for how the system handles artist names. The priority is **User Intent** and **Searchability**. From the user's perspective, no information is ever lost during a merge because names are simply consolidated into a single searchable identity.

## Core Concept
1.  **Search is King**: If you link "Freddie Mercury" to "Farrokh Bulsara", searching for either name will return all the same songs.
2.  **Names are Preserved**: Merging does not delete names. It transforms a "Primary Name" into an "Alias".
3.  **Action = Intent**: If a user renames an artist or links a name to another artist, they have already expressed their intent. The system should execute that intent silently.

## Scenarios & Handling

### 1. The Trivial Link (Silent)
**Scenario:** Linking a name (e.g., "The Ghost") that is currently independent or an empty shell.
*   **User Goal:** "This name belongs to this artist."
*   **Result:** The name is linked. All songs previously under that name are now searchable under the main artist. 
*   **UI:** **Silent.** The action is the confirmation.

### 2. The Alias Re-Link (Move Name)
**Scenario:** A user wants to use a name that is currently linked as an alias to someone else.
*   **User Goal:** "This name actually belongs here, not there."
*   **Result:** The name is moved to the new artist.
*   **UI:** **Prompt.** Small confirmation: " '{name}' is linked to '{artist}'. Link it here instead? "

### 3. The Identity Merge (Silent)
**Scenario:** Merging "Freddie Mercury" into "Queen".
*   **User Goal:** "Consolidate these."
*   **Result:** All songs are unified. "Freddie Mercury" becomes an alias of "Queen". Search remains perfect.
*   **UI:** **Silent.** Intent is implied.

### 4. The Baggage Merge (Prompt)
**Scenario:** Merging Artist A into Artist B, where both already have their own lists of aliases.
*   **User Goal:** "Combine these identities."
*   **Result:** The two groups of aliases are combined into one.
*   **UI:** **Prompt.** Single question: "Combine them?" (Only shown because we are merging two existing structures of names).

## Safety Principles
*   **Never warn about songs**: Songs are never "lost" or "deleted" during a merge; they are simply unified under a more accurate searchable identity.
*   **Never mention IDs**: The user doesn't care about database keys. Focus on the Names.

### 5. Click Redirection (The "Gustavo Rule")
*   **Rule**: Clicking an Alias or Group Member in the UI MUST redirect to the **Primary Identity**.
    *   *Example*: Clicking "Noelle" (Alias) redirects to "Gustavo" (Primary).
    *   *Mechanism*: The system automatically resolves ownership.

### 6. Unlinking Logic (The "Splitting Rule")
*   **Action**: "Removing" a name from an identity.
*   **Result**: The system **SPLITS** the name into a NEW, independent Identity.
    *   **NEVER DELETE**: Removing an alias MUST NOT delete the name record or its credits.
    *   **Outcome**: The name becomes a standalone artist again, preserving its history.
