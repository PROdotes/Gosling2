import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderSongList,
    renderStatus,
} from "../components/utils.js";
import { renderEntityList, renderDetailLoading, renderDeleteSection } from "./entity_renderer.js";

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
    const empty = renderEntityList(ctx, publishers, {
        entityType: "publisher",
        listTitle: "Publishers",
        emptyMessage: "No publishers found",
        renderRow: (publisher, index) => `
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
        getUnlinkedCount: (items) => items.filter((p) => p.can_delete).length,
        deleteAction: "bulk-delete-unlinked-publishers",
    });
    if (empty) return;
}

export function renderPublisherDetailLoading(ctx, publisher) {
    renderDetailLoading(
        ctx,
        publisher,
        "PUBLISHER",
        escapeHtml(publisher.name || "Unnamed Publisher"),
    );
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

            ${renderDeleteSection("delete-publisher", publisher.id, publisher.can_delete, "Cannot delete — publisher is linked to songs or albums")}
        </div>
    `);
}
