# [GOSLING3] The Big Picture: Road to Parity

This document outlines the phased transition from the legacy Gosling2 architecture to the decoupled, distributed Gosling3 model.

## 1. Phase 0: The Core Foundation (`v3core`)
**Goal**: Establish the "Laws of Physics" for the data.
- **Model Lockdown**: Implement all Pydantic models with `extra="forbid"` to prevent ghost fields.
- **The Identity Resolver**: Build the stateless service that handles the "Grohlton/Farrokh" expansion logic.
- **Clean Repositories**: Create repositories that return Pydantic objects instead of raw tuples.
- **Integrity Tests**: Re-implement the "10 Layers of Yell" to ensure the DB never drifts from the models.

## 2. Phase 1: The Engine Background (`v3engine`)
**Goal**: Build the independent, 24/7 service.
- **API Hub (FastAPI)**: The central gateway for all library and playback commands.
- **Audio Ownership**: Implement the Playback Service using a background audio thread (resilient to UI crashes).
- **Ingestion Service**: The "No-Unzip-in-UI" worker. Background hashing, unzipping, and tag-parsing.
- **State Broadcast**: Implement the WebSocket bus to notify all clients of library/playback changes.

## 3. Phase 2: The Studio Client (`v3studio`)
**Goal**: Build the high-power management interface.
- **ID-Skeleton UI**: Implement the virtualized 100k-song scrollable table.
- **Intent-Based Search**: The "Jazler-Debounce" search with identity expansion.
- **Deck Control**: A "Dumb Client" UI that strictly sends commands to the Engine API.
- **Remote-First**: Ensure the Studio works perfectly whether the Engine is local or at the station.

## 4. Phase 3: The Remote/Web Bridge (`v3remote`)
**Goal**: Enable "Work From Home" and mobile access.
- **Web Dashboard**: A lightweight browser interface for monitoring and remote control.
- **Stream Ingestion**: Enable binary file uploads to the Engine for remote song additions.
- **Shared State**: Zero-latency updates between the Studio and Web via the Engine Hub.

## 5. Phase 4: Migration & Parity
**Goal**: Import the legacy and reach feature-complete status.
- **The Great Migration**: A script to map the Gosling2 SQLite data into the new v3 Schema.
- **Audit Logs**: Implement the high-performance audit trail for all identity and metadata changes.
- **Rotation Engine**: Finalize the automation rules using the Identity Resolver for cooldowns.

---

## Technical Transformation Map

| Feature | Gosling2 (Legacy) | Gosling3 (Future) |
| :--- | :--- | :--- |
| **Logic Location** | Mixed in UI Widgets (SidePanel) | Isolated in Engine Services |
| **Data Handling** | Manual Tuple Mapping | Strict Pydantic Models |
| **Scale** | Freezes at 10k songs | Fluid at 100k+ (ID-Skeleton) |
| **Identities** | Simple text-matching | Relational Expansion (Resolver) |
| **Communication** | Direct Method Calls | REST / WebSocket API |
| **Audio** | Owned by UI Thread | Owned by Background Service |

## Current Progress: [█░░░░░░░░░] 10%
- [x] Architecture Planning
- [x] Identity Resolve Proof-of-Concept
- [x] Scaling Strategy (ID-Skeleton)
- [ ] Base Core Models (in code)
- [ ] Identity Resolver (in code)
