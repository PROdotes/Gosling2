/**
 * Duplicate check modal - Part 2A test harness UI. Calls
 * POST /api/v1/songs/{id}/find-duplicates and renders the result.
 * Read-only: no mutate call, nothing here writes to the database.
 *
 * Usage:
 *   openDuplicateCheckModal({ songId: 1, title: "Some Song" });
 */

import { findDuplicates } from "../api.js";
import { escapeHtml } from "./utils.js";
import { createModalLifecycle } from "./modal_lifecycle.js";

const overlay = document.getElementById("dup-check-modal");
const statusEl = document.getElementById("dup-check-status");
const resultsEl = document.getElementById("dup-check-results");

let modal;

// Score bands per docs/todo/duplicate_detection.md ("What was tested"):
// ~0.97+ same recording, ~0.75-0.95 related but different, below is noise floor.
const SAME_RECORDING_THRESHOLD = 0.97;

function renderMatch(match) {
    const scoreClass =
        match.score >= SAME_RECORDING_THRESHOLD
            ? "dup-check-match-score--same-recording"
            : "dup-check-match-score--related";
    const percent = Math.round(match.score * 100);
    const title = match.title || `Song ${match.song_id}`;

    return `
        <div class="dup-check-match">
            <div class="dup-check-match-title-row">
                <span class="dup-check-match-title">${escapeHtml(title)}</span>
                <span class="dup-check-match-score ${scoreClass}">${percent}%</span>
            </div>
            ${match.artist ? `<span class="dup-check-match-artist">${escapeHtml(match.artist)}</span>` : ""}
            ${match.path ? `<span class="dup-check-match-path">${escapeHtml(match.path)}</span>` : ""}
        </div>
    `;
}

async function runCheck(config) {
    statusEl.textContent = "Scanning library...";
    resultsEl.innerHTML = "";

    let result;
    try {
        result = await findDuplicates(config.songId, config.threshold);
    } catch (err) {
        statusEl.textContent = `Duplicate check failed: ${err.message}`;
        return;
    }

    if (!result.comparable) {
        statusEl.textContent =
            "No fingerprint computed for this song yet - it hasn't been " +
            "backfilled or was ingested before acoustic fingerprinting shipped.";
        return;
    }

    if (result.matches.length === 0) {
        statusEl.textContent = "No possible duplicates found.";
        return;
    }

    statusEl.textContent = `${result.matches.length} possible duplicate(s):`;
    resultsEl.innerHTML = result.matches.map(renderMatch).join("");
}

export async function openDuplicateCheckModal(config) {
    modal.open(config);
    // modal.open() does not await onOpen (see modal_lifecycle.js), so the
    // fetch is driven from here instead - callers that await this function
    // get the fully-loaded modal, not just the "Scanning..." placeholder.
    await runCheck(config);
}

export function closeDuplicateCheckModal() {
    modal.close();
}

modal = createModalLifecycle(overlay, {
    onClose: () => {
        statusEl.textContent = "";
        resultsEl.innerHTML = "";
    },
});
