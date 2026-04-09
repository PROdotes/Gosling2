import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderAuditTimeline,
    renderEmptyState,
    renderSongList,
    renderStatus,
    textOrDash,
} from "../components/utils.js";

function renderAlbumCredits(credits, albumId) {
    const items = asArray(credits);
    if (!items.length) {
        return '<div class="muted-note">No album credits linked</div>';
    }

    return `
        <div class="link-chip-list">
            ${items
                .map(
                    (credit) => `
                <span class="link-chip">
                    <button class="link-chip-label"
                            data-action="open-edit-modal"
                            data-chip-type="credit"
                            data-album-id="${albumId}"
                            data-item-id="${credit.name_id}">
                        ${escapeHtml(credit.display_name || credit.name || "-")}
                    </button>
                    <button class="link-chip-remove"
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
        <div class="link-chip-list">
            ${items
                .map(
                    (publisher) => `
                <span class="link-chip tag publisher">
                    <button class="link-chip-label"
                            data-action="open-edit-modal"
                            data-chip-type="publisher"
                            data-item-id="${publisher.id}">
                        ${escapeHtml(publisher.parent_name ? `${publisher.name} (${publisher.parent_name})` : publisher.name)}
                    </button>
                    <button class="link-chip-remove"
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
    ctx.setState({ selectedIndex: -1, displayedItems: albums });
    ctx.updateResultsSummary(albums.length, "album");

    if (!albums.length) {
        ctx.elements.resultsContainer.innerHTML =
            renderEmptyState("No albums found");
        return;
    }

    ctx.elements.resultsContainer.innerHTML = albums
        .map(
            (album, index) => `
        <article class="result-card album-card" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="card-icon">LP</div>
            <div class="card-body">
                <div class="card-title">${escapeHtml(album.title || "Untitled Album")}</div>
                <div class="card-subtitle">${escapeHtml(album.display_artist || "Unknown Artist")}</div>
            </div>
            <div class="card-meta">
                ${album.album_type ? `<span class="pill">${escapeHtml(album.album_type)}</span>` : ""}
                <span class="pill mono">${escapeHtml(album.release_year || "-")}</span>
                ${album.song_count ? `<span class="pill mono">${escapeHtml(album.song_count)} track${album.song_count === 1 ? "" : "s"}</span>` : ""}
                ${album.display_publisher ? `<span class="pill publisher">${escapeHtml(album.display_publisher)}</span>` : ""}
            </div>
            <div class="card-actions">
                <span class="pill mono">#${escapeHtml(album.id || "-")}</span>
            </div>
        </article>
    `,
        )
        .join("");
}

export function renderAlbumDetailLoading(ctx, album) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(album.title || "Untitled Album")} <span class="pill mono">#${escapeHtml(album.id || "-")}</span></div>
            <div class="detail-path">ALBUM${album.album_type ? ` • ${escapeHtml(String(album.album_type).toUpperCase())}` : ""}</div>
        </div>
        <div class="detail-content">
            ${renderStatus("loading", "Loading album detail...")}
        </div>
    `);
}

export function renderAlbumDetailComplete(ctx, album, auditHistory) {
    const credits = asArray(album.credits);
    const songs = asArray(album.songs);
    const publishers = asArray(album.publishers);
    const albumId = album.id;

    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(album.title || "Untitled Album")} <span class="pill mono">#${escapeHtml(album.id || "-")}</span></div>
            <div class="detail-path">ALBUM${album.album_type ? ` • ${escapeHtml(String(album.album_type).toUpperCase())}` : ""}</div>
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
                <div class="section-title-row">
                    <span class="section-title">Publishers</span>
                    <button class="section-add-btn" data-action="open-link-modal" data-modal-type="album-publishers" data-album-id="${albumId}">+ Add</button>
                </div>
                <div class="surface-box">
                    ${renderAlbumPublishers(publishers, albumId)}
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title-row">
                    <span class="section-title">Album Credits</span>
                    <button class="section-add-btn" data-action="open-link-modal" data-modal-type="album-credits" data-album-id="${albumId}">+ Add</button>
                </div>
                <div class="surface-box">
                    ${renderAlbumCredits(credits, albumId)}
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Track List (${songs.length})</div>
                ${renderSongList(songs)}
            </div>

            <div class="detail-section">
                <div class="section-title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>
        </div>
    `);
}
