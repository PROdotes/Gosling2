import { parseSpotifyCredits, importSpotifyCredits } from "../api.js";
import { escapeHtml } from "./utils.js";

const overlay = document.getElementById("spotify-modal");
const textarea = document.getElementById("spotify-raw-text");
const resultsSect = document.getElementById("spotify-parse-results");
const previewList = document.getElementById("spotify-preview-list");
const importBtn = document.getElementById("spotify-import-btn");
const warningEl = document.getElementById("spotify-title-warning");
const parsedTitleEl = document.getElementById("spotify-parsed-title");
const statusEl = document.getElementById("spotify-parsed-status");

let _songId = null;
let _songTitle = "";
let _onComplete = null;
let _isSelecting = false;
let _debounceTimer = null;
let _parseResult = null;

function showResults(result) {
    _parseResult = result;
    resultsSect.style.display = "block";
    
    // Title mismatch warning
    if (result.title_match) {
        warningEl.style.display = "none";
    } else {
        parsedTitleEl.textContent = result.parsed_title || "Unknown";
        warningEl.style.display = "block";
    }

    // Preview list
    const credits = result.credits || [];
    const publishers = result.publishers || [];
    
    statusEl.textContent = `${credits.length} artists, ${publishers.length} publishers`;

    const creditHtml = credits.map(c => `
        <div style="margin-bottom: 0.5rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.3rem;">
            <span style="color: var(--accent); font-weight: 500;">${escapeHtml(c.name)}</span>
            <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 0.5rem;">${escapeHtml(c.role)}</span>
        </div>
    `).join("");

    const pubHtml = publishers.map(p => `
        <div style="margin-bottom: 0.3rem;">
            <span class="pill genre" style="font-size: 0.7rem; border-radius: 4px;">PUB</span>
            <span style="margin-left: 0.4rem;">${escapeHtml(p)}</span>
        </div>
    `).join("");

    previewList.innerHTML = creditHtml + (credits.length && publishers.length ? '<hr style="opacity: 0.1; margin: 0.75rem 0;">' : '') + pubHtml;

    if (!credits.length && !publishers.length) {
        previewList.innerHTML = '<div class="muted-note">No credits found in pasted text.</div>';
        importBtn.disabled = true;
        importBtn.textContent = "No Credits Found";
    } else {
        importBtn.disabled = false;
        const total = credits.length + publishers.length;
        importBtn.textContent = `Import ${total} Credit${total === 1 ? '' : 's'}`;
    }
}

async function handleImport() {
    if (!_parseResult || !_songId) return;
    
    importBtn.disabled = true;
    importBtn.textContent = "Importing...";
    
    try {
        await importSpotifyCredits(
            _songId, 
            _parseResult.credits, 
            _parseResult.publishers
        );
        const onComplete = _onComplete;
        closeSpotifyModal();
        if (onComplete) onComplete();
    } catch (err) {
        console.error("[SpotifyModal] Import failed:", err);
        alert(`Import failed: ${err.message}`);
        importBtn.disabled = false;
        importBtn.textContent = "Retry Import";
    }
}

async function runParse() {
    const text = textarea.value.trim();
    if (!text) {
        resultsSect.style.display = "none";
        importBtn.disabled = true;
        importBtn.textContent = "Import Credits";
        return;
    }

    try {
        const result = await parseSpotifyCredits(text, _songTitle);
        showResults(result);
    } catch (err) {
        console.error("[SpotifyModal] Parse failed:", err);
        statusEl.textContent = "Error parsing text";
    }
}

textarea.addEventListener("input", () => {
    clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(runParse, 300);
});

importBtn.addEventListener("click", handleImport);

export function openSpotifyModal({ songId, title, onComplete }) {
    _songId = songId;
    _songTitle = title;
    _onComplete = onComplete;
    _parseResult = null;

    textarea.value = "";
    resultsSect.style.display = "none";
    importBtn.disabled = true;
    importBtn.textContent = "Import Credits";
    
    overlay.style.display = "flex";
    _isSelecting = false;
    textarea.focus();
}

export function closeSpotifyModal() {
    overlay.style.display = "none";
    _songId = null;
    _onComplete = null;
    textarea.value = "";
}

// Overlay click to close
overlay.addEventListener("click", (e) => {
    if (_isSelecting) return;
    if (e.target === overlay) closeSpotifyModal();
});

// ESC to close
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.style.display === "flex") {
        e.stopImmediatePropagation();
        closeSpotifyModal();
    }
});
