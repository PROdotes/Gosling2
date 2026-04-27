import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderAuditTimeline,
    renderSongList,
    renderStatus,
    textOrDash,
} from "../components/utils.js";
import { renderEntityList, renderDetailLoading, renderDeleteSection } from "./entity_renderer.js";

function renderAlbumCredits(credits, albumId) {
    const items = asArray(credits);
    if (!items.length) {
        return '<div class="muted-note">No album credits linked</div>';
    }

    return `
        <div class="chip-list">
            ${items
                .map(
                    (credit) => `
                <span class="chip">
                    <button class="inline-link"
                            data-action="open-edit-modal"
                            data-chip-type="credit"
                            data-album-id="${albumId}"
                            data-item-id="${credit.name_id}">
                        ${escapeHtml(credit.display_name || credit.name || "-")}
                    </button>
                    <button class="chip-remove"
                            data-action="remove-album-credit"
                            data-album-id="${albumId}"
                            data-credit-id="${credit.name_id}"
                            title="Remove">✕</button>
                </span>
            `,
                )
                .join("")}
        </div>
    `;
}

function renderAlbumPublishers(publishers, albumId) {
    const items = asArray(publishers);
    if (!items.length) {
        return '<div class="muted-note">No album publishers linked</div>';
    }

    return `
        <div class="chip-list">
            ${items
                .map(
                    (publisher) => `
                <span class="chip publisher">
                    <button class="inline-link"
                            data-action="open-edit-modal"
                            data-chip-type="publisher"
                            data-item-id="${publisher.id}">
                        ${escapeHtml(publisher.parent_name ? `${publisher.name} (${publisher.parent_name})` : publisher.name)}
                    </button>
                    <button class="chip-remove"
                            data-action="remove-album-publisher"
                            data-album-id="${albumId}"
                            data-publisher-id="${publisher.id}"
                            title="Remove">✕</button>
                </span>
            `,
                )
                .join("")}
        </div>
    `;
}

export function renderAlbums(ctx, albums) {
    const empty = renderEntityList(ctx, albums, {
        entityType: "album",
        listTitle: "Albums",
        emptyMessage: "No albums found",
        renderRow: (album, index) => `
        <div class="entity-row" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="entity-row-info">
                <div class="entity-row-title">
                    ${escapeHtml(album.title || "Untitled Album")}
                    <span class="entity-row-id">#${escapeHtml(album.id || "-")}</span>
                </div>
                <div class="entity-row-sub">${escapeHtml(album.display_artist || "Unknown Artist")}${album.album_type ? ` · ${escapeHtml(album.album_type)}` : ""}</div>
            </div>
            <div class="entity-row-meta">
                <span class="pill mono">${escapeHtml(album.release_year || "-")}</span>
                ${album.can_delete ? '<span class="pill unlinked">0</span>' : `<span class="pill">${album.song_count}</span>`}
                ${album.display_publisher ? `<span class="pill publisher">${escapeHtml(album.display_publisher)}</span>` : ""}
            </div>
        </div>
    `,
        getUnlinkedCount: (items) => items.filter((a) => a.can_delete).length,
        deleteAction: "bulk-delete-unlinked-albums",
    });
    if (empty) return;
}

export function renderAlbumDetailLoading(ctx, album) {
    renderDetailLoading(
        ctx,
        album,
        "ALBUM",
        escapeHtml(album.title || "Untitled Album"),
        album.album_type ? ` • ${escapeHtml(String(album.album_type).toUpperCase())}` : "",
    );
}

export function renderAlbumDetailComplete(ctx, album, auditHistory) {
    const credits = asArray(album.credits);
    const songs = asArray(album.songs);
    const publishers = asArray(album.publishers);
    const albumId = album.id;

    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(album.title || "Untitled Album")} <span class="pill mono">#${escapeHtml(album.id || "-")}</span></div>
            <div class="detail-subtitle">ALBUM${album.album_type ? ` • ${escapeHtml(String(album.album_type).toUpperCase())}` : ""}</div>
        </div>
        <div class="detail-content">
            <div class="detail-section">
                <div class="section-title">Overview</div>
                <div class="meta-grid">
                    <div class="meta-item"><div class="meta-label">Artist</div><div class="meta-value">${album.display_artist ? `<button class="inline-link" ${buildNavigateAttrs("artists", album.display_artist)}>${escapeHtml(album.display_artist)}</button>` : "-"}</div></div>
                    <div class="meta-item"><div class="meta-label">Year</div><div class="meta-value">${textOrDash(album.release_year)}</div></div>
                    <div class="meta-item"><div class="meta-label">Type</div><div class="meta-value">${textOrDash(album.album_type)}</div></div>
                    <div class="meta-item"><div class="meta-label">Songs</div><div class="meta-value">${escapeHtml(album.song_count || 0)}</div></div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">
                    <span>Publishers</span>
                    <button type="button" class="btn add small" data-action="open-link-modal" data-modal-type="album-publishers" data-album-id="${albumId}">+ Add</button>
                </div>
                ${renderAlbumPublishers(publishers, albumId)}
            </div>

            <div class="detail-section">
                <div class="section-title">
                    <span>Album Credits</span>
                    <button type="button" class="btn add small" data-action="open-link-modal" data-modal-type="album-credits" data-album-id="${albumId}">+ Add</button>
                </div>
                ${renderAlbumCredits(credits, albumId)}
            </div>

            <div class="detail-section">
                <div class="section-title">Track List (${songs.length})</div>
                ${renderSongList(songs)}
            </div>

            <div class="detail-section">
                <div class="title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>

            ${renderDeleteSection("delete-album", albumId, album.can_delete, "Cannot delete — album has songs")}
        </div>
    `);
}
