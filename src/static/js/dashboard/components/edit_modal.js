/**
 * Generic edit modal — rename a record, optional category field, optional flat children list.
 *
 * Usage:
 *   openEditModal({
 *     title: "Edit Publisher",
 *     name: "Sony Music",
 *     onRename: async (newName) => {},          // null = not renameable
 *     category: {                               // null = no category section
 *       label: "Category",
 *       value: "major",
 *       editable: true,
 *       onSave: async (val) => {},
 *     },
 *     children: {                               // null = no children section
 *       label: "Sub-publishers",
 *       items: [{ id, label }],
 *       onSearch: async (q) => [{ id, label }],
 *       onAdd: async (opt) => {},               // opt = { id|null, label, rawInput? }
 *       onRemove: async (item) => {},
 *       createLabel: (q) => `Add "${q}"`,
 *     },
 *   });
 */

const overlay   = document.getElementById("edit-modal");
const titleEl   = document.getElementById("edit-modal-title");
const bodyEl    = document.getElementById("edit-modal-body");

let _config = null;
let _suppressNextOverlayClick = false;
let _parentSnapshot = null; // saved state when drilling into a child edit
let _navigating = false;   // true while swapping modal content — suppress blur commits

// ─── Children sub-section state ───────────────────────────────────────────────
let _childItems = [];
let _childDebounce = null;
let _childDropdownItems = [];
let _childDropdownIndex = -1;
let _childInput = null;
let _childDropdown = null;
let _childItemsEl = null;

// ─── Render ───────────────────────────────────────────────────────────────────

function renderBody() {
    const sections = [];

    // Rename field
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
        const { label, value, editable } = _config.category;
        if (editable) {
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

    // Children section
    if (_config.children) {
        sections.push(`
            <div class="edit-modal-section-title">${escapeHtml(_config.children.label)}</div>
            <div id="edit-modal-child-items" class="link-modal-items"></div>
            <div class="link-modal-add">
                <input type="text" id="edit-modal-child-input" class="link-modal-input"
                    placeholder="Type to search or add..." autocomplete="off">
                <div id="edit-modal-child-dropdown" class="link-modal-dropdown" style="display:none"></div>
            </div>
        `);
    }

    bodyEl.innerHTML = sections.join("");
    attachHandlers();
}

function attachHandlers() {
    // Rename input — save on blur or Enter
    const nameInput = bodyEl.querySelector("#edit-modal-name-input");
    if (nameInput) {
        nameInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); commitRename(nameInput); }
            if (e.key === "Escape") { e.stopPropagation(); closeEditModal(); }
        });
        nameInput.addEventListener("blur", () => { if (!_navigating) commitRename(nameInput); });
    }

    // Category input — save on blur or Enter
    const catInput = bodyEl.querySelector("#edit-modal-category-input");
    if (catInput) {
        catInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); commitCategory(catInput); }
        });
        catInput.addEventListener("blur", () => commitCategory(catInput));
    }

    // Children section
    if (_config.children) {
        _childItems = _config.children.items;
        _childItemsEl = bodyEl.querySelector("#edit-modal-child-items");
        _childInput = bodyEl.querySelector("#edit-modal-child-input");
        _childDropdown = bodyEl.querySelector("#edit-modal-child-dropdown");

        renderChildItems();

        _childInput.addEventListener("input", () => {
            clearTimeout(_childDebounce);
            const q = _childInput.value.trim();
            if (!q) { _childDropdown.style.display = "none"; return; }
            _childDebounce = setTimeout(() => runChildSearch(q), 200);
        });

        _childInput.addEventListener("keydown", (e) => {
            if (e.key === "ArrowDown") {
                e.preventDefault();
                _childDropdownIndex = Math.min(_childDropdownIndex + 1, _childDropdownItems.length - 1);
                updateChildDropdownHighlight();
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                _childDropdownIndex = Math.max(_childDropdownIndex - 1, 0);
                updateChildDropdownHighlight();
            } else if (e.key === "Enter") {
                e.preventDefault();
                if (_childDropdownIndex >= 0) selectChildOption(_childDropdownIndex);
                else if (_childDropdownItems.length === 1) selectChildOption(0);
            } else if (e.key === "Escape") {
                e.stopPropagation();
                closeEditModal();
            }
        });

        _childInput.addEventListener("blur", () => {
            setTimeout(() => { _childDropdown.style.display = "none"; }, 150);
        });
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
        if (_parentSnapshot) { closeEditModal(); return; }
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
    } catch (err) {
        showError(`Save failed: ${err.message}`);
        input.value = _config.category.value;
        _lastCommittedCategory = _config.category.value;
    } finally {
        input.disabled = false;
    }
}

// ─── Children ─────────────────────────────────────────────────────────────────

function renderChildItems() {
    if (!_childItems.length) {
        _childItemsEl.innerHTML = '<span class="link-modal-empty">None linked</span>';
        return;
    }
    _childItemsEl.innerHTML = _childItems.map((item) => `
        <span class="link-chip">
            <button class="link-chip-label" data-edit-child-id="${item.id}">${escapeHtml(item.label)}</button>
            <button class="link-chip-remove" data-remove-child-id="${item.id}" title="Remove">✕</button>
        </span>
    `).join("");

    _childItemsEl.querySelectorAll("[data-edit-child-id]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const id = btn.dataset.editChildId;
            const item = _childItems.find(i => String(i.id) === String(id));
            if (!item) return;
            openChildEdit(item);
        });
    });

    _childItemsEl.querySelectorAll(".link-chip-remove").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.removeChildId;
            const item = _childItems.find(i => String(i.id) === String(id));
            if (!item) return;
            btn.disabled = true;
            try {
                await _config.children.onRemove(item);
                const idx = _childItems.findIndex(i => String(i.id) === String(id));
                if (idx >= 0) _childItems.splice(idx, 1);
                renderChildItems();
            } catch (err) {
                btn.disabled = false;
                showError(`Remove failed: ${err.message}`);
            }
        });
    });
}

async function runChildSearch(q) {
    const results = await _config.children.onSearch(q);
    const linkedIds = new Set(_childItems.map(i => String(i.id)));
    const options = results
        .filter(r => !linkedIds.has(String(r.id)))
        .map(r => ({ id: r.id, label: r.label }));
    const exactMatch = results.some(r => r.label.toLowerCase() === q.toLowerCase());
    if (!exactMatch) {
        options.unshift({ id: null, label: _config.children.createLabel(q), isCreate: true, rawInput: q });
    }
    renderChildDropdown(options);
}

function renderChildDropdown(options) {
    _childDropdownItems = options;
    _childDropdownIndex = -1;

    if (!options.length) { _childDropdown.style.display = "none"; return; }

    _childDropdown.innerHTML = options.map((opt, i) => `
        <div class="link-dropdown-item ${opt.isCreate ? "link-dropdown-create" : ""}" data-index="${i}">
            ${opt.isCreate ? "✦ " : ""}${escapeHtml(opt.label)}
        </div>
    `).join("");

    _childDropdown.querySelectorAll(".link-dropdown-item").forEach((el) => {
        el.addEventListener("mousedown", (e) => {
            e.preventDefault();
            e.stopPropagation();
            selectChildOption(Number(el.dataset.index));
        });
    });

    _childDropdown.style.display = "block";
    updateChildDropdownHighlight();
}

function updateChildDropdownHighlight() {
    _childDropdown.querySelectorAll(".link-dropdown-item").forEach((el, i) => {
        el.classList.toggle("link-dropdown-item--active", i === _childDropdownIndex);
    });
}

async function selectChildOption(index) {
    const opt = _childDropdownItems[index];
    if (!opt) return;
    _childInput.value = "";
    _childDropdown.style.display = "none";
    _childDropdownItems = [];
    _childDropdownIndex = -1;
    _childInput.disabled = true;
    _suppressNextOverlayClick = true;
    try {
        await _config.children.onAdd(opt);
        if (_config) renderChildItems();
    } catch (err) {
        if (_config) showError(`Add failed: ${err.message}`);
    } finally {
        if (_childInput && _config) {
            _childInput.disabled = false;
            _childInput.focus();
        }
    }
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

function openChildEdit(item) {
    _suppressNextOverlayClick = true;
    _navigating = true;
    // Save full parent state
    _parentSnapshot = {
        config: _config,
        childItems: _childItems,
        lastCommittedName: _lastCommittedName,
        lastCommittedCategory: _lastCommittedCategory,
    };

    const childConfig = {
        title: `Edit: ${item.label}`,
        name: item.label,
        onRename: async (newName) => {
            await _parentSnapshot.config.children.onRenameChild(item, newName);
            item.label = newName; // update the live item in parent's array
        },
        onClose: null, // closing returns to parent, not refreshActiveDetail
        category: null,
        children: null,
    };

    openEditModal(childConfig);
    _navigating = false;
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
    _childItems = [];
    _childDropdownItems = [];
    _childDropdownIndex = -1;
    _childInput = null;
    _childDropdown = null;
    _childItemsEl = null;

    titleEl.textContent = config.title;
    renderBody();
    overlay.style.display = "flex";

    // Focus name input if present
    const nameInput = bodyEl.querySelector("#edit-modal-name-input");
    if (nameInput) {
        nameInput.focus();
        nameInput.select();
    }
}

export function closeEditModal() {
    const onClose = _config && _config.onClose;

    if (_parentSnapshot) {
        // Restore parent modal instead of fully closing
        _navigating = true;
        const snap = _parentSnapshot;
        _parentSnapshot = null;
        openEditModal(snap.config, snap.config._triggerEl);
        _navigating = false;
        return;
    }

    overlay.style.display = "none";
    _config = null;
    bodyEl.innerHTML = "";
    if (onClose) onClose();
}

// Close on overlay click outside modal box
overlay.addEventListener("click", (e) => {
    if (_suppressNextOverlayClick) { _suppressNextOverlayClick = false; return; }
    if (!overlay.querySelector(".link-modal").contains(e.target)) closeEditModal();
});
