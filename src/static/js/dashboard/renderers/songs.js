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
    renderSongRows(ctx, sorted);
}

function clearSort(ctx) {
    currentSort = { field: null, direction: null };
    saveSort(null, null);
    ctx.setState({ displayedItems: currentSongs });
    renderSongRows(ctx, currentSongs);
}

function renderSongRows(ctx, songs) {
    const panel = document.getElementById("song-list-panel");
    if (!panel) return;

    const state = ctx.getState();
    const selectedId = state.displayedItems?.[state.selectedIndex]?.id ?? null;

    panel.innerHTML = songs
        .map((song, index) => {
            const title = escapeHtml(song.display_title);
            const artist = escapeHtml(song.display_artist || "Unknown Artist");
            const blockerLabels = {
                media_name: "TTL",
                year: "YR",
                performers: "ART",
                composers: "COMP",
                genres: "GNR",
                publishers: "PUB",
                albums: "ALB",
                duration: "DUR",
            };
            const pills = (song.review_blockers || [])
                .map(
                    (b) =>
                        `<span class="pill miss" title="Missing: ${b}">${blockerLabels[b] || b}</span>`,
                )
                .join("");
            const selectedClass = song.id === selectedId ? " selected" : "";
            return `<div class="song-row${selectedClass}" data-action="select-result" data-id="${song.id}" data-index="${index}" data-selectable="true">
  <div class="col-check"><input type="checkbox" data-song-id="${song.id}" title="Select"></div>
  <div class="col-info">
    <div class="row-title">${title}<span class="row-id"> #${song.id}</span></div>
    <div class="row-artist">${artist}</div>
  </div>
  <div class="col-missing">${pills}</div>
</div>`;
        })
        .join("");

    // Wire sort dropdown
    const sortSelect = document.getElementById("song-sort-select");
    if (sortSelect) {
        sortSelect.removeEventListener("change", sortSelect._v2Handler);
        sortSelect._v2Handler = (e) => {
            const val = e.target.value;
            if (val === "default") {
                currentSort = { field: null, direction: null };
                saveSort(null, null);
                ctx.setState({ displayedItems: currentSongs });
                renderSongRows(ctx, currentSongs);
            } else {
                const [field, dir] = val.split("-");
                const fieldMap = {
                    title: "media_name",
                    artist: "display_artist",
                    id: "id",
                };
                const sortField = fieldMap[field] || field;
                currentSort = { field: sortField, direction: dir };
                saveSort(sortField, dir);
                const sorted = sortSongs(currentSongs, sortField, dir);
                ctx.setState({ displayedItems: sorted });
                renderSongRows(ctx, sorted);
            }
        };
        sortSelect.addEventListener("change", sortSelect._v2Handler);

        // Sync dropdown to current sort state
        const reverseFieldMap = {
            media_name: "title",
            display_artist: "artist",
            id: "id",
        };
        if (currentSort.field) {
            const shortField =
                reverseFieldMap[currentSort.field] || currentSort.field;
            sortSelect.value = `${shortField}-${currentSort.direction}`;
        } else {
            sortSelect.value = "default";
        }
    }

    // Wire select-all checkbox
    const selectAll = document.getElementById("song-list-select-all");
    if (selectAll) {
        selectAll.removeEventListener("change", selectAll._v2Handler);
        selectAll._v2Handler = (e) => {
            panel
                .querySelectorAll(".col-check input[type=checkbox]")
                .forEach((cb) => {
                    cb.checked = e.target.checked;
                });
            panel.dispatchEvent(
                new CustomEvent("checkchange", { bubbles: true }),
            );
        };
        selectAll.addEventListener("change", selectAll._v2Handler);
    }

    // Wire individual checkboxes to fire checkchange without triggering row select
    panel.querySelectorAll(".col-check input[type=checkbox]").forEach((cb) => {
        cb.addEventListener("click", (e) => e.stopPropagation());
        cb.addEventListener("change", () => {
            panel.dispatchEvent(
                new CustomEvent("checkchange", { bubbles: true }),
            );
        });
    });
}

export function renderSongs(ctx, songs) {
    ctx.updateResultsSummary(songs.length, "song");

    currentSongs = songs;

    const panel = document.getElementById("song-list-panel");

    if (!songs.length) {
        ctx.setState({ selectedIndex: -1, displayedItems: [] });
        if (panel) {
            panel.innerHTML = `<div class="editor-empty-state">No songs found</div>`;
        }
        return;
    }

    // Apply current sort if active, otherwise show in API order
    const displaySongs = currentSort.field
        ? sortSongs(songs, currentSort.field, currentSort.direction)
        : songs;
    ctx.setState({ selectedIndex: -1, displayedItems: displaySongs });
    renderSongRows(ctx, displaySongs);
}
