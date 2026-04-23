import { PROCESSING_STATUS } from "../constants.js";

// Track mousedown origin so overlay click handlers can ignore drag-outside events
let _lastMousedownTarget = null;
document.addEventListener(
    "mousedown",
    (e) => {
        _lastMousedownTarget = e.target;
    },
    true,
);

/**
 * Returns true if the most recent mousedown started inside the given element.
 * Use this in overlay click handlers to prevent closing when the user drags out.
 */
export function wasMousedownInside(el) {
    return el.contains(_lastMousedownTarget);
}

export function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

export function pluralize(count, singular, plural = `${singular}s`) {
    return count === 1 ? singular : plural;
}

export function formatCountLabel(count, singular, plural) {
    return `${count} ${pluralize(count, singular, plural)}`;
}

export function basename(path) {
    return path?.split(/[/\\]/).pop() ?? "";
}

export function textOrDash(value) {
    if (value === null || value === undefined || value === "") {
        return "-";
    }
    return escapeHtml(value);
}

export function asArray(value) {
    return Array.isArray(value) ? value : [];
}

export function renderEmptyState(message) {
    return `
        <div class="empty-state">
            <div class="empty-glyph">♪</div>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

export function renderStatus(kind, message) {
    return `<div class="file-status ${escapeHtml(kind)}">${escapeHtml(message)}</div>`;
}

export function buildNavigateAttrs(mode, query) {
    return `data-action="navigate-search" data-mode="${escapeHtml(mode)}" data-query="${escapeHtml(String(query || "").trim())}"`;
}

export function renderModuleToolbar(_ctx, sortControlsHtml = "") {
    const separator = sortControlsHtml
        ? '<div class="toolbar-separator"></div>'
        : "";

    return `
        <div class="sort-controls">
            <button id="filter-toggle-btn" class="filter-toggle-btn" data-action="toggle-filter-sidebar">Filter</button>
            ${separator}
            ${sortControlsHtml}
        </div>
    `;
}

export function renderSongList(songs, emptyMessage = "No songs linked yet") {
    const items = asArray(songs);
    if (!items.length) {
        return `<div class="muted-note">${escapeHtml(emptyMessage)}</div>`;
    }

    return `
        <div class="song-sub-list">
            ${items
                .map(
                    (song) => `
                <div class="song-row" ${buildNavigateAttrs("songs", song.media_name || song.title || "")}>
                    <div class="col-check">
                         <label class="switch ${song.can_activate ? "" : "disabled"}"
                                data-action="toggle-active"
                                data-id="${song.id}"
                                title="${song.can_activate ? (song.is_active ? "Deactivate" : "Activate") : "Only reviewed songs can be active for airplay"}">
                             <input type="checkbox"
                                    ${song.is_active ? "checked" : ""}
                                    ${song.can_activate ? "" : "disabled"}>
                             <span class="slider"></span>
                         </label>
                     </div>
                    <div class="col-info">
                        <div class="row-title">${escapeHtml(song.media_name || song.title || "Untitled")}<span class="row-id"> #${song.id}</span></div>
                        <div class="row-artist">${escapeHtml(song.display_artist || "Unknown Artist")}</div>
                    </div>
                    <div class="col-meta">
                        <div>${escapeHtml(song.formatted_duration || "")}</div>
                        ${song.bpm ? `<div>${escapeHtml(song.bpm)} BPM</div>` : ""}
                    </div>
                </div>
            `,
                )
                .join("")}
        </div>
    `;
}

export function isModalOpen() {
    const modals = [
        "edit-modal",
        "link-modal",
        "scrubber-modal",
        "spotify-modal",
        "splitter-modal",
        "filename-parser-modal",
        "confirm-modal",
    ];
    return modals.some((id) => {
        const el = document.getElementById(id);
        return el && el.style.display === "flex";
    });
}

export function renderAuditTimeline(history) {
    const items = asArray(history);
    if (!items.length) {
        return '<div class="audit-empty">No history found for this record</div>';
    }

    return `
        <div class="audit-list">
            ${items
                .map((item) => {
                    const type = (item.type || "ACTION").toUpperCase();
                    const typeClass = escapeHtml(type);
                    let detailsHtml = escapeHtml(
                        item.details || item.label || "",
                    );

                    if (item.type === "CHANGE" && item.new !== undefined) {
                        const oldValue =
                            item.old === null || item.old === ""
                                ? "(empty)"
                                : item.old;
                        const newValue =
                            item.new === null || item.new === ""
                                ? "(empty)"
                                : item.new;
                        const label = item.label
                            ? `${escapeHtml(item.label)}: `
                            : "";
                        detailsHtml = `${label}<span class="audit-old">${escapeHtml(oldValue)}</span><span class="audit-new">${escapeHtml(newValue)}</span>`;
                    } else if (item.type === "LIFECYCLE" && item.snapshot) {
                        detailsHtml = `${escapeHtml(item.label || "Lifecycle")} — ${escapeHtml(item.snapshot)}`;
                    }

                    return `
                    <div class="audit-entry">
                        <span class="audit-ts">${escapeHtml(item.timestamp || "")}</span>
                        <span class="audit-action ${typeClass}">${typeClass}</span>
                        <span class="audit-details">${detailsHtml}</span>
                    </div>
                `;
                })
                .join("")}
        </div>
    `;
}
