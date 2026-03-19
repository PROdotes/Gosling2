export function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
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
    return `data-action="navigate-search" data-mode="${escapeHtml(mode)}" data-query="${escapeHtml(query || "")}"`;
}

export function renderAuditTimeline(history) {
    const items = asArray(history);
    if (!items.length) {
        return '<div class="muted-note">No history found for this record</div>';
    }

    return `
        <div class="timeline">
            ${items.map((item) => {
                const typeClass = escapeHtml((item.type || "ACTION").toUpperCase());
                const details = escapeHtml(item.details || "");
                let diffHtml = "";

                if (item.type === "CHANGE" && item.new !== undefined) {
                    const oldValue = item.old === null || item.old === "" ? "(empty)" : item.old;
                    const newValue = item.new === null || item.new === "" ? "(empty)" : item.new;
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
            }).join("")}
        </div>
    `;
}
