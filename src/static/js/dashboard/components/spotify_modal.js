import {
    importSpotifyCredits,
    parseSpotifyCredits,
    splitterPreview,
} from "../api.js";
import { escapeHtml, wasMousedownInside } from "./utils.js";
import { createModalLifecycle } from "./modal_lifecycle.js";

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
let _existingCredits = [];
let _existingPublishers = [];
let _isSelecting = false;
let _debounceTimer = null;
let _parseResult = null;
let _existence = { credits: [], publishers: [] };
let modal;

function getStatusBadge(type) {
    if (type === "linked") {
        return `<span class="splitter-preview-match" style="margin-left: 0.5rem; font-size: 0.65rem; border: 1px solid currentColor; padding: 0.05rem 0.3rem; border-radius: 4px; text-transform: uppercase; color: var(--success);">Linked</span>`;
    }
    if (type === "found") {
        return `<span class="splitter-preview-match" style="margin-left: 0.5rem; font-size: 0.65rem; border: 1px solid currentColor; padding: 0.05rem 0.3rem; border-radius: 4px; text-transform: uppercase;">Found</span>`;
    }
    return `<span class="splitter-preview-new" style="margin-left: 0.5rem; font-size: 0.65rem; border: 1px solid currentColor; padding: 0.05rem 0.3rem; border-radius: 4px; text-transform: uppercase; opacity: 0.5;">New</span>`;
}

function showResults(result) {
    _parseResult = result;
    resultsSect.style.display = "block";

    // Title mismatch warning
    if (result.title_match) {
        warningEl.style.display = "none";
        warningEl.classList.remove("has-attention");
    } else {
        parsedTitleEl.textContent = result.parsed_title || "Unknown";
        warningEl.style.display = "flex";

        // Trigger animation by resetting the class
        warningEl.classList.remove("has-attention");
        void warningEl.offsetWidth; // Force reflow
        warningEl.classList.add("has-attention");
    }

    // Preview list
    const credits = result.credits || [];
    const publishers = result.publishers || [];
    const credExistence = _existence.credits || [];
    const pubExistence = _existence.publishers || [];

    statusEl.textContent = `${credits.length} artists, ${publishers.length} publishers`;

    const creditHtml = credits
        .map((c, _i) => {
            const exist = credExistence.find((e) => e.name === c.name);
            // Link Check: Case-insensitive match on name and exact match on role
            const alreadyLinked = _existingCredits.some(
                (ec) =>
                    (ec.display_name?.toLowerCase() === c.name?.toLowerCase() ||
                        ec.name?.toLowerCase() === c.name?.toLowerCase()) &&
                    ec.role_name === c.role,
            );

            let type = "new";
            if (alreadyLinked) type = "linked";
            else if (exist?.exists) type = "found";

            return `
            <div style="margin-bottom: 0.5rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.3rem; display: flex; align-items: center; justify-content: space-between; ${alreadyLinked ? "opacity: 0.5" : ""}">
                <div>
                    <span style="color: var(--accent); font-weight: 500;">${escapeHtml(c.name)}</span>
                    ${getStatusBadge(type)}
                    <div style="color: var(--text-muted); font-size: 0.75rem;">${escapeHtml(c.role)}</div>
                </div>
            </div>
        `;
        })
        .join("");

    const pubHtml = publishers
        .map((p, _i) => {
            const exist = pubExistence.find((e) => e.name === p);
            const alreadyLinked = _existingPublishers.some(
                (ep) => ep.name?.toLowerCase() === p?.toLowerCase(),
            );

            let type = "new";
            if (alreadyLinked) type = "linked";
            else if (exist?.exists) type = "found";

            return `
            <div style="margin-bottom: 0.3rem; display: flex; align-items: center; justify-content: space-between; ${alreadyLinked ? "opacity: 0.5" : ""}">
                <div style="display: flex; align-items: center;">
                    <span class="pill genre" style="font-size: 0.7rem; border-radius: 4px; flex-shrink: 0;">PUB</span>
                    <span style="margin-left: 0.4rem;">${escapeHtml(p)}</span>
                </div>
                ${getStatusBadge(type)}
            </div>
        `;
        })
        .join("");

    previewList.innerHTML =
        creditHtml +
        (credits.length && publishers.length
            ? '<hr style="opacity: 0.1; margin: 0.75rem 0;">'
            : "") +
        pubHtml;

    if (!credits.length && !publishers.length) {
        previewList.innerHTML =
            '<div class="muted-note">No credits found in pasted text.</div>';
        importBtn.disabled = true;
        importBtn.textContent = "No Credits Found";
    } else {
        importBtn.disabled = false;
        const total = credits.length + publishers.length;
        importBtn.textContent = `Import ${total} Credit${total === 1 ? "" : "s"}`;
    }
}

async function handleImport() {
    if (!_parseResult || !_songId) return;

    importBtn.disabled = true;
    importBtn.textContent = "Importing...";

    try {
        await importSpotifyCredits(
            _songId,
            _parseResult.credits || [],
            _parseResult.publishers,
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

        // Parallel checks for existence
        const creditNames = (result.credits || []).map((c) => c.name);
        const pubNames = result.publishers || [];

        const [credCheck, pubCheck] = await Promise.all([
            creditNames.length
                ? splitterPreview(creditNames, "credits")
                : Promise.resolve([]),
            pubNames.length
                ? splitterPreview(pubNames, "publishers")
                : Promise.resolve([]),
        ]);

        _existence = { credits: credCheck, publishers: pubCheck };
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

export function openSpotifyModal({
    songId,
    title,
    existingCredits,
    existingPublishers,
    onComplete,
}) {
    modal.open({ songId, title, existingCredits, existingPublishers, onComplete });
}

export function closeSpotifyModal() {
    modal.close();
}

// ─── Modal Lifecycle ──────────────────────────────────────────

modal = createModalLifecycle(overlay, {
    onOpen: ({ songId, title, existingCredits, existingPublishers, onComplete }) => {
        _songId = songId;
        _songTitle = title;
        _onComplete = onComplete;
        _existingCredits = existingCredits || [];
        _existingPublishers = existingPublishers || [];
        _parseResult = null;

        textarea.value = "";
        resultsSect.style.display = "none";
        importBtn.disabled = true;
        importBtn.textContent = "Import Credits";
        overlay.style.display = "flex";
        _isSelecting = false;
        textarea.focus();
    },
    onClose: () => {
        _songId = null;
        _onComplete = null;
        textarea.value = "";
    },
    overlayClickCheck: (e) => {
        if (_isSelecting) return false;
        if (wasMousedownInside(overlay.querySelector(".link-modal"))) return false;
        return e.target === overlay;
    }
});
