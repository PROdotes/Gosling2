# Future Refactor: The "Identity Hub" (Artist Identity Editor)

## 1. Context & Objective
Currently, **Gosling2** implements a "Truth-First" database schema where every artist alias (`ArtistName`) is owned by a root **Identity**. However, the UI currently interacts with these as individual "chips" or separate alias records. 

**Objective:** Transition the artist editing experience from "Alias-First" to "Identity-First" by implementing a centralized **Identity Hub**.

## 2. The Core Concept
Instead of opening a "Rename Alias" modal when clicking an artist chip (e.g., clicking "Joanne"), the app should open the **Identity Hub** for the parent identity (e.g., "Lady Gaga").

### Key Features of the Identity Hub:
- **Primary Headline:** Uses the `is_primary=True` flag to determine the main title of the modal, regardless of which alias was clicked to open it.
- **Alias Tree Management:** Displays all linked aliases as chips. Allows adding new aliases or fixing typos in existing ones without losing the link to the parent identity.
- **Member/Group Connections:** Shows constituent persons (for groups) or parent groups (for persons).
- **Global Metadata:** A single place to store identity-level data like Date of Birth, Legal Name, or Country of Origin.

## 3. Why it Matters (The Payoff)
- **Data Integrity:** Prevents the creation of "Ghost Identities" where the same person is accidentally added multiple times under different aliases.
- **Deep Search:** Ensures that a search for "Lady Gaga" correctly returns songs where she is credited as "Stefani Germanotta" or "Joanne."
- **Efficiency:** Renaming a primary identity once propagates the "Headline" change across the entire library while preserving the specific alias used on individual song credits.

## 4. Implementation Debt (The "Revisit" List)
- [ ] **UI Action Hijack:** Update `open-edit-modal` to always fetch the `identity_id` and load the full `IdentityView` instead of just the `ArtistName`.
- [ ] **Recursive Renderer:** Build a modal renderer that can handle the recursive `members` and `groups` lists from the `IdentityView`.
- [ ] **Primary Toggle:** Add a way to "Promote" an alias to be the new `is_primary` name for an identity.

## 5. Current Workaround
We are currently focusing on **Airplay Readiness**. We use the `is_primary` flag in the backend to ensure search works, but we accept the UI limitation where aliases are edited individually for now.

---
*Note: This refactor is low priority until the core "Airplay Prep" metadata sprint is complete.*
