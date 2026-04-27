import {
    asArray,
    escapeHtml,
    renderSongList,
    renderStatus,
} from "../components/utils.js";
import { renderEntityList, renderDetailLoading, renderDeleteSection } from "./entity_renderer.js";

function renderCategoryBadge(category) {
    if (!category) {
        return '<span class="tag-category-badge other">other</span>';
    }
    const displayCategory = category.toLowerCase();
    return `<span class="tag-category-badge ${displayCategory}">${escapeHtml(displayCategory)}</span>`;
}

export function renderTags(ctx, tags) {
    const empty = renderEntityList(ctx, tags, {
        entityType: "tag",
        listTitle: "Tags",
        emptyMessage: "No tags found",
        renderRow: (tag, index) => `
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
        getUnlinkedCount: (items) => items.filter((t) => t.can_delete).length,
        deleteAction: "bulk-delete-unlinked-tags",
    });
    if (empty) return;
}

export function renderTagDetailLoading(ctx, tag) {
    renderDetailLoading(
        ctx,
        tag,
        "TAG",
        escapeHtml(tag.name || "Unnamed Tag"),
    );
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

            ${renderDeleteSection("delete-tag", tag.id, tag.can_delete, "Cannot delete — tag is linked to songs")}
        </div>
    `);
}
