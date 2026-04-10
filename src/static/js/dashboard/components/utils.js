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

export function renderModuleToolbar(ctx, sortControlsHtml = "") {
    const filterVisible = ctx.handlers?.filterSidebar?._sidebarVisible || false;
    const filterActiveClass = filterVisible ? " active" : "";
    const separator = sortControlsHtml
        ? '<div class="toolbar-separator"></div>'
        : "";

    return `
        <div class="sort-controls">
            <button id="filter-toggle-btn" class="filter-toggle-btn${filterActiveClass}" data-action="toggle-filter-sidebar">Filter</button>
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
        <div class="stack-list">
            ${items
                .map(
                    (song) => `
                <div class="list-row linkable" ${buildNavigateAttrs("songs", song.media_name || song.title || "")}>
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                         <label class="switch ${song.processing_status !== 0 ? "disabled" : ""}" 
                                data-action="toggle-active" 
                                data-id="${song.id}"
                                title="${song.processing_status !== 0 ? "Only reviewed songs can be active for airplay" : song.is_active ? "Deactivate" : "Activate"}">
                             <input type="checkbox" 
                                    ${song.is_active ? "checked" : ""} 
                                    ${song.processing_status !== 0 ? "disabled" : ""}>
                             <span class="slider"></span>
                        </label>
                        <div>
                            <div class="credit-name">${escapeHtml(song.media_name || song.title || "Untitled")}</div>
                            <div class="credit-role">${escapeHtml(song.display_artist || "Unknown Artist")}</div>
                        </div>
                    </div>
                    <div style="text-align: right">
                        <div class="credit-role mono">${escapeHtml(song.formatted_duration || "")}</div>
                        ${song.bpm ? `<div class="meta-label" style="margin: 0">${escapeHtml(song.bpm)} BPM</div>` : ""}
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
    ];
    return modals.some((id) => {
        const el = document.getElementById(id);
        return el && el.style.display === "flex";
    });
}

export function renderAuditTimeline(history) {
    const items = asArray(history);
    if (!items.length) {
        return '<div class="muted-note">No history found for this record</div>';
    }

    return `
        <div class="timeline">
            ${items
                .map((item) => {
                    const typeClass = escapeHtml(
                        (item.type || "ACTION").toUpperCase(),
                    );
                    const details = escapeHtml(item.details || "");
                    let diffHtml = "";

                    if (item.type === "CHANGE" && item.new !== undefined) {
                        const oldValue =
                            item.old === null || item.old === ""
                                ? "(empty)"
                                : item.old;
                        const newValue =
                            item.new === null || item.new === ""
                                ? "(empty)"
                                : item.new;
                        diffHtml = `
                        <div class="timeline-diff">
                            <span class="timeline-old">${escapeHtml(oldValue)}</span>
                            <span>→</span>
                            <span class="timeline-new">${escapeHtml(newValue)}</span>
                        </div>
                    `;
                    }

                    if (item.type === "LIFECYCLE" && item.snapshot) {
                        diffHtml = `<div class="snapshot-box">Snapshot: ${escapeHtml(item.snapshot)}</div>`;
                    }

                    return `
                    <div class="timeline-item ${typeClass}">
                        <div class="timeline-dot"></div>
                        <div class="timeline-content">
                            <div class="timeline-header">
                                <span class="timeline-label">${escapeHtml(item.label || item.type || "Event")}</span>
                                <span class="timeline-time">${escapeHtml(item.timestamp || "")}</span>
                            </div>
                            <div class="timeline-details">${details}</div>
                            ${diffHtml}
                            <div class="timeline-meta">User: ${escapeHtml(item.user || "SYSTEM")} • Batch: ${item.batch ? `#${escapeHtml(item.batch)}` : "-"}</div>
                        </div>
                    </div>
                `;
                })
                .join("")}
        </div>
    `;
}
