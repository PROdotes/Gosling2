import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderEmptyState,
    renderStatus,
    textOrDash,
} from "../components/utils.js";
import { PROCESSING_STATUS } from "../constants.js";

// Active status filter context, mirrored from the filter sidebar on each search
// (see setActiveStatusFilters). Used to decide whether an edited song still
// belongs in the current list — only STATUS filters are evaluated client-side.
let activeStatusFilters = [];
let activeFilterMode = "ALL";

// Songs that an in-editor edit has pushed out of the active status filter. They
// stay rendered (dimmed) until swept, so the list doesn't shift under the user.
const tombstonedIds = new Set();

// Status predicates, mirroring the SQL in song_repository.filter_slim. Keep in
// sync with status_map there if the status semantics ever change.
const STATUS_PREDICATES = {
    done: (s) => s.processing_status === PROCESSING_STATUS.REVIEWED,
    not_done: (s) => s.processing_status !== PROCESSING_STATUS.REVIEWED,
    missing_data: (s) => (s.review_blockers || []).length > 0,
    ready_to_finalize: (s) =>
        s.processing_status !== PROCESSING_STATUS.REVIEWED &&
        (s.review_blockers || []).length === 0,
};

// True if the song still matches the active status filters. No status filter
// active => always true (nothing to tombstone). Other facets (artist/genre/…)
// are intentionally not re-evaluated here.
function songMatchesStatuses(song) {
    if (!activeStatusFilters.length) return true;
    const preds = activeStatusFilters
        .map((key) => STATUS_PREDICATES[key])
        .filter(Boolean);
    if (!preds.length) return true;
    return activeFilterMode === "ALL"
        ? preds.every((p) => p(song))
        : preds.some((p) => p(song));
}

// Mirror the sidebar's active status filters into this module so patchSongRow
// can decide list membership without coupling the renderer to the sidebar.
export function setActiveStatusFilters(statuses, mode) {
    activeStatusFilters = statuses || [];
    activeFilterMode = mode || "ALL";
}

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
    } catch { }
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

// Single source of truth for a song-list row's markup. Used by the full
// render (renderSongRows) and by surgical single-row updates (patchSongRow).
function buildSongRowHtml(song, index, selectedId) {
    const title = escapeHtml(song.display_title);
    const artist = escapeHtml(song.display_artist || "Unknown Artist");
    const duration = escapeHtml(song.formatted_duration || "");
    const pills = (song.review_blockers || [])
        .map((b) => `<span class="pill miss" title="Missing: ${b.name}">${b.pill}</span>`)
        .join("");
    const selectedClass = song.id === selectedId ? " selected" : "";
    const tombstonedClass = tombstonedIds.has(song.id) ? " tombstoned" : "";
    return `<div class="song-row${selectedClass}${tombstonedClass}" data-action="select-result" data-id="${song.id}" data-index="${index}" data-selectable="true">
  <div class="col-check"><input type="checkbox" data-song-id="${song.id}" title="Select"></div>
  <div class="col-info">
    <div class="row-title">${title}<span class="row-id"> #${song.id}</span></div>
    <div class="row-artist">${artist}</div>
  </div>
  <div class="col-missing">${pills}</div>
  <div class="col-time">${duration}</div>
</div>`;
}

function renderSongRows(ctx, songs) {
    const panel = document.getElementById("song-list-panel");
    if (!panel) return;

    const state = ctx.getState();
    const selectedId = state.displayedItems?.[state.selectedIndex]?.id ?? null;

    panel.innerHTML = songs
        .map((song, index) => buildSongRowHtml(song, index, selectedId))
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

    // Fresh result set — the backend already excludes anything that left the
    // filter, so any prior tombstones are gone for good.
    tombstonedIds.clear();
    currentSongs = songs;

    const panel = document.getElementById("song-list-panel");

    // Wire the sweep interlock once: tombstoned rows are removed only when the
    // pointer leaves the list, so the list never shifts under the cursor.
    if (panel && !panel._sweepWired) {
        panel._sweepWired = true;
        panel.addEventListener("mouseleave", () => flushTombstones(ctx));
    }

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

// Row fields that an in-editor edit can change. Copied from the full SongView
// (returned by getCatalogSong) onto the cached slim row object so the list row
// reflects edits without a full re-fetch. processing_status + review_blockers
// also drive the status-filter membership check (see Unit 2).
const ROW_PATCH_FIELDS = [
    "review_blockers",
    "processing_status",
    "display_artist",
    "display_title",
    "formatted_duration",
    "media_name",
    "title",
    "year",
];

// Surgically refresh a single list row from a fresh full song object, without
// re-fetching or re-rendering the whole list. currentSongs shares object
// references with state.cachedSongs/displayedItems, so mutating the cached
// object updates every view of it. Returns true if the row was found.
export function patchSongRow(ctx, fresh) {
    if (!fresh || fresh.id == null) return false;
    const cached = currentSongs.find((s) => s.id === fresh.id);
    if (!cached) return false;

    for (const field of ROW_PATCH_FIELDS) {
        if (field in fresh) cached[field] = fresh[field];
    }

    const panel = document.getElementById("song-list-panel");
    const node = panel?.querySelector(`.song-row[data-id="${fresh.id}"]`);
    if (!node) return true; // data patched; row just isn't currently rendered

    // Decide list membership: an edit that pushes the song out of the active
    // status filter tombstones it (flash + dim, slot held) rather than removing
    // it, so the list doesn't shift under the user. A newly-tombstoned row gets
    // a one-shot flash; un-reviewing (back into the filter) clears the tombstone.
    const matches = songMatchesStatuses(cached);
    const wasTombstoned = tombstonedIds.has(fresh.id);
    const newlyTombstoned = !matches && !wasTombstoned;
    if (matches) {
        tombstonedIds.delete(fresh.id);
    } else {
        tombstonedIds.add(fresh.id);
    }

    const state = ctx.getState();
    const selectedId = state.displayedItems?.[state.selectedIndex]?.id ?? null;
    const index = Number(node.dataset.index);
    node.outerHTML = buildSongRowHtml(cached, index, selectedId);

    if (newlyTombstoned) {
        // Re-query: outerHTML replaced the node. Flash class is added imperatively
        // (not baked into the markup) so it only animates on the transition, not
        // on every subsequent re-render of an already-tombstoned row.
        panel
            .querySelector(`.song-row[data-id="${fresh.id}"]`)
            ?.classList.add("flash-done");
    }
    return true;
}

// Sweep tombstoned rows out of the list. Called when the pointer leaves the
// list (so the resulting shift never happens under the user's cursor). Plays a
// collapse animation, then does one clean re-render to re-sync row indices and
// selection. No-op if nothing is tombstoned.
function flushTombstones(ctx) {
    if (!tombstonedIds.size) return;
    const panel = document.getElementById("song-list-panel");
    if (!panel) {
        tombstonedIds.clear();
        return;
    }

    // The selected row is never swept — it stays (dimmed) until selection moves
    // off it, so the song the user is on never vanishes under them. It sweeps on
    // a later flush once it's no longer selected.
    const state = ctx.getState();
    const selectedId = state.displayedItems?.[state.selectedIndex]?.id ?? null;

    const swept = new Set();
    for (const id of tombstonedIds) {
        if (id !== selectedId) swept.add(id);
    }
    if (!swept.size) return; // only the selected tombstone remains; keep it
    for (const id of swept) tombstonedIds.delete(id);

    let animating = false;
    for (const id of swept) {
        const node = panel.querySelector(`.song-row[data-id="${id}"]`);
        if (node) {
            node.classList.add("sweeping");
            animating = true;
        }
    }

    const commit = () => {
        // Recompute from current state — selection may have changed during the
        // animation window. The selected song is never in `swept`, so it survives.
        const now = ctx.getState();
        const keepId = now.displayedItems?.[now.selectedIndex]?.id ?? null;
        currentSongs = currentSongs.filter((s) => !swept.has(s.id));
        const newDisplayed = (now.displayedItems || currentSongs).filter(
            (s) => !swept.has(s.id),
        );
        const newIndex =
            keepId == null
                ? -1
                : newDisplayed.findIndex((s) => s.id === keepId);
        ctx.setState({ displayedItems: newDisplayed, selectedIndex: newIndex });
        ctx.updateResultsSummary?.(newDisplayed.length, "song");
        renderSongRows(ctx, newDisplayed);
    };

    // Animation duration must track the .sweeping keyframe in songs_v2.css.
    if (animating) setTimeout(commit, 320);
    else commit();
}
