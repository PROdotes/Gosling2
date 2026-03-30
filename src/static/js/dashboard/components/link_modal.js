/**
 * Generic link modal — type-to-search autocomplete with existing item chips.
 *
 * Usage:
 *   openLinkModal({
 *     title: "Publishers",
 *     items: [ { id, label } ],           // current links
 *     onSearch: async (q) => [...],       // returns [{ id, label }]
 *     onAdd: async (option) => {},        // option is { id|null, label }
 *     onRemove: async (item) => {},       // item is { id, label }
 *     createLabel: (q) => `Add "${q}"`,  // label for the create-new option
 *   });
 */

const overlay = document.getElementById("link-modal");
const titleEl = document.getElementById("link-modal-title");
const itemsEl = document.getElementById("link-modal-items");
const input = document.getElementById("link-modal-input");
const dropdown = document.getElementById("link-modal-dropdown");

let _config = null;
let _debounce = null;
let _dropdownItems = [];
let _dropdownIndex = -1;
let _isSelecting = false;

function renderItems() {
    if (!_config.items.length) {
        itemsEl.innerHTML = '<span class="link-modal-empty">None linked</span>';
        return;
    }
    itemsEl.innerHTML = _config.items.map((item) => `
        <span class="link-chip">
            ${item.label}
            <button class="link-chip-remove" data-remove-id="${item.id}" title="Remove">✕</button>
        </span>
    `).join("");

    itemsEl.querySelectorAll(".link-chip-remove").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.removeId;
            const item = _config.items.find(i => String(i.id) === String(id));
            if (!item) return;
            btn.disabled = true;
            try {
                await _config.onRemove(item);
                _config.items = _config.items.filter(i => String(i.id) !== String(id));
                renderItems();
            } catch (err) {
                btn.disabled = false;
                showError(`Remove failed: ${err.message}`);
            }
        });
    });
}

function renderDropdown(options) {
    _dropdownItems = options;
    _dropdownIndex = -1;

    if (!options.length) {
        dropdown.style.display = "none";
        return;
    }

    dropdown.innerHTML = options.map((opt, i) => `
        <div class="link-dropdown-item ${opt.isCreate ? "link-dropdown-create" : ""}" data-index="${i}">
            ${opt.isCreate ? "✦ " : ""}${opt.label}
        </div>
    `).join("");

    dropdown.querySelectorAll(".link-dropdown-item").forEach((el) => {
        el.addEventListener("mousedown", (e) => {
            e.preventDefault(); // prevent input blur
            selectOption(Number(el.dataset.index));
        });
    });

    dropdown.style.display = "block";
    updateDropdownHighlight();
}

function updateDropdownHighlight() {
    dropdown.querySelectorAll(".link-dropdown-item").forEach((el, i) => {
        el.classList.toggle("link-dropdown-item--active", i === _dropdownIndex);
    });
}

async function selectOption(index) {
    if (_isSelecting) return;

    const opt = _dropdownItems[index];
    if (!opt) return;

    _isSelecting = true;
    input.value = "";
    dropdown.style.display = "none";
    _dropdownItems = [];
    _dropdownIndex = -1;
    input.disabled = true;

    try {
        // Optimistic UI update before initiating long network/DOM work
        const newItem = { id: opt.id, label: opt.label };
        if (!_config.items.some(i => String(i.id) === String(opt.id))) {
            _config.items.push(newItem);
        }
        renderItems();

        // Perform the background addition and detail panel refresh
        await _config.onAdd(opt);

        // Final sync in case the server returned a different ID/Name (e.g. for new items)
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

async function runSearch(q) {
    const raw = q.trim();
    const results = raw ? await _config.onSearch(raw) : [];

    // Filter out items already in the currentItems list
    const filteredResults = results.filter(r => {
        const alreadyLinked = _config.items.some(linked => {
             const idMatch = r.id != null && String(linked.id) === String(r.id);
             const labelMatch = linked.label.toLowerCase() === r.label.toLowerCase();
             return idMatch || labelMatch;
        });
        return !alreadyLinked;
    });

    const options = filteredResults.map(r => ({ id: r.id, label: r.label }));

    // Add create-new option if query doesn't exactly match an existing result
    const exactMatch = results.some(r => r.label.toLowerCase() === raw.toLowerCase());
    if (raw && !exactMatch) {
        options.unshift({ id: null, label: _config.createLabel(raw), isCreate: true, rawInput: raw });
    }

    renderDropdown(options);
}

export function openLinkModal(config) {
    _config = config;
    titleEl.textContent = config.title;
    input.placeholder = config.placeholder || "Type to search or create...";
    input.value = "";
    dropdown.style.display = "none";
    _dropdownItems = [];
    _dropdownIndex = -1;
    renderItems();
    overlay.style.display = "flex";
    input.focus();
}

export function closeLinkModal() {
    overlay.style.display = "none";
    _config = null;
    input.value = "";
    dropdown.style.display = "none";
}

// Input handler
input.addEventListener("input", () => {
    clearTimeout(_debounce);
    const q = input.value.trim();
    if (!q) {
        dropdown.style.display = "none";
        return;
    }
    _debounce = setTimeout(() => runSearch(q), 200);
});

overlay.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        e.stopPropagation();
        closeLinkModal();
    }
});

input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") {
        e.preventDefault();
        _dropdownIndex = Math.min(_dropdownIndex + 1, _dropdownItems.length - 1);
        updateDropdownHighlight();
    } else if (e.key === "ArrowUp") {
        e.preventDefault();
        _dropdownIndex = Math.max(_dropdownIndex - 1, 0);
        updateDropdownHighlight();
    } else if (e.key === "Enter") {
        e.preventDefault();
        if (_dropdownIndex >= 0) {
            selectOption(_dropdownIndex);
        } else if (_dropdownItems.length === 1) {
            selectOption(0);
        }
    }
});

input.addEventListener("blur", () => {
    // Small delay so mousedown on dropdown items fires first
    setTimeout(() => { dropdown.style.display = "none"; }, 150);
});

// Close on overlay click outside modal box
overlay.addEventListener("click", (e) => {
    if (_isSelecting) return;
    if (e.target === overlay) {
        closeLinkModal();
    }
});
