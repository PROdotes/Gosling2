import { checkIngestion, getDownloadsFolder, uploadFile } from "../api.js";
import {
    escapeHtml,
    renderStatus,
} from "../components/utils.js";

const PATH_INPUT_ID = "ingest-path-input";
const CHECK_BTN_ID = "ingest-check-btn";
const RESULTS_LIST_ID = "ingest-results";

export async function renderIngestionPanel(ctx) {
    ctx.updateResultsSummary(0, "ingestion check");

    const DROP_ZONE_ID = "ingest-drop-zone";
    let downloadsFolder = "";

    try {
        downloadsFolder = await getDownloadsFolder();
    } catch (e) {
        downloadsFolder = "C:\\Users\\Downloads";
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
                <button class="ingest-btn-secondary" id="ingest-clear-btn">Clear Results</button>
                <span class="ingest-hint muted-note">Press Enter to check</span>
            </div>

            <div id="${RESULTS_LIST_ID}" class="ingest-results">
            </div>
        </div>
    `;

    setupDropZone(DROP_ZONE_ID, RESULTS_LIST_ID);
    setupInputHandlers(PATH_INPUT_ID, CHECK_BTN_ID, RESULTS_LIST_ID);
    setupClearButton("ingest-clear-btn", RESULTS_LIST_ID);
    setupManualIngestHandlers(RESULTS_LIST_ID);
}

function setupDropZone(zoneId, resultsId) {
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

        const file = e.dataTransfer?.files?.[0];
        if (!file) return;

        showLoading(true);
        try {
            const result = await uploadFile(file);
            appendResult(resultsId, result, file.name);
        } catch (error) {
            appendResult(resultsId, { status: "ERROR", message: error.message }, file.name);
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
            appendResult(resultsId, result, path);
        } catch (error) {
            appendResult(resultsId, { status: "ERROR", message: error.message }, path);
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
    });
}

function setLoading(btn, loading) {
    const label = btn.querySelector(".btn-label");
    const loadingEl = btn.querySelector(".btn-loading");
    if (label) label.style.display = loading ? "none" : "inline";
    if (loadingEl) loadingEl.style.display = loading ? "inline" : "none";
    btn.disabled = loading;
}

function appendResult(resultsId, result, path) {
    const list = document.getElementById(resultsId);
    if (!list) return;

    const item = createResultCard(result, path);
    list.insertBefore(item, list.firstChild);
}

function createResultCard(result, path) {
    const card = document.createElement("article");
    const status = result.status;
    card.className = `result-card ingest-card ${status.toLowerCase()}`;

    const statusConfig = {
        "NEW": { class: "found", icon: "&#10003;", text: "New File" },
        "INGESTED": { class: "found", icon: "&#10003;", text: "Ingested" },
        "ALREADY_EXISTS": { class: "loading", icon: "&#9888;", text: `Exists (${result.match_type})` },
        "ERROR": { class: "missing", icon: "&#10007;", text: "Error" }
    };

    const config = statusConfig[status] || statusConfig["ERROR"];

    const song = result.song;
    const title = song?.media_name || song?.title || "Unknown Title";
    const artist = song?.display_artist || "-";

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
