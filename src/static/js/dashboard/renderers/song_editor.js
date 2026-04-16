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

function renderScalarField(label, value, inputId, type = "text") {
    const missing = value == null || value === "";
    return `
<div class="editor-field${missing ? " missing" : ""}">
  <label class="editor-label" for="${inputId}">${escapeHtml(label)}</label>
  <input class="editor-input" id="${inputId}" type="${type}"
    value="${escapeHtml(value ?? "")}" readonly>
</div>`;
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
];

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
            if (e.key === "Enter") { e.preventDefault(); commit(); }
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
export function wireChipInputs(song, onUpdated, onSplit, validationRules) {
    async function refresh() {
        const fresh = await getCatalogSong(song.id);
        updateListRowBlockers(song.id, fresh.review_blockers);
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
            .map((c) => ({ id: c.credit_id, label: c.display_name, _identityId: c.identity_id }));

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
        });
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
        const getItems = (s) => s.tags.map((t) => ({ id: t.id, label: t.name, category: t.category }));
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
        });
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
        });
    }

    // ── Album ──────────────────────────────────────────────────────────────────
    const albumWrap = getContainer("album");
    if (albumWrap) {
        const getItems = (s) => s.albums.map((a) => ({ id: a.album_id, label: a.display_title }));
        const handle = createChipInput({
            container: albumWrap,
            items: getItems(song),
            onSearch: async (q) => {
                const r = await searchAlbums(q);
                if (r === ABORTED || !r) return [];
                return r.map((a) => ({ id: a.id, label: a.title }));
            },
            onAdd: async (opt) => {
                await addSongAlbum(song.id, opt.id ?? null, opt.label, null, null);
                const fresh = await refresh();
                handle.setItems(getItems(fresh));
            },
            onRemove: async (albumId) => {
                await removeSongAlbum(song.id, albumId);
                await refresh();
            },
            allowCreate: true,
        });
    }
}

export function renderSongEditorEmpty() {
    const panel = document.getElementById("editor-panel");
    if (!panel) return;
    const scroll = panel.querySelector(".editor-scroll");
    if (!scroll) return;
    scroll.innerHTML = `<div class="editor-empty-state">Select a song to edit</div>`;
}

export function renderSongEditorV2(song) {
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
      ${renderScalarField("Title", song.media_name, "ef-title")}
    </div>
    <div class="editor-col col-4">
      ${renderScalarField("Year", song.year, "ef-year", "number")}
    </div>
  </div>
  ${REQUIRED_ROLES.map((role) => renderChipField(role, creditsByRole[role], `No ${role.toLowerCase()}s`, true, role.toLowerCase())).join("")}
  ${renderChipField("Tags", tags, "No tags", true, "tags")}
  ${renderChipField("Publisher", publishers, "No publisher", true, "publisher")}
  ${renderChipField("Album / Release", albums, "No album", true, "album")}
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
`;
}
