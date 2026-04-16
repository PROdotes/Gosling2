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
    const left =
        dbValue === null || dbValue === undefined || dbValue === ""
            ? "-"
            : String(dbValue);
    const right =
        fileValue === null || fileValue === undefined || fileValue === ""
            ? "-"
            : String(fileValue);
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
    const display =
        dbValue === null || dbValue === undefined || dbValue === ""
            ? "-"
            : String(dbValue);
    const right =
        fileValue === null || fileValue === undefined || fileValue === ""
            ? "-"
            : String(fileValue);
    const matches = display.toLowerCase() === right.toLowerCase();
    const rightClass = matches ? "comparison-match" : "comparison-miss";

    // Only show casing buttons for titles
    const hasValue =
        dbValue !== null && dbValue !== undefined && dbValue !== "";
    const showActions = hasValue && ["media_name"].includes(field);
    const actionsHtml = showActions
        ? `
        <div class="case-actions">
            <button class="btn-case" data-action="format-case" data-entity-type="song" data-entity-id="${songId}" data-field="${field}" data-type="sentence" title="Sentence Case">S</button>
            <button class="btn-case" data-action="format-case" data-entity-type="song" data-entity-id="${songId}" data-field="${field}" data-type="title" title="Title Case">T</button>
        </div>
    `
        : "";

    return `
        <tr>
            <td>${escapeHtml(label)}</td>
            <td>
                <span class="inline-edit-display" data-action="start-edit-scalar" data-song-id="${songId}" data-field="${field}" title="Click to edit">${escapeHtml(display)}</span>
                ${actionsHtml}
            </td>
            <td class="${rightClass}">${escapeHtml(right)}</td>
        </tr>
    `;
}

function clickableM2MRow(
    label,
    dbValue,
    fileValue,
    songId,
    modalType,
    role = null,
) {
    const left =
        dbValue === null || dbValue === undefined || dbValue === ""
            ? "-"
            : String(dbValue);
    const right =
        fileValue === null || fileValue === undefined || fileValue === ""
            ? "-"
            : String(fileValue);
    const matches = left.toLowerCase() === right.toLowerCase();
    const rightClass = matches ? "comparison-match" : "comparison-miss";

    const roleAttr = role ? `data-role="${escapeHtml(role)}"` : "";

    return `
        <tr>
            <td>${escapeHtml(label)}</td>
            <td>
                <button class="inline-link" 
                        data-action="open-link-modal" 
                        data-modal-type="${modalType}" 
                        data-song-id="${songId}"
                        ${roleAttr}
                        title="Add/Link ${escapeHtml(label)}">
                    ${escapeHtml(left)}
                </button>
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
                ${
                    groupItems.length
                        ? `
                <div class="link-chip-list">
                    ${groupItems
                        .map(
                            (credit) => `
                        <span class="link-chip">
                            <button class="link-chip-label"
                                    data-action="open-edit-modal"
                                    data-chip-type="credit"
                                    data-song-id="${songId}"
                                    data-item-id="${credit.name_id}"
                                    data-identity-id="${credit.identity_id || ""}">
                                ${escapeHtml(credit.display_name || "-")}
                            </button>
                            <button class="link-chip-split"
                                    data-action="open-splitter-modal"
                                    data-song-id="${songId}"
                                    data-text="${escapeHtml(credit.display_name || "")}"
                                    data-target="credits"
                                    data-classification="${escapeHtml(role)}"
                                    data-remove-type="credit"
                                    data-remove-id="${credit.credit_id}"
                                    title="Split">⋯</button>
                            <button class="link-chip-remove"
                                    data-action="remove-credit"
                                    data-song-id="${songId}"
                                    data-credit-id="${credit.credit_id}"
                                    title="Remove">✕</button>
                        </span>
                    `,
                        )
                        .join("")}
                </div>`
                        : ""
                }
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

    return items
        .map((album) => {
            const title =
                album.album_title || album.display_title || "Unknown Album";
            const albumCredits = asArray(album.credits);
            const albumPublishers = asArray(album.album_publishers);
            const albumId = album.album_id || album.id;
            const isEditable = !!songId;

            const typeOptions = ALBUM_TYPES.map(
                (t) =>
                    `<option value="${t}" ${album.album_type === t ? "selected" : ""}>${t}</option>`,
            ).join("");

            return `
            <div class="album-card-detail">
                <div class="card-title-row">
                    ${
                        isEditable
                            ? `<span class="editable-scalar" data-action="start-edit-album-scalar" data-album-id="${albumId}" data-song-id="${songId}" data-field="title" style="flex:1">${escapeHtml(title)}</span>
                           <div class="case-actions">
                               <button class="btn-case" data-action="format-case" data-entity-type="album" data-entity-id="${albumId}" data-song-id="${songId}" data-field="title" data-type="sentence" title="Sentence Case">S</button>
                               <button class="btn-case" data-action="format-case" data-entity-type="album" data-entity-id="${albumId}" data-song-id="${songId}" data-field="title" data-type="title" title="Title Case">T</button>
                           </div>`
                            : `<button class="inline-link" ${buildNavigateAttrs("albums", title)}>${escapeHtml(title)}</button>`
                    }
                    ${isEditable ? `<button class="link-chip-remove" data-action="remove-album" data-song-id="${songId}" data-album-id="${albumId}" title="Remove album">✕</button>` : ""}
                </div>
                <div class="stack-list">
                    <button class="mini-label mini-label--clickable" data-action="open-link-modal" data-modal-type="album-credits" data-album-id="${albumId}" data-song-id="${songId}" title="Add artist">Performer +</button>
                    <div class="link-chip-list">
                        ${
                            isEditable
                                ? albumCredits
                                      .map(
                                          (credit) => `
                            <span class="link-chip">
                                <button class="link-chip-label" data-action="open-edit-modal" data-chip-type="credit" data-album-id="${albumId}" data-item-id="${credit.name_id}" data-identity-id="${credit.identity_id || ""}">${escapeHtml(credit.display_name || credit.name || "-")}</button>
                                <button class="link-chip-remove" data-action="remove-album-credit" data-album-id="${albumId}" data-song-id="${songId}" data-credit-id="${credit.name_id}" title="Remove">✕</button>
                            </span>
                        `,
                                      )
                                      .join("")
                                : albumCredits.length
                                  ? albumCredits
                                        .map(
                                            (credit) =>
                                                `<span class="link-chip"><button class="link-chip-label">${escapeHtml(credit.display_name || credit.name || "-")}</button></span>`,
                                        )
                                        .join("")
                                  : '<span class="muted-note">-</span>'
                        }
                    </div>
                </div>
                <div class="stack-list">
                    <button class="mini-label mini-label--clickable" data-action="open-link-modal" data-modal-type="album-publishers" data-album-id="${albumId}" data-song-id="${songId}" title="Add publisher">Publisher +</button>
                    <div class="link-chip-list">
                        ${
                            isEditable
                                ? albumPublishers
                                      .map(
                                          (p) => `
                            <span class="link-chip tag publisher">
                                <button class="link-chip-label" data-action="open-edit-modal" data-chip-type="publisher" data-item-id="${p.id}">${escapeHtml(p.name)}</button>
                                <button class="link-chip-remove" data-action="remove-album-publisher" data-album-id="${albumId}" data-song-id="${songId}" data-publisher-id="${p.id}" title="Remove">✕</button>
                            </span>
                        `,
                                      )
                                      .join("")
                                : albumPublishers.length
                                  ? albumPublishers
                                        .map(
                                            (p) =>
                                                `<span class="link-chip tag publisher">${escapeHtml(p.name)}</span>`,
                                        )
                                        .join("")
                                  : '<span class="muted-note">-</span>'
                        }
                    </div>
                </div>
                ${
                    isEditable
                        ? `
                <div class="album-field-row">
                    <span class="mini-label">Type</span>
                    <select class="album-type-select" data-action="change-album-type" data-album-id="${albumId}" data-song-id="${songId}">${typeOptions}</select>
                </div>`
                        : `<div class="album-field-row"><span class="mini-label">Type</span> ${album.album_type ? `<span class="pill">${escapeHtml(album.album_type)}</span>` : `<span class="pill">-</span>`}</div>`
                }
                ${
                    isEditable
                        ? `
                <div class="album-field-row">
                    <span class="mini-label">Year</span>
                    <span class="editable-scalar" data-action="start-edit-album-scalar" data-album-id="${albumId}" data-song-id="${songId}" data-field="release_year">${album.release_year || "-"}</span>
                </div>`
                        : `<div class="album-field-row"><span class="mini-label">Year</span> ${album.release_year ? `<span class="pill mono">${escapeHtml(album.release_year)}</span>` : `<span class="pill mono">-</span>`}</div>`
                }
                ${
                    isEditable
                        ? `
                <div class="album-field-row">
                    <span class="mini-label">Disc</span>
                    <span class="editable-scalar" data-action="start-edit-album-link" data-album-id="${albumId}" data-song-id="${songId}" data-field="disc_number">${album.disc_number ?? "-"}</span>
                </div>`
                        : `<div class="album-field-row"><span class="mini-label">Disc</span> <span class="pill mono">${album.disc_number ?? "-"}</span></div>`
                }
                ${
                    isEditable
                        ? `
                <div class="album-field-row">
                    <span class="mini-label">Track</span>
                    <span class="editable-scalar" data-action="start-edit-album-link" data-album-id="${albumId}" data-song-id="${songId}" data-field="track_number">${album.track_number ?? "-"}</span>
                </div>`
                        : `<div class="album-field-row"><span class="mini-label">Track</span> <span class="pill mono">${album.track_number ?? "-"}</span></div>`
                }
                ${isEditable ? `<button class="section-add-btn" data-action="sync-album-from-song" data-album-id="${albumId}" data-song-id="${songId}" style="margin-top:0.5rem">↓ sync from song</button>` : ""}
            </div>
        `;
        })
        .join("");
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
        .map(
            ([cat, groupItems]) => `
            <div class="stack-list" style="margin-bottom: 0.85rem;">
                <div class="mini-label">${escapeHtml(cat)}</div>
                <div class="link-chip-list">
                    ${groupItems
                        .map((tag) => {
                            const label = tag.name || "-";
                            // Find framing metadata for styling (colors/icons/variants)
                            const framesMap = id3Frames || {};
                            const frameDef = Object.values(framesMap).find(
                                (f) =>
                                    typeof f === "object" &&
                                    f.tag_category === cat,
                            );
                            const variant = frameDef?.variant
                                ? frameDef.variant
                                : "";
                            const chipClass = variant
                                ? `link-chip tag ${variant}`
                                : "link-chip tag";
                            const isGenre = cat === "Genre";
                            const isPrimary = !!tag.is_primary;
                            const primaryAction = isGenre
                                ? `
                <button class="link-chip-primary ${isPrimary ? "active" : ""}" 
                        data-action="set-primary-tag" 
                        data-song-id="${songId}" 
                        data-tag-id="${tag.id}" 
                        title="${isPrimary ? "Primary Genre" : "Set as Primary Genre"}">
                    ★
                </button>`
                                : "";

                            return `
                            <span class="${chipClass}">
                                ${primaryAction}
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
                        })
                        .join("")}
                </div>
            </div>
        `,
        )
        .join("");
}

// TODO: Migrate to backend sorting when expanding the frontend dashboard (Router, Service, and Repository ORDER BY support).
// State for frontend sorting
let currentSongs = [];
const SORT_STORAGE_KEY = "gosling_song_sort";
function loadSavedSort() {
    try {
        const saved = localStorage.getItem(SORT_STORAGE_KEY);
        return saved ? JSON.parse(saved) : { field: null, direction: null };
    } catch {
        return { field: null, direction: null };
    }
}
function saveSort(field, direction) {
    try {
        localStorage.setItem(
            SORT_STORAGE_KEY,
            JSON.stringify({ field, direction }),
        );
    } catch {}
}
let currentSort = loadSavedSort();

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
    saveSort(field, direction);
    const sorted = field
        ? sortSongs(currentSongs, field, direction)
        : currentSongs;
    ctx.setState({ displayedItems: sorted });
    renderSongsCards(ctx, sorted);
}

function clearSort(ctx) {
    currentSort = { field: null, direction: null };
    saveSort(null, null);
    ctx.setState({ displayedItems: currentSongs });
    renderSongsCards(ctx, currentSongs);
}

function renderSortControls() {
    const fields = [
        { field: "media_name", label: "Title" },
        { field: "display_artist", label: "Artist" },
        { field: "id", label: "ID" },
    ];
    const buttons = fields
        .map(({ field, label }) => {
            const isActive = currentSort.field === field;
            const arrow = isActive
                ? currentSort.direction === "asc"
                    ? " ↑"
                    : " ↓"
                : "";
            const activeClass = isActive ? " active" : "";
            return `<button class="sort-btn${activeClass}" data-action="toggle-sort" data-sort-field="${field}">${label}${arrow}</button>`;
        })
        .join("");
    const clearBtn = currentSort.field
        ? `<button class="sort-clear-btn" data-action="clear-sort">Clear</button>`
        : "";

    const filterActiveClass =
        document.getElementById("filter-sidebar")?.style.display !== "none"
            ? " active"
            : "";
    return `<button id="filter-toggle-btn" class="sort-btn${filterActiveClass}" data-action="toggle-filter-sidebar">Filter</button><div class="toolbar-separator"></div><span class="sort-label">Sort:</span>${buttons}${clearBtn}`;
}

function renderSongsCards(ctx, songs) {
    const cardsHtml = songs
        .map(
            (song, index) => `
        <article class="result-card song-card" data-action="select-result" data-id="${song.id}" data-index="${index}" data-selectable="true">
            <div class="card-icon">♪</div>
            <div class="card-body">
                <div class="card-title">${escapeHtml(song.title || song.media_name || "Untitled")}</div>
                <div class="card-subtitle">${escapeHtml(song.display_artist || "Unknown Artist")}</div>
            </div>
            <div class="card-meta">
                ${song.primary_genre ? `<span class="pill genre">${escapeHtml(song.primary_genre)}</span>` : ""}
                <span class="pill mono">${escapeHtml(song.year || "-")}</span>
                ${song.formatted_duration ? `<span class="pill mono">${escapeHtml(song.formatted_duration)}</span>` : ""}
            </div>
            <div class="card-actions">
                <label class="switch ${song.processing_status !== 0 ? "disabled" : ""}" 
                        data-action="toggle-active" 
                        data-id="${song.id}"
                        title="${song.processing_status !== 0 ? "Only reviewed songs can be active for airplay" : song.is_active ? "Deactivate" : "Activate"}">
                        <input type="checkbox" 
                            ${song.is_active ? "checked" : ""} 
                            ${song.processing_status !== 0 ? "disabled" : ""}>
                        <span class="slider"></span>
                </label>
                <span class="pill mono">#${escapeHtml(song.id || "-")}</span>
            </div>
        </article>
    `,
        )
        .join("");

    ctx.elements.sortControlsBox.innerHTML = renderSortControls();
    ctx.elements.resultsContainer.innerHTML = cardsHtml;

    // Attach event handlers
    ctx.elements.sortControlsBox
        .querySelectorAll("[data-action='toggle-sort']")
        .forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const field = btn.getAttribute("data-sort-field");
                const direction =
                    currentSort.field === field &&
                    currentSort.direction === "asc"
                        ? "desc"
                        : "asc";
                applySortAndRender(ctx, field, direction);
            });
        });

    ctx.elements.sortControlsBox
        .querySelector("[data-action='clear-sort']")
        ?.addEventListener("click", (e) => {
            e.stopPropagation();
            clearSort(ctx);
        });

    ctx.elements.resultsContainer
        .querySelector("[data-action='bulk-parse-library']")
        ?.addEventListener("click", (e) => {
            e.stopPropagation();
            const state = ctx.getState();
            const songs = state.displayedItems || [];
            if (!songs.length) return;

            import("../components/filename_parser_modal.js").then((m) => {
                m.openFilenameParserModal({
                    entries: songs.map((s) => ({
                        id: s.id,
                        filename: s.media_name || s.title,
                    })),
                    onApply: async () => {
                        // Search view usually refreshes on navigate or state change
                        // No easy way to 'refresh' current specific search filter without re-triggering main search
                    },
                });
            });
        });
}

export function renderSongs(ctx, songs) {
    ctx.updateResultsSummary(songs.length, "song");

    currentSongs = songs;

    if (!songs.length) {
        ctx.setState({ selectedIndex: -1, displayedItems: [] });
        ctx.elements.resultsContainer.innerHTML =
            renderEmptyState("No songs found");
        return;
    }

    // Apply current sort if active, otherwise show in API order
    const displaySongs = currentSort.field
        ? sortSongs(songs, currentSort.field, currentSort.direction)
        : songs;
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

const STATUS_LABELS = {
    0: "Reviewed",
    1: "Ready for Review",
    2: "Imported",
    3: "Converting",
};
const STATUS_CSS = { 0: "found", 1: "warning", 2: "missing", 3: "pending" };

function renderWorkflowStatus(song) {
    const status = song.processing_status ?? 1;
    const blockers = asArray(song.review_blockers);
    const label = STATUS_LABELS[status] ?? `Status ${status}`;
    const css = STATUS_CSS[status] ?? "";

    const blockerHtml = blockers.length
        ? `<div class="workflow-blockers">Required: ${blockers.map((b) => `<span class="pill">${escapeHtml(b)}</span>`).join("")}</div>`
        : "";

    const isInStaging = (song.source_path || "")
        .toLowerCase()
        .includes("staging");
    let buttonHtml = "";
    if (status === 1 && blockers.length === 0) {
        buttonHtml = `<button class="ingest-btn-secondary workflow-approve-btn" data-action="mark-reviewed" data-id="${song.id}">Mark as Reviewed</button>`;
    } else if (status === 0) {
        if (isInStaging) {
            buttonHtml = `
                <button class="ingest-btn-secondary workflow-approve-btn" data-action="unreview-song" data-id="${song.id}">Unreview</button>
                <button class="ingest-btn-primary workflow-approve-btn" data-action="move-to-library" data-id="${song.id}">Organize to Library</button>
            `;
        } else {
            buttonHtml = `<button class="ingest-btn-secondary workflow-approve-btn" data-action="unreview-song" data-id="${song.id}">Unreview</button>`;
        }
    }

    const targetHtml =
        isInStaging && song.organized_path_preview
            ? `<div class="path-preview">Target: <span class="mono">${escapeHtml(song.organized_path_preview)}</span></div>`
            : "";

    const originalClass = song.original_exists
        ? "exists-yes clickable"
        : "exists-no";
    const originalAction = song.original_exists
        ? `data-action="cleanup-original" data-path="${escapeHtml(song.estimated_original_path)}"`
        : "";

    const originalHtml =
        isInStaging && song.estimated_original_path
            ? `<div class="path-preview ${originalClass}" ${originalAction}>Original: <span class="mono">${escapeHtml(song.estimated_original_path)}</span></div>`
            : "";

    // 3. Hide the entire banner if everything is 'OK' (Reviewed and in Library)
    if (status === 0 && !isInStaging) {
        return "";
    }

    // Use a more neutral styling for 'Reviewed' when in staging
    const finalCss = status === 0 && isInStaging ? "" : css;

    return `
        <div class="file-status ${finalCss} workflow-status">
            <span class="workflow-status-label">${escapeHtml(label)}</span>
            ${blockerHtml}
            ${buttonHtml}
            ${originalHtml}
            ${targetHtml}
        </div>`;
}

export function renderSongDetailComplete(
    ctx,
    song,
    fileData,
    auditHistory,
    id3Frames,
    allRoles,
    searchEngines = {},
    defaultSearchEngine = null,
) {
    const dbCredits = asArray(song.credits);
    const fileCredits = asArray(fileData?.credits);
    const dbAlbums = asArray(song.albums);
    const fileAlbums = asArray(fileData?.albums);
    const dbTags = asArray(song.tags);
    const fileTags = asArray(fileData?.tags);
    const dbPublishers = asArray(song.publishers);
    const filePublishers = asArray(fileData?.publishers);
    const statusHtml = fileData
        ? ""
        : renderStatus("missing", "File not found");
    const rawTags = fileData?.raw_tags ? Object.entries(fileData.raw_tags) : [];
    const _artistValue = song.display_artist
        ? `<button class="inline-link" ${buildNavigateAttrs("artists", song.display_artist)}>${escapeHtml(song.display_artist)}</button>`
        : "-";

    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">
                <span class="pill mono">#${escapeHtml(song.id || "-")}</span>
                ${escapeHtml(song.title || song.media_name || "Untitled")}
            </div>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem;">
                <button class="ingest-btn-secondary" data-action="open-filename-parser-single" data-id="${song.id}" data-filename="${escapeHtml(
                    (song.source_path || "")
                        .split(/[\\/]/)
                        .pop()
                        .replace(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{12}_/i, ""),
                )}" title="Parse filename for metadata">
                    Parse Filename
                </button>
                <button class="ingest-btn-secondary" data-action="open-spotify-modal" data-song-id="${song.id}" data-title="${escapeHtml(song.media_name || song.title)}">
                    Spotify ⇅
                </button>
                ${(() => {
                    const engines = Object.entries(searchEngines);
                    if (!engines.length) return "";
                    const activeEngine = defaultSearchEngine || engines[0][0];
                    const activeLabel =
                        searchEngines[activeEngine] || activeEngine;
                    const otherEngines = engines.filter(
                        ([id]) => id !== activeEngine,
                    );
                    return `<div class="web-search-split">
                        <button class="ingest-btn-secondary web-search-main" data-action="web-search" data-song-id="${song.id}" data-engine="${escapeHtml(activeEngine)}" title="Hold for one-time engine picker">
                            ${escapeHtml(activeLabel)}
                        </button><button class="ingest-btn-secondary web-search-arrow" data-action="web-search-set-engine" data-song-id="${song.id}" title="Change default search engine">▾</button>
                        <div class="web-search-dropdown" hidden>
                            ${otherEngines.map(([id, label]) => `<button class="web-search-option" data-engine="${escapeHtml(id)}">${escapeHtml(label)}</button>`).join("")}
                        </div>
                    </div>`;
                })()}
                <button class="ingest-btn-secondary" data-action="open-scrubber" data-song-id="${song.id}" data-title="${escapeHtml(song.title || song.media_name || "Untitled")}">
                    ▶ Play
                </button>
                <button class="ingest-btn-danger" data-action="delete-song" data-id="${song.id}" data-title="${escapeHtml(song.title || song.media_name)}">
                    Delete
                </button>
            </div>
            <div class="detail-path">${escapeHtml(song.source_path || "No source path")}</div>
            <div style="display:flex; align-items:center; gap:0.5rem; margin-top:0.25rem;">
                <span class="sync-led" data-song-id="${song.id}" title="Checking sync..." style="width:8px;height:8px;border-radius:50%;background:#888;display:inline-block;flex-shrink:0;cursor:pointer;"></span>
                <button class="ingest-btn-secondary" data-action="sync-id3" data-song-id="${song.id}" style="padding:0.1rem 0.4rem;font-size:0.7rem;" title="Write DB data to ID3 tags">↑ ID3</button>
                <span class="sync-mismatch-list" data-song-id="${song.id}" style="font-size:0.72rem;color:#f44336;"></span>
            </div>
        </div>
        <div class="detail-content">
            ${statusHtml}
            ${renderWorkflowStatus(song)}

            <div class="detail-section">
                <div class="section-title">Library Completion</div>
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
                            ${editableScalarRow("Title", "media_name", song.media_name, fileData?.media_name, song.id)}
                            ${editableScalarRow("Year", "year", song.year, fileData?.year, song.id)}
                            ${clickableM2MRow("Artist", song.display_artist, fileData?.display_artist, song.id, "credits", "Performer")}
                            ${clickableM2MRow("Composer", song.display_composer, fileData?.display_composer, song.id, "credits", "Composer")}
                            ${clickableM2MRow("Genre", song.display_genres, fileData?.display_genres, song.id, "tags")}
                            ${clickableM2MRow("Publisher (Master)", song.display_master_publisher, fileData?.display_master_publisher, song.id, "publishers")}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Additional Metadata</div>
                <div class="surface-box">
                    <table class="comparison-table">
                        <tbody>
                            ${compareRow("Duration", song.formatted_duration, fileData?.formatted_duration)}
                            ${editableScalarRow("BPM", "bpm", song.bpm, fileData?.bpm, song.id)}
                            ${editableScalarRow("ISRC", "isrc", song.isrc, fileData?.isrc, song.id)}
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
                    <button class="section-add-btn" data-action="open-link-modal" data-modal-type="album" data-song-id="${song.id}" data-song-title="${escapeHtml(song.media_name || song.title || "")}">+ Add</button>
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
                            ${
                                dbPublishers.length
                                    ? dbPublishers
                                          .map(
                                              (p) => `
                                <span class="link-chip">
                                    <button class="link-chip-label" data-action="open-edit-modal" data-chip-type="publisher" data-item-id="${p.id}">${escapeHtml(p.name)}</button>
                                    <button class="link-chip-split"
                                            data-action="open-splitter-modal"
                                            data-song-id="${song.id}"
                                            data-text="${escapeHtml(p.name)}"
                                            data-target="publishers"
                                            data-remove-type="publisher"
                                            data-remove-id="${p.id}"
                                            title="Split">⋯</button>
                                    <button class="link-chip-remove" data-action="remove-publisher" data-song-id="${song.id}" data-publisher-id="${p.id}" title="Remove">✕</button>
                                </span>
                            `,
                                          )
                                          .join("")
                                    : '<span class="muted-note">None</span>'
                            }
                        </div>
                    </div>
                    <div class="surface-box"><div class="mini-label">File (${filePublishers.length})</div>
                        <div class="link-chip-list">
                            ${
                                filePublishers.length
                                    ? filePublishers
                                          .map(
                                              (tag) => `
                                <span class="link-chip tag publisher">
                                    <button class="link-chip-label" data-action="open-edit-modal" data-chip-type="tag" data-item-id="${tag.id}">${escapeHtml(tag.name || "-")}</button>
                                    <button class="link-chip-remove" data-action="remove-tag" data-song-id="${song.id}" data-tag-id="${tag.id}" title="Remove">✕</button>
                                </span>
                            `,
                                          )
                                          .join("")
                                    : '<span class="muted-note">None</span>'
                            }
                        </div>
                    </div>
                </div>
            </div>

            ${
                rawTags.length
                    ? `
                <div class="detail-section">
                    <div class="section-title">Raw Tags (${rawTags.length})</div>
                    <div class="surface-box mono">
                        ${rawTags.map(([key, value]) => `<div><span class="comparison-label">${escapeHtml(key)}</span>: ${escapeHtml(asArray(value).join(", "))}</div>`).join("")}
                    </div>
                </div>
            `
                    : ""
            }

            <div class="detail-section">
                <div class="section-title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>
        </div>
    `);
}
