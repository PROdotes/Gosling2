/**
 * Song Editor V2 — form renderer + scalar interactivity.
 * Renders into #editor-panel .editor-scroll from getCatalogSong data.
 */
import { validators } from "../utils/validators.js";
import { parseTagInput } from "../utils/tag_input.js";
import { patchSongScalars, getCatalogSong, searchArtists, searchTags, searchPublishers, searchAlbums, addSongCredit, removeSongCredit, addSongTag, removeSongTag, addSongPublisher, removeSongPublisher, addSongAlbum, removeSongAlbum, ABORTED } from "../api.js";
import { createChipInput } from "../components/chip_input.js";

function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function renderChips(items, emptyLabel) {
    if (!items || items.length === 0) {
        return `<span class="editor-chip miss">${escapeHtml(emptyLabel)}</span>`;
    }
    return items
        .map((item) => `<span class="editor-chip">${escapeHtml(item)}</span>`)
        .join("");
}

function renderScalarField(label, value, inputId, type = "text", extraButtons = "") {
    const missing = value == null || value === "";
    return `
<div class="editor-field${missing ? " missing" : ""}">
  <label class="editor-label" for="${inputId}">${escapeHtml(label)}</label>
  <div class="editor-input-row">
    <input class="editor-input" id="${inputId}" type="${type}"
      value="${escapeHtml(value ?? "")}" readonly>${extraButtons}
  </div>
</div>`;
}

function renderCaseButtons(songId, field) {
    return `<button class="editor-case-btn" data-action="format-case" data-entity-type="song" data-entity-id="${songId}" data-field="${field}" data-type="sentence" title="Sentence case" type="button">S</button><button class="editor-case-btn" data-action="format-case" data-entity-type="song" data-entity-id="${songId}" data-field="${field}" data-type="title" title="Title Case" type="button">T</button>`;
}

function renderChipField(label, chips, emptyLabel, canMiss = true, fieldKey = null) {
    const missing = canMiss && (!chips || chips.length === 0);
    const dataAttr = fieldKey ? ` data-chip-field="${fieldKey}"` : "";
    return `
<div class="editor-field${missing ? " missing" : ""}"${dataAttr}>
  <label class="editor-label">${escapeHtml(label)}</label>
  <div class="editor-chip-row">${renderChips(chips, emptyLabel)}</div>
</div>`;
}

const SCALAR_FIELDS = [
    { inputId: "ef-title", field: "media_name", numeric: false },
    { inputId: "ef-year",  field: "year",       numeric: true  },
    { inputId: "ef-bpm",   field: "bpm",        numeric: true  },
    { inputId: "ef-isrc",  field: "isrc",       numeric: false },
    { inputId: "ef-notes", field: "notes",      numeric: false },
];

const ALBUM_TYPES = ["Album", "EP", "Single", "Compilation", "Anthology"];

function renderAlbumSubCards(albums, songId) {
    if (!albums || !albums.length) return "";
    return albums.map((album) => {
        const title = album.album_title || album.display_title || "Unknown Album";
        const albumId = album.album_id || album.id;
        const typeOptions = ALBUM_TYPES.map(
            (t) => `<option value="${t}" ${album.album_type === t ? "selected" : ""}>${t}</option>`
        ).join("");
        return `
<div class="album-sub-card" data-album-id="${albumId}">
  <div class="album-sub-header">
    <div class="editor-input-row" style="flex:1">
      <span class="editable-scalar editor-input album-sub-title" data-action="start-edit-album-scalar" data-album-id="${albumId}" data-song-id="${songId}" data-field="title">${escapeHtml(title)}</span>
      <button class="editor-case-btn" data-action="format-case" data-entity-type="album" data-entity-id="${albumId}" data-song-id="${songId}" data-field="title" data-type="sentence" title="Sentence case" type="button">S</button>
      <button class="editor-case-btn" data-action="format-case" data-entity-type="album" data-entity-id="${albumId}" data-song-id="${songId}" data-field="title" data-type="title" title="Title case" type="button">T</button>
    </div>
    <button class="album-sub-remove" data-action="remove-album" data-song-id="${songId}" data-album-id="${albumId}" title="Unlink album" type="button">✕</button>
  </div>
  <div class="album-sub-meta-row">
    <div class="album-sub-meta-item">
      <span class="editor-label">Type</span>
      <select class="editor-input album-sub-select" data-action="change-album-type" data-album-id="${albumId}" data-song-id="${songId}">${typeOptions}</select>
    </div>
    <div class="album-sub-meta-item">
      <span class="editor-label">Year</span>
      <span class="editable-scalar editor-input" data-action="start-edit-album-scalar" data-album-id="${albumId}" data-song-id="${songId}" data-field="release_year">${album.release_year || "-"}</span>
    </div>
    <div class="album-sub-meta-item">
      <span class="editor-label">Disc</span>
      <span class="editable-scalar editor-input" data-action="start-edit-album-link" data-album-id="${albumId}" data-song-id="${songId}" data-field="disc_number">${album.disc_number ?? "-"}</span>
    </div>
    <div class="album-sub-meta-item">
      <span class="editor-label">Track</span>
      <span class="editable-scalar editor-input" data-action="start-edit-album-link" data-album-id="${albumId}" data-song-id="${songId}" data-field="track_number">${album.track_number ?? "-"}</span>
    </div>
  </div>
  <div class="album-sub-actions">
    <button class="album-sub-sync-btn" data-action="sync-album-from-song" data-album-id="${albumId}" data-song-id="${songId}" type="button">↓ sync from song</button>
  </div>
</div>`;
    }).join("");
}

function updateAlbumSubSection(freshSong) {
    const el = document.querySelector(`[data-album-sub-song="${freshSong.id}"]`);
    if (el) el.innerHTML = renderAlbumSubCards(freshSong.albums, freshSong.id);
    // Sync missing state on the field
    const field = document.querySelector(`[data-chip-field="album"]`);
    if (field) field.classList.toggle("missing", (freshSong.albums || []).length === 0);
}

const BLOCKER_LABELS = {
    media_name: "TTL", year: "YR", performers: "ART",
    composers: "COMP", genres: "GNR", publishers: "PUB",
    albums: "ALB", duration: "DUR",
};

function updateListRowBlockers(songId, reviewBlockers) {
    const row = document.querySelector(`.song-row[data-id="${songId}"]`);
    if (!row) return;
    const colMissing = row.querySelector(".col-missing");
    if (!colMissing) return;
    colMissing.innerHTML = (reviewBlockers || [])
        .map((b) => `<span class="pill miss" title="Missing: ${b}">${BLOCKER_LABELS[b] || b}</span>`)
        .join("");
}

/**
 * Wires scalar inputs in the V2 editor for Enter/Escape/blur save behaviour.
 * Must be called after renderSongEditorV2.
 *
 * @param {object} song - initial song from getCatalogSong
 * @param {object} validationRules - state.validationRules
 * @param {function} onUpdated - called with fresh song after a successful save
 */
export function wireScalarInputs(song, validationRules, onUpdated) {
    const blurSaves = validationRules?.blur_saves_scalars ?? true;

    for (const { inputId, field, numeric } of SCALAR_FIELDS) {
        const input = document.getElementById(inputId);
        if (!input) continue;

        input.removeAttribute("readonly");

        let committedValue = input.value;
        let hasError = false;
        let saving = false;

        const errorEl = document.createElement("div");
        errorEl.className = "editor-input-error";
        input.after(errorEl);

        function showError(msg) {
            hasError = true;
            input.classList.add("editor-input--error");
            errorEl.textContent = msg;
        }

        function clearError() {
            hasError = false;
            input.classList.remove("editor-input--error");
            errorEl.textContent = "";
        }

        function revert() {
            input.value = committedValue;
            clearError();
        }

        async function commit() {
            if (saving) return;
            const raw = input.value.trim();
            clearError();

            const validate = validators[field];
            const error = validate ? validate(raw, validationRules) : null;
            if (error) { showError(error); return; }

            if (raw === committedValue) return;

            const payload = numeric ? (raw === "" ? null : Number(raw)) : (raw === "" ? null : raw);

            saving = true;
            input.disabled = true;
            try {
                await patchSongScalars(song.id, { [field]: payload });
                committedValue = raw;
                const fresh = await getCatalogSong(song.id);
                updateListRowBlockers(song.id, fresh.review_blockers);
                if (onUpdated) onUpdated(fresh);
            } catch (err) {
                showError(`Save failed: ${err.message}`);
                revert();
            } finally {
                input.disabled = false;
                saving = false;
            }
        }

        input.addEventListener("input", () => {
            const validate = validators[field];
            if (!validate) return;
            const error = validate(input.value.trim(), validationRules);
            if (error) showError(error);
            else clearError();
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && input.tagName !== "TEXTAREA") { e.preventDefault(); commit(); }
            if (e.key === "Escape") { e.preventDefault(); revert(); }
        });

        input.addEventListener("blur", () => {
            if (hasError) { revert(); return; }
            if (blurSaves) commit();
            else revert();
        });
    }
}

/**
 * Replaces static chip rows with live chip inputs.
 * Must be called after renderSongEditorV2.
 *
 * @param {object} song - initial song from getCatalogSong
 * @param {function} onUpdated - called with fresh song after add/remove
 * @param {function} onSplit - ({songId, text, role, creditId}) => void — null to disable
 * @param {object} validationRules - state.validationRules (for tag parsing)
 */
/**
 * Adds drift indicator dots to scalar field labels when DB value ≠ file value.
 * Must be called after renderSongEditorV2.
 *
 * @param {object} dbSong - from getCatalogSong
 * @param {object} fileSong - from getSongDetail (inspect-file)
 */
export function wireDriftIndicators(dbSong, fileSong) {
    document.querySelectorAll("#editor-panel .drift-dot").forEach((el) => el.remove());
    if (!fileSong) return;

    const SCALAR_FIELDS = [
        { inputId: "ef-title", dbField: "media_name", fileField: "media_name" },
        { inputId: "ef-year",  dbField: "year",        fileField: "year"       },
        { inputId: "ef-bpm",   dbField: "bpm",         fileField: "bpm"        },
        { inputId: "ef-isrc",  dbField: "isrc",        fileField: "isrc"       },
    ];
    for (const { inputId, dbField, fileField } of SCALAR_FIELDS) {
        const input = document.getElementById(inputId);
        if (!input) continue;
        const dbVal = dbSong[dbField] ?? null;
        const fileVal = fileSong[fileField] ?? null;
        if (String(dbVal ?? "") === String(fileVal ?? "")) continue;
        appendDot(input.closest(".editor-field")?.querySelector(".editor-label"),
            `DB: ${dbVal ?? "(empty)"}\nFile: ${fileVal ?? "(empty)"}`);
    }

    const norm = (s) => String(s ?? "").trim().toLowerCase();
    const keySet = (arr) => new Set((arr || []).map(norm).filter((x) => x !== ""));
    const eqSet = (a, b) => a.size === b.size && [...a].every((v) => b.has(v));

    const creditsByRole = (song, role) =>
        (song.credits || []).filter((c) => c.role_name === role).map((c) => c.display_name);

    const CHIP_FIELDS = [
        { fieldKey: "performer", getDb: (s) => creditsByRole(s, "Performer"), getFile: (s) => creditsByRole(s, "Performer") },
        { fieldKey: "composer",  getDb: (s) => creditsByRole(s, "Composer"),  getFile: (s) => creditsByRole(s, "Composer")  },
        { fieldKey: "lyricist",  getDb: (s) => creditsByRole(s, "Lyricist"),  getFile: (s) => creditsByRole(s, "Lyricist")  },
        { fieldKey: "producer",  getDb: (s) => creditsByRole(s, "Producer"),  getFile: (s) => creditsByRole(s, "Producer")  },
        { fieldKey: "publisher", getDb: (s) => (s.publishers || []).map((p) => p.name), getFile: (s) => (s.publishers || []).map((p) => p.name) },
        { fieldKey: "album",     getDb: (s) => (s.albums || []).map((a) => a.album_title), getFile: (s) => (s.albums || []).map((a) => a.album_title) },
    ];
    for (const { fieldKey, getDb, getFile } of CHIP_FIELDS) {
        const field = document.querySelector(`[data-chip-field="${fieldKey}"]`);
        if (!field) continue;
        const dbItems = getDb(dbSong);
        const fileItems = getFile(fileSong);
        if (eqSet(keySet(dbItems), keySet(fileItems))) continue;
        appendDot(field.querySelector(".editor-label"),
            `DB: ${dbItems.join(", ") || "(empty)"}\nFile: ${fileItems.join(", ") || "(empty)"}`);
    }
}

function appendDot(labelEl, title) {
    if (!labelEl) return;
    const dot = document.createElement("span");
    dot.className = "drift-dot";
    dot.title = title;
    labelEl.appendChild(dot);
}

export function wireChipInputs(song, onUpdated, onSplit, validationRules) {
    const handles = {};
    const getItemsByField = {};

    function syncMissing(fieldKey, items) {
        const field = document.querySelector(`[data-chip-field="${fieldKey}"]`);
        if (!field) return;
        field.classList.toggle("missing", (items || []).length === 0);
    }

    async function refresh() {
        const fresh = await getCatalogSong(song.id);
        updateListRowBlockers(song.id, fresh.review_blockers);
        for (const [key, getItems] of Object.entries(getItemsByField)) {
            syncMissing(key, getItems(fresh));
        }
        if (onUpdated) onUpdated(fresh);
        return fresh;
    }

    function getContainer(fieldKey) {
        const field = document.querySelector(`[data-chip-field="${fieldKey}"]`);
        if (!field) return null;
        const chipRow = field.querySelector(".editor-chip-row");
        if (!chipRow) return null;
        const wrap = document.createElement("div");
        wrap.className = "editor-chip-wrap";
        chipRow.replaceWith(wrap);
        return wrap;
    }

    // ── Helper to wire a credit role ───────────────────────────────────────────
    function wireCreditRole(role) {
        const wrap = getContainer(role.toLowerCase());
        if (!wrap) return;
        const getItems = (s) => s.credits
            .filter((c) => c.role_name === role)
            .map((c) => ({ id: c.credit_id, label: c.display_name, _identityId: c.identity_id, _nameId: c.name_id }));

        const handle = createChipInput({
            container: wrap,
            items: getItems(song),
            onSearch: async (q) => {
                const r = await searchArtists(q);
                if (r === ABORTED || !r) return [];
                return r.map((a) => ({ id: a.id, label: a.display_name || a.legal_name || a.name }));
            },
            onAdd: async (opt) => {
                await addSongCredit(song.id, opt.label, role, opt.id);
                const fresh = await refresh();
                handle.setItems(getItems(fresh));
            },
            onRemove: async (creditId) => {
                await removeSongCredit(song.id, creditId);
                await refresh();
            },
            onSplit: onSplit ? (item) => onSplit({ songId: song.id, text: item.label, role, creditId: item.id }) : null,
            allowCreate: true,
            labelAttrs: (item) => item._identityId ? {
                "data-action": "open-edit-modal",
                "data-chip-type": "credit",
                "data-song-id": song.id,
                "data-item-id": item._nameId ?? "",
                "data-identity-id": item._identityId,
            } : null,
        });
        handles[role.toLowerCase()] = handle;
        getItemsByField[role.toLowerCase()] = getItems;
    }

    wireCreditRole("Performer");
    wireCreditRole("Composer");
    wireCreditRole("Lyricist");
    wireCreditRole("Producer");

    // ── Tags ───────────────────────────────────────────────────────────────────
    const tagsWrap = getContainer("tags");
    if (tagsWrap) {
        const tagRules = validationRules?.tags || {};
        const categoryColors = tagRules.category_colors || {};
        const getItems = (s) => s.tags.map((t) => ({ id: t.id, label: t.name, category: t.category, _isPrimary: !!t.is_primary }));
        const handle = createChipInput({
            container: tagsWrap,
            items: getItems(song),
            onSearch: async (q) => {
                const { name } = parseTagInput(q, tagRules);
                const r = await searchTags(name);
                if (r === ABORTED || !r) return [];
                return r.map((t) => ({ id: t.id, label: t.name, category: t.category }));
            },
            onAdd: async (opt) => {
                const { name, category } = opt.id ? opt : parseTagInput(opt.label, tagRules);
                await addSongTag(song.id, name, category ?? null, opt.id ?? null);
                const fresh = await refresh();
                handle.setItems(getItems(fresh));
            },
            onRemove: async (tagId) => {
                await removeSongTag(song.id, tagId);
                await refresh();
            },
            allowCreate: true,
            tagMode: true,
            categoryColors,
            getCreateLabel: (q) => {
                const { name, category } = parseTagInput(q, tagRules);
                return `+ Add "${name}" in "${category}"`;
            },
            labelAttrs: (item) => ({
                "data-action": "open-edit-modal",
                "data-chip-type": "tag",
                "data-item-id": item.id,
            }),
            extraChipButtons: (item) => {
                if (item.category !== "Genre") return [];
                return [{
                    className: `chip-input__chip-btn chip-input__chip-star${item._isPrimary ? " is-primary" : ""}`,
                    html: "★",
                    title: item._isPrimary ? "Primary genre" : "Set as primary genre",
                    dataset: {
                        action: "set-primary-tag",
                        songId: String(song.id),
                        tagId: String(item.id),
                    },
                }];
            },
        });
        handles.tags = handle;
        getItemsByField.tags = getItems;
    }

    // ── Publisher ──────────────────────────────────────────────────────────────
    const pubWrap = getContainer("publisher");
    if (pubWrap) {
        const getItems = (s) => s.publishers.map((p) => ({ id: p.id, label: p.name }));
        const handle = createChipInput({
            container: pubWrap,
            items: getItems(song),
            onSearch: async (q) => {
                const r = await searchPublishers(q);
                if (r === ABORTED || !r) return [];
                return r.map((p) => ({ id: p.id, label: p.name }));
            },
            onAdd: async (opt) => {
                await addSongPublisher(song.id, opt.label, opt.id);
                const fresh = await refresh();
                handle.setItems(getItems(fresh));
            },
            onRemove: async (pubId) => {
                await removeSongPublisher(song.id, pubId);
                await refresh();
            },
            allowCreate: true,
            singleSelect: true,
            labelAttrs: (item) => ({
                "data-action": "open-edit-modal",
                "data-chip-type": "publisher",
                "data-item-id": item.id,
            }),
        });
        handles.publisher = handle;
        getItemsByField.publisher = getItems;
    }

    // ── Album ──────────────────────────────────────────────────────────────────
    // Albums render as sub-cards (not chips). We only wire the search-to-add
    // input here. The cards themselves are rendered by renderAlbumSubCards and
    // refreshed via updateAlbumSubSection.
    const albumField = document.querySelector(`[data-chip-field="album"]`);
    if (albumField) {
        const searchWrap = albumField.querySelector(".album-search-wrap");
        if (searchWrap) {
            // Re-use createChipInput with no initial items — it gives us a
            // search input + dropdown for free. We suppress chip rendering
            // (items always stays empty; cards are the display).
            createChipInput({
                container: searchWrap,
                items: [],
                onSearch: async (q) => {
                    const r = await searchAlbums(q);
                    if (r === ABORTED || !r) return [];
                    return r.map((a) => ({ id: a.id, label: a.display_title || a.title || a.name }));
                },
                onAdd: async (opt) => {
                    await addSongAlbum(song.id, opt.id ?? null, opt.id ? null : opt.label, null, null);
                    const fresh = await refresh();
                    updateAlbumSubSection(fresh);
                },
                onRemove: async () => {}, // removal handled by card × buttons
                allowCreate: true,
                getCreateLabel: (q) => `+ Create "${q}"`,
            });
        }
    }

    return {
        updateField(fieldKey, freshSong) {
            const key = String(fieldKey).toLowerCase();
            if (key === "album") {
                updateAlbumSubSection(freshSong);
                updateListRowBlockers(freshSong.id, freshSong.review_blockers);
                return;
            }
            const handle = handles[key];
            const getItems = getItemsByField[key];
            if (!handle || !getItems) return;
            const items = getItems(freshSong);
            handle.setItems(items);
            syncMissing(key, items);
            updateListRowBlockers(freshSong.id, freshSong.review_blockers);
        },
    };
}

/**
 * Renders the action sidebar for a song.
 * Must be called after renderSongEditorV2.
 *
 * @param {object} song - from getCatalogSong
 * @param {object} opts - { searchEngines, defaultSearchEngine }
 */
export function renderActionSidebar(song, { searchEngines = {}, defaultSearchEngine = null } = {}) {
    const panel = document.getElementById("editor-panel");
    if (!panel) return;
    const sidebar = panel.querySelector(".action-sidebar");
    if (!sidebar) return;

    const status = song.processing_status ?? 1;
    const blockers = song.review_blockers || [];
    const isInStaging = (song.source_path || "").toLowerCase().includes("staging");

    // ── Organize / Mark as Done button ────────────────────────────────────────
    let organizeBtn = "";
    let unreviewBtn = "";
    if (status === 1) {
        const blocked = blockers.length > 0;
        organizeBtn = `<button class="sidebar-btn organize${blocked ? " blocked" : ""}"
            data-action="mark-reviewed" data-id="${song.id}"
            ${blocked ? "disabled title=\"Missing required fields\"" : ""}>Mark as Done</button>`;
    } else if (status === 0 && isInStaging) {
        organizeBtn = `<button class="sidebar-btn organize" data-action="move-to-library" data-id="${song.id}">Organize to Library</button>`;
        unreviewBtn = `<button class="sidebar-btn" data-action="unreview-song" data-id="${song.id}">Unreview</button>`;
    }

    const targetPath = isInStaging && song.organized_path_preview
        ? `<div class="sidebar-path">→ ${escapeHtml(song.organized_path_preview)}</div>` : "";

    // ── Web search split button ────────────────────────────────────────────────
    const engine = defaultSearchEngine || Object.keys(searchEngines)[0] || "spotify";
    const engineLabel = searchEngines[engine] || engine;
    const otherEngines = Object.entries(searchEngines)
        .filter(([k]) => k !== engine)
        .map(([k, v]) => `<button class="web-search-option" data-engine="${escapeHtml(k)}">${escapeHtml(v)}</button>`)
        .join("");
    const searchSplitBtn = `
<div class="web-search-split sidebar-split-btn">
    <button class="sidebar-btn web-search-main" data-action="web-search" data-song-id="${song.id}" data-engine="${escapeHtml(engine)}" style="flex:1;border-right:none;border-radius:5px 0 0 5px">${escapeHtml(engineLabel)}</button><button class="sidebar-btn" data-action="web-search-set-engine" style="border-radius:0 5px 5px 0;padding:8px 6px;width:22px;flex-shrink:0">▾</button>
    <div class="web-search-dropdown" hidden>${otherEngines}</div>
</div>`;

    // ── Delete Original ────────────────────────────────────────────────────────
    const hasOriginal = song.original_exists && isInStaging && song.estimated_original_path;
    const deleteOriginalBtn = hasOriginal
        ? `<button class="sidebar-btn delete-original" data-action="cleanup-original" data-path="${escapeHtml(song.estimated_original_path)}">⚠ Delete Original</button>
           <div class="sidebar-path" style="opacity:0.6">${escapeHtml(song.estimated_original_path)}</div>`
        : "";

    const playBtn = `<button class="sidebar-btn" data-action="open-scrubber" data-id="${song.id}" data-title="${escapeHtml(song.media_name || "")}">▶ Play</button>`;

    const syncLedHtml = `<span class="sync-led" data-song-id="${song.id}" title="Checking sync..."></span><span class="sync-mismatch-list" data-song-id="${song.id}"></span>`;

    sidebar.innerHTML = `
<div class="sidebar-group-label">Playback</div>
${playBtn}

<div class="sidebar-divider"></div>

<div class="sidebar-group-label">Research</div>
<button class="sidebar-btn" data-action="open-filename-parser-single" data-id="${song.id}" data-filename="${escapeHtml((song.source_path || "").split(/[\\/]/).pop())}">Parse</button>
<button class="sidebar-btn sidebar-btn--spotify" data-action="open-spotify-modal" data-id="${song.id}" data-title="${escapeHtml(song.media_name || "")}">Spotify ⇅</button>
${searchSplitBtn}

<div class="sidebar-divider"></div>

<div class="sidebar-group-label">Finalize</div>
<div class="sidebar-sync-row">${syncLedHtml}</div>
<button class="sidebar-btn sidebar-btn--id3" data-action="sync-id3" data-song-id="${song.id}">↑ Write ID3</button>
${organizeBtn}
${unreviewBtn}
${targetPath}

<div class="sidebar-divider"></div>

${deleteOriginalBtn}
<button class="sidebar-btn sidebar-btn--danger" data-action="delete-song" data-id="${song.id}" style="margin-top:auto">🗑 Delete Record</button>
`;
}

export function renderSongEditorMultiSelect(count) {
    const panel = document.getElementById("editor-panel");
    if (!panel) return;
    const scroll = panel.querySelector(".editor-scroll");
    if (scroll) scroll.innerHTML = `<div class="editor-empty-state">${count} songs selected</div>`;
    const sidebar = panel.querySelector(".action-sidebar");
    if (sidebar) sidebar.innerHTML = "";
}

export function wireAuditHistory(songId, fetchAuditHistory) {
    const details = document.querySelector(`.editor-audit-details[data-song-id="${songId}"]`);
    if (!details) return;
    let loaded = false;
    details.addEventListener("toggle", async () => {
        if (!details.open || loaded) return;
        loaded = true;
        const body = details.querySelector(".editor-audit-body");
        try {
            const history = await fetchAuditHistory();
            if (!history || history.length === 0) {
                body.innerHTML = `<div class="audit-empty">No history found.</div>`;
                return;
            }
            body.innerHTML = history.map((entry) => `
<div class="audit-entry">
  <span class="audit-ts">${escapeHtml(entry.timestamp || "")}</span>
  <span class="audit-action">${escapeHtml(entry.type || "")}</span>
  <span class="audit-details">${escapeHtml(entry.label || "")}${entry.old != null ? ` (${escapeHtml(String(entry.old))} → ${escapeHtml(String(entry.new ?? ""))})` : ""}</span>
</div>`).join("");
        } catch {
            body.innerHTML = `<div class="audit-empty">Failed to load history.</div>`;
        }
    });
}

export function renderSongEditorEmpty() {
    const panel = document.getElementById("editor-panel");
    if (!panel) return;
    const scroll = panel.querySelector(".editor-scroll");
    if (scroll) scroll.innerHTML = `<div class="editor-empty-state">Select a song to edit</div>`;
    const sidebar = panel.querySelector(".action-sidebar");
    if (sidebar) sidebar.innerHTML = "";
}

export function renderSongEditorV2(song, fileData = null) {
    const panel = document.getElementById("editor-panel");
    if (!panel) return;
    const scroll = panel.querySelector(".editor-scroll");
    if (!scroll) return;

    const REQUIRED_ROLES = ["Performer", "Composer"];
    const OPTIONAL_ROLES = ["Lyricist", "Producer"];
    const creditsByRole = {};
    for (const role of [...REQUIRED_ROLES, ...OPTIONAL_ROLES]) {
        creditsByRole[role] = song.credits
            .filter((c) => c.role_name === role)
            .map((c) => c.display_name);
    }
    const publishers = song.publishers.map((p) => p.name);
    const albums = song.albums.map((a) => a.display_title);
    const tags = song.tags.map((t) =>
        t.category ? `${t.category}::${t.name}` : t.name
    );

    scroll.innerHTML = `
<div class="editor-song-id">ID: ${escapeHtml(String(song.id ?? "?"))}</div>
<div class="editor-section">
  <div class="editor-section-title">Required Metadata</div>
  <div class="editor-row">
    <div class="editor-col col-8">
      ${renderScalarField("Title", song.media_name, "ef-title", "text", renderCaseButtons(song.id, "media_name"))}
    </div>
    <div class="editor-col col-4">
      ${renderScalarField("Year", song.year, "ef-year", "number")}
    </div>
  </div>
  ${REQUIRED_ROLES.map((role) => renderChipField(role, creditsByRole[role], `No ${role.toLowerCase()}s`, true, role.toLowerCase())).join("")}
  ${renderChipField("Tags", tags, "No tags", true, "tags")}
  ${renderChipField("Publisher", publishers, "No publisher", true, "publisher")}
  <div class="editor-field${song.albums.length === 0 ? " missing" : ""}" data-chip-field="album">
    <label class="editor-label">Album / Release</label>
    <div data-album-sub-song="${song.id}">${renderAlbumSubCards(song.albums, song.id)}</div>
    <div class="album-search-wrap"></div>
  </div>
</div>

<div class="editor-section">
  <div class="editor-section-title">Additional Data</div>
  ${OPTIONAL_ROLES.map((role) => renderChipField(role, creditsByRole[role], `No ${role.toLowerCase()}s`, false, role.toLowerCase())).join("")}
  <div class="editor-row">
    <div class="editor-col col-4">
      ${renderScalarField("BPM", song.bpm, "ef-bpm", "number")}
    </div>
    <div class="editor-col col-4">
      ${renderScalarField("ISRC", song.isrc, "ef-isrc")}
    </div>
  </div>
</div>

<div class="editor-section">
  <div class="editor-section-title">Raw / File Data</div>
  <div class="editor-field">
    <label class="sidebar-toggle" data-action="toggle-active" data-id="${song.id}">
      <input type="checkbox" ${song.is_active ? "checked" : ""} ${song.processing_status !== 0 ? "disabled" : ""}>
      <span>Active (airplay)</span>
    </label>
  </div>
  <div class="editor-field">
    <label class="editor-label" for="ef-notes">Comments</label>
    <textarea class="editor-input editor-textarea" id="ef-notes" rows="3">${escapeHtml(song.notes ?? "")}</textarea>
  </div>
  ${fileData && fileData.raw_tags && Object.keys(fileData.raw_tags).length > 0 ? `
  <div class="editor-field">
    <label class="editor-label">Raw ID3 Tags</label>
    <div class="editor-raw-tags">
      ${Object.entries(fileData.raw_tags).map(([k, vals]) => `
      <div class="raw-tag-row">
        <span class="raw-tag-key">${escapeHtml(k)}</span>
        <span class="raw-tag-val">${escapeHtml(Array.isArray(vals) ? vals.join(", ") : String(vals))}</span>
      </div>`).join("")}
    </div>
  </div>` : ""}
  <details class="editor-audit-details" data-song-id="${escapeHtml(String(song.id))}">
    <summary class="editor-audit-summary">Audit History</summary>
    <div class="editor-audit-body">Loading…</div>
  </details>
</div>
`;
}
