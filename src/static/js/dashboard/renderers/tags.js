import {
    asArray,
    escapeHtml,
    renderSongList,
    renderStatus,
} from "../components/utils.js";

function renderCategoryBadge(category) {
    if (!category) {
        return '<span class="tag-category-badge other">other</span>';
    }
    const displayCategory = category.toLowerCase();
    return `<span class="tag-category-badge ${displayCategory}">${escapeHtml(displayCategory)}</span>`;
}

export function renderTags(ctx, tags) {
    ctx.setState({ selectedIndex: -1, displayedItems: tags });
    ctx.updateResultsSummary(tags.length, "tag");

    const listTitle = document.getElementById("entity-list-title");
    if (listTitle) listTitle.textContent = `Tags (${tags.length})`;

    const actionsSlot = document.getElementById("entity-list-actions");
    if (actionsSlot) {
        const unlinkedCount = tags.filter((t) => t.can_delete).length;
        actionsSlot.innerHTML = unlinkedCount > 0
            ? `<button type="button" class="btn danger small" data-action="bulk-delete-unlinked-tags">Delete ${unlinkedCount} unlinked</button>`
            : "";
    }

    if (!tags.length) {
        ctx.elements.resultsContainer.innerHTML =
            '<div class="entity-empty-state">No tags found</div>';
        return;
    }

    ctx.elements.resultsContainer.innerHTML = tags
        .map(
            (tag, index) => `
        <div class="entity-row" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="entity-row-info">
                <div class="entity-row-title">
                    ${escapeHtml(tag.name || "Unnamed Tag")}
                    <span class="entity-row-id">#${escapeHtml(tag.id || "-")}</span>
                </div>
                <div class="entity-row-sub">${renderCategoryBadge(tag.category)}</div>
            </div>
            <div class="entity-row-meta">
                ${tag.can_delete ? '<span class="pill unlinked">0</span>' : `<span class="pill">${tag.song_count}</span>`}
            </div>
        </div>
    `,
        )
        .join("");
}

export function renderTagDetailLoading(ctx, tag) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(tag.name || "Unnamed Tag")} <span class="pill mono">#${escapeHtml(tag.id || "-")}</span></div>
            <div class="detail-subtitle">TAG</div>
        </div>
        <div class="detail-content">
            ${renderStatus("loading", "Loading songs...")}
        </div>
    `);
}

export function renderTagDetailComplete(ctx, tag, songs) {
    const songCount = asArray(songs).length;
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(tag.name || "Unnamed Tag")} <span class="pill mono">#${escapeHtml(tag.id || "-")}</span></div>
            <div class="detail-subtitle">TAG</div>
        </div>
        <div class="detail-content">
            <div class="detail-section">
                <div class="section-title">Identity</div>
                <div class="meta-grid">
                    <div class="meta-item"><div class="meta-label">Name</div><div class="meta-value">${escapeHtml(tag.name || "-")}</div></div>
                    <div class="meta-item"><div class="meta-label">Category</div><div class="meta-value">${renderCategoryBadge(tag.category)}</div></div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Songs (${songCount})</div>
                ${renderSongList(songs, "No songs linked to this tag")}
            </div>

            <div class="detail-section">
                <button
                    type="button"
                    class="btn danger"
                    data-action="delete-tag"
                    data-tag-id="${tag.id}"
                    ${!tag.can_delete ? 'disabled title="Cannot delete — tag is linked to songs"' : ""}
                >Delete Tag</button>
            </div>
        </div>
    `);
}
