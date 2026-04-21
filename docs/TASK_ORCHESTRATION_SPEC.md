# Task Orchestration Spec
**Status**: Proposal / Architectural Debt
**Topic**: Decoupling Long-Running Operations from Client Sessions

## 1. The Core Problem
Most heavy lifting (WAV conversion, directory scanning, bulk moving) is currently executed via **blocking HTTP requests**.
- If the browser tab closes, the operation might be orphaned or fail to finalize state.
- If multiple frontends (Web + PyQt) are added, there is no centralized state to track "What is the server doing right now?".
- The backend is a "slave" to the request-response cycle rather than an autonomous worker.

## 2. The Vision: "Fire and Forget"
Clients should submit a request, receive a `TaskID`, and disconnect. The backend completes the work independently.

### Proposed Workflow
1. **Submission**: `POST /api/v1/tasks/convert-wav?path=...` -> Returns `{"task_id": "uuid", "status": "PENDING"}`.
2. **Execution**: Backend runs the task (FFmpeg, DB update) and updates a centralized `Tasks` table or in-memory registry.
3. **Discovery**:
   - **Polling**: Clients call `GET /api/v1/tasks/{id}` to check progress.
   - **Streaming/Events**: A global `/api/v1/events` stream notifies all connected clients (Web, PyQt) when ANY task finishes.

---

## 3. Implementation Targets

### Phase A: The Task Registry
Add a simple `TaskService` that tracks:
- `task_id`, `type` (CONVERT, INGEST, MOVE), `status` (PENDING, RUNNING, DONE, FAILED), `payload`, `result`.

### Phase B: Refactor WAV Conversion
Transition `POST /api/v1/ingest/convert-wav` to use the Task Registry.
- The request returns immediately.
- FFmpeg runs in a background thread/process.
- On finish, the task marks itself `DONE` and the frontend updates its state via discovery.

### Phase C: Bulk Operations
Move `scan_folder` and `move_to_library` into this pattern. This prevents timeouts on huge libraries.

---

## 4. Multi-Frontend Ready
By decoupling the process, a user could:
1. Start a 100-song import on the **Web Interface**.
2. Close the browser.
3. Open the **PyQt Desktop App** and see the imports still processing in a "Background Tasks" panel.

---

## 5. Technical Constraints
- **Concurrency**: Use a `ThreadPoolExecutor` or `asyncio.create_task` with a limited semaphore to prevent server saturation.
- **Persistence**: Task status should ideally survive a server restart (DB-backed tasks table).
