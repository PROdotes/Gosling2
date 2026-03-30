# GOSLING2: Re-Planning & Status Audit (2026-03-30)

## 1. The Core Misalignment
To clarify any "mixed up" concepts:
*   **Backend Status**: **100% Core Ready.** `CatalogService` and the API endpoints for full Metabolic Updates (CRUD for Credits, Albums, Tags, Publishers) are implemented and tested.
*   **Frontend Status**: **Skeleton Stage (30%).** We have a display-only Dashboard. The scalars (Title, Year, etc.) have partial "Edit" scaffolding, but the "Functional Skeleton" for relationships, audio, and discovery is currently missing from the JavaScript layer.

---

## 2. General Project Status (Pillar Audit)

### **Pillar A: Discovery Engine (Advanced Filters)**
*   **Spec**: `PHASE_2_ADVANCED_FILTERS_SPEC.md` is complete.
*   **Status**: 0% UI / 50% Backend. Need the `/filter` endpoint in the Router and the Sidebar UI.
*   **Current Goal**: Implement the `ALL/ANY` logic toggle and Sidebar search.

### **Pillar B: Workflow Engine**
*   **Spec**: `SONG_WORKFLOW_SPEC.md` is complete.
*   **Status**: Backend implemented (`ProcessingStatus` 2/1/0).
*   **Current Goal**: UI indicators for "Status 0 (Approved)" logic.

### **Pillar C: Metabolic Foundation (Relationship CRUD)**
*   **Spec**: `PHASE_2_METABOLIC_UPDATES_SPEC.md` is complete.
*   **Status**: **Backend 100% / Frontend 10%**.
*   **Current Goal**: "Finish the chips." We need the JavaScript `api.js` bridge functions for all relationship types and the Modal system to drive them.

### **Pillar D: Audio Player**
*   **Status**: Planned.
*   **Current Goal**: A functional stream API and a global footer player to anchor the "Real Life" experience.

---

## 3. High-Level Weekly Plan: "The Skeleton Sprint"

The strategy is to **get all functional parts in** using MVP styling first, then pivot to the "Premium Tier" redesign once the engine is complete.

### **Phase 1: Finish the "Metabolic" Logic (Mon-Tue)**
*   **Monday**: Finalize the remaining 10+ API mutation functions for Artists, Albums, Tags, and Publishers in `api.js`.
*   **Tuesday**: Build the **Universal Modal Skeleton** and the **Autocomplete Engine**. Ensure clicking a "Chip" opens the correct edit context and saves to the DB.

### **Phase 2: The Audio & Discovery Bridge (Wed-Thu)**
*   **Wednesday**: Build the `/audio/stream` endpoint and the **Global Playback Footer**. 
*   **Thursday**: Implement the **Filter Sidebar**. Wire the search bar to filter *sidebar values* and toggle `ALL/ANY` logic modes.

### **Phase 3: The "Premium" Redesign (Fri-Week 2)**
Once the skeleton is alive, we move beyond the "MVP" look:
*   Transition to a curated harmonious color palette (HSL-based).
*   Implement glassmorphism and subtle micro-animations for interactions (hover effects, smooth transitions).
*   Replace standard browser layouts with a modern, high-tier typography system.

---

## 4. Next Tooling Pass (For Review)
When we start "coding at work," I will focus on these missing "Skeletal" parts in this order:
1.  **API Bridge**: Finish all relationship CRUD functions.
2.  **Universal Modal**: A single container for all relationship editing.
3.  **Filter Sidebar**: The logic toggle and dynamic category population.
4.  **Audio Player**: The streaming foundation.
