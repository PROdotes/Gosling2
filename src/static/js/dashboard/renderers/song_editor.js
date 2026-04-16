/**
 * Song Editor V2 — static form renderer.
 * Renders into #editor-panel .editor-scroll from getCatalogSong data.
 * No interactivity in this phase — chips and inputs are read-only display.
 */

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

function renderChipField(label, chips, emptyLabel, canMiss = true) {
    const missing = canMiss && (!chips || chips.length === 0);
    return `
<div class="editor-field${missing ? " missing" : ""}">
  <label class="editor-label">${escapeHtml(label)}</label>
  <div class="editor-chip-row">${renderChips(chips, emptyLabel)}</div>
</div>`;
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
  ${REQUIRED_ROLES.map((role) => renderChipField(role, creditsByRole[role], `No ${role.toLowerCase()}s`)).join("")}
  ${renderChipField("Tags", tags, "No tags")}
  ${renderChipField("Publisher", publishers, "No publisher")}
  ${renderChipField("Album / Release", albums, "No album")}
</div>

<div class="editor-section">
  <div class="editor-section-title">Additional Data</div>
  ${OPTIONAL_ROLES.map((role) => renderChipField(role, creditsByRole[role], `No ${role.toLowerCase()}s`, false)).join("")}
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
