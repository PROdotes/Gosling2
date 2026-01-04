# T-05: Audit Log Viewer (The Flight Recorder) Implementation Plan

## 🎯 Objective
Transform the `LogViewerDialog` into a "Pro Console" diagnostic hub that provides a visual audit trail of every database change (`ChangeLog`) and significant system action (`ActionLog`). This ensures manual verification of data integrity is tactile and immediate.

---

## 🏗️ Architecture & Data Flow

0.  **Service Layer Rectification (Missing Links)**:
    *   Implement `PublisherService` and `AlbumService` to decouple dialogs from raw repositories.
    *   This ensures all "Manager" dialogs use a consistent Service -> Repository pattern.
1.  **Storage**: 
    *   `ActionLog`: High-level events (e.g., "Imported 50 files", "Database Truncated").
    *   `ChangeLog`: Field-level diffs (e.g., "Field 'Title' changed from 'A' to 'B'").
2.  **Access**: `AuditService` wraps `AuditRepository` to provide clean, dictionary-based history to the UI.
3.  **UI**: `LogViewerDialog` refactored with `QTabWidget` to separate "Diagnostic Logs" from "Audit History".

---

## 🛠️ Phase-by-Phase Breakdown

### **Phase 0: Service Layer Rectification (Prerequisite) - ✅ COMPLETED**
- [x] **PublisherService**: Created and wired into `PublisherManagerDialog`.
- [x] **AlbumService**: Created and wired into `AlbumManagerDialog`.
- [x] **ContributorService**: Refactored `ArtistManagerDialog` to use Service Layer (The "Rabbit Hole").
- [x] **AuditService Integration**: Foundation laid, ready for UI wiring.

### **Phase 1: `AuditHistoryDialog` (Standalone Chassis) - ✅ COMPLETED**
- [x] **New Dialog**: Create `src/presentation/dialogs/audit_history_dialog.py`.
- [x] **UI Layout**:
    - **Header**: Search bar + "Truncate History" button (Pro style).
    - **Main Area**: `QTableView` for the data.
    - **Footer**: Status bar showing record count.

### **Phase 2: Audit Engine (The Wiring) - ✅ COMPLETED**
- [x] **Audit Model**: Implement a `QAbstractTableModel` (not StandardItemModel, for performance) specifically for audit data.
- [x] **Data Fetching**: Use `AuditService.get_recent_changes()` to populate the table.
- [x] **Auto-Refresh**: Simple reload button or timer.

### **Phase 3: Visual Identity (Data Visualization) - ✅ COMPLETED**
- [x] **Pro Console Style**:
    - **INSERT**: Green tint row.
    - **UPDATE**: Amber tint for `NewValue` cell.
    - **DELETE**: Red tint row / strikethrough.
- [x] **Formatting**: Timestamps in readable local time, formatted via `MetadataService` utilities if possible.

### **Phase 4: Integration - ✅ COMPLETED**
- [x] **Main Window**: Wire up the "HISTORY" toggle in `TerminalHeader` (or rather `CustomTitleBar`) to open this new dialog.

---

## 🧪 Validation & Testing
- [x] Manual: Edit metadata and verify logs
- [x] Automatic: Unit tests for View Logic and Service Integration
- [x] Verified: No "Truncate" button exists (Safety)

---

## 📂 Impacted Files
- `src/presentation/dialogs/audit_history_dialog.py` (New File)
- `src/presentation/views/main_window.py` (Wiring the button)
- `src/business/services/audit_service.py` (Already exists)

