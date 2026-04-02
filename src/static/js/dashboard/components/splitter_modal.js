/**
 * Splitter modal — splits a combined credit or publisher string into individual entities.
 *
 * Usage:
 *   openSplitterModal({
 *     text: "Earth, Wind & Fire & ABBA",
 *     target: "credits" | "publishers",
 *     classification: "Composer" | null,
 *     remove: { type: "credit" | "publisher", id: 42 },
 *     songId: 1,
 *     onConfirm: async () => {},   // called after successful confirm
 *   });
 */

import { splitterTokenize, splitterPreview, splitterConfirm } from "../api.js";

const overlay    = document.getElementById("splitter-modal");
const tokenRow   = document.getElementById("splitter-token-row");
const previewEl  = document.getElementById("splitter-preview");
const confirmBtn = document.getElementById("splitter-confirm-btn");
const customInput = document.getElementById("splitter-custom-input");
const addBtn     = document.getElementById("splitter-add-btn");

let _config = null;
let _tokens = [];
let _separators = [];

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

function renderTokenRow() {
    tokenRow.innerHTML = _tokens.map((token, i) => {
        if (token.type === "name") {
            return `<span class="splitter-name-token">${escapeHtml(token.text)}</span>`;
        }
        const ignored = !!token.ignore;
        return `
            <button class="splitter-sep-token ${ignored ? "splitter-sep--join" : "splitter-sep--split"}"
                    data-index="${i}" title="${ignored ? "Join (click to split)" : "Split (click to join)"}">
                ${escapeHtml(token.text)}
            </button>`;
    }).join("");

    tokenRow.querySelectorAll(".splitter-sep-token").forEach(btn => {
        btn.addEventListener("click", () => {
            const i = Number(btn.dataset.index);
            if (_tokens[i].ignore) {
                delete _tokens[i].ignore;
            } else {
                _tokens[i].ignore = true;
            }
            renderTokenRow();
            updatePreview();
        });
    });
}

async function updatePreview() {
    const names = resolveNames(_tokens);
    previewEl.innerHTML = '<span class="muted-note" style="font-size:0.8rem;">Loading…</span>';

    let results;
    try {
        results = await splitterPreview(names, _config.target);
    } catch {
        previewEl.innerHTML = '<span class="muted-note" style="font-size:0.8rem; color:red;">Preview failed</span>';
        return;
    }

    previewEl.innerHTML = results.map(r => {
        const badge = r.exists
            ? `<span class="splitter-preview-match">existing</span>`
            : `<span class="splitter-preview-new">new</span>`;
        return `<span class="splitter-preview-chip">${escapeHtml(r.name)} ${badge}</span>`;
    }).join("");
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resolveNames(tokens) {
    const names = [];
    let current = [];
    for (const token of tokens) {
        if (token.type === "name") {
            current.push(token.text);
        } else if (token.ignore) {
            current.push(token.text);
        } else if (current.length) {
            names.push(current.join(""));
            current = [];
        }
    }
    if (current.length) names.push(current.join(""));
    return names;
}

function escapeHtml(str) {
    return String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Open / Close
// ---------------------------------------------------------------------------

export async function openSplitterModal(config) {
    _config = config;
    _separators = [...(config.separators || [])];
    _tokens = [];
    tokenRow.innerHTML = '<span class="muted-note" style="font-size:0.8rem;">Loading…</span>';
    previewEl.innerHTML = "";
    customInput.value = "";
    confirmBtn.disabled = false;
    overlay.style.display = "flex";

    try {
        _tokens = await splitterTokenize(config.text, _separators);
    } catch {
        tokenRow.innerHTML = '<span class="muted-note" style="color:red;">Tokenize failed</span>';
        return;
    }

    renderTokenRow();
    updatePreview();
}

export function closeSplitterModal() {
    overlay.style.display = "none";
    _config = null;
    _tokens = [];
}

// ---------------------------------------------------------------------------
// Add custom separator
// ---------------------------------------------------------------------------

addBtn.addEventListener("click", async () => {
    const raw = customInput.value.trim();
    if (!raw || _separators.includes(raw)) return;
    _separators.push(raw);
    customInput.value = "";

    try {
        _tokens = await splitterTokenize(_config.text, _separators);
    } catch {
        return;
    }
    renderTokenRow();
    updatePreview();
});

customInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") addBtn.click();
});

// ---------------------------------------------------------------------------
// Confirm
// ---------------------------------------------------------------------------

confirmBtn.addEventListener("click", async () => {
    if (!_config) return;
    confirmBtn.disabled = true;
    try {
        await splitterConfirm(
            _config.songId,
            _tokens,
            _config.target,
            _config.classification ?? null,
            _config.remove,
        );
        const onConfirm = _config.onConfirm;
        closeSplitterModal();
        await onConfirm();
    } catch (err) {
        confirmBtn.disabled = false;
        console.error("Splitter confirm failed:", err);
    }
});

// ---------------------------------------------------------------------------
// Close handlers
// ---------------------------------------------------------------------------

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.style.display === "flex") {
        e.stopImmediatePropagation();
        closeSplitterModal();
    }
});

overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeSplitterModal();
});
