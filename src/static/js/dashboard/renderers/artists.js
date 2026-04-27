import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderAuditTimeline,
    renderSongList,
    renderStatus,
} from "../components/utils.js";
import { renderEntityList, renderDetailLoading, renderDeleteSection } from "./entity_renderer.js";

function renderIdentityTags(items) {
    const identities = asArray(items);
    if (!identities.length) {
        return "";
    }

    return `
        <div class="chip-list">
            ${identities
                .map(
                    (identity) => `
                <button type="button" class="chip link" ${buildNavigateAttrs("artists", identity.display_name || "")}>${escapeHtml(identity.display_name || "-")}</button>
            `,
                )
                .join("")}
        </div>
    `;
}

function renderAliasTags(items) {
    const aliases = asArray(items).filter((a) => !a.is_primary);
    if (!aliases.length) {
        return "";
    }

    return `
        <div class="chip-list">
            ${aliases
                .map(
                    (alias) => `
                <button type="button" class="chip link" ${buildNavigateAttrs("artists", alias.display_name || "")}>${escapeHtml(alias.display_name || "-")}</button>
            `,
                )
                .join("")}
        </div>
    `;
}

export function renderArtists(ctx, artists) {
    const empty = renderEntityList(ctx, artists, {
        entityType: "artist",
        listTitle: "Artists",
        emptyMessage: "No artists found",
        renderRow: (artist, index) => `
        <div class="entity-row" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="entity-row-info">
                <div class="entity-row-title">
                    ${escapeHtml(artist.display_name || "Unnamed Identity")}
                    <span class="entity-row-id">#${escapeHtml(artist.id || "-")}</span>
                </div>
                <div class="entity-row-sub">${escapeHtml(artist.type || "identity")}</div>
            </div>
            <div class="entity-row-meta">
                <span class="pill artist">${escapeHtml(artist.type || "identity")}</span>
                ${artist.can_delete ? '<span class="pill unlinked">0</span>' : `<span class="pill">${artist.song_count}</span>`}
            </div>
        </div>
    `,
        getUnlinkedCount: (items) => items.filter((a) => a.can_delete).length,
        deleteAction: "bulk-delete-unlinked-identities",
    });
    if (empty) return;
}

export function renderArtistDetailLoading(ctx, artist) {
    renderDetailLoading(
        ctx,
        artist,
        escapeHtml(String(artist.type || "identity").toUpperCase()),
        escapeHtml(artist.display_name || "Unnamed Identity"),
        artist.legal_name ? ` • Legal: ${escapeHtml(artist.legal_name)}` : "",
    );
}

export function renderArtistDetailComplete(ctx, tree, songs, auditHistory) {
    const aliases = renderAliasTags(tree.aliases);
    const members = renderIdentityTags(tree.members);
    const groups = renderIdentityTags(tree.groups);
    const catalogHtml = renderSongList(songs, "No songs mapped yet");

    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(tree.display_name || "Unnamed Identity")} <span class="pill mono">#${escapeHtml(tree.id || "-")}</span></div>
            <div class="detail-subtitle">${escapeHtml(String(tree.type || "identity").toUpperCase())}${tree.legal_name ? ` • Legal: ${escapeHtml(tree.legal_name)}` : ""}</div>
        </div>
        <div class="detail-content">
            ${aliases ? `<div class="detail-section"><div class="section-title">Aliases</div>${aliases}</div>` : ""}
            ${members ? `<div class="detail-section"><div class="section-title">Members</div>${members}</div>` : ""}
            ${groups ? `<div class="detail-section"><div class="section-title">Member Of</div>${groups}</div>` : ""}
 
            <div class="detail-section">
                <div class="section-title">Full Catalog (${asArray(songs).length})</div>
                ${catalogHtml}
            </div>

            <div class="detail-section">
                <div class="title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>

            ${renderDeleteSection("delete-identity", tree.id, tree.can_delete, "Cannot delete — identity is linked to songs or albums")}
        </div>
    `);
}
