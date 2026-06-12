/**
 * Song Editor V2 — form renderer + scalar interactivity.
 * Renders into #editor-panel .editor-scroll from getCatalogSong data.
 */

import {
    ABORTED,
    addAlbumCredit,
    addAlbumPublisher,
    addSongAlbum,
    addSongCredit,
    addSongPublisher,
    addSongTag,
    getCatalogSong,
    getMultiView,
    multiMutate,
    patchSongScalars,
    removeAlbumCredit,
    removeAlbumPublisher,
    removeSongAlbum,
    removeSongCredit,
    removeSongPublisher,
    removeSongTag,
    searchAlbums,
    searchArtists,
    searchArtistNames,
    searchPublishers,
    searchTags,
    updateAlbum,
    updateSongAlbumLink,
} from "../api.js";
import { createChipInput } from "../components/chip_input.js";
import { showToast } from "../components/toast.js";
import { PROCESSING_STATUS } from "../constants.js";
import { parseTagInput } from "../utils/tag_input.js";
import { escapeHtml } from "../components/utils.js";

// Per the filing warnings contract: mutate responses are 200 even when the
// post-commit ID3/file pass failed; surface those warnings to the user.
function notifyMutateWarnings(result) {
    if (result?.warnings?.length) {
        const msg = result.warnings.map((w) => w.error || w.kind).join("; ");
        showToast(`Saved, but file operation failed: ${msg}`, "warning", 5000);
    }
}

function renderChips(items, emptyLabel) {
    if (!items || items.length === 0) {
        return `<span class="editor-chip miss">${escapeHtml(emptyLabel)}</span>`;
    }
    return items
        .map((item) => `<span class="editor-chip">${escapeHtml(item)}</span>`)
        .join("");
}

function renderScalarField(
    label,
    value,
    inputId,
    type = "text",
    extraButtons = "",
    required = true,
) {
    const missing = required && (value == null || value === "");
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

function renderChipField(
    label,
    chips,
    emptyLabel,
    canMiss = true,
    fieldKey = null,
) {
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
    { inputId: "ef-year", field: "year", numeric: true },
    { inputId: "ef-bpm", field: "bpm", numeric: true },
    { inputId: "ef-isrc", field: "isrc", numeric: false },
    { inputId: "ef-notes", field: "notes", numeric: false },
];

const ALBUM_TYPES = ["Album", "EP", "Single", "Compilation", "Anthology"];

function renderAlbumSubCards(albums, songId) {
    if (!albums || !albums.length) return "";
    return albums
        .map((album) => {
            const title = album.album_title || album.display_title || "Unknown Album";
            const albumId = album.album_id || album.id;
            const typeOptions = ALBUM_TYPES.map(
                (t) =>
                    `<option value="${t}" ${album.album_type === t ? "selected" : ""}>${t}</option>`,
            ).join("");

            return `
<div class="album-sub-card" data-album-id="${albumId}">
  <div class="album-sub-title-row">
    <button class="album-sub-star${album.is_primary ? " is-primary" : ""}" data-action="set-primary-album" data-song-id="${songId}" data-album-id="${albumId}" title="${album.is_primary ? "Primary album" : "Set as primary album"}" type="button">&#9733;</button>
    <div class="album-title-input-wrap">
      <div class="editor-input-row">
        <input class="editor-input" data-album-scalar="title" data-album-id="${albumId}" data-song-id="${songId}" type="text" value="${escapeHtml(title)}" readonly>
        <button class="editor-case-btn" data-action="format-case" data-entity-type="album" data-entity-id="${albumId}" data-song-id="${songId}" data-field="title" data-type="sentence" title="Sentence case" type="button">S</button>
        <button class="editor-case-btn" data-action="format-case" data-entity-type="album" data-entity-id="${albumId}" data-song-id="${songId}" data-field="title" data-type="title" title="Title case" type="button">T</button>
      </div>
    </div>
    <button class="album-sub-sync-btn" data-action="sync-album-from-song" data-album-id="${albumId}" data-song-id="${songId}" title="Sync metadata from song" type="button">&#8595;</button>
    <button class="album-sub-remove" data-action="remove-album" data-song-id="${songId}" data-album-id="${albumId}" title="Unlink album" type="button">&#10005;</button>
  </div>

  <div class="editor-field">
    <label class="editor-label">Artist</label>
    <div class="album-sub-chips" data-album-chips="artist" data-album-id="${albumId}"></div>
  </div>

  <div class="editor-field">
    <label class="editor-label">Publisher</label>
    <div class="album-sub-chips" data-album-chips="publisher" data-album-id="${albumId}"></div>
  </div>

  <div class="album-sub-meta-row">
    <div class="editor-field">
      <label class="editor-label">Type</label>
      <select class="editor-input" data-action="change-album-type" data-album-id="${albumId}" data-song-id="${songId}">${typeOptions}</select>
    </div>
    <div class="editor-field">
      <label class="editor-label">Year</label>
      <input class="editor-input" data-album-scalar="release_year" data-album-id="${albumId}" data-song-id="${songId}" type="number" value="${album.release_year ?? ""}" readonly>
    </div>
    <div class="editor-field">
      <label class="editor-label">Disc</label>
      <input class="editor-input" data-album-link="disc_number" data-album-id="${albumId}" data-song-id="${songId}" type="number" value="${album.disc_number ?? ""}" readonly>
    </div>
    <div class="editor-field">
      <label class="editor-label">Track</label>
      <input class="editor-input" data-album-link="track_number" data-album-id="${albumId}" data-song-id="${songId}" type="number" value="${album.track_number ?? ""}" readonly>
    </div>
  </div>
</div>`;
        })
        .join("");
}

function updateAlbumSubSection(freshSong, refreshCallback) {
    const el = document.querySelector(
        `[data-album-sub-song="${freshSong.id}"]`,
    );
    if (el) {
        // Preserve the on-screen card order across in-place updates so toggling
        // primary doesn't reorder cards under the cursor. The server returns
        // albums primary-first (used on full load); here we freeze the existing
        // order and append any newly-added albums at the end.
        const domOrder = Array.from(
            el.querySelectorAll(".album-sub-card"),
        ).map((c) => c.dataset.albumId);
        const ordered = [...(freshSong.albums || [])].sort((a, b) => {
            const ai = domOrder.indexOf(String(a.album_id ?? a.id));
            const bi = domOrder.indexOf(String(b.album_id ?? b.id));
            return (
                (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi)
            );
        });
        el.innerHTML = renderAlbumSubCards(ordered, freshSong.id);
        wireAlbumSubChips(freshSong, refreshCallback);
        wireAlbumScalarInputs(freshSong, refreshCallback);
    }
    // Sync missing state on the field
    const field = document.querySelector(`[data-chip-field="album"]`);
    if (field)
        field.classList.toggle(
            "missing",
            (freshSong.albums || []).length === 0,
        );
}

function wireAlbumScalarInput(input, onCommit, refresh) {
    input.removeAttribute("readonly");

    const errorEl = document.createElement("div");
    errorEl.className = "editor-input-error";
    const inputRow = input.closest(".editor-input-row");
    (inputRow ?? input).after(errorEl);

    let saving = false;

    function showError(msg) {
        input.classList.add("editor-input--error");
        errorEl.textContent = msg;
    }

    function clearError() {
        input.classList.remove("editor-input--error");
        errorEl.textContent = "";
    }

    function revert() {
        input.value = input.defaultValue;
        clearError();
    }

    async function commit() {
        if (saving) return;
        const raw = input.value.trim();
        clearError();
        if (raw === input.defaultValue) return;

        const isNumeric = input.type === "number";
        const payload = raw === "" ? null : isNumeric ? Number(raw) : raw;

        saving = true;
        input.blur();
        input.disabled = true;
        try {
            await onCommit(payload);
            input.defaultValue = raw;
            await refresh();
        } catch (err) {
            input.value = input.defaultValue;
            showError(`Save failed: ${err.message}`);
        } finally {
            input.disabled = false;
            saving = false;
        }
    }

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && input.tagName !== "TEXTAREA") {
            e.preventDefault();
            e.stopPropagation();
            commit();
            input.blur();
        }
        if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            revert();
            input.blur();
        }
    });

    input.addEventListener("blur", () => {
        if (errorEl.textContent) {
            revert();
            return;
        }
        commit();
    });
}

export function wireAlbumScalarInputs(song, refresh) {
    const card = document.querySelector(`[data-album-sub-song="${song.id}"]`);
    if (!card) return;

    card.querySelectorAll("[data-album-scalar]").forEach((input) => {
        const { albumScalar: field, albumId } = input.dataset;
        wireAlbumScalarInput(input, (val) => updateAlbum(albumId, { [field]: val }), refresh);
    });

    card.querySelectorAll("[data-album-link]").forEach((input) => {
        const { albumLink: field, albumId, songId } = input.dataset;
        const onCommit = (val) => updateSongAlbumLink(
            songId, albumId,
            field === "track_number" ? val : undefined,
            field === "disc_number" ? val : undefined,
        );
        wireAlbumScalarInput(input, onCommit, refresh);
    });
}

function wireAlbumSubChips(song, refresh) {
    const containers = document.querySelectorAll(
        `[data-album-id][data-album-chips]`,
    );
    containers.forEach((container) => {
        const { albumId, albumChips: field } = container.dataset;
        const album = (song.albums || []).find(
            (a) => String(a.album_id || a.id) === String(albumId),
        );
        if (!album) return;

        if (field === "artist") {
            const getItems = (a) => {
                return (a.credits || [])
                    .filter((c) => c.role_name === "Performer")
                    .map((c) => ({
                        id: c.name_id || c.credit_id || c.id,
                        label: c.display_name,
                        _identityId: c.identity_id,
                        _nameId: c.name_id,
                    }));
            };

            createChipInput({
                container,
                items: getItems(album),
                onSearch: async (q) => {
                    const r = await searchArtistNames(q);
                    return (r || []).map((i) => ({
                        id: i.owner_identity_id,
                        name_id: i.name_id,
                        label: i.display_name,
                    }));
                },
                onAdd: async (opt) => {
                    await addAlbumCredit(
                        albumId,
                        opt.label,
                        "Performer",
                        opt.id,
                    );
                    await refresh();
                },
                onRemove: async (nameId) => {
                    await removeAlbumCredit(albumId, nameId);
                    await refresh();
                },
                allowCreate: true,
                placeholder: "Add album artist",
                labelAttrs: (item) =>
                    item._identityId
                        ? {
                              "data-action": "open-edit-modal",
                              "data-chip-type": "credit",
                              "data-item-id": item._nameId ?? "",
                              "data-identity-id": item._identityId,
                          }
                        : null,
            });
        } else if (field === "publisher") {
            const getItems = (a) =>
                (a.album_publishers || []).map((p) => ({
                    id: p.id,
                    label: p.name,
                }));

            createChipInput({
                container,
                items: getItems(album),
                onSearch: async (q) => {
                    const r = await searchPublishers(q);
                    return (r || []).map((p) => ({ id: p.id, label: p.name }));
                },
                onAdd: async (opt) => {
                    await addAlbumPublisher(albumId, opt.label, opt.id);
                    await refresh();
                },
                onRemove: async (pubId) => {
                    await removeAlbumPublisher(albumId, pubId);
                    await refresh();
                },
                allowCreate: true,
                placeholder: "Add album publisher",
                labelAttrs: (item) => ({
                    "data-action": "open-edit-modal",
                    "data-chip-type": "publisher",
                    "data-item-id": item.id,
                }),
            });
        }
    });
}

function updateListRowBlockers(songId, reviewBlockers) {
    const row = document.querySelector(`.song-row[data-id="${songId}"]`);
    if (!row) return;
    const colMissing = row.querySelector(".col-missing");
    if (!colMissing) return;
    colMissing.innerHTML = (reviewBlockers || [])
        .map(
            (b) =>
                `<span class="pill miss" title="Missing: ${b.name}">${b.pill}</span>`,
        )
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
    // Multi-edit: the virtual song carries the selection; saves fan out
    // server-side via multi-mutate and overwrite the field on all songs.
    const multiIds = song._multiIds || null;

    for (const { inputId, field, numeric } of SCALAR_FIELDS) {
        const input = document.getElementById(inputId);
        if (!input) continue;

        input.removeAttribute("readonly");

        let committedValue = input.value;
        let hasError = false;
        let saving = false;

        const errorEl = document.createElement("div");
        errorEl.className = "editor-input-error";
        const container = input.closest(".editor-input-row");
        if (container) {
            container.after(errorEl);
        } else {
            input.after(errorEl);
        }

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

            if (raw === committedValue) return;

            const payload = numeric
                ? raw === ""
                    ? null
                    : Number(raw)
                : raw === ""
                  ? null
                  : raw;

            saving = true;
            input.disabled = true;
            try {
                if (multiIds) {
                    const result = await multiMutate(multiIds, {
                        update: { [field]: payload },
                    });
                    committedValue = raw;
                    // The field now agrees across the selection
                    input.placeholder = "";
                    notifyMutateWarnings(result);
                    if (onUpdated) onUpdated(null);
                    return;
                }
                const fresh = await patchSongScalars(song.id, { [field]: payload });
                committedValue = raw;
                updateListRowBlockers(song.id, fresh.review_blockers);
                if (onUpdated) onUpdated(fresh);
            } catch (err) {
                input.value = committedValue;
                showError(`Save failed: ${err.message}`);
            } finally {
                input.disabled = false;
                saving = false;
            }
        }

        input.addEventListener("input", () => {
            // Backend handles validation - no client-side checking needed
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && input.tagName !== "TEXTAREA") {
                e.preventDefault();
                e.stopPropagation();
                commit();
                input.blur();
            }
            if (e.key === "Escape") {
                e.preventDefault();
                e.stopPropagation();
                revert();
                input.blur();
            }
        });

        input.addEventListener("blur", () => {
            if (hasError) {
                revert();
                return;
            }
            if (blurSaves) commit();
            else revert();
        });
    }

    return {
        updateField(field, value) {
            const input = document.getElementById(
                SCALAR_FIELDS.find((f) => f.field === field)?.inputId,
            );
            if (!input) return;
            input.value = value ?? "";
        },
    };
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
 * Adds drift indicator dots to scalar/chip field labels for every drift entry.
 * Must be called after renderSongEditorV2.
 *
 * @param {object|null} diff - {key: {db, file}} from inspect-file. null/empty = in sync.
 *   Keys: media_name, year, bpm, isrc, notes (scalars); credit:{Role}, tag:{Cat},
 *   publisher, album (chips). Unknown keys (e.g. duration) are silently ignored.
 */
const SCALAR_DIFF_INPUT_BY_KEY = {
    media_name: "ef-title",
    year: "ef-year",
    bpm: "ef-bpm",
    isrc: "ef-isrc",
    notes: "ef-notes",
};

export function wireDriftIndicators(diff) {
    document
        .querySelectorAll("#editor-panel .drift-dot")
        .forEach((el) => el.remove());
    if (!diff || Object.keys(diff).length === 0) return;
    const fmt = (v) => {
        if (v == null || v === "") return "(empty)";
        if (Array.isArray(v)) return v.length ? v.join(", ") : "(empty)";
        return String(v);
    };

    for (const [key, entry] of Object.entries(diff)) {
        const tooltip = `DB: ${fmt(entry.db)}\nFile: ${fmt(entry.file)}`;
        let labelEl = null;

        if (SCALAR_DIFF_INPUT_BY_KEY[key]) {
            const input = document.getElementById(SCALAR_DIFF_INPUT_BY_KEY[key]);
            labelEl = input
                ?.closest(".editor-field")
                ?.querySelector(".editor-label");
        } else if (key.startsWith("credit:")) {
            const role = key.slice(7).toLowerCase();
            labelEl = document
                .querySelector(`[data-chip-field="${role}"]`)
                ?.querySelector(".editor-label");
        } else if (key.startsWith("tag:")) {
            // Tag drift surfaces on the unified Tags chip field.
            labelEl = document
                .querySelector(`[data-chip-field="tags"]`)
                ?.querySelector(".editor-label");
        } else if (key === "publisher" || key === "album") {
            labelEl = document
                .querySelector(`[data-chip-field="${key}"]`)
                ?.querySelector(".editor-label");
        }

        if (labelEl) appendDot(labelEl, tooltip);
    }
}

function appendDot(labelEl, title) {
    if (!labelEl) return;
    const dot = document.createElement("span");
    dot.className = "drift-dot";
    dot.title = title;
    labelEl.appendChild(dot);
}

export function wireChipInputs(song, onUpdated, onSplit, validationRules, onSplitPublisher) {
    const handles = {};
    const getItemsByField = {};
    // Multi-edit: the virtual song carries the selection; chip saves fan out
    // server-side via multi-mutate (adds target all songs, removes only
    // universal entries).
    const multiIds = song._multiIds || null;

    function syncMissing(fieldKey, items) {
        const field = document.querySelector(`[data-chip-field="${fieldKey}"]`);
        if (!field) return;
        field.classList.toggle("missing", (items || []).length === 0);
    }

    async function refresh() {
        if (multiIds) {
            // The collapsed view must be rebuilt (universal flags shift);
            // onUpdated re-renders the whole multi editor from it.
            const fresh = await getMultiView(multiIds);
            if (onUpdated) onUpdated(fresh);
            return fresh;
        }
        const fresh = await getCatalogSong(song.id);
        updateListRowBlockers(song.id, fresh.review_blockers);
        for (const [key, getItems] of Object.entries(getItemsByField)) {
            syncMissing(key, getItems(fresh));
        }
        if (onUpdated) onUpdated(fresh);
        return fresh;
    }

    async function saveChipOp(ops, singleCall) {
        if (multiIds) {
            notifyMutateWarnings(await multiMutate(multiIds, ops));
            return;
        }
        notifyMutateWarnings(await singleCall());
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
        const getItems = (s) =>
            s.credits
                .filter((c) => c.role_name === role)
                .map((c) => ({
                    id: c.credit_id,
                    label: c.display_name,
                    _identityId: c.identity_id,
                    _nameId: c.name_id,
                }));

        const handle = createChipInput({
            container: wrap,
            items: getItems(song),
            onSearch: async (q) => {
                const r = await searchArtistNames(q);
                if (r === ABORTED || !r) return [];
                return r.map((a) => ({
                    id: a.owner_identity_id,
                    name_id: a.name_id,
                    label: a.display_name,
                }));
            },
            onAdd: async (opt) => {
                await saveChipOp(
                    { add: [{ type: "credit", name: opt.label, id: opt.id ?? null, role }] },
                    () => addSongCredit(song.id, opt.label, role, opt.id),
                );
                const fresh = await refresh();
                handle.setItems(getItems(fresh));
            },
            onRemove: async (creditId) => {
                await saveChipOp(
                    { remove: [{ type: "credit", id: creditId }] },
                    () => removeSongCredit(song.id, creditId),
                );
                await refresh();
            },
            placeholder: `Add ${role.toLowerCase()}`,
            onSplit: onSplit
                ? (item) =>
                      onSplit({
                          songId: song.id,
                          text: item.label,
                          role,
                          creditId: item.id,
                      })
                : null,
            allowCreate: true,
            labelAttrs: (item) =>
                item._identityId
                    ? {
                          "data-action": "open-edit-modal",
                          "data-chip-type": "credit",
                          "data-song-id": song.id,
                          "data-item-id": item._nameId ?? "",
                          "data-identity-id": item._identityId,
                      }
                    : null,
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
        const getItems = (s) =>
            s.tags.map((t) => ({
                id: t.id,
                label: t.name,
                category: t.category,
                _isPrimary: !!t.is_primary,
            }));
        const handle = createChipInput({
            container: tagsWrap,
            items: getItems(song),
            onSearch: async (q) => {
                const { name } = parseTagInput(q, tagRules);
                const r = await searchTags(name);
                if (r === ABORTED || !r) return [];
                return r.map((t) => ({
                    id: t.id,
                    label: t.name,
                    category: t.category,
                }));
            },
            onAdd: async (opt) => {
                const { name, category } = opt.id
                    ? opt
                    : parseTagInput(opt.label, tagRules);
                await saveChipOp(
                    {
                        add: [
                            {
                                type: "tag",
                                name,
                                category: category ?? null,
                                id: opt.id ?? null,
                            },
                        ],
                    },
                    () => addSongTag(song.id, name, category ?? null, opt.id ?? null),
                );
                const fresh = await refresh();
                handle.setItems(getItems(fresh));
            },
            onRemove: async (tagId) => {
                await saveChipOp(
                    { remove: [{ type: "tag", id: tagId }] },
                    () => removeSongTag(song.id, tagId),
                );
                await refresh();
            },
            allowCreate: true,
            placeholder: "Add tag",
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
                return [
                    {
                        className: `chip-input__chip-btn chip-input__chip-star${item._isPrimary ? " is-primary" : ""}`,
                        html: "★",
                        title: item._isPrimary
                            ? "Primary genre"
                            : "Set as primary genre",
                        dataset: {
                            action: "set-primary-tag",
                            songId: String(song.id),
                            tagId: String(item.id),
                        },
                    },
                ];
            },
        });
        handles.tags = handle;
        getItemsByField.tags = getItems;
    }

    // ── Publisher ──────────────────────────────────────────────────────────────
    const pubWrap = getContainer("publisher");
    if (pubWrap) {
        const getItems = (s) =>
            s.publishers.map((p) => ({ id: p.id, label: p.name }));
        const handle = createChipInput({
            container: pubWrap,
            items: getItems(song),
            onSearch: async (q) => {
                const r = await searchPublishers(q);
                if (r === ABORTED || !r) return [];
                return r.map((p) => ({ id: p.id, label: p.name }));
            },
            onAdd: async (opt) => {
                await saveChipOp(
                    { add: [{ type: "publisher", name: opt.label, id: opt.id ?? null }] },
                    () => addSongPublisher(song.id, opt.label, opt.id),
                );
                const fresh = await refresh();
                handle.setItems(getItems(fresh));
            },
            onRemove: async (pubId) => {
                await saveChipOp(
                    { remove: [{ type: "publisher", id: pubId }] },
                    () => removeSongPublisher(song.id, pubId),
                );
                await refresh();
            },
            allowCreate: true,
            placeholder: "Add publisher",
            onSplit: onSplitPublisher
                ? (item) => onSplitPublisher({ songId: song.id, text: item.label, publisherId: item.id })
                : null,
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
            handles.album = createChipInput({
                container: searchWrap,
                items: [],
                onSearch: async (q) => {
                    const r = await searchAlbums(q);
                    if (r === ABORTED || !r) return [];
                    return r.map((a) => ({
                        id: a.id,
                        label: a.display_title || a.title || a.name,
                    }));
                },
                onAdd: async (opt) => {
                    await saveChipOp(
                        {
                            add: [
                                {
                                    type: "album",
                                    id: opt.id ?? null,
                                    name: opt.id ? null : opt.label,
                                },
                            ],
                        },
                        () =>
                            addSongAlbum(
                                song.id,
                                opt.id ?? null,
                                opt.id ? null : opt.label,
                                null,
                                null,
                            ),
                    );
                    const fresh = await refresh();
                    // Multi re-renders the whole editor via onUpdated
                    if (!multiIds) updateAlbumSubSection(fresh, refresh);
                },
                onRemove: async () => {}, // removal handled by card × buttons
                allowCreate: true,
                placeholder: "Add album / release",
                getCreateLabel: (q) => `+ Create "${q}"`,
            });
        }
    }

    // Album artist/publisher chips are album-level; always wire them.
    // Track/disc scalar inputs are per-song-link; skip in multi mode.
    wireAlbumSubChips(song, refresh);
    if (!multiIds) {
        wireAlbumScalarInputs(song, refresh);
    }

    return {
        updateField(fieldKey, freshSong) {
            const key = String(fieldKey).toLowerCase();
            if (key === "album") {
                updateAlbumSubSection(freshSong, refresh);
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
        // Re-open a field's add-input after a structural re-render so the user
        // can keep adding (e.g. several composers) without re-clicking the stub.
        expandField(fieldKey) {
            if (!fieldKey) return;
            const handle = handles[String(fieldKey).toLowerCase()];
            if (handle && handle.expand) handle.expand();
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
export function renderActionSidebar(
    song,
    { searchEngines = {}, defaultSearchEngine = null } = {},
) {
    const panel = document.getElementById("editor-panel");
    if (!panel) return;
    const sidebar = panel.querySelector(".action-sidebar");
    if (!sidebar) return;

    const status = song.processing_status ?? PROCESSING_STATUS.NEEDS_REVIEW;
    const blockers = song.review_blockers || [];
    const isInStaging = song.is_in_staging ?? false;

    // ── Organize / Mark as Done button ────────────────────────────────────────
    let organizeBtn = "";
    let unreviewBtn = "";
    const actions = song.available_actions || [];
    if (actions.includes("mark_reviewed")) {
        const blocked = blockers.length > 0;
        organizeBtn = `<button class="sidebar-btn organize${blocked ? " blocked" : ""}"
            data-action="mark-reviewed" data-id="${song.id}"
            ${blocked ? 'disabled title="Missing required fields"' : ""}>Mark as Done</button>`;
    } else if (actions.includes("move_to_library") || actions.includes("unreview")) {
        if (actions.includes("move_to_library")) {
            organizeBtn = `<button class="sidebar-btn organize" data-action="move-to-library" data-id="${song.id}">Organize to Library</button>`;
        }
        if (actions.includes("unreview")) {
            unreviewBtn = `<button class="sidebar-btn" data-action="unreview-song" data-id="${song.id}">Unreview</button>`;
        }
    }

    const targetPath =
        song.organized_path_preview
            ? `<div class="sidebar-path">→ ${escapeHtml(song.organized_path_preview)}</div>`
            : "";

    // ── Web search split button ────────────────────────────────────────────────
    const engine =
        defaultSearchEngine || Object.keys(searchEngines)[0] || "spotify";
    const engineLabel = searchEngines[engine] || engine;
    const otherEngines = Object.entries(searchEngines)
        .filter(([k]) => k !== engine)
        .map(
            ([k, v]) =>
                `<button class="web-search-option" data-engine="${escapeHtml(k)}" data-label="${escapeHtml(v)}">${escapeHtml(v)}</button>`,
        )
        .join("");
    const searchSplitBtn = `
<div class="web-search-split sidebar-split-btn">
    <button class="sidebar-btn web-search-main" data-action="web-search" data-song-id="${song.id}" data-engine="${escapeHtml(engine)}" data-label="${escapeHtml(engineLabel)}" style="flex:1;border-right:none;border-radius:5px 0 0 5px">Search [${escapeHtml(engineLabel.slice(0, 2).toUpperCase())}]</button><button class="sidebar-btn" data-action="web-search-set-engine" style="border-radius:0 5px 5px 0;padding:8px 6px;width:22px;flex-shrink:0">▾</button>
    <div class="web-search-dropdown" hidden>${otherEngines}</div>
</div>`;

    // ── Delete Original ────────────────────────────────────────────────────────
    const hasOriginal = song.original_exists && song.estimated_original_path;
    const hasStaleOrigin = !song.original_exists && song.estimated_original_path;
    const deleteOriginalBtn = hasOriginal
        ? `<button class="sidebar-btn delete-original" data-action="cleanup-original" data-song-id="${song.id}" data-path="${escapeHtml(song.estimated_original_path)}">Delete Original</button>
           <div class="sidebar-path" style="opacity:0.6">${escapeHtml(song.estimated_original_path)}</div>`
        : hasStaleOrigin
        ? `<button class="sidebar-btn" data-action="cleanup-original" data-song-id="${song.id}" data-path="${escapeHtml(song.estimated_original_path)}">Clear Stale Origin Record</button>
           <div class="sidebar-path" style="opacity:0.6">${escapeHtml(song.estimated_original_path)}</div>`
        : "";

    const fileIndicator = song.file_exists
        ? `<span class="file-indicator file-indicator--ok" title="File found"></span>`
        : `<span class="file-indicator file-indicator--missing" title="File not found"></span>`;
    const playBtn = `<button class="sidebar-btn" data-action="open-scrubber" data-id="${song.id}" data-title="${escapeHtml(song.media_name || "")}">${fileIndicator} Play</button>`;

    const syncLedHtml = `<span class="sync-led" data-song-id="${song.id}"></span>`;

    sidebar.innerHTML = `
<div class="sidebar-group-label">File</div>
${playBtn}
<button class="sidebar-btn" data-action="open-filename-parser-single" data-id="${song.id}" data-filename="${escapeHtml((song.source_path || "").split(/[\\/]/).pop())}">Parse Filename</button>

<div class="sidebar-divider"></div>

<div class="sidebar-group-label">Research</div>
${searchSplitBtn}
<button class="sidebar-btn sidebar-btn--spotify" data-action="open-spotify-modal" data-id="${song.id}" data-title="${escapeHtml(song.media_name || "")}"><img class="sidebar-btn__icon" src="/static/resources/Spotify_icon.svg" alt="">Spotify</button>

<div class="sidebar-divider"></div>

<div class="sidebar-group-label">Finalize</div>
<button class="sidebar-btn sidebar-btn--id3" data-action="sync-id3" data-song-id="${song.id}">${syncLedHtml} Write ID3</button>
${organizeBtn}
${unreviewBtn}
${targetPath}

<div class="sidebar-divider"></div>

${deleteOriginalBtn}
<div style="margin-top:auto; display:flex; flex-direction:column; gap:6px;">
<button class="sidebar-btn sidebar-btn--warning" data-action="reject-song" data-id="${song.id}">Reject Song</button>
<button class="sidebar-btn sidebar-btn--danger" data-action="delete-song" data-id="${song.id}" data-processing-status="${song.processing_status}" data-in-staging="${song.is_in_staging ? "1" : "0"}">Delete Record</button>
</div>
`;
}

// The scroll container survives re-renders, so multi-preview state attached to
// it (class + capture-phase save guard) must be stripped whenever the editor
// re-renders as anything else.
function clearMultiPreview(scroll) {
    scroll.classList.remove("editor-multi-preview");
    if (scroll._multiGuard) {
        scroll.removeEventListener("click", scroll._multiGuard, true);
        scroll.removeEventListener("mousedown", scroll._multiGuard, true);
        delete scroll._multiGuard;
    }
}

const MULTI_SCALAR_INPUTS = {
    media_name: "ef-title",
    year: "ef-year",
    bpm: "ef-bpm",
    isrc: "ef-isrc",
    notes: "ef-notes",
};

function mixedPlaceholder(values) {
    const parts = values.map((v) => (v == null || v === "" ? "(empty)" : String(v)));
    const text = parts.join(", ");
    return text.length > 60 ? "Mixed" : `Mixed: ${text}`;
}

export function renderSongEditorMulti(view, songIds, validationRules = null) {
    renderSongEditorV2(view, null, null);
    const panel = document.getElementById("editor-panel");
    const scroll = panel?.querySelector(".editor-scroll");
    if (!scroll) return;

    scroll.classList.add("editor-multi-preview");
    const sidebar = panel.querySelector(".action-sidebar");
    if (sidebar) sidebar.innerHTML = `<div class="multi-edit-count">Editing ${songIds.length} songs</div>`;

    // The virtual song carries the selection: wire* fan saves out through
    // multi-mutate, and any save re-collapses the view and re-renders here.
    view._multiIds = songIds;
    const rerender = (freshView) => {
        if (freshView) {
            renderSongEditorMulti(freshView, songIds, validationRules);
            return;
        }
        // Scalar saves don't carry a view; re-fetch the collapsed state.
        getMultiView(songIds)
            .then((v) => renderSongEditorMulti(v, songIds, validationRules))
            .catch((err) =>
                showToast("Multi-view refresh failed: " + err.message, "error", 5000),
            );
    };

    // The visible chip UI (chips, category styling, add stubs, folding) is
    // built by the chip-input component, not the static markup — wire it so
    // the editor matches the single-song editor pixel for pixel.
    wireChipInputs(view, rerender, null, validationRules, null);
    wireScalarInputs(view, validationRules, rerender);

    // Actions that still have no multi path (album-card internals, splitters,
    // primary stars, edit modals) stay blocked at capture phase.
    const blockMutations = (e) => {
        const t = e.target.closest(".chip-input__chip-split, [data-action]");
        if (t && t.dataset.action !== "remove-album") {
            e.preventDefault();
            e.stopPropagation();
            if (e.type === "click")
                showToast("Not supported in multi-edit yet", "error", 3000);
        }
    };
    scroll.addEventListener("click", blockMutations, true);
    // Autocomplete options commit on mousedown, not click
    scroll.addEventListener("mousedown", blockMutations, true);
    scroll._multiGuard = blockMutations;

    // Mixed scalars: empty input + ghost text listing the conflicting values
    for (const [field, values] of Object.entries(view.mixed_fields || {})) {
        const input = document.getElementById(MULTI_SCALAR_INPUTS[field] || "");
        if (input) input.placeholder = mixedPlaceholder(values);
    }

    // Partial chips: dim entries that exist on some but not all selected songs
    const partialByField = {
        tags: new Set(
            (view.tags || []).filter((t) => !t.universal).map((t) => t.name),
        ),
        publisher: new Set(
            (view.publishers || [])
                .filter((p) => !p.universal)
                .map((p) => p.name),
        ),
    };
    for (const c of view.credits || []) {
        if (c.universal) continue;
        const role = c.role_name.toLowerCase();
        (partialByField[role] = partialByField[role] || new Set()).add(
            c.display_name,
        );
    }
    scroll.querySelectorAll("[data-chip-field]").forEach((fieldEl) => {
        const partial = partialByField[fieldEl.dataset.chipField];
        if (!partial) return;
        fieldEl.querySelectorAll(".chip-input__chip").forEach((chip) => {
            const label = chip.querySelector(
                ".chip-input__chip-label",
            )?.textContent;
            if (partial.has(label)) chip.classList.add("chip-partial");
        });
    });

    // Album sub-cards render in view.albums order; dim the partial ones
    const cards = scroll.querySelectorAll("[data-album-sub-song] > *");
    (view.albums || []).forEach((album, i) => {
        if (!album.universal && cards[i]) cards[i].classList.add("chip-partial");
    });
}


export function renderSongEditorEmpty() {
    const panel = document.getElementById("editor-panel");
    if (!panel) return;
    const scroll = panel.querySelector(".editor-scroll");
    if (scroll) {
        clearMultiPreview(scroll);
        scroll.innerHTML = `<div class="editor-empty-state">Select a song to edit</div>`;
    }
    const sidebar = panel.querySelector(".action-sidebar");
    if (sidebar) sidebar.innerHTML = "";
}

export function renderSongEditorV2(song, diff = null, rawTags = null) {
    const panel = document.getElementById("editor-panel");
    if (!panel) return;
    const scroll = panel.querySelector(".editor-scroll");
    if (!scroll) return;
    clearMultiPreview(scroll);

    const REQUIRED_ROLES = ["Performer", "Composer"];
    const OPTIONAL_ROLES = ["Lyricist", "Producer"];
    const creditsByRole = song.credits_by_role || {};
    const publishers = song.publishers.map((p) => p.name);
    const albums = song.albums.map((a) => a.display_title);
    const tags = song.tags.map((t) =>
        t.category ? `${t.category}::${t.name}` : t.name,
    );

    scroll.innerHTML = `
<div class="editor-section">
  <div class="editor-section-title">Required Metadata</div>
  ${renderScalarField("Title", song.media_name, "ef-title", "text", renderCaseButtons(song.id, "media_name"))}
  ${renderScalarField("Year", song.year, "ef-year", "number")}
  ${REQUIRED_ROLES.map((role) => renderChipField(role, creditsByRole[role], `No ${role.toLowerCase()}s`, true, role.toLowerCase())).join("")}
  ${renderChipField("Tags", tags, "No tags", true, "tags")}
  ${renderChipField("Publisher", publishers, "No publisher", true, "publisher")}
  <div class="editor-field${song.albums.length === 0 ? " missing" : ""}" data-chip-field="album">
    <label class="editor-label">Album</label>
    <div class="album-field-body">
      <div data-album-sub-song="${song.id}">${renderAlbumSubCards(song.albums, song.id)}</div>
      <div class="album-search-wrap"></div>
      <button class="editor-quick-create-btn" data-action="quick-create-album" data-song-id="${song.id}" title="Quick-create a Single album from this song's title">+ Create single</button>
    </div>
  </div>
</div>

<div class="editor-section">
  <div class="editor-section-title">Additional Data</div>
  ${OPTIONAL_ROLES.map((role) => renderChipField(role, creditsByRole[role], `No ${role.toLowerCase()}s`, false, role.toLowerCase())).join("")}
  ${renderScalarField("BPM", song.bpm, "ef-bpm", "number", "", false)}
  ${renderScalarField("ISRC", song.isrc, "ef-isrc", "text", "", false)}
</div>

${(() => {
    if (!diff && !rawTags) return "";

    const rows = [];

    // Drift entries where the DB is empty and the file has a value:
    // "the file knows something the DB doesn't". Mismatches where both have
    // values are surfaced via drift dots, not here.
    const isEmpty = (v) =>
        v == null
        || v === ""
        || (Array.isArray(v) && v.length === 0);
    const fmtVal = (v) => (Array.isArray(v) ? v.join(", ") : String(v));
    const labelFor = (key) => {
        if (key.startsWith("credit:")) return key.slice(7);
        if (key.startsWith("tag:")) return key.slice(4);
        if (key === "media_name") return "Title";
        if (key === "isrc") return "ISRC";
        if (key === "bpm") return "BPM";
        return key.charAt(0).toUpperCase() + key.slice(1);
    };

    if (diff) {
        for (const [key, entry] of Object.entries(diff)) {
            if (!isEmpty(entry.db) || isEmpty(entry.file)) continue;
            rows.push(`<div class="raw-tag-row">
        <span class="raw-tag-key">${escapeHtml(labelFor(key))}</span>
        <span class="raw-tag-val">${escapeHtml(fmtVal(entry.file))}</span>
      </div>`);
        }
    }

    if (rawTags) {
        for (const [k, vals] of Object.entries(rawTags)) {
            rows.push(`<div class="raw-tag-row">
        <span class="raw-tag-key">${escapeHtml(k)}</span>
        <span class="raw-tag-val">${escapeHtml(Array.isArray(vals) ? vals.join(", ") : String(vals))}</span>
      </div>`);
        }
    }

    if (rows.length === 0) return "";

    return `
<div class="editor-section">
  <div class="editor-section-title">File-Only Data</div>
  <div class="editor-field">
    <div class="editor-raw-tags">
      ${rows.join("")}
    </div>
  </div>
</div>`;
})()}

<div class="editor-section">
  <div class="editor-section-title">Notes</div>
  <div class="editor-field">
    <label class="sidebar-toggle" data-action="toggle-active" data-id="${song.id}">
      <input type="checkbox" ${song.is_active ? "checked" : ""} ${song.can_activate ? "" : "disabled"}>
      <span>Active (airplay)</span>
    </label>
  </div>
  <div class="editor-field">
    <label class="editor-label" for="ef-notes">Comments</label>
    <textarea class="editor-input editor-textarea" id="ef-notes" rows="3">${escapeHtml(song.notes ?? "")}</textarea>
  </div>
</div>
`;
}
