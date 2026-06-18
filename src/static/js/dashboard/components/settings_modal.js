/**
 * Settings modal — Tier-1 "General" settings editor.
 *
 * Pure functions (renderSettingsForm, collectPatch, renderWarnings) are DOM-only
 * and unit-tested. Orchestration (open/save/close) is the thin shell that talks
 * to GET/POST /api/v1/settings. The module is import-side-effect-free: every
 * element lookup is deferred into the orchestration functions so the pure
 * functions can be tested against an arbitrary container.
 *
 * Adding a new setting requires no changes here: renderSettingsForm generates
 * the form from the schema returned by GET /api/v1/settings.
 */

import { fetchSettings, saveSettings } from "../api.js";
import { createModalLifecycle } from "./modal_lifecycle.js";

/**
 * Resolve a JSON Schema property into a flat field descriptor the form can
 * render. Handles the pydantic shapes: plain typed properties (boolean /
 * integer / string) and enum fields, which pydantic emits as a $ref into
 * $defs. Adding a new setting to the Settings model needs no change here.
 */
function describeField(key, prop, schema) {
    const label = prop.title || key;
    if (prop.$ref) {
        const def = (schema.$defs || {})[prop.$ref.split("/").pop()];
        if (def && Array.isArray(def.enum)) {
            return { key, label, kind: "select", options: def.enum };
        }
    }
    if (prop.type === "boolean") return { key, label, kind: "bool" };
    if (prop.type === "integer" || prop.type === "number")
        return { key, label, kind: "number" };
    return { key, label, kind: "text" };
}

function buildControl(field, settings) {
    if (field.kind === "bool") {
        const box = document.createElement("input");
        box.type = "checkbox";
        box.id = `set-${field.key}`;
        box.dataset.key = field.key;
        box.dataset.kind = field.kind;
        box.checked = Boolean(settings[field.key]);
        return box;
    }
    if (field.kind === "select") {
        const select = document.createElement("select");
        select.id = `set-${field.key}`;
        select.dataset.key = field.key;
        select.dataset.kind = field.kind;
        select.className = "link-modal-input";
        for (const opt of field.options || []) {
            const o = document.createElement("option");
            o.value = opt;
            o.textContent = opt;
            select.appendChild(o);
        }
        select.value = settings[field.key];
        return select;
    }
    const input = document.createElement("input");
    input.type = field.kind === "number" ? "number" : "text";
    input.id = `set-${field.key}`;
    input.dataset.key = field.key;
    input.dataset.kind = field.kind;
    input.className = "link-modal-input";
    input.value = settings[field.key] ?? "";
    return input;
}

function fieldRow(labelText, control) {
    const row = document.createElement("div");
    row.className = "settings-row";
    const label = document.createElement("label");
    label.textContent = labelText;
    if (control.id) label.htmlFor = control.id;
    row.appendChild(label);
    row.appendChild(control);
    return row;
}

export function renderSettingsForm(container, settings, schema) {
    container.innerHTML = "";
    const properties = (schema && schema.properties) || {};
    for (const [key, prop] of Object.entries(properties)) {
        const field = describeField(key, prop, schema);
        const control = buildControl(field, settings);
        container.appendChild(fieldRow(field.label, control));
    }
}

export function collectPatch(container, original) {
    const patch = {};
    for (const el of container.querySelectorAll("[data-key]")) {
        const key = el.dataset.key;
        let value;
        if (el.dataset.kind === "bool") value = el.checked;
        else if (el.dataset.kind === "number") value = Number(el.value);
        else value = el.value;
        if (value !== original[key]) {
            patch[key] = value;
        }
    }
    return patch;
}

export function renderWarnings(container, warnings) {
    container.innerHTML = "";
    if (!warnings || warnings.length === 0) return null;
    const banner = document.createElement("div");
    banner.className = "ui-banner ui-banner-warning";
    banner.textContent = warnings
        .map((w) => w.error || w.kind || "Unknown warning")
        .join("; ");
    container.appendChild(banner);
    return banner;
}

// ─── Orchestration ────────────────────────────────────────────

let _modal = null;
let _ctx = null;
let _original = null;
let _schema = null;

function ensureModal(overlay) {
    if (!_modal) _modal = createModalLifecycle(overlay);
    return _modal;
}

export async function openSettingsModal(ctx) {
    _ctx = ctx;
    const overlay = document.getElementById("settings-modal");
    if (!overlay) return;
    const form = document.getElementById("settings-modal-form");
    const warn = document.getElementById("settings-modal-warning");
    const saveBtn = document.getElementById("settings-save-btn");

    let data;
    try {
        data = await fetchSettings();
    } catch (e) {
        ctx.showBanner(e.message || "Failed to load settings", "error");
        return;
    }

    _original = data.settings;
    _schema = data.schema;
    renderSettingsForm(form, _original, _schema);
    renderWarnings(warn, data.warnings || []);
    saveBtn.onclick = handleSave;
    ensureModal(overlay).open();
}

async function handleSave() {
    const form = document.getElementById("settings-modal-form");
    const warn = document.getElementById("settings-modal-warning");
    const patch = collectPatch(form, _original);
    if (Object.keys(patch).length === 0) {
        closeSettingsModal();
        return;
    }
    try {
        const data = await saveSettings(patch);
        _original = data.settings;
        _ctx.applySettings?.(data.settings);
        closeSettingsModal();
        _ctx.showBanner("Settings saved", "success");
    } catch (e) {
        renderWarnings(warn, [
            { kind: "save_error", error: e.message || "Failed to save settings" },
        ]);
    }
}

export function closeSettingsModal() {
    const overlay = document.getElementById("settings-modal");
    if (overlay) ensureModal(overlay).close();
}
