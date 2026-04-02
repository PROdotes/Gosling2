import { checkIngestion, getDownloadsFolder, uploadFiles, scanFolder, getAcceptedFormats, convertAndIngest } from "../api.js";
import {
    escapeHtml,
    renderStatus,
} from "../components/utils.js";
import { openFilenameParserModal } from "../components/filename_parser_modal.js";

const PATH_INPUT_ID = "ingest-path-input";
const CHECK_BTN_ID = "ingest-check-btn";
const RESULTS_LIST_ID = "ingest-results";

/**
 * Recursively collect all File objects from DataTransferItemList.
 * Handles both files and directories.
 */
async function collectFilesFromItems(items, allowedExtensions) {
    const files = [];
    const queue = [];
    const exts = (allowedExtensions || []).map(e => e.toLowerCase());

    // Convert items to entries
    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.kind === "file") {
            const entry = item.webkitGetAsEntry();
            if (entry) {
                queue.push(entry);
            }
        }
    }

    // Process queue
    while (queue.length > 0) {
        const entry = queue.shift();

        if (entry.isFile) {
            const isAllowed = exts.some(ext => entry.name.toLowerCase().endsWith(ext));
            if (isAllowed) {
                // Get the actual File object
                const file = await new Promise((resolve) => entry.file(resolve));
                files.push(file);
            }
        } else if (entry.isDirectory) {
            // Read ALL directory contents (readEntries returns batches)
            const reader = entry.createReader();
            let batch;
            do {
                batch = await new Promise((resolve) => reader.readEntries(resolve));
                queue.push(...batch);
            } while (batch.length > 0);
        }
    }

    return files;
}

export async function renderIngestionPanel(ctx) {
    ctx.updateResultsSummary(0, "ingestion check");
    
    // Initialize session state for this panel
    const state = ctx.getState();
    if (!state.ingestTasks) {
        state.ingestTasks = [];
    }

    const DROP_ZONE_ID = "ingest-drop-zone";
    let downloadsFolder = "";
    let allowedExtensions = [];

    try {
        const [folder, exts] = await Promise.all([
            getDownloadsFolder(),
            getAcceptedFormats()
        ]);
        downloadsFolder = folder;
        allowedExtensions = exts;
    } catch (e) {
        console.error("Failed to load ingestion configuration:", e);
        // No fallbacks. UI will handle missing config.
    }

    ctx.elements.resultsContainer.innerHTML = `
        <div class="ingestion-view">
            <div class="ingestion-header">
                <div class="section-title">File Verification</div>
                <p class="muted-note">Paste an absolute file path or drag a file here.</p>
            </div>

            <div class="ingest-drop-zone" id="${DROP_ZONE_ID}">
                <div class="drop-zone-content">
                    <div class="drop-zone-icon">+</div>
                    <div class="drop-zone-label">Drop file here for instant ingestion</div>
                    <div class="drop-zone-hint muted-note">or paste path below</div>
                    <div class="drop-zone-loading" style="display: none;">
                         <div class="spinner"></div>
                         <span>Uploading...</span>
                    </div>
                </div>
            </div>

            <div class="ingest-input-row">
                <input
                    type="text"
                    id="${PATH_INPUT_ID}"
                    placeholder="${downloadsFolder}\\Song.mp3"
                    autocomplete="off"
                    spellcheck="false"
                />
                <button id="${CHECK_BTN_ID}" class="ingest-btn-primary">
                    <span class="btn-label">Check</span>
                    <span class="btn-loading" style="display: none;">Checking...</span>
                </button>
            </div>

            <div class="ingest-actions">
                <button class="ingest-btn-secondary" id="ingest-scan-folder-btn">Scan Server Folder</button>
                <button class="ingest-btn-secondary" id="ingest-bulk-parse-btn">Fix Metadata (Bulk)</button>
                <button class="ingest-btn-secondary" id="ingest-clear-btn">Clear Results</button>
                <span class="ingest-hint muted-note">Press Enter to check</span>
            </div>

            <div id="${RESULTS_LIST_ID}" class="ingest-results">
            </div>
        </div>
    `;

    setupDropZone(DROP_ZONE_ID, RESULTS_LIST_ID, allowedExtensions, ctx);
    setupInputHandlers(PATH_INPUT_ID, CHECK_BTN_ID, RESULTS_LIST_ID);
    setupClearButton("ingest-clear-btn", RESULTS_LIST_ID);
    setupScanFolderButton("ingest-scan-folder-btn", PATH_INPUT_ID, RESULTS_LIST_ID, ctx);
    setupManualIngestHandlers(RESULTS_LIST_ID);
    setupBulkParseButton("ingest-bulk-parse-btn", RESULTS_LIST_ID, ctx);
}

function appendPendingConversionCard(resultsId, stagedPaths, ctx) {
    const list = document.getElementById(resultsId);
    if (!list) return;

    const card = document.createElement("article");
    card.className = "result-card pending-conversion-card";
    card.innerHTML = `
        <div class="result-card-header">
            <span class="result-status status-pending">PENDING CONVERSION</span>
            <span class="result-path">${stagedPaths.length} WAV file(s) ready to convert</span>
        </div>
        <div class="result-card-body">
            <button class="ingest-btn-primary convert-confirm-btn">Convert &amp; Ingest</button>
            <button class="ingest-btn-secondary convert-dismiss-btn">Dismiss</button>
        </div>
    `;

    card.querySelector(".convert-confirm-btn").addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        btn.disabled = true;
        btn.textContent = "Converting…";
        try {
            await convertAndIngest(stagedPaths);
            ctx.showBanner(`Converting ${stagedPaths.length} WAV file(s) in background — refresh in a moment`, "info");
            card.remove();
        } catch (err) {
            btn.disabled = false;
            btn.textContent = "Convert & Ingest";
            ctx.showBanner(`Conversion failed: ${err.message}`, "error");
        }
    });

    card.querySelector(".convert-dismiss-btn").addEventListener("click", () => card.remove());

    list.insertBefore(card, list.firstChild);
}

function setupDropZone(zoneId, resultsId, allowedExtensions, ctx) {
    const zone = document.getElementById(zoneId);
    if (!zone) return;

    const showLoading = (loading) => {
        const content = zone.querySelector(".drop-zone-content");
        const loader = zone.querySelector(".drop-zone-loading");
        if (content) content.style.display = loading ? "none" : "flex";
        if (loader) loader.style.display = loading ? "flex" : "none";
        zone.classList.toggle("uploading", loading);
    };

    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("drag-over");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("drag-over");
    });

    zone.addEventListener("drop", async (e) => {
        e.preventDefault();
        zone.classList.remove("drag-over");

        const items = e.dataTransfer?.items;

        if (!items || items.length === 0) {
            return;
        }

        showLoading(true);
        try {
            // Recursively collect all files from dropped items (supports folders)
            const allFiles = await collectFilesFromItems(items, allowedExtensions);

            if (allFiles.length === 0) {
                appendResult(resultsId, {
                    status: "ERROR",
                    message: "No audio files found in dropped folder(s)"
                }, "Drag and Drop");
                showLoading(false);
                return;
            }

            // Upload all collected files
            const result = await uploadFiles(allFiles);

            // Result is now BatchIngestReport
            const summary = `Processed ${result.total_files} files: ${result.ingested} ingested, ${result.duplicates} duplicates, ${result.conflicts || 0} conflicts, ${result.errors} errors`;
            appendBatchSummary(resultsId, result, summary);

            // Show individual file results
            for (const fileResult of result.results) {
                const fileName = fileResult.song?.source_path?.split(/[/\\]/).pop() || "Unknown";
                appendResult(resultsId, fileResult, fileName, ctx);
            }

            if (result.pending_conversion?.length) {
                appendPendingConversionCard(resultsId, result.pending_conversion, ctx);
            }
        } catch (error) {
            console.error("Drop error:", error);
            appendResult(resultsId, { status: "ERROR", message: error.message }, "Batch Upload", ctx);
        } finally {
            showLoading(false);
        }
    });
}

function setupInputHandlers(inputId, btnId, resultsId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    if (!input || !btn) return;

    const performCheck = async () => {
        const path = input.value.trim();
        if (!path) return;

        setLoading(btn, true);
        try {
            const result = await checkIngestion(path);
            appendResult(resultsId, result, path, ctx);
        } catch (error) {
            appendResult(resultsId, { status: "ERROR", message: error.message }, path, ctx);
        } finally {
            setLoading(btn, false);
        }
    };

    btn.addEventListener("click", performCheck);

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            performCheck();
        }
    });
}

function setupManualIngestHandlers(resultsId) {
    const container = document.getElementById(resultsId);
    if (!container) return;

    container.addEventListener("click", async (e) => {
        const btn = e.target.closest(".manual-ingest-btn");
        if (!btn) return;

        const path = btn.dataset.path;
        // In this MVP, we actually don't have a POST /ingest-by-path endpoint.
        // The API only has POST /upload (binary).
        // Since the user is on the same machine (host), we COULD implement /ingest-by-path.
        // But for now, I'll alert that manual path ingestion requires server-side file access.
        btn.disabled = true;
        btn.textContent = "Uploading...";

        try {
            // For now, remind them to drop the file for instant ingestion.
            throw new Error("Path-based ingestion restricted. Please drag and drop the physical file for instant ingestion.");
        } catch (err) {
            alert(err.message);
            btn.disabled = false;
            btn.textContent = "Ingest (Beta)";
        }
    });
}

function setupClearButton(btnId, resultsId) {
    const btn = document.getElementById(btnId);
    const list = document.getElementById(resultsId);
    if (!btn || !list) return;

    btn.addEventListener("click", () => {
        list.innerHTML = "";
        const state = ctx.getState();
        if (state.ingestTasks) state.ingestTasks = [];
    });
}

function setupScanFolderButton(btnId, inputId, resultsId, ctx) {
    const btn = document.getElementById(btnId);
    const input = document.getElementById(inputId);
    if (!btn || !input) return;

    btn.addEventListener("click", async () => {
        const folderPath = input.value.trim();
        if (!folderPath) {
            alert("Please enter a folder path (e.g., Z:\\Songs\\NewAlbum)");
            return;
        }

        btn.disabled = true;
        btn.textContent = "Scanning...";

        try {
            const result = await scanFolder(folderPath, true);

            // Result is BatchIngestReport
            const summary = `Scanned folder: ${result.total_files} files processed (${result.ingested} ingested, ${result.duplicates} duplicates, ${result.errors} errors)`;
            appendBatchSummary(resultsId, result, summary);

            // Show individual file results
            for (const fileResult of result.results) {
                const fileName = fileResult.song?.source_path?.split(/[/\\]/).pop() || "Unknown";
                appendResult(resultsId, fileResult, fileName, ctx);
            }

            if (result.pending_conversion?.length) {
                appendPendingConversionCard(resultsId, result.pending_conversion, ctx);
            }
        } catch (error) {
            appendResult(resultsId, { status: "ERROR", message: error.message }, folderPath, ctx);
        } finally {
            btn.disabled = false;
            btn.textContent = "Scan Server Folder";
        }
    });
}

function setLoading(btn, loading) {
    const label = btn.querySelector(".btn-label");
    const loadingEl = btn.querySelector(".btn-loading");
    if (label) label.style.display = loading ? "none" : "inline";
    if (loadingEl) loadingEl.style.display = loading ? "inline" : "none";
    btn.disabled = loading;
}

function appendResult(resultsId, result, path, ctx) {
    const list = document.getElementById(resultsId);
    if (!list) return;

    // Track in state for bulk tools
    const state = ctx.getState();
    if (state.ingestTasks) {
        state.ingestTasks.push({
            status: result.status,
            id: result.song?.id || result.ghost_id,
            filename: path.split(/[/\\]/).pop() || path,
            path: path
        });
    }

    const item = createResultCard(result, path);
    list.insertBefore(item, list.firstChild);
}

function appendBatchSummary(resultsId, batchReport, summary) {
    const list = document.getElementById(resultsId);
    if (!list) return;

    const card = document.createElement("article");
    card.className = "result-card batch-summary-card";

    const successRate = batchReport.total_files > 0
        ? Math.round((batchReport.ingested / batchReport.total_files) * 100)
        : 0;

    card.innerHTML = `
        <div class="card-icon ingest-icon">📦</div>
        <div class="card-body">
            <div class="card-title-row">
                <div class="card-title">Batch Processing Complete</div>
                ${renderStatus("found", `${successRate}% Success`)}
            </div>
            <div class="card-subtitle">${escapeHtml(summary)}</div>
            <div class="batch-stats" style="margin-top: 0.75rem; display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem;">
                <div class="stat-pill">
                    <div class="stat-value">${batchReport.total_files}</div>
                    <div class="stat-label muted-note">Total</div>
                </div>
                <div class="stat-pill">
                    <div class="stat-value" style="color: var(--accent);">${batchReport.ingested}</div>
                    <div class="stat-label muted-note">Ingested</div>
                </div>
                <div class="stat-pill">
                    <div class="stat-value" style="color: var(--warning);">${batchReport.duplicates}</div>
                    <div class="stat-label muted-note">Duplicates</div>
                </div>
                <div class="stat-pill">
                    <div class="stat-value" style="color: #ff9500;">${batchReport.conflicts || 0}</div>
                    <div class="stat-label muted-note">Conflicts</div>
                </div>
                <div class="stat-pill">
                    <div class="stat-value" style="color: var(--danger);">${batchReport.errors}</div>
                    <div class="stat-label muted-note">Errors</div>
                </div>
            </div>
        </div>
    `;

    list.insertBefore(card, list.firstChild);
}

function createResultCard(result, path) {
    const card = document.createElement("article");
    const status = result.status;
    card.className = `result-card ingest-card ${status.toLowerCase()}`;

    const statusConfig = {
        "NEW": { class: "found", icon: "&#10003;", text: "New File" },
        "INGESTED": { class: "found", icon: "&#10003;", text: "Ingested" },
        "ALREADY_EXISTS": { class: "loading", icon: "&#9888;", text: `Exists (${result.match_type})` },
        "CONFLICT": { class: "loading", icon: "&#9888;", text: `Ghost (${result.match_type})` },
        "ERROR": { class: "missing", icon: "&#10007;", text: "Error" }
    };

    const config = statusConfig[status] || statusConfig["ERROR"];

    // For CONFLICT status, use ghost record data
    const song = result.song;
    const title = status === "CONFLICT" && result.title
        ? result.title
        : (song?.media_name || song?.title || "Unknown Title");
    const artist = song?.display_artist || "-";

    // Helper to format duration (seconds to MM:SS)
    const formatDuration = (seconds) => {
        if (!seconds) return "Unknown";
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    card.innerHTML = `
        <div class="card-icon ingest-icon">${config.icon}</div>
        <div class="card-body">
            <div class="card-title-row">
                <div class="card-title">${escapeHtml(title)}</div>
                ${renderStatus(config.class, config.text)}
            </div>
            <div class="card-subtitle">${escapeHtml(artist)}</div>
            <div class="detail-path">${escapeHtml(path)}</div>
            ${result.message && status === "ERROR" ? `<div class="muted-note" style="margin-top: 0.5rem; color: var(--danger);">${escapeHtml(result.message)}</div>` : ""}

            ${status === "CONFLICT" ? `
                <div style="margin-top: 1rem; padding: 0.75rem; background: rgba(255, 149, 0, 0.1); border-left: 3px solid #ff9500; border-radius: 4px;">
                    <div class="muted-note" style="font-size: 0.75rem; margin-bottom: 0.5rem; color: #ff9500; font-weight: 600;">EXISTING GHOST RECORD (Soft-Deleted)</div>
                    <div style="display: grid; grid-template-columns: auto 1fr; gap: 0.5rem; font-size: 0.85rem;">
                        <div class="muted-note">ID:</div>
                        <div class="mono" style="font-weight: 500;">#${result.ghost_id}</div>

                        <div class="muted-note">Title:</div>
                        <div style="font-weight: 500;">${escapeHtml(result.title || "Unknown")}</div>

                        <div class="muted-note">Duration:</div>
                        <div class="mono">${formatDuration(result.duration_s)}</div>

                        <div class="muted-note">Year:</div>
                        <div class="mono">${result.year || "(none)"}</div>

                        <div class="muted-note">ISRC:</div>
                        <div class="mono" style="font-size: 0.8rem;">${result.isrc ? escapeHtml(result.isrc) : "(none)"}</div>
                    </div>
                    <div class="muted-note" style="font-size: 0.75rem; margin-top: 0.75rem; font-style: italic;">
                        This file matches a previously deleted record. Click below to re-activate with new metadata.
                    </div>
                    <div style="margin-top: 0.75rem;">
                        <button style="padding: 0.5rem 1rem; background: #ff9500; color: white; border: none; border-radius: 4px; font-weight: 600; cursor: pointer;" data-action="resolve-conflict" data-ghost-id="${result.ghost_id}" data-staged-path="${escapeHtml(result.staged_path)}">
                            Re-ingest & Activate
                        </button>
                    </div>
                </div>
            ` : ""}

            ${status === "INGESTED" ? `
                <div class="ingest-actions-row">
                    <button class="ingest-btn-link" data-action="navigate-search" data-mode="songs" data-query="${escapeHtml(title)}">
                        View in Library
                    </button>
                    <span class="muted-note">• UUID Staged</span>
                </div>
            ` : ""}

            ${status === "NEW" ? `
                <div class="ingest-actions-row">
                    <span class="muted-note">Verified. Drop physical file to commit.</span>
                </div>
            ` : ""}
        </div>
        ${song ? `
            <div class="ingest-meta">
                ${song.bpm ? `<span class="pill mono">${escapeHtml(song.bpm)} BPM</span>` : ""}
                ${song.year ? `<span class="pill mono">${escapeHtml(song.year)}</span>` : ""}
                ${song.id ? `<span class="pill mono">#${escapeHtml(song.id)}</span>` : ""}
            </div>
        ` : ""}
    `;

    return card;
}

function setupBulkParseButton(btnId, resultsId, ctx) {
    const btn = document.getElementById(btnId);
    if (!btn) return;

    btn.addEventListener("click", () => {
        const state = ctx.getState();
        if (!state.ingestTasks || state.ingestTasks.length === 0) {
            alert("No files to parse. Ingest some files first.");
            return;
        }

        // We only want songs that already exist in DB (INGESTED or CONFLICT/GHOST)
        const entries = state.ingestTasks
            .filter(t => t.id && (t.status === "INGESTED" || t.status === "CONFLICT"))
            .map(t => ({
                id: t.id,
                filename: t.filename
            }));

        if (entries.length === 0) {
            alert("No successfully ingested songs found in the results list.");
            return;
        }

        openFilenameParserModal({
            entries,
            onApply: async () => {
                // Refresh logic if needed
            }
        });
    });
}
