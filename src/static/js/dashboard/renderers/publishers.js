import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderSongList,
    renderStatus,
} from "../components/utils.js";

function renderSubPublishers(items) {
    const publishers = asArray(items);
    if (!publishers.length) {
        return '<div class="muted-note">No sub-publishers linked</div>';
    }

    return `
        <div class="chip-list">
            ${publishers
                .map(
                    (publisher) => `
                <button type="button" class="chip publisher link" ${buildNavigateAttrs("publishers", publisher.name || "")}>${escapeHtml(publisher.name || "-")}</button>
            `,
                )
                .join("")}
        </div>
    `;
}

export function renderPublishers(ctx, publishers) {
    ctx.setState({ selectedIndex: -1, displayedItems: publishers });
    ctx.updateResultsSummary(publishers.length, "publisher");

    const listTitle = document.getElementById("entity-list-title");
    if (listTitle) listTitle.textContent = `Publishers (${publishers.length})`;

    const actionsSlot = document.getElementById("entity-list-actions");
    if (actionsSlot) {
        const unlinkedCount = publishers.filter((p) => p.can_delete).length;
        actionsSlot.innerHTML = unlinkedCount > 0
            ? `<button type="button" class="btn danger small" data-action="bulk-delete-unlinked-publishers">Delete ${unlinkedCount} unlinked</button>`
            : "";
    }

    if (!publishers.length) {
        ctx.elements.resultsContainer.innerHTML =
            '<div class="entity-empty-state">No publishers found</div>';
        return;
    }

    ctx.elements.resultsContainer.innerHTML = publishers
        .map(
            (publisher, index) => `
        <div class="entity-row" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="entity-row-info">
                <div class="entity-row-title">
                    ${escapeHtml(publisher.name || "Unnamed Publisher")}
                    <span class="entity-row-id">#${escapeHtml(publisher.id || "-")}</span>
                </div>
                <div class="entity-row-sub">${escapeHtml(publisher.parent_name || "Independent / top level")}</div>
            </div>
            <div class="entity-row-meta">
                ${publisher.can_delete
                    ? '<span class="pill unlinked">0</span>'
                    : `<span class="pill">${publisher.song_count}S</span><span class="pill">${publisher.album_count}A</span>`}
            </div>
        </div>
    `,
        )
        .join("");
}

export function renderPublisherDetailLoading(ctx, publisher) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(publisher.name || "Unnamed Publisher")} <span class="pill mono">#${escapeHtml(publisher.id || "-")}</span></div>
            <div class="detail-subtitle">PUBLISHER</div>
        </div>
        <div class="detail-content">
            ${renderStatus("loading", "Loading repertoire...")}
        </div>
    `);
}

export function renderPublisherDetailComplete(ctx, publisher, repertoire) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(publisher.name || "Unnamed Publisher")} <span class="pill mono">#${escapeHtml(publisher.id || "-")}</span></div>
            <div class="detail-subtitle">PUBLISHER</div>
        </div>
        <div class="detail-content">
            <div class="detail-section">
                <div class="section-title">Identity</div>
                <div class="meta-grid">
                    <div class="meta-item"><div class="meta-label">Name</div><div class="meta-value">${escapeHtml(publisher.name || "-")}</div></div>
                    <div class="meta-item"><div class="meta-label">Parent</div><div class="meta-value">${publisher.parent_name ? `<button class="inline-link" ${buildNavigateAttrs("publishers", publisher.parent_name)}>${escapeHtml(publisher.parent_name)}</button>` : "None"}</div></div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Sub-Publishers</div>
                ${renderSubPublishers(publisher.sub_publishers)}
            </div>

            <div class="detail-section">
                <div class="section-title">Repertoire (${asArray(repertoire).length})</div>
                ${renderSongList(repertoire, "No songs explicitly linked as master")}
            </div>

            <div class="detail-section">
                <button
                    type="button"
                    class="btn danger"
                    data-action="delete-publisher"
                    data-publisher-id="${publisher.id}"
                    ${!publisher.can_delete ? 'disabled title="Cannot delete — publisher is linked to songs or albums"' : ""}
                >Delete Publisher</button>
            </div>
        </div>
    `);
}
