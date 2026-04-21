/**
 * Chip Input Component — inline add/remove for relationship fields.
 *
 * createChipInput({
 *   container,     // DOM element to render into
 *   items,         // [{id, label, category?}]
 *   onSearch,      // async (q) => [{id, label}] | ABORTED sentinel
 *   onAdd,         // async ({id, label}) => void
 *   onRemove,      // async (id) => void
 *   onSplit,       // async ({id, label}) => void  — per-chip ✂, optional
 *   allowCreate,   // bool — show "+ Add X" option when no exact match
 *   singleSelect,  // bool — hide text input when an item is present
 *   tagMode,       // bool — show category prefix on chips
 * })
 */

import { ABORTED } from "../api.js";

function escHtml(str) {
    if (str == null) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

export function createChipInput({
    container,
    items: initialItems,
    onSearch,
    onAdd,
    onRemove,
    onSplit,
    allowCreate = false,
    singleSelect = false,
    tagMode = false,
    getCreateLabel = null, // (query) => string — custom label for the "+ Add" option
    categoryColors = {},   // {Category: "#hexcolor"} — for tagMode chips
    labelAttrs = null,     // (item) => {[attr]: value} — extra data-* attrs on chip label (for open-edit-modal wiring)
    extraChipButtons = null, // (item) => [{html, onClick}] — buttons rendered before ×
}) {
    let items = [...initialItems];
    let dropdownResults = [];
    let activeIndex = -1;
    let searchTimeout = null;
    let pendingAdd = false;

    // ── Build DOM ──────────────────────────────────────────────────────────────

    container.innerHTML = "";
    container.classList.add("chip-input");

    const chipsEl = document.createElement("div");
    chipsEl.className = "chip-input__chips";

    const inputEl = document.createElement("input");
    inputEl.type = "text";
    inputEl.className = "chip-input__text";
    inputEl.placeholder = "Search…";
    inputEl.autocomplete = "off";

    const dropdownEl = document.createElement("div");
    dropdownEl.className = "chip-input__dropdown";
    dropdownEl.hidden = true;

    container.appendChild(chipsEl);
    container.appendChild(inputEl);
    container.appendChild(dropdownEl);

    // ── Render ─────────────────────────────────────────────────────────────────

    function renderChips() {
        chipsEl.innerHTML = "";
        for (const item of items) {
            const chip = document.createElement("span");
            chip.className = "chip-input__chip";

            const attrs = labelAttrs ? labelAttrs(item) : null;
            const attrStr = attrs
                ? Object.entries(attrs).map(([k, v]) => `${k}="${escHtml(String(v))}"`).join(" ")
                : "";
            const labelTag = attrs ? "button" : "span";
            const labelHtml = `<${labelTag} class="chip-input__chip-label" ${attrStr} type="button">${escHtml(item.label)}</${labelTag}>`;

            if (tagMode && item.category) {
                const color = categoryColors[item.category] || "#888";
                chip.innerHTML = `<span class="chip-input__tag-cat" style="color:${escHtml(color)}">${escHtml(item.category)}</span>${labelHtml}`;
            } else {
                chip.innerHTML = labelHtml;
            }

            if (extraChipButtons) {
                for (const btnSpec of extraChipButtons(item)) {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = btnSpec.className || "chip-input__chip-btn";
                    btn.innerHTML = btnSpec.html;
                    if (btnSpec.title) btn.title = btnSpec.title;
                    if (btnSpec.dataset) {
                        for (const [k, v] of Object.entries(btnSpec.dataset)) btn.dataset[k] = v;
                    }
                    if (btnSpec.onClick) {
                        btn.addEventListener("click", (e) => { e.stopPropagation(); btnSpec.onClick(item); });
                    }
                    chip.appendChild(btn);
                }
            }

            if (onSplit) {
                const splitBtn = document.createElement("button");
                splitBtn.type = "button";
                splitBtn.className = "chip-input__chip-btn chip-input__chip-split";
                splitBtn.textContent = "✂";
                splitBtn.title = "Split";
                splitBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    onSplit(item);
                });
                chip.appendChild(splitBtn);
            }

            const removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "chip-input__chip-btn chip-input__chip-remove";
            removeBtn.textContent = "×";
            removeBtn.title = "Remove";
            removeBtn.addEventListener("click", async (e) => {
                e.stopPropagation();
                removeBtn.disabled = true;
                try {
                    await onRemove(item.id);
                    items = items.filter((i) => i.id !== item.id || i.label !== item.label);
                    renderChips();
                    updateInputVisibility();
                } catch {
                    removeBtn.disabled = false;
                }
            });
            chip.appendChild(removeBtn);

            chipsEl.appendChild(chip);
        }
    }

    function updateInputVisibility() {
        if (singleSelect && items.length > 0) {
            inputEl.hidden = true;
            closeDropdown();
        } else {
            inputEl.hidden = false;
        }
    }

    function renderDropdown(results, query) {
        dropdownEl.innerHTML = "";
        activeIndex = -1;

        const queryTrimmed = query.trim();
        const exactMatch = results.some(
            (r) => r.label.toLowerCase() === queryTrimmed.toLowerCase()
        );

        if (results.length === 0 && (!allowCreate || !queryTrimmed)) {
            dropdownEl.hidden = true;
            return;
        }

        for (let i = 0; i < results.length; i++) {
            const opt = results[i];
            const row = document.createElement("div");
            row.className = "chip-input__option";
            row.dataset.index = i;
            if (tagMode && opt.category) {
                const color = categoryColors[opt.category] || "#888";
                row.innerHTML = `<span class="chip-input__tag-cat" style="color:${escHtml(color)};border:none">${escHtml(opt.category)}</span>${escHtml(opt.label)}`;
            } else {
                row.textContent = opt.label;
            }
            row.addEventListener("mousedown", (e) => {
                e.preventDefault(); // prevent blur before click
                selectOption(opt);
            });
            dropdownEl.appendChild(row);
        }

        if (allowCreate && queryTrimmed && !exactMatch) {
            const row = document.createElement("div");
            row.className = "chip-input__option chip-input__option--create";
            row.dataset.index = results.length;
            row.textContent = getCreateLabel ? getCreateLabel(queryTrimmed) : `+ Add "${queryTrimmed}"`;
            row.addEventListener("mousedown", (e) => {
                e.preventDefault();
                selectOption({ id: null, label: queryTrimmed });
            });
            dropdownEl.appendChild(row);
        }

        dropdownEl.hidden = dropdownEl.children.length === 0;
        if (!dropdownEl.hidden) highlightOption(0);
        dropdownResults = results;
    }

    function closeDropdown() {
        dropdownEl.hidden = true;
        dropdownEl.innerHTML = "";
        activeIndex = -1;
        dropdownResults = [];
    }

    function highlightOption(index) {
        const opts = dropdownEl.querySelectorAll(".chip-input__option");
        opts.forEach((o, i) => o.classList.toggle("chip-input__option--active", i === index));
        activeIndex = index;
    }

    // ── Actions ────────────────────────────────────────────────────────────────

    async function selectOption(opt) {
        if (pendingAdd) return;
        pendingAdd = true;
        inputEl.value = "";
        closeDropdown();
        try {
            await onAdd(opt);
        } finally {
            pendingAdd = false;
        }
    }

    // ── Input events ───────────────────────────────────────────────────────────

    inputEl.addEventListener("input", () => {
        clearTimeout(searchTimeout);
        const q = inputEl.value;
        if (!q.trim()) { closeDropdown(); return; }
        searchTimeout = setTimeout(async () => {
            const results = await onSearch(q);
            if (results === ABORTED || results == null) return;
            renderDropdown(results, q);
        }, 180);
    });

    inputEl.addEventListener("keydown", (e) => {
        const opts = dropdownEl.querySelectorAll(".chip-input__option");
        const count = opts.length;

        if (e.key === "ArrowDown") {
            e.preventDefault();
            highlightOption((activeIndex + 1) % count);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            highlightOption((activeIndex - 1 + count) % count);
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (activeIndex >= 0 && activeIndex < count) {
                opts[activeIndex].dispatchEvent(new MouseEvent("mousedown"));
            } else if (allowCreate && inputEl.value.trim()) {
                selectOption({ id: null, label: inputEl.value.trim() });
            }
        } else if (e.key === "Escape") {
            closeDropdown();
        }
    });

    inputEl.addEventListener("blur", () => {
        // Small delay so mousedown on option fires first
        setTimeout(closeDropdown, 150);
    });

    // ── Init ───────────────────────────────────────────────────────────────────

    renderChips();
    updateInputVisibility();

    // Return a handle for the parent to refresh items after a server round-trip
    return {
        setItems(newItems) {
            items = [...newItems];
            renderChips();
            updateInputVisibility();
        },
    };
}
