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
 *   tagMode,       // bool — show category prefix on chips
 * })
 */

import { ABORTED } from "../api.js";
import { escapeHtml } from "./utils.js";
import { createAutocomplete } from "./autocomplete.js";

export function createChipInput({
    container,
    items: initialItems,
    onSearch,
    onAdd,
    onRemove,
    onSplit,
    allowCreate = false,
    tagMode = false,
    getCreateLabel = null,
    categoryColors = {},
    labelAttrs = null,
    extraChipButtons = null,
}) {
    let items = [...initialItems];

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

    // ── Chip rendering ────────────────────────────────────────────────────────

    function escapeHtmlLocal(str) {
        if (str === null || str === undefined) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function renderChips() {
        chipsEl.innerHTML = "";
        for (const item of items) {
            const chip = document.createElement("span");
            chip.className = "chip-input__chip";

            const attrs = labelAttrs ? labelAttrs(item) : null;
            const attrStr = attrs
                ? Object.entries(attrs).map(([k, v]) => `${k}="${escapeHtmlLocal(String(v))}"`).join(" ")
                : "";
            const labelTag = attrs ? "button" : "span";
            const labelHtml = `<${labelTag} class="chip-input__chip-label" ${attrStr} type="button">${escapeHtmlLocal(item.label)}</${labelTag}>`;

            if (tagMode && item.category) {
                const color = categoryColors[item.category] || "#888";
                chip.innerHTML = `<span class="chip-input__tag-cat" style="color:${escapeHtmlLocal(color)}">${escapeHtmlLocal(item.category)}</span>${labelHtml}`;
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
                } catch {
                    removeBtn.disabled = false;
                }
            });
            chip.appendChild(removeBtn);

            chipsEl.appendChild(chip);
        }
    }

    // ── Dropdown rendering ─────────────────────────────────────────────────

    function renderItem(opt, i, isCreate) {
        const el = document.createElement("div");
        el.className = `chip-input__option${isCreate ? " chip-input__option--create" : ""}`;
        el.dataset.acIndex = i;

        if (tagMode && opt.category && !isCreate) {
            const color = categoryColors[opt.category] || "#888";
            el.innerHTML = `<span class="chip-input__tag-cat" style="color:${escapeHtmlLocal(color)};border:none">${escapeHtmlLocal(opt.category)}</span>${escapeHtmlLocal(opt.label)}`;
        } else if (isCreate) {
            const label = getCreateLabel ? getCreateLabel(opt.label) : `+ Add "${opt.label}"`;
            el.textContent = label;
        } else {
            el.textContent = opt.label;
        }

        return el.outerHTML;
    }

    // ─── Autocomplete setup ───────────────────────────────────────────────

    const ac = createAutocomplete({
        inputEl,
        dropdownEl,
        onSearch: async (q) => {
            const results = await onSearch(q);
            if (results === ABORTED || results == null) return [];
            return results;
        },
        onSelect: async (opt) => {
            await onAdd(opt);
        },
        renderItem,
        allowCreate,
        getCreateLabel,
        debounceMs: 180,
    });

    // ── Init ─────────────────────────────────────────────────────────────────

    renderChips();

    return {
        setItems(newItems) {
            items = [...newItems];
            renderChips();
        },
    };
}