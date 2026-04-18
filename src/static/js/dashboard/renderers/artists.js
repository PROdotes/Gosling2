import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderAuditTimeline,
    renderSongList,
    renderStatus,
} from "../components/utils.js";

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
    ctx.setState({ selectedIndex: -1, displayedItems: artists });
    ctx.updateResultsSummary(artists.length, "artist");

    const listTitle = document.getElementById("entity-list-title");
    if (listTitle) listTitle.textContent = `Artists (${artists.length})`;

    const actionsSlot = document.getElementById("entity-list-actions");
    if (actionsSlot) {
        const unlinkedCount = artists.filter((a) => a.song_count === 0).length;
        actionsSlot.innerHTML = unlinkedCount > 0
            ? `<button type="button" class="btn danger small" data-action="bulk-delete-unlinked-identities">Delete ${unlinkedCount} unlinked</button>`
            : "";
    }

    if (!artists.length) {
        ctx.elements.resultsContainer.innerHTML =
            '<div class="entity-empty-state">No artists found</div>';
        return;
    }

    ctx.elements.resultsContainer.innerHTML = artists
        .map(
            (artist, index) => `
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
                ${artist.song_count === 0 ? '<span class="pill unlinked">0</span>' : `<span class="pill">${artist.song_count}</span>`}
            </div>
        </div>
    `,
        )
        .join("");
}

export function renderArtistDetailLoading(ctx, artist) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(artist.display_name || "Unnamed Identity")} <span class="pill mono">#${escapeHtml(artist.id || "-")}</span></div>
            <div class="detail-subtitle">${escapeHtml(String(artist.type || "identity").toUpperCase())}${artist.legal_name ? ` • Legal: ${escapeHtml(artist.legal_name)}` : ""}</div>
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
                <div class="section-title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>

            <div class="detail-section">
                <button
                    type="button"
                    class="btn danger"
                    data-action="delete-identity"
                    data-identity-id="${tree.id}"
                    ${!isUnlinked ? 'disabled title="Cannot delete — identity is linked to songs or albums"' : ""}
                >Delete Identity</button>
            </div>
        </div>
    `);
}
