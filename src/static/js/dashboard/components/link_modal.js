import { wasMousedownInside } from "./utils.js";
import { createModalLifecycle } from "./modal_lifecycle.js";
import { createAutocomplete } from "./autocomplete.js";

/**
 * Generic link modal — type-to-search autocomplete with existing item chips.
 *
 * Usage:
 *   openLinkModal({
 *     title: "Publishers",
 *     items: [ { id, label } ],           // current links
 *     onSearch: async (q) => [...],       // returns [{ id, label }]
 *     onAdd: async (option) => {},        // option is { id|null, label }
 *     onRemove: async (item) => {},        // item is { id, label }
 *     createLabel: (q) => `Add "${q}"`,   // label for the create-new option
 *   });
 */

const overlay = document.getElementById("link-modal");
const titleEl = document.getElementById("link-modal-title");
const itemsEl = document.getElementById("link-modal-items");
const input = document.getElementById("link-modal-input");
const dropdown = document.getElementById("link-modal-dropdown");

let _config = null;
let _isSelecting = false;
let _ac = null;

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function renderItems() {
    if (!_config.items.length) {
        itemsEl.innerHTML = '<span class="link-modal-empty">None linked</span>';
        return;
    }
    itemsEl.innerHTML = _config.items
        .map(
            (item) => `
        <span class="link-chip">
            ${escapeHtml(item.label)}
            <button class="link-chip-remove" data-remove-id="${item.id}" title="Remove">✕</button>
        </span>
    `,
        )
        .join("");

    itemsEl.querySelectorAll(".link-chip-remove").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.removeId;
            const item = _config.items.find((i) => String(i.id) === String(id));
            if (!item) return;
            btn.disabled = true;
            try {
                await _config.onRemove(item);
                _config.items = _config.items.filter(
                    (i) => String(i.id) !== String(id),
                );
                renderItems();
            } catch (err) {
                btn.disabled = false;
                showError(`Remove failed: ${err.message}`);
            }
        });
    });
}

function renderItem(opt, i, isCreate) {
    return `<div class="link-dropdown-item${isCreate ? " link-dropdown-create" : ""}" data-ac-index="${i}">${isCreate ? "✦ " : ""}${escapeHtml(opt.label)}</div>`;
}

async function onSearchWrapper(q) {
    const raw = q.trim();
    if (!raw) return [];

    const results = await _config.onSearch(raw);

    // Filter out items already in the currentItems list
    const filteredResults = results.filter((r) => {
        const alreadyLinked = _config.items.some((linked) => {
            const idMatch = r.id != null && String(linked.id) === String(r.id);
            const labelMatch =
                linked.label.toLowerCase() === r.label.toLowerCase();
            return idMatch || labelMatch;
        });
        return !alreadyLinked;
    });

    const options = filteredResults.map((r) => ({ id: r.id, label: r.label }));

    // Add create-new option unless suppressed
    const exactMatch = results.some(
        (r) => r.label.toLowerCase() === raw.toLowerCase(),
    );
    const showCreate = _config.shouldCreate
        ? _config.shouldCreate(raw, results)
        : !exactMatch;
    if (raw && showCreate) {
        options.unshift({
            id: null,
            label: _config.createLabel(raw),
            isCreate: true,
            rawInput: raw,
        });
    }

    return options;
}

async function onSelectWrapper(opt) {
    if (_isSelecting) return;

    _isSelecting = true;
    input.value = "";
    input.disabled = true;

    try {
        // Optimistic UI update
        const newItem = { id: opt.id, label: opt.label };
        if (!_config.items.some((i) => String(i.id) === String(opt.id))) {
            _config.items.push(newItem);
        }
        renderItems();

        await _config.onAdd(opt);

        newItem.id = opt.id;
        newItem.label = opt.label;
        renderItems();
    } catch (err) {
        showError(`Add failed: ${err.message}`);
    } finally {
        input.disabled = false;
        input.focus();
        setTimeout(() => {
            _isSelecting = false;
        }, 150);
    }
}

function showError(msg) {
    let errEl = overlay.querySelector(".link-modal-error");
    if (!errEl) {
        errEl = document.createElement("div");
        errEl.className = "link-modal-error";
        overlay.querySelector(".link-modal-body").prepend(errEl);
    }
    errEl.textContent = msg;
    setTimeout(() => errEl.remove(), 3000);
}

const modal = createModalLifecycle(overlay, {
    onOpen: (config) => {
        _config = config;
        _isSelecting = false;
        titleEl.textContent = config.title;
        input.placeholder = config.placeholder || "Type to search or create...";
        input.value = "";
        dropdown.style.display = "none";
        renderItems();

_ac = createAutocomplete({
            inputEl: input,
            dropdownEl: dropdown,
            onSearch: onSearchWrapper,
            onSelect: onSelectWrapper,
            renderItem,
            allowCreate: true,
            getCreateLabel: config.createLabel,
            debounceMs: 200,
            onEnterEmpty: closeLinkModal,
        });

        // Quick-add button (e.g. "New album named after song")
        const existing = overlay.querySelector(".link-modal-quick-add");
        if (existing) existing.remove();
        if (config.quickAdd) {
            const btn = document.createElement("button");
            btn.className = "link-modal-quick-add ingest-btn-secondary";
            btn.textContent = config.quickAdd.label;
            btn.style.cssText = "width:100%; margin-top:0.5rem; font-size:0.8rem;";
            btn.addEventListener("click", async () => {
                btn.disabled = true;
                const opt = {
                    id: null,
                    label: config.quickAdd.rawInput,
                    isCreate: true,
                    rawInput: config.quickAdd.rawInput,
                };
                try {
                    _config.items.push({
                        id: null,
                        label: config.quickAdd.rawInput,
                    });
                    renderItems();
                    await _config.onAdd(opt);
                } catch (err) {
                    showError(`Add failed: ${err.message}`);
                    btn.disabled = false;
                }
            });
            overlay.querySelector(".link-modal-body").appendChild(btn);
        }

        input.focus();
    },
    onClose: () => {
        if (_ac) {
            _ac.destroy();
            _ac = null;
        }
        _config = null;
        input.value = "";
        dropdown.style.display = "none";
    },
    overlayClickCheck: (e) => {
        if (_isSelecting) return false;
        if (wasMousedownInside(overlay.querySelector(".link-modal"))) return false;
        return e.target === overlay;
    }
});

export const openLinkModal = modal.open;
export const closeLinkModal = modal.close;