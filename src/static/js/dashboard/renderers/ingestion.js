import {
    checkIngestion,
    deleteStagingOrphan,
    getAcceptedFormats,
    getDownloadsFolder,
    getPendingConvert,
    getStagingOrphans,
    readNdjsonStream,
    resolveConflict,
    scanFolder,
    uploadFiles,
} from "../api.js";
import { openFilenameParserModal } from "../components/filename_parser_modal.js";
import { showToast } from "../components/toast.js";
import { basename, escapeHtml, renderStatus } from "../components/utils.js";

const PATH_INPUT_ID = "ingest-path-input";
const CHECK_BTN_ID = "ingest-check-btn";
const RESULTS_LIST_ID = "ingest-results";

/**
 * Recursively collect all File objects from DataTransferItemList.
 * Handles both files and directories.
 */
export async function collectFilesFromItems(items, allowedExtensions) {
    const files = [];
    const queue = [];
    const exts = (allowedExtensions || []).map((e) => e.toLowerCase());

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
            const isAllowed =
                exts.length === 0 ||
                exts.some((ext) => entry.name.toLowerCase().endsWith(ext));
            if (isAllowed) {
                // Get the actual File object
                const file = await new Promise((resolve) =>
                    entry.file(resolve),
                );
                files.push(file);
            }
        } else if (entry.isDirectory) {
            // Read ALL directory contents (readEntries returns batches)
            const reader = entry.createReader();
            let batch;
            do {
                batch = await new Promise((resolve) =>
                    reader.readEntries(resolve),
                );
                queue.push(...batch);
            } while (batch.length > 0);
        }
    }

    return files;
}

/**
 * Shared ingest drop pipeline: collect → upload → stream.
 * @param {DataTransferItemList} items
 * @param {string[]} allowedExtensions
 * @param {{ onStarted(update): void, onUpdate(update): void, onError(err): void, onEmpty(): void }} callbacks
 */
export async function handleIngestDrop(items, allowedExtensions, { onStarted, onUpdate, onError, onEmpty }) {
    const allFiles = await collectFilesFromItems(items, allowedExtensions);
    if (allFiles.length === 0) {
        onEmpty();
        return;
    }
    try {
        const response = await uploadFiles(allFiles);
        if (!response.ok) throw new Error("Upload failed");
        await readNdjsonStream(response, (update) => {
            if (update.error) {
                onError(new Error(update.error));
                return;
            }
            if (update.started) {
                onStarted(update);
                return;
            }
            onUpdate(update);
        });
    } catch (err) {
        onError(err);
    }
}

export async function renderIngestionPanel(ctx) {
    ctx.updateResultsSummary(0, "ingestion check");

    // Initialize session state for this panel
    const state = ctx.getState();
    if (!state.ingestTasks) {
        state.ingestTasks = [];
    }

    // Already initialized — don't re-render or re-attach listeners
    if (document.getElementById("ingest-drop-zone")) return;

    const DROP_ZONE_ID = "ingest-drop-zone";
    let downloadsFolder = "";
    let allowedExtensions = [];

    try {
        const [folder, exts] = await Promise.all([
            getDownloadsFolder(),
            getAcceptedFormats(),
        ]);
        downloadsFolder = folder;
        allowedExtensions = exts;
    } catch (e) {
        console.error("Failed to load ingestion configuration:", e);
        // No fallbacks. UI will handle missing config.
    }

    const container =
        document.getElementById("ingest-container") ||
        ctx.elements.resultsContainer;
    container.innerHTML = `
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

            <div id="ingest-orphan-section" class="orphan-section">
                <button class="orphan-toggle muted-note">▶ Orphaned Staging Files</button>
                <div class="orphan-body" style="display:none"></div>
            </div>
        </div>
    `;

    setupDropZone(DROP_ZONE_ID, RESULTS_LIST_ID, allowedExtensions, ctx);
    setupInputHandlers(PATH_INPUT_ID, CHECK_BTN_ID, RESULTS_LIST_ID, ctx);
    setupClearButton("ingest-clear-btn", RESULTS_LIST_ID, ctx);
    setupScanFolderButton(
        "ingest-scan-folder-btn",
        PATH_INPUT_ID,
        RESULTS_LIST_ID,
        ctx,
    );
    setupBulkParseButton("ingest-bulk-parse-btn", RESULTS_LIST_ID, ctx);
    setupOrphanSection("ingest-orphan-section");

    // Restore cached tasks/results
    if (state.cachedIngestResults && state.cachedIngestResults.length > 0) {
        const list = document.getElementById(RESULTS_LIST_ID);
        if (list) {
            // Cache is newest-first, so appendChild maintains that visual order
            state.cachedIngestResults.forEach((cached) => {
                if (cached.isBatch) {
                    _appendBatchToDom(
                        list,
                        cached.report,
                        cached.summary,
                        true,
                    );
                } else {
                    _appendResultToDom(list, cached.result, cached.path, true);
                }
            });
        }
    }

    // Load any WAVs that were uploaded but not yet converted (status=3)
    getPendingConvert()
        .then((pending) => {
            if (!pending || pending.length === 0) return;
            const list = document.getElementById(RESULTS_LIST_ID);
            if (!list) return;
            pending.forEach((result) => {
                const path = result.staged_path || result.source_path;
                list.prepend(createResultCard(result, path));
            });
        })
        .catch(() => {}); // silently ignore on load failure
}

function setupOrphanSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (!section) return;

    const toggle = section.querySelector(".orphan-toggle");
    const body = section.querySelector(".orphan-body");
    if (!toggle || !body) return;

    toggle.addEventListener("click", async () => {
        const isOpen = body.style.display !== "none";
        if (isOpen) {
            body.style.display = "none";
            toggle.textContent = "▶ Orphaned Staging Files";
            return;
        }
        body.style.display = "block";
        toggle.textContent = "▼ Orphaned Staging Files";
        await refreshOrphanList(body);
    });
}

async function refreshOrphanList(body) {
    body.innerHTML = `<div class="muted-note" style="padding: 0.5rem 0;">Loading...</div>`;
    try {
        const orphans = await getStagingOrphans();
        if (orphans.length === 0) {
            body.innerHTML = `<div class="muted-note" style="padding: 0.5rem 0;">No orphaned files found.</div>`;
            return;
        }
        body.innerHTML = orphans
            .map(
                (f) => `
            <div class="orphan-row" data-path="${escapeHtml(f.path)}">
                <span class="orphan-name mono">${escapeHtml(f.filename)}</span>
                <span class="muted-note orphan-size">${escapeHtml(f.display_size)}</span>
                <div class="row-actions">
                    ${f.is_ghost ? `<button class="ingest-btn-primary orphan-reactivate-btn" data-path="${escapeHtml(f.path)}" data-ghost-id="${f.ghost_id}">Re-activate</button>` : ""}
                    <button class="ingest-btn-danger orphan-delete-btn" data-path="${escapeHtml(f.path)}">Delete</button>
                </div>
            </div>
        `,
            )
            .join("");

        body.querySelectorAll(".orphan-reactivate-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const { path, ghostId } = btn.dataset;
                btn.disabled = true;
                btn.textContent = "Reactivating...";
                try {
                    await resolveConflict(ghostId, path);
                    btn.closest(".orphan-row").remove();
                    showToast("Song reactivated successfully!", "success");
                } catch (err) {
                    btn.disabled = false;
                    btn.textContent = "Re-activate";
                    showToast(`Error: ${err.message}`, "error");
                }
            });
        });

        body.querySelectorAll(".orphan-delete-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const path = btn.dataset.path;
                btn.disabled = true;
                btn.textContent = "Deleting...";
                try {
                    await deleteStagingOrphan(path);
                    btn.closest(".orphan-row").remove();
                    if (body.querySelectorAll(".orphan-row").length === 0) {
                        body.innerHTML = `<div class="muted-note" style="padding: 0.5rem 0;">No orphaned files found.</div>`;
                    }
                } catch (err) {
                    btn.disabled = false;
                    btn.textContent = "Delete";
                    alert(`Failed: ${err.message}`);
                }
            });
        });
    } catch (err) {
        body.innerHTML = `<div class="muted-note" style="padding: 0.5rem 0; color: var(--danger);">Error: ${escapeHtml(err.message)}</div>`;
    }
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
        if (!items || items.length === 0) return;

        showLoading(true);
        await handleIngestDrop(items, allowedExtensions, {
            onEmpty() {
                appendResult(resultsId, { status: "ERROR", message: "No audio files found in dropped folder(s)" }, "Drag and Drop", ctx);
                showLoading(false);
            },
            onStarted(update) {
                insertPendingCard(resultsId, update.filename, update.is_wav);
                ctx.updateIngestBadges?.({ currentFile: update.filename });
            },
            onUpdate(update) {
                ctx.updateIngestBadges?.({ success: update.success, action: update.action, pending: update.pending, currentFile: null });
                const res = update.last_result;
                if (res) {
                    const fileName = basename(res.song?.source_path) || basename(res.staged_path) || "Unknown";
                    resolvePendingCard(resultsId, res, fileName, update.filename);
                    _trackResult(res, fileName, ctx);
                }
            },
            onError(err) {
                console.error("Drop error:", err);
                appendResult(resultsId, { status: "ERROR", message: err.message }, "Batch Upload", ctx);
            },
        });
        showLoading(false);
    });
}

function setupInputHandlers(inputId, btnId, resultsId, ctx) {
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
            appendResult(
                resultsId,
                { status: "ERROR", message: error.message },
                path,
                ctx,
            );
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

function setupClearButton(btnId, resultsId, ctx) {
    const btn = document.getElementById(btnId);
    const list = document.getElementById(resultsId);
    if (!btn || !list) return;

    btn.addEventListener("click", () => {
        list.innerHTML = "";
        const state = ctx.getState();
        if (state.ingestTasks) state.ingestTasks = [];
        if (state.cachedIngestResults) state.cachedIngestResults = [];
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
            const response = await scanFolder(folderPath, true, true);
            if (!response.ok) throw new Error("Scan failed");

            await readNdjsonStream(response, (update) => {
                if (update.error) {
                    showToast(update.error, "error");
                    return;
                }
                if (update.started) {
                    insertPendingCard(resultsId, update.filename, update.is_wav);
                    ctx.updateIngestBadges?.({ currentFile: update.filename });
                    return;
                }
                ctx.updateIngestBadges?.({
                    success: update.success,
                    action: update.action,
                    pending: update.pending,
                    currentFile: null,
                });
                const res = update.last_result;
                if (res) {
                    const fileName =
                        basename(res.song?.source_path) ||
                        basename(res.staged_path) ||
                        "Unknown";
                    resolvePendingCard(resultsId, res, fileName, update.filename);
                    _trackResult(res, fileName, ctx);
                }
            });
        } catch (error) {
            appendResult(
                resultsId,
                { status: "ERROR", message: error.message },
                folderPath,
                ctx,
            );
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

function _trackResult(result, path, ctx) {
    const state = ctx.getState();
    if (state.ingestTasks) {
        state.ingestTasks.push({
            status: result.status,
            id: result.song?.id || result.ghost_id,
            filename: basename(path) || path,
            path: path,
        });
    }
    if (state.cachedIngestResults) {
        state.cachedIngestResults.unshift({
            isBatch: false,
            result,
            path,
            stagedPath: result.staged_path || null,
        });
    }
}

function appendResult(resultsId, result, path, ctx) {
    const list = document.getElementById(resultsId);
    if (!list) return;
    _trackResult(result, path, ctx);
    _appendResultToDom(list, result, path, false);
}

function _appendResultToDom(list, result, path, appendAtEnd = false) {
    const item = createResultCard(result, path);
    if (appendAtEnd) {
        list.appendChild(item);
    } else {
        list.insertBefore(item, list.firstChild);
    }
}

function createPendingCard(filename, isWav) {
    const card = document.createElement("article");
    card.className = "result-card ingest-card pending-ingest";
    card.dataset.pendingFile = filename;
    const label = isWav ? "Converting WAV→MP3…" : "Ingesting…";
    card.innerHTML = `
        <div class="card-icon ingest-icon">&#8635;</div>
        <div class="card-body">
            <div class="card-title-row">
                <div class="card-title">${escapeHtml(filename)}</div>
                ${renderStatus("loading", label)}
            </div>
        </div>
    `;
    return card;
}

function insertPendingCard(resultsId, filename, isWav) {
    const list = document.getElementById(resultsId);
    if (!list) return;
    const card = createPendingCard(filename, isWav);
    list.insertBefore(card, list.firstChild);
}

function resolvePendingCard(resultsId, result, path, stagedFilename) {
    const list = document.getElementById(resultsId);
    if (!list) return;
    const lookupKey = stagedFilename || basename(path) || path;
    const pending = list.querySelector(`[data-pending-file="${CSS.escape(lookupKey)}"]`);
    const newCard = createResultCard(result, path);
    if (pending) {
        list.replaceChild(newCard, pending);
    } else {
        list.insertBefore(newCard, list.firstChild);
    }
}

function appendBatchSummary(resultsId, batchReport, summary, ctx) {
    const list = document.getElementById(resultsId);
    if (!list) return;

    // Persist to cache
    const state = ctx.getState();
    if (state.cachedIngestResults) {
        state.cachedIngestResults.unshift({
            isBatch: true,
            report: batchReport,
            summary,
        });
    }

    _appendBatchToDom(list, batchReport, summary, false);
}

function _appendBatchToDom(list, batchReport, summary, appendAtEnd = false) {
    const card = document.createElement("article");
    card.className = "result-card batch-summary-card";

    const successRate =
        batchReport.total_files > 0
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

    if (appendAtEnd) {
        list.appendChild(card);
    } else {
        list.insertBefore(card, list.firstChild);
    }
}

function createResultCard(result, path) {
    const card = document.createElement("article");
    const status = result.status;
    card.className = `result-card ingest-card ${status.toLowerCase()}`;

    const SEVERITY_ICONS = {
        success: "&#10003;",
        info: "&#8635;",
        warning: "&#9888;",
        error: "&#10007;",
    };

    const icon = SEVERITY_ICONS[result.status_severity] || SEVERITY_ICONS.error;
    const statusLabel = result.status_label || status;
    const statusClass = result.status_severity || "error";

    const song = result.song;
    const title =
        status === "CONFLICT" && result.title
            ? result.title
            : song?.media_name || song?.title || result.display_title || "Unknown Title";
    const artist = song?.display_artist || "-";

    card.innerHTML = `
        <div class="card-icon ingest-icon">${icon}</div>
        <div class="card-body">
            <div class="card-title-row">
                <div class="card-title">${escapeHtml(title)}</div>
                ${renderStatus(statusClass, statusLabel)}
            </div>
            <div class="card-subtitle">${escapeHtml(artist)}</div>
            <div class="detail-path">${escapeHtml(path)}</div>
            ${result.message && status === "ERROR" ? `<div class="muted-note" style="margin-top: 0.5rem; color: var(--danger);">${escapeHtml(result.message)}</div>` : ""}

            ${
                status === "CONFLICT"
                    ? (() => {
                        const isRejected = result.notes && result.notes.startsWith("REJECTED");
                        return `
                <div class="pending-convert-box" data-ghost-box>
                    <div class="muted-note" style="font-size: 10px; margin-bottom: 6px; color: ${isRejected ? "var(--danger)" : "var(--accent-amber)"}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">${isRejected ? "Rejected Song" : "Existing Ghost Record (Soft-Deleted)"}</div>
                    <div style="display: grid; grid-template-columns: 70px 1fr; gap: 4px 8px; font-size: 12px;">
                        <div class="muted-note">ID:</div>
                        <div class="mono">#${result.ghost_id}</div>
                        <div class="muted-note">Title:</div>
                        <div>${escapeHtml(result.title || "Unknown")}</div>
                        <div class="muted-note">Duration:</div>
                        <div class="mono">${result.formatted_duration || "Unknown"}</div>
                        <div class="muted-note">Year:</div>
                        <div class="mono">${result.year || "(none)"}</div>
                        <div class="muted-note">ISRC:</div>
                        <div class="mono">${result.isrc ? escapeHtml(result.isrc) : "(none)"}</div>
                    </div>
                    <div class="muted-note" style="font-size: 11px; margin-top: 8px; font-style: italic; color: ${isRejected ? "var(--danger)" : "inherit"};">
                        ${isRejected ? "This song was previously rejected — it is not suitable for this station. Re-ingest only if you are sure." : "This file matches a previously deleted record. Re-activate with new metadata."}
                    </div>
                    <div style="margin-top: 8px;">
                        <button type="button" class="ingest-btn-primary" data-action="resolve-conflict" data-ghost-id="${result.ghost_id}" data-staged-path="${escapeHtml(result.staged_path)}">
                            Re-ingest & Activate
                        </button>
                    </div>
                </div>`;
                    })()
                    : ""
            }

            ${
                status === "PENDING_CONVERT"
                    ? `
                <div class="pending-convert-box">
                    <div class="muted-note" style="font-size: 11px; margin-bottom: 8px; font-style: italic;">
                        This WAV file needs to be converted to MP3 before ingestion.
                    </div>
                    <button type="button" class="ingest-btn-primary" data-action="convert-wav" data-staged-path="${escapeHtml(result.staged_path)}">
                        Convert & Ingest
                    </button>
                </div>
            `
                    : ""
            }

            ${
                status === "INGESTED" || status === "ALREADY_EXISTS"
                    ? `
                <div class="ingest-actions-row">
                    <button class="ingest-btn-link" data-action="navigate-search" data-mode="songs" data-query="${escapeHtml(title)}">
                        View in Library
                    </button>
                    ${status === "ALREADY_EXISTS" && song?.id && result.staged_path ? `
                    <button class="ingest-btn-primary" data-action="recover-file" data-song-id="${song.id}" data-staged-path="${escapeHtml(result.staged_path)}" style="margin-left: 8px;">
                        Recover File
                    </button>
                    ` : ""}
                    <span class="muted-note">• ${status === "INGESTED" ? "UUID Staged" : "Already In Library"}</span>
                </div>
            `
                    : ""
            }

            ${
                status === "NEW"
                    ? `
                <div class="ingest-actions-row">
                    <span class="muted-note">Verified. Drop physical file to commit.</span>
                </div>
            `
                    : ""
            }
        </div>
        <div class="ingest-meta">
            <span class="pill mono">${escapeHtml(path.split(".").pop()?.toUpperCase() || "?")}</span>
            ${song && song.bpm ? `<span class="pill mono">${escapeHtml(song.bpm)} BPM</span>` : ""}
            ${song && song.year ? `<span class="pill mono">${escapeHtml(song.year)}</span>` : ""}
            ${song && song.id ? `<span class="pill mono">#${escapeHtml(song.id)}</span>` : ""}
        </div>
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
            .filter(
                (t) =>
                    t.id &&
                    (t.status === "INGESTED" ||
                        t.status === "CONFLICT" ||
                        t.status === "CONVERTING"),
            )
            .map((t) => ({
                id: t.id,
                filename: t.filename,
            }));

        if (entries.length === 0) {
            alert("No successfully ingested songs found in the results list.");
            return;
        }

        openFilenameParserModal({
            entries,
            onApply: async () => {
                // Refresh logic if needed
            },
        });
    });
}
