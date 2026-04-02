/**
 * Filename Parser Modal — Extracts metadata from filenames in bulk using patterns.
 * 
 * Usage:
 *   openFilenameParserModal({
 *     entries: [{ id: 1, filename: "Artist - Title.mp3", ... }],
 *     onApply: async () => {}, // Refresh UI after batch update
 *   });
 */

import { previewFilenameParsing, applyFilenameParsing } from "../api.js";
import { escapeHtml } from "./utils.js";

const overlay = document.getElementById("filename-parser-modal");
const patternInput = document.getElementById("filename-pattern-input");
const presetSelect = document.getElementById("filename-preset-select");
const tokenContainer = document.getElementById("filename-parser-tokens");
const previewThead = document.getElementById("filename-preview-thead");
const previewTbody = document.getElementById("filename-preview-tbody");
const applyBtn = document.getElementById("filename-parser-apply-btn");
const indicator = document.getElementById("pattern-valid-indicator");

let _config = null;
let _debounceTimer = null;
let _lastPreview = [];

const TOKENS = [
    { label: "Artist", code: "{Artist}" },
    { label: "Title", code: "{Title}" },
    { label: "Album", code: "{Album}" },
    { label: "Year", code: "{Year}" },
    { label: "BPM", code: "{BPM}" },
    { label: "Genre", code: "{Genre}" },
    { label: "Publisher", code: "{Publisher}" },
    { label: "ISRC", code: "{ISRC}" },
    { label: "Junk", code: "{Ignore}", title: "Skip this part" }
];

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

function initTokens() {
    tokenContainer.innerHTML = TOKENS.map(t => `
        <button class="token-chip ${t.code === '{Ignore}' ? 'ignore' : ''}" 
                data-code="${t.code}" 
                title="${t.title || 'Add ' + t.label}">
            ${t.label}
        </button>
    `).join("");

    tokenContainer.querySelectorAll(".token-chip").forEach(btn => {
        btn.addEventListener("click", () => {
            const code = btn.dataset.code;
            const start = patternInput.selectionStart;
            const end = patternInput.selectionEnd;
            const text = patternInput.value;
            
            // Insert at cursor
            patternInput.value = text.slice(0, start) + code + text.slice(end);
            patternInput.dispatchEvent(new Event("input"));
            
            // Refocus
            patternInput.focus();
            const newPos = start + code.length;
            patternInput.setSelectionRange(newPos, newPos);
        });
    });
}

initTokens();

// ---------------------------------------------------------------------------
// Main Logic
// ---------------------------------------------------------------------------

async function updatePreview() {
    const pattern = patternInput.value.trim();
    if (!pattern || !_config || _config.entries.length === 0) {
        previewThead.innerHTML = "";
        previewTbody.innerHTML = "";
        applyBtn.disabled = true;
        indicator.textContent = "";
        return;
    }

    indicator.textContent = "⏳";
    
    try {
        const filenames = _config.entries.map(e => e.filename);
        const data = await previewFilenameParsing(filenames, pattern);
        
        _lastPreview = data.results;
        renderPreviewTable(data.results);
        
        // Validation indicator
        const successCount = data.results.filter(r => Object.keys(r.metadata).length > 0).length;
        if (successCount === data.results.length) {
            indicator.textContent = "✓";
            indicator.style.color = "var(--success)";
        } else if (successCount > 0) {
            indicator.textContent = "⚠";
            indicator.style.color = "var(--warning)";
        } else {
            indicator.textContent = "✕";
            indicator.style.color = "var(--danger)";
        }
        
        applyBtn.disabled = successCount === 0;
    } catch (err) {
        console.error("Preview failed:", err);
        indicator.textContent = "✕";
        indicator.style.color = "var(--danger)";
        applyBtn.disabled = true;
    }
}

function renderPreviewTable(results) {
    if (!results.length) {
        previewThead.innerHTML = "";
        previewTbody.innerHTML = "";
        return;
    }

    // Single-file mode: filename header + field rows
    const r = results[0];
    const fields = Object.entries(r.metadata || {});

    previewThead.innerHTML = `
        <tr><th colspan="2" class="preview-filename" title="${escapeHtml(r.filename)}">${escapeHtml(r.filename)}</th></tr>
    `;

    previewTbody.innerHTML = fields.length
        ? fields.map(([k, v]) => `
            <tr>
                <td class="preview-field-name">${escapeHtml(k)}</td>
                <td class="preview-val-found">${escapeHtml(v)}</td>
            </tr>`).join("")
        : `<tr><td colspan="2" class="preview-val-missing">No fields matched</td></tr>`;
}

// ---------------------------------------------------------------------------
// Event Handlers
// ---------------------------------------------------------------------------

patternInput.addEventListener("input", () => {
    clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(updatePreview, 300);
    
    // Update Preset Select if it matches
    presetSelect.value = Array.from(presetSelect.options).some(o => o.value === patternInput.value) 
        ? patternInput.value 
        : "";
});

presetSelect.addEventListener("change", () => {
    patternInput.value = presetSelect.value;
    patternInput.dispatchEvent(new Event("input"));
});

applyBtn.addEventListener("click", async () => {
    if (!_config) return;
    
    const pattern = patternInput.value.trim();
    if (!pattern) return;

    applyBtn.disabled = true;
    applyBtn.textContent = "Applying...";
    const { onApply, onError } = _config;

    try {
        const items = _config.entries.map(e => ({
            song_id: e.id,
            filename: e.filename
        }));

        await applyFilenameParsing(items, pattern);
        closeFilenameParserModal();
        if (onApply) await onApply();
    } catch (err) {
        if (typeof onError === "function") onError(`Apply failed: ${err.message}`);
        applyBtn.disabled = false;
        applyBtn.textContent = "Apply Metadata";
    }
});

// ---------------------------------------------------------------------------
// Open / Close
// ---------------------------------------------------------------------------

export function openFilenameParserModal(config) {
    _config = config;
    overlay.style.display = "flex";
    applyBtn.disabled = true;
    applyBtn.textContent = "Apply Metadata";
    
    // Default pattern from storage or simple default
    const saved = localStorage.getItem("gosling_last_pattern");
    patternInput.value = saved || "{Artist} - {Title}";
    presetSelect.value = patternInput.value;
    
    updatePreview();
}

export function closeFilenameParserModal() {
    overlay.style.display = "none";
    localStorage.setItem("gosling_last_pattern", patternInput.value);
    _config = null;
    _lastPreview = [];
}

// Modal closing helpers
overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeFilenameParserModal();
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.style.display === "flex") {
        e.stopImmediatePropagation();
        closeFilenameParserModal();
    }
});
