import {
    asArray,
    escapeHtml,
    renderEmptyState,
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

    if (!tags.length) {
        ctx.elements.resultsContainer.innerHTML =
            renderEmptyState("No tags found");
        return;
    }

    const unlinkedCount = tags.filter((t) => t.song_count === 0).length;
    const bulkBtn =
        unlinkedCount > 0
            ? `<div class="list-actions"><button class="btn-danger" data-action="bulk-delete-unlinked-tags">Delete ${unlinkedCount} unlinked</button></div>`
            : "";

    ctx.elements.resultsContainer.innerHTML =
        bulkBtn +
        tags
            .map(
                (tag, index) => `
        <article class="result-card tag-card" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="card-icon">TAG</div>
            <div class="card-body">
                <div class="card-title-row">
                    <div class="card-title">${escapeHtml(tag.name || "Unnamed Tag")}</div>
                    <span class="pill mono">#${escapeHtml(tag.id || "-")}</span>
                </div>
                <div class="card-subtitle">${renderCategoryBadge(tag.category)}</div>
            </div>
            <div class="card-meta">
                ${tag.song_count === 0 ? '<span class="pill unlinked">0</span>' : `<span class="pill">${tag.song_count}</span>`}
            </div>
        </article>
    `,
            )
            .join("");
}

export function renderTagDetailLoading(ctx, tag) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(tag.name || "Unnamed Tag")} <span class="pill mono">#${escapeHtml(tag.id || "-")}</span></div>
            <div class="detail-path">TAG</div>
        </div>
        <div class="detail-content">
            ${renderStatus("loading", "Loading songs...")}
        </div>
    `);
}

export function renderTagDetailComplete(ctx, tag, songs) {
    const songCount = asArray(songs).length;
    const isUnlinked = songCount === 0;
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(tag.name || "Unnamed Tag")} <span class="pill mono">#${escapeHtml(tag.id || "-")}</span></div>
            <div class="detail-path">TAG</div>
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
                    class="btn-danger"
                    data-action="delete-tag"
                    data-tag-id="${tag.id}"
                    ${!isUnlinked ? 'disabled title="Cannot delete — tag is linked to songs"' : ""}
                >Delete Tag</button>
            </div>
        </div>
    `);
}
