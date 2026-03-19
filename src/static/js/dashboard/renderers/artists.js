import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderAuditTimeline,
    renderEmptyState,
    renderStatus,
} from "../components/utils.js";

function renderIdentityTags(items) {
    const identities = asArray(items);
    if (!identities.length) {
        return "";
    }

    return `
        <div class="tag-list">
            ${identities.map((identity) => `
                <button class="tag link" ${buildNavigateAttrs("artists", identity.display_name || "")}>${escapeHtml(identity.display_name || "-")}</button>
            `).join("")}
        </div>
    `;
}

function renderAliasTags(items) {
    const aliases = asArray(items);
    if (!aliases.length) {
        return "";
    }

    return `
        <div class="tag-list">
            ${aliases.map((alias) => `
                <button class="tag ${alias.is_primary ? "genre" : ""} link" ${buildNavigateAttrs("artists", alias.display_name || "")}>${escapeHtml(alias.display_name || "-")}</button>
            `).join("")}
        </div>
    `;
}

function renderCatalogSongs(songs) {
    const items = asArray(songs);
    if (!items.length) {
        return '<div class="muted-note">No songs mapped yet</div>';
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

export function renderArtists(ctx, artists) {
    ctx.setState({ selectedIndex: -1 });
    ctx.updateResultsSummary(artists.length, "artist");

    if (!artists.length) {
        ctx.elements.resultsContainer.innerHTML = renderEmptyState("No artists found");
        return;
    }

    ctx.elements.resultsContainer.innerHTML = artists.map((artist, index) => `
        <article class="result-card artist-card" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="card-icon">ID</div>
            <div class="card-body">
                <div class="card-title-row">
                    <div class="card-title">${escapeHtml(artist.display_name || "Unnamed Identity")}</div>
                    <span class="artist-badge">${escapeHtml(artist.type || "identity")}</span>
                </div>
                <div class="card-subtitle mono">#${escapeHtml(artist.id || "-")}</div>
            </div>
        </article>
    `).join("");
}

export function renderArtistDetailLoading(ctx, artist) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(artist.display_name || "Unnamed Identity")} <span class="pill mono">#${escapeHtml(artist.id || "-")}</span></div>
            <div class="detail-path">${escapeHtml(String(artist.type || "identity").toUpperCase())}${artist.legal_name ? ` • Legal: ${escapeHtml(artist.legal_name)}` : ""}</div>
        </div>
        <div class="detail-content">
            ${renderStatus("loading", "Loading artist catalog...")}
        </div>
    `);
}

export function renderArtistDetailComplete(ctx, tree, songs, auditHistory) {
    const aliases = renderAliasTags(tree.aliases);
    const members = renderIdentityTags(tree.members);
    const groups = renderIdentityTags(tree.groups);
    const catalogSongs = renderCatalogSongs(songs);

    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(tree.display_name || "Unnamed Identity")} <span class="pill mono">#${escapeHtml(tree.id || "-")}</span></div>
            <div class="detail-path">${escapeHtml(String(tree.type || "identity").toUpperCase())}${tree.legal_name ? ` • Legal: ${escapeHtml(tree.legal_name)}` : ""}</div>
        </div>
        <div class="detail-content">
            ${aliases ? `<div class="detail-section"><div class="section-title">Aliases</div>${aliases}</div>` : ""}
            ${members ? `<div class="detail-section"><div class="section-title">Members</div>${members}</div>` : ""}
            ${groups ? `<div class="detail-section"><div class="section-title">Member Of</div>${groups}</div>` : ""}

            <div class="detail-section">
                <div class="section-title">Full Catalog (${asArray(songs).length})</div>
                ${catalogSongs}
            </div>

            <div class="detail-section">
                <div class="section-title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>
        </div>
    `);
}
