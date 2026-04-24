import { wasMousedownInside } from "./utils.js";
import { createModalLifecycle } from "./modal_lifecycle.js";
import { createAutocomplete } from "./autocomplete.js";

/**
 * Generic edit modal — form fields rendered from config schema.
 *
 * The modal doesn't know about "categories", "children", "toggles" — it just
 * renders fields based on their type.
 *
 * Usage:
 *   openEditModal({
 *     title: "Edit Publisher",
 *     triggerEl: chipElement, // optional — updates chip label after rename
 *     fields: {
 *       name: { type: "text", value: "Sony", onSave: async (val) => {} },
 *       type: { type: "toggle", value: "person", options: ["person", "group"], onSave, disabledReason: "..." },
 *       category: { type: "search", value: "major", onSearch: (q) => [], onSave },
 *       members: { type: "chipList", items: [{id, label}], onSearch, onAdd, onRemove, onRename: (item, newName) => {} },
 *       subItems: { type: "chipList", items: [], ... },
 *     },
 *     onClose: () => {},
 *   });
 */

const overlay = document.getElementById("edit-modal");
const titleEl = document.getElementById("edit-modal-title");
const bodyEl = document.getElementById("edit-modal-body");

let _fields = null;
let _triggerEl = null;
let _onClose = null;
let _autocompletes = {};
let modal;

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function camelToData(str) {
    return str.replace(/([A-Z])/g, (m) => `-${m.toLowerCase()}`);
}

// ─── Render fields ───────────────────────────────────────────────────────────

function renderFields() {
    const sections = [];

    for (const [key, field] of Object.entries(_fields)) {
        if (field.type === "text") {
            sections.push(renderTextField(key, field));
        } else if (field.type === "toggle") {
            sections.push(renderToggleField(key, field));
        } else if (field.type === "search") {
            sections.push(renderSearchField(key, field));
        } else if (field.type === "chipList") {
            sections.push(renderChipListField(key, field));
        }
    }

    bodyEl.innerHTML = sections.join("");
    attachFieldHandlers();
}

function renderTextField(key, field) {
    return `
        <div class="edit-modal-field" id="edit-field-${key}">
            <label>${escapeHtml(field.label || key)}</label>
            <input type="text" class="link-modal-input" data-field-key="${key}"
                value="${escapeHtml(field.value || "")}" autocomplete="off">
        </div>
    `;
}

function renderToggleField(key, field) {
    const { value, options = [], disabledReason } = field;
    const disabled = !!disabledReason;

    return `
        <div class="edit-modal-field" id="edit-field-${key}">
            <label>${escapeHtml(field.label || key)}</label>
            <div class="edit-modal-toggle" ${disabled ? `title="${escapeHtml(disabledReason)}"` : ""}>
                ${options.map((opt) => `
                    <button class="edit-modal-toggle-btn ${opt === value ? "active" : ""} ${disabled && opt !== value ? "disabled" : ""}"
                        data-toggle-value="${escapeHtml(opt)}" ${disabled && opt !== value ? "disabled" : ""}>
                        ${escapeHtml(opt)}
                    </button>
                `).join("")}
            </div>
        </div>
    `;
}

function renderSearchField(key, field) {
    const { value, editable = true, onSearch } = field;
    const fieldId = `edit-field-${key}`;

    if (editable && onSearch) {
        return `
            <div class="edit-modal-field" id="${fieldId}">
                <label>${escapeHtml(field.label || key)}</label>
                <div class="link-modal-add" style="position:relative">
                    <input type="text" class="link-modal-input" data-field-key="${key}"
                        value="${escapeHtml(value || "")}" autocomplete="off">
                    <div class="link-modal-dropdown" data-field-key="${key}" style="display:none"></div>
                </div>
            </div>
        `;
    }

    return `
        <div class="edit-modal-field" id="${fieldId}">
            <label>${escapeHtml(field.label || key)}</label>
            <input type="text" class="link-modal-input" data-field-key="${key}"
                value="${escapeHtml(value || "")}" ${!editable ? "readonly" : ""} autocomplete="off">
        </div>
    `;
}

function renderChipListField(key, field) {
    const { label, items = [] } = field;

    return `
        <div class="edit-modal-section-title">${escapeHtml(label || key)}</div>
        <div class="link-modal-items" data-field-key="${key}">
            ${items.length ? items.map((item) => `
                <span class="link-chip">
                    <button class="link-chip-label" data-chip-id="${item.id}">${escapeHtml(item.label)}</button>
                    <button class="link-chip-remove" data-chip-id="${item.id}" title="Remove">✕</button>
                </span>
            `).join("") : '<span class="link-modal-empty">None</span>'}
        </div>
        <div class="link-modal-add" style="position:relative">
            <input type="text" class="link-modal-input" data-field-key="${key}"
                placeholder="Type to search or add..." autocomplete="off">
            <div class="link-modal-dropdown" data-field-key="${key}" style="display:none"></div>
        </div>
    `;
}

// ─── Attach handlers ──────────────────────────────────────────────────

function attachFieldHandlers() {
    for (const [key, field] of Object.entries(_fields)) {
        if (field.type === "text") {
            attachTextHandler(key, field);
        } else if (field.type === "toggle") {
            attachToggleHandler(key, field);
        } else if (field.type === "search") {
            attachSearchHandler(key, field);
        } else if (field.type === "chipList") {
            attachChipListHandler(key, field);
        }
    }
}

function attachTextHandler(key, field) {
    const input = bodyEl.querySelector(`[data-field-key="${key}"]`);
    if (!input || !field.onSave) return;

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            commitText(key, input.value);
        }
    });
}

async function commitText(key, value) {
    const field = _fields[key];
    const input = bodyEl.querySelector(`[data-field-key="${key}"]`);
    if (!input || !field.onSave) return;

    const trimmed = value.trim();
    if (!trimmed) {
        closeEditModal();
        return;
    }
    if (trimmed === field.value) return;

    input.disabled = true;
    try {
        await field.onSave(trimmed);
        field.value = trimmed;
        if (key === "name" && _triggerEl) {
            _triggerEl.textContent = trimmed;
        }
    } catch (err) {
        showError(`Save failed: ${err.message}`);
        input.value = field.value;
    } finally {
        input.disabled = false;
    }
}

async function commitSearch(key, value) {
    const field = _fields[key];
    const input = bodyEl.querySelector(`[data-field-key="${key}"]`);
    if (!input || !field.onSave) return;

    const trimmed = value.trim();
    if (!trimmed || trimmed === field.value) {
        if (!trimmed) closeEditModal();
        return;
    }

    input.disabled = true;
    try {
        await field.onSave(trimmed);
        field.value = trimmed;
    } catch (err) {
        showError(`Save failed: ${err.message}`);
        input.value = field.value;
    } finally {
        input.disabled = false;
    }
}

function attachToggleHandler(key, field) {
    const container = bodyEl.querySelector(`[id="edit-field-${key}"] .edit-modal-toggle`);
    if (!container || !field.onSave) return;

    container.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const newVal = btn.dataset.toggleValue;
            if (newVal === field.value || btn.disabled) return;

            btn.disabled = true;
            try {
                await field.onSave(newVal);
                field.value = newVal;
                container.querySelectorAll("button").forEach((b) => {
                    b.classList.toggle("active", b.dataset.toggleValue === newVal);
                    b.disabled = (b.dataset.toggleValue !== newVal) && field.disabledReason;
                });
            } catch (err) {
                showError(`Save failed: ${err.message}`);
            } finally {
                btn.disabled = false;
            }
        });
    });
}

function attachSearchHandler(key, field) {
    const input = bodyEl.querySelector(`[data-field-key="${key}"]`);
    const dropdown = bodyEl.querySelector(`.link-modal-dropdown[data-field-key="${key}"]`);
    if (!input || !field.onSearch) return;

    // Enter key commits
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            commitSearch(key, input.value);
        }
    });

    const renderItem = (opt, i, isCreate) => {
        return `<div class="link-dropdown-item${isCreate ? " link-dropdown-create" : ""}" data-ac-index="${i}">${isCreate ? "✦ " : ""}${escapeHtml(opt.label)}</div>`;
    };

    const ac = createAutocomplete({
        inputEl: input,
        dropdownEl: dropdown,
        onSearch: async (q) => {
            const results = await field.onSearch(q);
            const exactMatch = results.some((r) => r.label.toLowerCase() === q.toLowerCase());
            const options = results.map((r) => ({ id: r.id, label: r.label }));
            if (!exactMatch && field.createLabel) {
                options.unshift({ id: null, label: field.createLabel(q), isCreate: true, rawInput: q });
            }
            return options;
        },
        onSelect: async (opt) => {
            await field.onSave(opt.rawInput || opt.label);
            field.value = opt.rawInput || opt.label;
            input.value = field.value;
        },
        renderItem,
        allowCreate: !!field.createLabel,
        getCreateLabel: field.createLabel,
        debounceMs: 200,
    });

    _autocompletes[key] = ac;
}

function attachChipButtons(key, field) {
    const itemsEl = bodyEl.querySelector(`.link-modal-items[data-field-key="${key}"]`);
    if (!itemsEl) return;

    itemsEl.querySelectorAll(".link-chip-remove").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.chipId;
            const item = field.items.find((i) => String(i.id) === String(id));
            if (!item || !field.onRemove) return;

            btn.disabled = true;
            try {
                await field.onRemove(item);
                field.items = field.items.filter((i) => String(i.id) !== String(id));
                refreshChipList(key);
            } catch (err) {
                btn.disabled = false;
                showError(`Remove failed: ${err.message}`);
            }
        });
    });

    itemsEl.querySelectorAll(".link-chip-label").forEach((btn) => {
        btn.addEventListener("click", () => {
            const id = btn.dataset.chipId;
            const item = field.items.find((i) => String(i.id) === String(id));
            if (item && field.onRename) {
                openChildEdit(item, key);
            }
        });
    });
}

function attachChipListHandler(key, field) {
    const input = bodyEl.querySelector(`.link-modal-add input[data-field-key="${key}"]`);
    const dropdown = bodyEl.querySelector(`.link-modal-add .link-modal-dropdown[data-field-key="${key}"]`);

    if (!input || !field.onSearch) return;

    attachChipButtons(key, field);

    // Chip input autocomplete
    const renderItem = (opt, i, isCreate) => {
        return `<div class="link-dropdown-item${isCreate ? " link-dropdown-create" : ""}" data-ac-index="${i}">${isCreate ? "✦ " : ""}${escapeHtml(opt.label)}</div>`;
    };

    const ac = createAutocomplete({
        inputEl: input,
        dropdownEl: dropdown,
        onSearch: async (q) => {
            const results = await field.onSearch(q);
            const linkedIds = new Set(field.items.map((i) => String(i.id)));
            const filtered = results.filter((r) => !linkedIds.has(String(r.id)));
            const options = filtered.map((r) => ({ id: r.id, label: r.label }));
            const exactMatch = results.some((r) => r.label.toLowerCase() === q.toLowerCase());
            if (!exactMatch && field.createLabel) {
                options.unshift({ id: null, label: field.createLabel(q), isCreate: true, rawInput: q });
            }
            return options;
        },
        onSelect: async (opt) => {
            const result = await field.onAdd(opt);
            if (result) field.items.push(result);
            refreshChipList(key);
        },
        renderItem,
        allowCreate: !!field.createLabel,
        getCreateLabel: field.createLabel,
        debounceMs: 200,
    });

    _autocompletes[key] = ac;
}

function refreshChipList(key) {
    const field = _fields[key];
    const itemsEl = bodyEl.querySelector(`.link-modal-items[data-field-key="${key}"]`);
    if (!itemsEl) return;

    if (!field.items.length) {
        itemsEl.innerHTML = '<span class="link-modal-empty">None</span>';
        return;
    }

    itemsEl.innerHTML = field.items.map((item) => `
        <span class="link-chip">
            <button class="link-chip-label" data-chip-id="${item.id}">${escapeHtml(item.label)}</button>
            <button class="link-chip-remove" data-chip-id="${item.id}" title="Remove">✕</button>
        </span>
    `).join("");

    // Re-attach chip button handlers only — autocomplete stays alive on its input
    attachChipButtons(key, field);
}

// ─── Child edit (drill one level) ────────────────────────────────────────

function openChildEdit(item, fieldKey) {
    const field = _fields[fieldKey];
    const parentConfig = {
        title: titleEl.textContent,
        fields: _fields,
        onClose: _onClose,
    };
    const parentTriggerEl = _triggerEl;

    openEditModal({
        title: `Edit: ${item.label}`,
        fields: {
            name: {
                type: "text",
                label: "Name",
                value: item.label,
                onSave: async (newName) => {
                    await field.onRename(item, newName);
                    item.label = newName;
                },
            },
        },
        onClose: () => {
            // Re-open parent modal, restoring all state
            openEditModal(parentConfig, parentTriggerEl);
        },
    });
}

// ─── Error handling ───────────────────────────────────────────────

function showError(msg) {
    let errEl = bodyEl.querySelector(".link-modal-error");
    if (!errEl) {
        errEl = document.createElement("div");
        errEl.className = "link-modal-error";
        bodyEl.prepend(errEl);
    }
    errEl.textContent = msg;
    setTimeout(() => errEl.remove(), 6000);
}

// ─── Modal lifecycle ────────────────────────────────────────────

modal = createModalLifecycle(overlay, {
    onOpen: (config, triggerEl) => {
        _fields = config.fields || {};
        _triggerEl = triggerEl || null;
        _onClose = config.onClose || null;
        _autocompletes = {};

        titleEl.textContent = config.title;
        renderFields();

        const firstInput = bodyEl.querySelector("input");
        if (firstInput) {
            firstInput.focus();
            firstInput.select();
        }
    },
    onClose: () => {
        const onClose = _onClose;
        for (const ac of Object.values(_autocompletes)) {
            ac.destroy();
        }
        _autocompletes = {};
        _fields = null;
        _triggerEl = null;
        _onClose = null;
        bodyEl.innerHTML = "";
        if (onClose) onClose();
    },
    overlayClickCheck: (e) => {
        const modalBox = overlay.querySelector(".link-modal");
        if (!modalBox) return false;
        if (wasMousedownInside(modalBox)) return false;
        return e.target === overlay;
    }
});

export function openEditModal(config, triggerEl = null) {
    modal.open(config, triggerEl);
}

export function closeEditModal() {
    modal.close();
}