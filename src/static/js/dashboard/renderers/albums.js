import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderAuditTimeline,
    renderEmptyState,
    renderStatus,
    textOrDash,
} from "../components/utils.js";

function renderAlbumSongs(songs) {
    const items = asArray(songs);
    if (!items.length) {
        return '<div class="muted-note">No songs linked yet</div>';
    }

    return `
        <div class="stack-list">
            ${items.map((song) => `
                <div class="list-row linkable" data-action="navigate-search" data-mode="songs" data-query="${escapeHtml(song.media_name || song.title || "")}">
                    <div>
                        <div class="credit-name">${escapeHtml(song.media_name || song.title || "Untitled")}</div>
                        <div class="credit-role">${escapeHtml(song.display_artist || "Unknown Artist")}</div>
                    </div>
                    <span class="credit-role mono">${escapeHtml(song.formatted_duration || "")}</span>
                </div>
            `).join("")}
        </div>
    `;
}

function renderCredits(credits) {
    const items = asArray(credits);
    if (!items.length) {
        return '<div class="muted-note">No album credits linked</div>';
    }

    return `
        <div class="credits-list">
            ${items.map((credit) => `
                <div class="credit-item">
                    <span class="credit-name"><button class="inline-link" ${buildNavigateAttrs("artists", credit.display_name || credit.name || "")}>${escapeHtml(credit.display_name || credit.name || "-")}</button></span>
                    <span class="credit-role">${escapeHtml(credit.role_name || "-")}</span>
                </div>
            `).join("")}
        </div>
    `;
}

function renderPublishers(publishers) {
    const items = asArray(publishers);
    if (!items.length) {
        return '<div class="muted-note">No album publishers linked</div>';
    }

    return `
        <div class="tag-list">
            ${items.map((publisher) => `
                <button class="tag publisher link" ${buildNavigateAttrs("publishers", publisher.name)}>
                    ${escapeHtml(publisher.parent_name ? `${publisher.name} (${publisher.parent_name})` : publisher.name)}
                </button>
            `).join("")}
        </div>
    `;
}

export function renderAlbums(ctx, albums) {
    ctx.setState({ selectedIndex: -1 });
    ctx.updateResultsSummary(albums.length, "album");

    if (!albums.length) {
        ctx.elements.resultsContainer.innerHTML = renderEmptyState("No albums found");
        return;
    }

    ctx.elements.resultsContainer.innerHTML = albums.map((album, index) => `
        <article class="result-card album-card" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="card-icon">LP</div>
            <div class="card-body">
                <div class="card-title-row">
                    <div class="card-title">${escapeHtml(album.title || "Untitled Album")}</div>
                    <span class="pill mono">#${escapeHtml(album.id || "-")}</span>
                </div>
                <div class="card-subtitle">${escapeHtml(album.display_artist || "Unknown Artist")}</div>
                <div class="card-meta">
                    ${album.album_type ? `<span class="pill">${escapeHtml(album.album_type)}</span>` : ""}
                    <span class="pill mono">${escapeHtml(album.release_year || "-")}</span>
                    ${album.song_count ? `<span class="pill mono">${escapeHtml(album.song_count)} track${album.song_count === 1 ? "" : "s"}</span>` : ""}
                    ${album.display_publisher ? `<span class="pill publisher">${escapeHtml(album.display_publisher)}</span>` : ""}
                </div>
            </div>
        </article>
    `).join("");
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
                <div class="section-title">Publishers</div>
                ${renderPublishers(album.publishers)}
            </div>

            <div class="detail-section">
                <div class="section-title">Album Credits</div>
                ${renderCredits(credits)}
            </div>

            <div class="detail-section">
                <div class="section-title">Track List (${songs.length})</div>
                ${renderAlbumSongs(songs)}
            </div>

            <div class="detail-section">
                <div class="section-title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>
        </div>
    `);
}
