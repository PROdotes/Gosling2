import { wasMousedownInside } from "./utils.js";

/**
 * Generic edit modal — rename a record, optional category field, optional flat children list.
 *
 * Usage:
 *   openEditModal({
 *     title: "Edit Publisher",
 *     name: "Sony Music",
 *     onRename: async (newName) => {},          // null = not renameable
 *     toggle: {                                 // null = no toggle
 *       value: "person",                        // current value
 *       options: ["person", "group"],
 *       onSave: async (val) => {},
 *       disabledReason: "Remove members first", // optional tooltip when disabled
 *     },
 *     category: {                               // null = no category section
 *       label: "Category",
 *       value: "major",
 *       editable: true,
 *       onSave: async (val) => {},
 *       onSearch: async (q) => ["Genre", "Mood"],  // optional — renders search dropdown instead of plain input
 *     },
 *     children: {                               // null = no children section
 *       label: "Sub-publishers",
 *       items: [{ id, label }],
 *       onSearch: async (q) => [{ id, label }],
 *       onAdd: async (opt) => {},               // opt = { id|null, label, rawInput? }
 *       onRemove: async (item) => {},
 *       createLabel: (q) => `Add "${q}"`,
 *     },
 *     secondChildren: { ... },                  // null = no second children section (same shape as children)
 *   });
 */

const overlay = document.getElementById("edit-modal");
const titleEl = document.getElementById("edit-modal-title");
const bodyEl = document.getElementById("edit-modal-body");

let _config = null;
let _parentSnapshot = null; // saved state when drilling into a child edit
let _isSelecting = false;

// ─── Children slot state ──────────────────────────────────────────────────────
// Each slot is keyed by config key ("children" | "secondChildren") and holds
// { items, debounce, dropdownItems, dropdownIndex, inputEl, dropdownEl, itemsEl }
const _slots = {};

// ─── Category dropdown state ──────────────────────────────────────────────────
let _catDebounce = null;
let _catDropdownItems = [];
let _catDropdownIndex = -1;
let _catInput = null;
let _catDropdown = null;

// ─── Children slot helpers ────────────────────────────────────────────────────

function createSlot(key) {
    const slot = {
        key,
        items: [],
        debounce: null,
        dropdownItems: [],
        dropdownIndex: -1,
        inputEl: null,
        dropdownEl: null,
        itemsEl: null,
    };
    _slots[key] = slot;
    return slot;
}

function getSlotConfig(key) {
    return _config[key];
}

// DOM id helpers — "children" → "child", "secondChildren" → "child2"
const _domId = { children: "child", secondChildren: "child2" };
const _dataAttr = { children: "editChildId", secondChildren: "editChild2Id" };
const _removeAttr = {
    children: "removeChildId",
    secondChildren: "removeChild2Id",
};

function renderSlotItems(slot) {
    const cfg = getSlotConfig(slot.key);
    const editAttr = _dataAttr[slot.key];
    const removeAttr = _removeAttr[slot.key];

    if (!slot.items.length) {
        slot.itemsEl.innerHTML =
            '<span class="link-modal-empty">None linked</span>';
        return;
    }
    slot.itemsEl.innerHTML = slot.items
        .map(
            (item) => `
        <span class="link-chip">
            <button class="link-chip-label" data-${camelToData(editAttr)}="${item.id}">${escapeHtml(item.label)}</button>
            ${cfg.onRemove ? `<button class="link-chip-remove" data-${camelToData(removeAttr)}="${item.id}" title="Remove">✕</button>` : ""}
        </span>
    `,
        )
        .join("");

    slot.itemsEl
        .querySelectorAll(`[data-${camelToData(editAttr)}]`)
        .forEach((btn) => {
            btn.addEventListener("click", () => {
                const id = btn.dataset[editAttr];
                const item = slot.items.find(
                    (i) => String(i.id) === String(id),
                );
                if (item) openChildEdit(item, slot.key);
            });
        });

    slot.itemsEl.querySelectorAll(".link-chip-remove").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset[removeAttr];
            const item = slot.items.find((i) => String(i.id) === String(id));
            if (!item) return;
            btn.disabled = true;
            try {
                await cfg.onRemove(item);
                const idx = slot.items.findIndex(
                    (i) => String(i.id) === String(id),
                );
                if (idx >= 0) slot.items.splice(idx, 1);
                renderSlotItems(slot);
            } catch (err) {
                btn.disabled = false;
                showError(`Remove failed: ${err.message}`);
            }
        });
    });
}

async function runSlotSearch(slot, q) {
    const cfg = getSlotConfig(slot.key);
    const results = await cfg.onSearch(q);
    const linkedIds = new Set(slot.items.map((i) => String(i.id)));
    const options = results
        .filter((r) => !linkedIds.has(String(r.id)))
        .map((r) => ({ id: r.id, label: r.label }));
    const exactMatch = results.some(
        (r) => r.label.toLowerCase() === q.toLowerCase(),
    );
    if (!exactMatch && cfg.createLabel) {
        options.unshift({
            id: null,
            label: cfg.createLabel(q),
            isCreate: true,
            rawInput: q,
        });
    }
    renderSlotDropdown(slot, options);
}

function renderSlotDropdown(slot, options) {
    slot.dropdownItems = options;
    slot.dropdownIndex = options.length > 0 ? 0 : -1;

    if (!options.length) {
        slot.dropdownEl.style.display = "none";
        return;
    }

    slot.dropdownEl.innerHTML = options
        .map(
            (opt, i) => `
        <div class="link-dropdown-item ${opt.isCreate ? "link-dropdown-create" : ""}" data-index="${i}">
            ${opt.isCreate ? "✦ " : ""}${escapeHtml(opt.label)}
        </div>
    `,
        )
        .join("");

    slot.dropdownEl.querySelectorAll(".link-dropdown-item").forEach((el) => {
        el.addEventListener("mousedown", (e) => {
            e.preventDefault();
            e.stopPropagation();
            selectSlotOption(slot, Number(el.dataset.index));
        });
    });

    slot.dropdownEl.style.display = "block";
    updateSlotDropdownHighlight(slot);
}

function updateSlotDropdownHighlight(slot) {
    slot.dropdownEl.querySelectorAll(".link-dropdown-item").forEach((el, i) => {
        el.classList.toggle(
            "link-dropdown-item--active",
            i === slot.dropdownIndex,
        );
    });
}

async function selectSlotOption(slot, index) {
    const opt = slot.dropdownItems[index];
    if (!opt) return;
    const cfg = getSlotConfig(slot.key);

    _isSelecting = true;
    slot.inputEl.value = "";
    slot.dropdownEl.style.display = "none";
    slot.dropdownItems = [];
    slot.dropdownIndex = -1;
    slot.inputEl.disabled = true;

    try {
        const result = await cfg.onAdd(opt);
        if (_config) {
            if (result) slot.items.push(result);
            renderSlotItems(slot);
        }
    } catch (err) {
        if (_config) showError(`Add failed: ${err.message}`);
    } finally {
        if (slot.inputEl && _config) {
            slot.inputEl.disabled = false;
            slot.inputEl.focus();
        }
        setTimeout(() => {
            _isSelecting = false;
        }, 150);
    }
}

function attachSlotHandlers(slot) {
    slot.inputEl.addEventListener("input", () => {
        clearTimeout(slot.debounce);
        const q = slot.inputEl.value.trim();
        if (!q) {
            slot.dropdownEl.style.display = "none";
            return;
        }
        slot.debounce = setTimeout(() => runSlotSearch(slot, q), 200);
    });

    slot.inputEl.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown") {
            e.preventDefault();
            slot.dropdownIndex = Math.min(
                slot.dropdownIndex + 1,
                slot.dropdownItems.length - 1,
            );
            updateSlotDropdownHighlight(slot);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            slot.dropdownIndex = Math.max(slot.dropdownIndex - 1, 0);
            updateSlotDropdownHighlight(slot);
        } else if (e.key === "Enter") {
            e.preventDefault();
            const q = slot.inputEl.value.trim();
            if (slot.dropdownIndex >= 0)
                selectSlotOption(slot, slot.dropdownIndex);
            else if (slot.dropdownItems.length === 1)
                selectSlotOption(slot, 0);
            else if (!q)
                closeEditModal();
        }
    });

    slot.inputEl.addEventListener("blur", () => {
        setTimeout(() => {
            slot.dropdownEl.style.display = "none";
        }, 150);
    });
}

// Convert camelCase data attribute name to kebab-case for HTML
function camelToData(str) {
    return str.replace(/([A-Z])/g, (m) => `-${m.toLowerCase()}`);
}

// ─── Render ───────────────────────────────────────────────────────────────────

function renderBody() {
    const sections = [];

    // Name field
    if (_config.onRename) {
        sections.push(`
            <div class="edit-modal-field" id="edit-modal-rename-field">
                <label for="edit-modal-name-input">Name</label>
                <input type="text" id="edit-modal-name-input" class="link-modal-input"
                    value="${escapeHtml(_config.name)}" autocomplete="off">
            </div>
        `);
    }

    // Category field
    if (_config.category) {
        const { label, value, editable, onSearch } = _config.category;
        if (editable && onSearch) {
            sections.push(`
                <div class="edit-modal-field" id="edit-modal-category-field">
                    <label for="edit-modal-category-input">${escapeHtml(label)}</label>
                    <div class="link-modal-add" style="position:relative">
                        <input type="text" id="edit-modal-category-input" class="link-modal-input"
                            value="${escapeHtml(value || "")}" autocomplete="off">
                        <div id="edit-modal-category-dropdown" class="link-modal-dropdown" style="display:none"></div>
                    </div>
                </div>
            `);
        } else if (editable) {
            sections.push(`
                <div class="edit-modal-field" id="edit-modal-category-field">
                    <label for="edit-modal-category-input">${escapeHtml(label)}</label>
                    <input type="text" id="edit-modal-category-input" class="link-modal-input"
                        value="${escapeHtml(value || "")}" autocomplete="off">
                </div>
            `);
        } else {
            sections.push(`
                <div class="edit-modal-field">
                    <label>${escapeHtml(label)}</label>
                    <span style="font-size:0.88rem; color:var(--text-secondary)">${escapeHtml(value || "-")}</span>
                </div>
            `);
        }
    }

    // Toggle field (e.g. person/group)
    if (_config.toggle) {
        const { value, options, disabledReason } = _config.toggle;
        const disabled = !!disabledReason;
        sections.push(`
            <div class="edit-modal-field">
                <label>Type</label>
                <div class="edit-modal-toggle" ${disabled ? `title="${escapeHtml(disabledReason)}"` : ""}>
                    ${options
                        .map(
                            (opt) => `
                        <button class="edit-modal-toggle-btn ${opt === value ? "active" : ""} ${disabled && opt !== value ? "disabled" : ""}"
                            data-toggle-value="${escapeHtml(opt)}"
                            ${disabled && opt !== value ? "disabled" : ""}>
                            ${escapeHtml(opt)}
                        </button>
                    `,
                        )
                        .join("")}
                </div>
            </div>
        `);
    }

    // Children sections (generic — "children" then "secondChildren")
    for (const key of ["children", "secondChildren"]) {
        if (_config[key]) {
            const domKey = _domId[key];
            sections.push(`
                <div class="edit-modal-section-title">${escapeHtml(_config[key].label)}</div>
                <div id="edit-modal-${domKey}-items" class="link-modal-items"></div>
                <div class="link-modal-add">
                    <input type="text" id="edit-modal-${domKey}-input" class="link-modal-input"
                        placeholder="Type to search or add..." autocomplete="off">
                    <div id="edit-modal-${domKey}-dropdown" class="link-modal-dropdown" style="display:none"></div>
                </div>
            `);
        }
    }

    bodyEl.innerHTML = sections.join("");
    attachHandlers();
}

function attachHandlers() {
    // Rename input — save on Enter
    const nameInput = bodyEl.querySelector("#edit-modal-name-input");
    if (nameInput) {
        nameInput.addEventListener("input", () => {
            const field = nameInput.closest(".edit-modal-field");
            field.classList.toggle(
                "edit-modal-field--dirty",
                nameInput.value.trim() !== _lastCommittedName,
            );
        });
        nameInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                if (!nameInput.value.trim()) closeEditModal();
                else commitRename(nameInput);
            }
        });
    }

    // Category input — plain (save on Enter) or search dropdown
    const catInput = bodyEl.querySelector("#edit-modal-category-input");
    if (catInput) {
        _catInput = catInput;
        const hasSearch = !!_config.category?.onSearch;

        catInput.addEventListener("input", () => {
            const field = catInput.closest(".edit-modal-field");
            field.classList.toggle(
                "edit-modal-field--dirty",
                catInput.value.trim() !== _lastCommittedCategory,
            );

            if (hasSearch) {
                clearTimeout(_catDebounce);
                const q = catInput.value.trim();
                if (!q) {
                    hideCatDropdown();
                    return;
                }
                _catDebounce = setTimeout(() => runCatSearch(q), 200);
            }
        });

        catInput.addEventListener("keydown", (e) => {
            if (hasSearch) {
                if (e.key === "ArrowDown") {
                    e.preventDefault();
                    _catDropdownIndex = Math.min(
                        _catDropdownIndex + 1,
                        _catDropdownItems.length - 1,
                    );
                    updateCatDropdownHighlight();
                } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    _catDropdownIndex = Math.max(_catDropdownIndex - 1, 0);
                    updateCatDropdownHighlight();
                } else if (e.key === "Enter") {
                    e.preventDefault();
                    if (_catDropdownIndex >= 0)
                        selectCatOption(_catDropdownIndex);
                    else {
                        const q = catInput.value.trim();
                        if (!q) closeEditModal();
                        else commitCategory(catInput);
                    }
                }
            } else {
                if (e.key === "Enter") {
                    e.preventDefault();
                    if (!catInput.value.trim()) closeEditModal();
                    else commitCategory(catInput);
                }
            }
        });

        catInput.addEventListener("blur", () => {
            setTimeout(() => hideCatDropdown(), 150);
        });

        if (hasSearch) {
            _catDropdown = bodyEl.querySelector(
                "#edit-modal-category-dropdown",
            );
        }
    }

    // Toggle buttons
    if (_config.toggle) {
        bodyEl.querySelectorAll("[data-toggle-value]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const newVal = btn.dataset.toggleValue;
                if (newVal === _config.toggle.value || btn.disabled) return;
                btn.disabled = true;
                try {
                    await _config.toggle.onSave(newVal);
                    _config.toggle.value = newVal;
                    bodyEl
                        .querySelectorAll("[data-toggle-value]")
                        .forEach((b) => {
                            b.classList.toggle(
                                "active",
                                b.dataset.toggleValue === newVal,
                            );
                        });
                } catch (err) {
                    showError(`Save failed: ${err.message}`);
                } finally {
                    btn.disabled = false;
                }
            });
        });
    }

    // Children slots
    for (const key of ["children", "secondChildren"]) {
        if (_config[key]) {
            const domKey = _domId[key];
            const slot = createSlot(key);
            slot.items = [..._config[key].items];
            slot.itemsEl = bodyEl.querySelector(`#edit-modal-${domKey}-items`);
            slot.inputEl = bodyEl.querySelector(`#edit-modal-${domKey}-input`);
            slot.dropdownEl = bodyEl.querySelector(
                `#edit-modal-${domKey}-dropdown`,
            );
            renderSlotItems(slot);
            attachSlotHandlers(slot);
        }
    }
}

// ─── Rename ───────────────────────────────────────────────────────────────────

let _lastCommittedName = null;

async function commitRename(input) {
    const newName = input.value.trim();
    if (!newName || newName === _lastCommittedName) return;
    _lastCommittedName = newName;
    input.disabled = true;
    try {
        await _config.onRename(newName);
        _config.name = newName;
        if (_config._triggerEl) _config._triggerEl.textContent = newName;
        input
            .closest(".edit-modal-field")
            ?.classList.remove("edit-modal-field--dirty");
        if (_parentSnapshot) {
            closeEditModal();
            return;
        }
    } catch (err) {
        showError(`Rename failed: ${err.message}`);
        input.value = _config.name;
        _lastCommittedName = _config.name;
    } finally {
        input.disabled = false;
    }
}

// ─── Category ─────────────────────────────────────────────────────────────────

let _lastCommittedCategory = null;

async function commitCategory(input) {
    const newVal = input.value.trim();
    if (newVal === _lastCommittedCategory) return;
    _lastCommittedCategory = newVal;
    input.disabled = true;
    try {
        await _config.category.onSave(newVal);
        _config.category.value = newVal;
        input
            .closest(".edit-modal-field")
            ?.classList.remove("edit-modal-field--dirty");
    } catch (err) {
        showError(`Save failed: ${err.message}`);
        input.value = _config.category.value;
        _lastCommittedCategory = _config.category.value;
    } finally {
        input.disabled = false;
    }
}

async function runCatSearch(q) {
    const results = await _config.category.onSearch(q);
    const filtered = results.filter((c) =>
        c.toLowerCase().includes(q.toLowerCase()),
    );
    const exactMatch = filtered.some(
        (c) => c.toLowerCase() === q.toLowerCase(),
    );
    const options = filtered.map((c) => ({ label: c }));
    if (!exactMatch) {
        options.unshift({ label: `Use "${q}"`, rawInput: q, isCreate: true });
    }
    renderCatDropdown(options);
}

function renderCatDropdown(options) {
    _catDropdownItems = options;
    _catDropdownIndex = options.length > 0 ? 0 : -1;

    if (!options.length) {
        hideCatDropdown();
        return;
    }

    _catDropdown.innerHTML = options
        .map(
            (opt, i) => `
        <div class="link-dropdown-item ${opt.isCreate ? "link-dropdown-create" : ""}" data-index="${i}">
            ${opt.isCreate ? "✦ " : ""}${escapeHtml(opt.label)}
        </div>
    `,
        )
        .join("");

    _catDropdown.querySelectorAll(".link-dropdown-item").forEach((el) => {
        el.addEventListener("mousedown", (e) => {
            e.preventDefault();
            e.stopPropagation();
            selectCatOption(Number(el.dataset.index));
        });
    });

    _catDropdown.style.display = "block";
    updateCatDropdownHighlight();
}

function updateCatDropdownHighlight() {
    _catDropdown.querySelectorAll(".link-dropdown-item").forEach((el, i) => {
        el.classList.toggle(
            "link-dropdown-item--active",
            i === _catDropdownIndex,
        );
    });
}

function selectCatOption(index) {
    const opt = _catDropdownItems[index];
    if (!opt) return;

    _isSelecting = true;
    const value = opt.rawInput || opt.label;
    _catInput.value = value;

    hideCatDropdown();
    const field = _catInput.closest(".edit-modal-field");
    field.classList.toggle(
        "edit-modal-field--dirty",
        value !== _lastCommittedCategory,
    );
    setTimeout(() => {
        _isSelecting = false;
    }, 150);
}

function hideCatDropdown() {
    if (_catDropdown) _catDropdown.style.display = "none";
    _catDropdownItems = [];
    _catDropdownIndex = -1;
}

// ─── Error ────────────────────────────────────────────────────────────────────

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

// ─── Child edit (drill one level, no further) ────────────────────────────────

function openChildEdit(item, slotKey) {
    _parentSnapshot = {
        config: _config,
        lastCommittedName: _lastCommittedName,
        lastCommittedCategory: _lastCommittedCategory,
    };

    openEditModal({
        title: `Edit: ${item.label}`,
        name: item.label,
        onRename: async (newName) => {
            await _parentSnapshot.config[slotKey].onRenameChild(item, newName);
            item.label = newName;
        },
        onClose: null,
        category: null,
        children: null,
    });
}

// ─── Utility ──────────────────────────────────────────────────────────────────

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// ─── Public API ───────────────────────────────────────────────────────────────

export function openEditModal(config, triggerEl = null) {
    _config = { ...config, _triggerEl: triggerEl };
    _lastCommittedName = config.name;
    _lastCommittedCategory = config.category ? config.category.value : null;

    // Clear all slot state
    for (const key of Object.keys(_slots)) delete _slots[key];

    _catDropdownItems = [];
    _catDropdownIndex = -1;
    _catInput = null;
    _catDropdown = null;

    titleEl.textContent = config.title;
    renderBody();
    overlay.style.display = "flex";

    const nameInput = bodyEl.querySelector("#edit-modal-name-input");
    if (nameInput) {
        nameInput.focus();
        nameInput.select();
    }
}

export function closeEditModal() {
    const onClose = _config && _config.onClose;

    if (_parentSnapshot) {
        const snap = _parentSnapshot;
        _parentSnapshot = null;
        openEditModal(snap.config, snap.config._triggerEl);
        return;
    }

    overlay.style.display = "none";
    _config = null;
    bodyEl.innerHTML = "";
    if (onClose) onClose();
}

// Close on overlay click outside modal box
overlay.addEventListener("click", (e) => {
    if (_isSelecting) return;
    if (wasMousedownInside(overlay.querySelector(".link-modal"))) return;
    if (e.target === overlay) closeEditModal();
});

// Escape from anywhere closes it
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.style.display === "flex") {
        e.stopImmediatePropagation();
        closeEditModal();
    }
});
