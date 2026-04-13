import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderAuditTimeline,
    renderEmptyState,
    renderSongList,
    renderStatus,
} from "../components/utils.js";

function renderIdentityTags(items) {
    const identities = asArray(items);
    if (!identities.length) {
        return "";
    }

    return `
        <div class="tag-list">
            ${identities
                .map(
                    (identity) => `
                <button class="tag link" ${buildNavigateAttrs("artists", identity.display_name || "")}>${escapeHtml(identity.display_name || "-")}</button>
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
        <div class="tag-list">
            ${aliases
                .map(
                    (alias) => `
                <button class="tag ${alias.is_primary ? "genre" : ""} link" ${buildNavigateAttrs("artists", alias.display_name || "")}>${escapeHtml(alias.display_name || "-")}</button>
            `,
                )
                .join("")}
        </div>
    `;
}

export function renderArtists(ctx, artists) {
    ctx.setState({ selectedIndex: -1, displayedItems: artists });
    ctx.updateResultsSummary(artists.length, "artist");

    ctx.elements.sortControlsBox.innerHTML =
        '<span class="sort-label">Sort:</span><span class="muted-note" style="font-size:0.75rem; margin-left:0.5rem;">(Not available for artists)</span>';

    if (!artists.length) {
        ctx.elements.resultsContainer.innerHTML =
            renderEmptyState("No artists found");
        return;
    }

    const unlinkedCount = artists.filter((a) => a.song_count === 0).length;
    const bulkBtn =
        unlinkedCount > 0
            ? `<div class="list-actions"><button class="btn-danger" data-action="bulk-delete-unlinked-identities">Delete ${unlinkedCount} unlinked</button></div>`
            : "";

    ctx.elements.resultsContainer.innerHTML =
        bulkBtn +
        artists
            .map(
                (artist, index) => `
        <article class="result-card artist-card" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="card-icon">ID</div>
            <div class="card-body">
                <div class="card-title">${escapeHtml(artist.display_name || "Unnamed Identity")}</div>
                <div class="card-subtitle mono">#${escapeHtml(artist.id || "-")}</div>
            </div>
            <div class="card-meta">
                <span class="pill artist-badge">${escapeHtml(artist.type || "identity")}</span>
                ${artist.song_count === 0 ? '<span class="pill unlinked">0</span>' : `<span class="pill">${artist.song_count}</span>`}
            </div>
        </article>
    `,
            )
            .join("");
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
    const catalogHtml = renderSongList(songs, "No songs mapped yet");
    const isUnlinked = asArray(songs).length === 0;

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
                ${catalogHtml}
            </div>

            <div class="detail-section">
                <div class="section-title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>

            <div class="detail-section">
                <button
                    class="btn-danger"
                    data-action="delete-identity"
                    data-identity-id="${tree.id}"
                    ${!isUnlinked ? 'disabled title="Cannot delete — identity is linked to songs or albums"' : ""}
                >Delete Identity</button>
            </div>
        </div>
    `);
}
