import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderAuditTimeline,
    renderEmptyState,
    renderStatus,
    textOrDash,
} from "../components/utils.js";

function compareRow(label, dbValue, fileValue) {
    const left = dbValue === null || dbValue === undefined || dbValue === "" ? "-" : String(dbValue);
    const right = fileValue === null || fileValue === undefined || fileValue === "" ? "-" : String(fileValue);
    const matches = left.toLowerCase() === right.toLowerCase();
    const rightClass = matches ? "comparison-match" : "comparison-miss";

    return `
        <tr>
            <td>${escapeHtml(label)}</td>
            <td>${escapeHtml(left)}</td>
            <td class="${rightClass}">${escapeHtml(right)}</td>
        </tr>
    `;
}

function editableScalarRow(label, field, dbValue, fileValue, songId) {
    const display = dbValue === null || dbValue === undefined || dbValue === "" ? "-" : String(dbValue);
    const right = fileValue === null || fileValue === undefined || fileValue === "" ? "-" : String(fileValue);
    const matches = display.toLowerCase() === right.toLowerCase();
    const rightClass = matches ? "comparison-match" : "comparison-miss";
    return `
        <tr>
            <td>${escapeHtml(label)}</td>
            <td>
                <span class="inline-edit-display" data-action="start-edit-scalar" data-song-id="${songId}" data-field="${field}" title="Click to edit">${escapeHtml(display)}</span>
            </td>
            <td class="${rightClass}">${escapeHtml(right)}</td>
        </tr>
    `;
}

function renderCreditsGroups(credits, songId, allRoles) {
    const items = asArray(credits);

    // Group credits by role_name
    const grouped = new Map();
    items.forEach((credit) => {
        const role = credit.role_name || "";
        if (!grouped.has(role)) grouped.set(role, []);
        grouped.get(role).push(credit);
    });

    // Build ordered list: all known roles first, then any unexpected roles from credits
    const roles = [...(allRoles || [])];
    for (const role of grouped.keys()) {
        if (role && !roles.includes(role)) roles.push(role);
    }

    if (!roles.length && !items.length) {
        return '<div class="muted-note">No credits found</div>';
    }

    return roles
        .map((role) => {
            const groupItems = grouped.get(role) || [];
            return `
            <div class="stack-list" style="margin-bottom: 0.85rem;">
                <button class="mini-label mini-label--clickable"
                        data-action="open-link-modal"
                        data-modal-type="credits"
                        data-song-id="${songId}"
                        data-role="${escapeHtml(role)}"
                        title="Add ${escapeHtml(role)}">
                    ${escapeHtml(role || "Unknown")} +
                </button>
                ${groupItems.length ? `
                <div class="link-chip-list">
                    ${groupItems.map((credit) => `
                        <span class="link-chip">
                            <button class="link-chip-label"
                                    data-action="open-edit-modal"
                                    data-chip-type="credit"
                                    data-song-id="${songId}"
                                    data-item-id="${credit.name_id}">
                                ${escapeHtml(credit.display_name || "-")}
                            </button>
                            <button class="link-chip-remove"
                                    data-action="remove-credit"
                                    data-song-id="${songId}"
                                    data-credit-id="${credit.credit_id}"
                                    title="Remove">✕</button>
                        </span>
                    `).join("")}
                </div>` : ""}
            </div>`;
        })
        .join("");
}

const ALBUM_TYPES = ["Album", "EP", "Single", "Compilation", "Anthology"];

function renderAlbumCards(albums, songId) {
    const items = asArray(albums);
    if (!items.length) {
        return '<div class="muted-note">No albums linked</div>';
    }

    return items.map((album) => {
        const title = album.album_title || album.display_title || "Unknown Album";
        const albumCredits = asArray(album.credits);
        const albumPublishers = asArray(album.album_publishers);
        const albumId = album.album_id || album.id;
        const isEditable = !!songId;

        const typeOptions = ALBUM_TYPES.map((t) =>
            `<option value="${t}" ${album.album_type === t ? "selected" : ""}>${t}</option>`
        ).join("");

        return `
            <div class="album-card-detail">
                <div class="card-title-row">
                    ${isEditable
                        ? `<span class="editable-scalar" data-action="start-edit-album-scalar" data-album-id="${albumId}" data-song-id="${songId}" data-field="title">${escapeHtml(title)}</span>`
                        : `<button class="inline-link" ${buildNavigateAttrs("albums", title)}>${escapeHtml(title)}</button>`
                    }
                    ${isEditable ? `<button class="link-chip-remove" data-action="remove-album" data-song-id="${songId}" data-album-id="${albumId}" title="Remove album">✕</button>` : ""}
                </div>
                <div class="stack-list">
                    <button class="mini-label mini-label--clickable" data-action="open-link-modal" data-modal-type="album-credits" data-album-id="${albumId}" data-song-id="${songId}" title="Add artist">Performer +</button>
                    <div class="link-chip-list">
                        ${isEditable ? albumCredits.map((credit) => `
                            <span class="link-chip">
                                <button class="link-chip-label" data-action="open-edit-modal" data-chip-type="credit" data-album-id="${albumId}" data-item-id="${credit.name_id}">${escapeHtml(credit.display_name || credit.name || "-")}</button>
                                <button class="link-chip-remove" data-action="remove-album-credit" data-album-id="${albumId}" data-song-id="${songId}" data-credit-id="${credit.name_id}" title="Remove">✕</button>
                            </span>
                        `).join("") : (albumCredits.length ? albumCredits.map((credit) => `<span class="link-chip"><button class="link-chip-label">${escapeHtml(credit.display_name || credit.name || "-")}</button></span>`).join("") : '<span class="muted-note">-</span>')}
                    </div>
                </div>
                <div class="stack-list">
                    <button class="mini-label mini-label--clickable" data-action="open-link-modal" data-modal-type="album-publishers" data-album-id="${albumId}" data-song-id="${songId}" title="Add publisher">Publisher +</button>
                    <div class="link-chip-list">
                        ${isEditable ? albumPublishers.map((p) => `
                            <span class="link-chip tag publisher">
                                <button class="link-chip-label" data-action="open-edit-modal" data-chip-type="publisher" data-item-id="${p.id}">${escapeHtml(p.name)}</button>
                                <button class="link-chip-remove" data-action="remove-album-publisher" data-album-id="${albumId}" data-song-id="${songId}" data-publisher-id="${p.id}" title="Remove">✕</button>
                            </span>
                        `).join("") : (albumPublishers.length ? albumPublishers.map((p) => `<span class="link-chip tag publisher">${escapeHtml(p.name)}</span>`).join("") : '<span class="muted-note">-</span>')}
                    </div>
                </div>
                ${isEditable ? `
                <div class="album-field-row">
                    <span class="mini-label">Type</span>
                    <select class="album-type-select" data-action="change-album-type" data-album-id="${albumId}" data-song-id="${songId}">${typeOptions}</select>
                </div>` : `<div class="album-field-row"><span class="mini-label">Type</span> ${album.album_type ? `<span class="pill">${escapeHtml(album.album_type)}</span>` : `<span class="pill">-</span>`}</div>`}
                ${isEditable ? `
                <div class="album-field-row">
                    <span class="mini-label">Year</span>
                    <span class="editable-scalar" data-action="start-edit-album-scalar" data-album-id="${albumId}" data-song-id="${songId}" data-field="release_year">${album.release_year || "-"}</span>
                </div>` : `<div class="album-field-row"><span class="mini-label">Year</span> ${album.release_year ? `<span class="pill mono">${escapeHtml(album.release_year)}</span>` : `<span class="pill mono">-</span>`}</div>`}
                ${isEditable ? `
                <div class="album-field-row">
                    <span class="mini-label">Disc</span>
                    <span class="editable-scalar" data-action="start-edit-album-link" data-album-id="${albumId}" data-song-id="${songId}" data-field="disc_number">${album.disc_number ?? "-"}</span>
                </div>` : `<div class="album-field-row"><span class="mini-label">Disc</span> <span class="pill mono">${album.disc_number ?? "-"}</span></div>`}
                ${isEditable ? `
                <div class="album-field-row">
                    <span class="mini-label">Track</span>
                    <span class="editable-scalar" data-action="start-edit-album-link" data-album-id="${albumId}" data-song-id="${songId}" data-field="track_number">${album.track_number ?? "-"}</span>
                </div>` : `<div class="album-field-row"><span class="mini-label">Track</span> <span class="pill mono">${album.track_number ?? "-"}</span></div>`}
                ${isEditable ? `<button class="section-add-btn" data-action="sync-album-from-song" data-album-id="${albumId}" data-song-id="${songId}" style="margin-top:0.5rem">↓ sync from song</button>` : ""}
            </div>
        `;
    }).join("");
}


/**
 * Renders clusters of tags grouped by their category (Genre, Mood, etc.).
 * Mirrors the grouping logic used in credits.
 */
function renderTagGroups(tags, songId, id3Frames) {
    const items = asArray(tags);
    if (!items.length) {
        return '<div class="muted-note">No tags linked</div>';
    }

    // Group by category (Genre, Mood, Era, etc.)
    const grouped = new Map();
    items.forEach((tag) => {
        const cat = tag.category || "Other";
        if (!grouped.has(cat)) {
            grouped.set(cat, []);
        }
        grouped.get(cat).push(tag);
    });

    return Array.from(grouped.entries())
        .map(([cat, groupItems]) => `
            <div class="stack-list" style="margin-bottom: 0.85rem;">
                <div class="mini-label">${escapeHtml(cat)}</div>
                <div class="link-chip-list">
                    ${groupItems.map((tag) => {
            const label = tag.name || "-";
            // Find framing metadata for styling (colors/icons/variants)
            const framesMap = id3Frames || {};
            const frameDef = Object.values(framesMap).find(
                f => typeof f === 'object' && f.tag_category === cat
            );
            const variant = (frameDef && frameDef.variant) ? frameDef.variant : "";
            const chipClass = variant ? `link-chip tag ${variant}` : "link-chip tag";
            return `
                            <span class="${chipClass}">
                                <button class="link-chip-label" 
                                        data-action="open-edit-modal" 
                                        data-chip-type="tag" 
                                        data-item-id="${tag.id}">
                                    ${escapeHtml(label)}
                                </button>
                                <button class="link-chip-remove" 
                                        data-action="remove-tag" 
                                        data-song-id="${songId}" 
                                        data-tag-id="${tag.id}" 
                                        title="Remove">✕</button>
                            </span>
                        `;
        }).join("")}
                </div>
            </div>
        `)
        .join("");
}

// TODO: Migrate to backend sorting when expanding the frontend dashboard (Router, Service, and Repository ORDER BY support).
// State for frontend sorting
let currentSongs = [];
let currentSort = { field: null, direction: null };

function sortSongs(songs, field, direction) {
    const sorted = [...songs];
    sorted.sort((a, b) => {
        const aVal = a[field];
        const bVal = b[field];

        // Null handling: ASC = nulls to bottom, DESC = nulls to top
        if (aVal === null || aVal === undefined || aVal === "") {
            return direction === "asc" ? 1 : -1;
        }
        if (bVal === null || bVal === undefined || bVal === "") {
            return direction === "asc" ? -1 : 1;
        }

        // Numeric comparison for ID field
        if (field === "id") {
            const diff = aVal - bVal;
            return direction === "asc" ? diff : -diff;
        }

        // String comparison (case-insensitive) for text fields
        const aStr = String(aVal).toLowerCase();
        const bStr = String(bVal).toLowerCase();

        if (aStr < bStr) return direction === "asc" ? -1 : 1;
        if (aStr > bStr) return direction === "asc" ? 1 : -1;
        return 0;
    });
    return sorted;
}

function applySortAndRender(ctx, field, direction) {
    currentSort = { field, direction };
    const sorted = field ? sortSongs(currentSongs, field, direction) : currentSongs;
    ctx.setState({ displayedItems: sorted });
    renderSongsCards(ctx, sorted);
    updateSortButtonStates();
}

function clearSort(ctx) {
    currentSort = { field: null, direction: null };
    ctx.setState({ displayedItems: currentSongs });
    renderSongsCards(ctx, currentSongs);
    updateSortButtonStates();
}

function updateSortButtonStates() {
    document.querySelectorAll("[data-sort-field]").forEach((btn) => {
        const field = btn.getAttribute("data-sort-field");
        const direction = btn.getAttribute("data-sort-direction");
        if (field === currentSort.field && direction === currentSort.direction) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
}

function renderSortControls(ctx) {
    return `
        <div class="sort-controls">
            <span class="sort-label">Sort:</span>
            <button class="sort-clear-btn" data-action="clear-sort">Clear</button>
            <div class="sort-buttons">
                <div class="sort-row">
                    <span class="sort-direction">↑</span>
                    <button class="sort-btn" data-action="apply-sort" data-sort-field="media_name" data-sort-direction="asc">Title</button>
                    <button class="sort-btn" data-action="apply-sort" data-sort-field="display_artist" data-sort-direction="asc">Artist</button>
                    <button class="sort-btn" data-action="apply-sort" data-sort-field="id" data-sort-direction="asc">ID</button>
                </div>
                <div class="sort-row">
                    <span class="sort-direction">↓</span>
                    <button class="sort-btn" data-action="apply-sort" data-sort-field="media_name" data-sort-direction="desc">Title</button>
                    <button class="sort-btn" data-action="apply-sort" data-sort-field="display_artist" data-sort-direction="desc">Artist</button>
                    <button class="sort-btn" data-action="apply-sort" data-sort-field="id" data-sort-direction="desc">ID</button>
                </div>
            </div>
        </div>
    `;
}

function renderSongsCards(ctx, songs) {
    const cardsHtml = songs.map((song, index) => `
        <article class="result-card song-card" data-action="select-result" data-id="${song.id}" data-index="${index}" data-selectable="true">
            <div class="card-icon">♪</div>
            <div class="card-body">
                <div class="card-title-row">
                    <div class="card-title">${escapeHtml(song.title || song.media_name || "Untitled")}</div>
                    <span class="pill mono">#${escapeHtml(song.id || "-")}</span>
                </div>
                <div class="card-subtitle">${escapeHtml(song.display_artist || "Unknown Artist")}</div>
                <div class="card-meta">
                    ${song.primary_genre ? `<span class="pill genre">${escapeHtml(song.primary_genre)}</span>` : ""}
                    <span class="pill mono">${escapeHtml(song.year || "-")}</span>
                    ${song.formatted_duration ? `<span class="pill mono">${escapeHtml(song.formatted_duration)}</span>` : ""}
                </div>
            </div>
        </article>
    `).join("");

    ctx.elements.resultsContainer.innerHTML = renderSortControls(ctx) + cardsHtml;

    // Attach event handlers
    ctx.elements.resultsContainer.querySelectorAll("[data-action='apply-sort']").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const field = btn.getAttribute("data-sort-field");
            const direction = btn.getAttribute("data-sort-direction");
            applySortAndRender(ctx, field, direction);
        });
    });

    ctx.elements.resultsContainer.querySelector("[data-action='clear-sort']")?.addEventListener("click", (e) => {
        e.stopPropagation();
        clearSort(ctx);
    });

    updateSortButtonStates();
}

export function renderSongs(ctx, songs) {
    ctx.updateResultsSummary(songs.length, "song");

    currentSongs = songs;

    if (!songs.length) {
        ctx.setState({ selectedIndex: -1, displayedItems: [] });
        ctx.elements.resultsContainer.innerHTML = renderEmptyState("No songs found");
        return;
    }

    // Apply current sort if active, otherwise show in API order
    const displaySongs = currentSort.field ? sortSongs(songs, currentSort.field, currentSort.direction) : songs;
    ctx.setState({ selectedIndex: -1, displayedItems: displaySongs });
    renderSongsCards(ctx, displaySongs);
}

export function renderSongDetailLoading(ctx, song) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(song.title || song.media_name || "Untitled")} <span class="pill mono">#${escapeHtml(song.id || "-")}</span></div>
            <div class="detail-path">${escapeHtml(song.source_path || "No source path")}</div>
        </div>
        <div class="detail-content">
            ${renderStatus("loading", "Loading file info...")}
            <div class="meta-grid">
                <div class="meta-item"><div class="meta-label">Title</div><div class="meta-value">${escapeHtml(song.media_name || song.title || "-")}</div></div>
                <div class="meta-item"><div class="meta-label">Artist</div><div class="meta-value">${escapeHtml(song.display_artist || "-")}</div></div>
                <div class="meta-item"><div class="meta-label">Year</div><div class="meta-value">${textOrDash(song.year)}</div></div>
                <div class="meta-item"><div class="meta-label">BPM</div><div class="meta-value">${textOrDash(song.bpm)}</div></div>
                <div class="meta-item"><div class="meta-label">Duration</div><div class="meta-value">${textOrDash(song.formatted_duration)}</div></div>
                <div class="meta-item"><div class="meta-label">ISRC</div><div class="meta-value mono">${textOrDash(song.isrc)}</div></div>
            </div>
        </div>
    `);
}

const STATUS_LABELS = { 0: "Reviewed", 1: "Ready for Review", 2: "Imported" };
const STATUS_CSS = { 0: "found", 1: "warning", 2: "missing" };

function renderWorkflowStatus(song) {
    const status = song.processing_status ?? 1;
    const blockers = asArray(song.review_blockers);
    const label = STATUS_LABELS[status] ?? `Status ${status}`;
    const css = STATUS_CSS[status] ?? "";

    const blockerHtml = blockers.length
        ? `<div class="workflow-blockers">Required: ${blockers.map(b => `<span class="pill">${escapeHtml(b)}</span>`).join("")}</div>`
        : "";

    const buttonHtml = status === 1 && blockers.length === 0
        ? `<button class="ingest-btn-secondary workflow-approve-btn" data-action="mark-reviewed" data-id="${song.id}">Mark as Reviewed</button>`
        : status === 0
            ? `<button class="ingest-btn-secondary workflow-approve-btn" data-action="unreview-song" data-id="${song.id}">Unreview</button>`
            : "";

    return `
        <div class="file-status ${css} workflow-status">
            <span class="workflow-status-label">${escapeHtml(label)}</span>
            ${blockerHtml}
            ${buttonHtml}
        </div>`;
}

export function renderSongDetailComplete(ctx, song, fileData, auditHistory, id3Frames, allRoles) {
    const dbCredits = asArray(song.credits);
    const fileCredits = asArray(fileData && fileData.credits);
    const dbAlbums = asArray(song.albums);
    const fileAlbums = asArray(fileData && fileData.albums);
    const dbTags = asArray(song.tags);
    const fileTags = asArray(fileData && fileData.tags);
    const dbPublishers = asArray(song.publishers);
    const filePublishers = asArray(fileData && fileData.publishers);
    const statusHtml = fileData ? renderStatus("found", "File verified") : renderStatus("missing", "File not found");
    const rawTags = fileData && fileData.raw_tags ? Object.entries(fileData.raw_tags) : [];
    const artistValue = song.display_artist
        ? `<button class="inline-link" ${buildNavigateAttrs("artists", song.display_artist)}>${escapeHtml(song.display_artist)}</button>`
        : "-";

    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="card-title-row" style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; width: 100%;">
                <div class="detail-title" style="flex: 1;">
                    ${escapeHtml(song.title || song.media_name || "Untitled")} 
                    <span class="pill mono">#${escapeHtml(song.id || "-")}</span>
                </div>
                <button class="ingest-btn-danger" data-action="delete-song" data-id="${song.id}" data-title="${escapeHtml(song.title || song.media_name)}">
                    Delete
                </button>
            </div>
            <div class="detail-path">${escapeHtml(song.source_path || "No source path")}</div>
        </div>
        <div class="detail-content">
            ${statusHtml}
            ${renderWorkflowStatus(song)}

            <div class="detail-section">
                <div class="section-title">Core Metadata</div>
                <div class="surface-box">
                    <table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Field</th>
                                <th>Library</th>
                                <th>File</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${editableScalarRow("Title", "media_name", song.media_name, fileData && fileData.media_name, song.id)}
                            ${compareRow("Artist", song.display_artist, fileData && fileData.display_artist)}
                            ${compareRow("Composer", song.display_composer, fileData && fileData.display_composer)}
                            ${editableScalarRow("Year", "year", song.year, fileData && fileData.year, song.id)}
                            ${compareRow("Genre", song.display_genres, fileData && fileData.display_genres)}
                            ${editableScalarRow("BPM", "bpm", song.bpm, fileData && fileData.bpm, song.id)}
                            ${compareRow("Duration", song.formatted_duration, fileData && fileData.formatted_duration)}
                            ${editableScalarRow("ISRC", "isrc", song.isrc, fileData && fileData.isrc, song.id)}
                            ${compareRow("Publisher (Master)", song.display_master_publisher, fileData && fileData.display_master_publisher)}
                        </tbody>
                    </table>
                </div>
                <div class="meta-item" style="grid-column: span 2">
                    <div class="meta-label">Audio Hash</div>
                    <div class="meta-value mono" style="font-size: 0.72rem; word-break: break-all">${textOrDash(song.audio_hash)}</div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Credits</div>
                <div class="two-column">
                    <div class="surface-box">
                        <div class="mini-label">Library (${dbCredits.length})</div>
                        ${renderCreditsGroups(dbCredits, song.id, allRoles)}
                    </div>
                    <div class="surface-box">
                        <div class="mini-label">File (${fileCredits.length})</div>
                        ${renderCreditsGroups(fileCredits, song.id)}
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title-row">
                    <span class="section-title">Albums</span>
                    <button class="section-add-btn" data-action="open-link-modal" data-modal-type="album" data-song-id="${song.id}">+ Add</button>
                </div>
                <div class="two-column">
                    <div class="surface-box">
                        <div class="mini-label">Library (${dbAlbums.length})</div>
                        <div class="stack-list">${renderAlbumCards(dbAlbums, song.id)}</div>
                    </div>
                    <div class="surface-box">
                        <div class="mini-label">File (${fileAlbums.length})</div>
                        <div class="stack-list">${renderAlbumCards(fileAlbums)}</div>
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title-row">
                    <span class="section-title">Tags</span>
                    <button class="section-add-btn" data-action="open-link-modal" data-modal-type="tags" data-song-id="${song.id}">+ Add</button>
                </div>
                <div class="two-column">
                    <div class="surface-box">
                        <div class="mini-label">Library (${dbTags.length})</div>
                        ${renderTagGroups(dbTags, song.id, id3Frames)}
                    </div>
                    <div class="surface-box">
                        <div class="mini-label">File (${fileTags.length})</div>
                        ${renderTagGroups(fileTags, song.id, id3Frames)}
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title-row">
                    <span class="section-title">Publishers</span>
                    <button class="section-add-btn" data-action="open-link-modal" data-modal-type="publishers" data-song-id="${song.id}">+ Add</button>
                </div>
                <div class="two-column">
                    <div class="surface-box">
                        <div class="mini-label">Library (${dbPublishers.length})</div>
                        <div class="link-chip-list">
                            ${dbPublishers.length ? dbPublishers.map(p => `
                                <span class="link-chip">
                                    <button class="link-chip-label" data-action="open-edit-modal" data-chip-type="publisher" data-item-id="${p.id}">${escapeHtml(p.name)}</button>
                                    <button class="link-chip-remove" data-action="remove-publisher" data-song-id="${song.id}" data-publisher-id="${p.id}" title="Remove">✕</button>
                                </span>
                            `).join("") : '<span class="muted-note">None</span>'}
                        </div>
                    </div>
                    <div class="surface-box"><div class="mini-label">File (${filePublishers.length})</div>
                        <div class="link-chip-list">
                            ${filePublishers.length ? filePublishers.map(tag => `
                                <span class="link-chip tag publisher">
                                    <button class="link-chip-label" data-action="open-edit-modal" data-chip-type="tag" data-item-id="${tag.id}">${escapeHtml(tag.name || "-")}</button>
                                    <button class="link-chip-remove" data-action="remove-tag" data-song-id="${song.id}" data-tag-id="${tag.id}" title="Remove">✕</button>
                                </span>
                            `).join("") : '<span class="muted-note">None</span>'}
                        </div>
                    </div>
                </div>
            </div>

            ${rawTags.length ? `
                <div class="detail-section">
                    <div class="section-title">Raw Tags (${rawTags.length})</div>
                    <div class="surface-box mono">
                        ${rawTags.map(([key, value]) => `<div><span class="comparison-label">${escapeHtml(key)}</span>: ${escapeHtml(asArray(value).join(", "))}</div>`).join("")}
                    </div>
                </div>
            ` : ""}

            <div class="detail-section">
                <div class="section-title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>
        </div>
    `);
}
