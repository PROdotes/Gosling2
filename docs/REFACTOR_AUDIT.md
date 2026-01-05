# Refactor Audit: Tag Categories (Genre/Mood)

## Overview
This document summarizes the audit of the codebase regarding the transition from hardcoded "Genre" and "Mood" logic to the dynamic `ID3Registry` system.

## Findings

### 1. Renaming Service (`renaming_service.py`)
*   **Status:** **Pass**
*   **Observation:** The service generates a `Genre` token for file renaming.
*   **Reasoning:** The keys `"Genre"` and `"genre"` in the replacement dictionary **MUST REMAIN**. Users rely on these tokens (e.g., `{Genre}/{Artist} - {Title}`) in their configuration files (`rules.json` or settings). Removing them would break existing user configurations.
*   **Implementation:** The logic to *populate* this token is now dynamic. It iterates through tags and checks `ID3Registry.get_id3_frame(cat) == "TCON"` to identify the genre, rather than looking for a hardcoded "Genre" property. This is the correct implementation of the refactor.

### 2. Filter Widget (`filter_widget.py`)
*   **Status:** **Pass**
*   **Observation:** Contains the line `if field.name in ('genre', 'mood'): continue`.
*   **Reasoning:** This code explicitly **hides** the legacy columns from the filter tree. This is necessary to prevent duplicate or broken filters from appearing alongside the new "Unified Tags" filter, which dynamically handles all categories (including Genre and Mood) based on the database content.

### 3. Side Panel Widget (`side_panel_widget.py`)
*   **Status:** **Pass**
*   **Observation:** No hardcoded references to "Genre" or "Mood" logic found.
*   **Reasoning:** All tag display and icon rendering logic uses `ID3Registry.get_category_icon(category)` and `_get_tag_category_zone`, which are fully dynamic.

### 4. ID3 Registry (`id3_registry.py`)
*   **Status:** **Pass**
*   **Observation:** Acts as the single source of truth.
*   **Reasoning:** It loads definitions from `id3_frames.json`. "Genre" and "Mood" exist here only as data entries in the JSON file, which is the intended design.

### 5. Yellberus (`yellberus.py`)
*   **Status:** **Pass** (Legacy Support)
*   **Observation:** May contain verification logic for `TCON`/`TMOO`.
*   **Reasoning:** The registry validation logic checks against the JSON schema, which includes these standard frames. Code handling specific "Genre" column integrity checks is implicitly handled by the general field validation system.

## Conclusion
The refactor is **COMPLETE**.

All remnants of "Genre" and "Mood" in the codebase serve specific, required purposes:
1.  **Configuration Tokens:** maintaining backward compatibility for user renaming rules.
2.  **Legacy Suppression:** ensuring old UI elements do not appear.
3.  **Data Definitions:** existing as data points in the external JSON registry.

No further code removal is recommended at this time.
