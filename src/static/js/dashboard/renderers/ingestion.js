import { checkIngestion, getDownloadsFolder } from "../api.js";
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
                    <div class="drop-zone-label">Drop file here</div>
                    <div class="drop-zone-hint muted-note">or paste path below</div>
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
                    <span class="btn-loading" hidden>Checking...</span>
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

    setupDropZone(DROP_ZONE_ID, PATH_INPUT_ID, downloadsFolder);
    setupInputHandlers(PATH_INPUT_ID, CHECK_BTN_ID, RESULTS_LIST_ID);
    setupClearButton("ingest-clear-btn", RESULTS_LIST_ID);
}

function setupDropZone(zoneId, inputId, downloadsFolder) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    if (!zone || !input) return;

    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("drag-over");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("drag-over");
    });

    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("drag-over");

        const file = e.dataTransfer?.files?.[0];
        if (file) {
            input.value = `${downloadsFolder}\\${file.name}`;
            input.focus();
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
    if (label) label.hidden = loading;
    if (loadingEl) loadingEl.hidden = !loading;
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
    card.className = `result-card ingest-card ${result.status.toLowerCase()}`;

    const statusClass = result.status === "NEW" ? "found" : result.status === "ALREADY_EXISTS" ? "loading" : "missing";
    const statusIcon = result.status === "NEW" ? "&#10003;" : result.status === "ALREADY_EXISTS" ? "&#9888;" : "&#10007;";
    const statusText = result.status === "NEW" ? "New File" : result.status === "ALREADY_EXISTS" ? `Exists (${result.match_type})` : "Error";

    const song = result.song;
    const title = song?.media_name || song?.title || "Unknown Title";
    const artist = song?.display_artist || "-";

    card.innerHTML = `
        <div class="card-icon ingest-icon">${statusIcon}</div>
        <div class="card-body">
            <div class="card-title-row">
                <div class="card-title">${escapeHtml(title)}</div>
                ${renderStatus(statusClass, statusText)}
            </div>
            <div class="card-subtitle">${escapeHtml(artist)}</div>
            <div class="detail-path">${escapeHtml(path)}</div>
            ${result.message && result.status === "ERROR" ? `<div class="muted-note" style="margin-top: 0.5rem; color: var(--danger);">${escapeHtml(result.message)}</div>` : ""}
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
