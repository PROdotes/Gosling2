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

// Fields with more than this many chips auto-fold on initial render.
const FOLD_THRESHOLD = 5;

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
    placeholder = "Search...",
}) {
    let items = [...initialItems];

    // ── Build DOM ──────────────────────────────────────────────────────────────

    container.innerHTML = "";
    container.classList.add("chip-input");

    const chipsEl = document.createElement("div");
    chipsEl.className = "chip-input__chips";

    // Folded one-liner: shows value text + overflow count. Click to unfold.
    const previewEl = document.createElement("button");
    previewEl.type = "button";
    previewEl.className = "chip-input__preview";
    previewEl.hidden = true;

    // Collapsed-by-default "add" trigger. At rest the field is just chips + this
    // faint worded stub ("+ Add composer"); clicking it reveals the search box.
    // Keeps the editor calm with many empty fields while staying self-explanatory.
    const stubEl = document.createElement("button");
    stubEl.type = "button";
    stubEl.className = "chip-input__stub";

    const inputEl = document.createElement("input");
    inputEl.type = "text";
    inputEl.className = "chip-input__text";
    inputEl.placeholder = placeholder;
    inputEl.autocomplete = "off";
    inputEl.hidden = true;

    const dropdownEl = document.createElement("div");
    dropdownEl.className = "chip-input__dropdown";
    dropdownEl.hidden = true;

    container.appendChild(chipsEl);
    container.appendChild(previewEl);
    container.appendChild(stubEl);
    container.appendChild(inputEl);
    container.appendChild(dropdownEl);

    // ── Collapsed / expanded state ─────────────────────────────────────────────

    let expanded = false;

    function stubLabel() {
        return items.length > 0 ? "+ add" : `+ ${placeholder}`;
    }

    function syncStub() {
        if (!expanded) stubEl.textContent = stubLabel();
    }

    function expand() {
        if (expanded) return;
        expanded = true;
        container.classList.add("chip-input--expanded");
        stubEl.hidden = true;
        inputEl.hidden = false;
        inputEl.focus();
    }

    function collapse() {
        if (!expanded) return;
        expanded = false;
        container.classList.remove("chip-input--expanded");
        inputEl.value = "";
        inputEl.hidden = true;
        stubEl.hidden = false;
        syncStub();
    }

    stubEl.addEventListener("click", expand);

    inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            // Autocomplete also closes its dropdown on Escape; we additionally
            // collapse the whole field back to the stub.
            collapse();
            inputEl.blur();
        }
    });

    inputEl.addEventListener("blur", () => {
        // Collapse only if focus truly left and nothing's half-typed. Option
        // clicks use mousedown+preventDefault, so they never blur the input.
        setTimeout(() => {
            if (document.activeElement === inputEl) return;
            if (inputEl.value.trim() === "") collapse();
        }, 160);
    });

    // ── Fold state ────────────────────────────────────────────────────────────
    // Fold is a separate axis from expand/collapse (which controls the add-input).
    // Folded: chips hidden, one-liner preview shown. Expanded: add-input shown.

    let folded = initialItems.length > FOLD_THRESHOLD;

    function buildPreviewText() {
        const shown = items.slice(0, 2).map((i) => escapeHtml(i.label)).join(", ");
        if (items.length > 2) {
            return `${shown}<span class="chip-input__preview-more"> +${items.length - 2} more</span>`;
        }
        return shown;
    }

    function applyFold() {
        const hasFoldable = items.length > 0;
        if (!hasFoldable) folded = false; // can't fold an empty field

        const field = container.closest(".editor-field");
        if (field) {
            field.classList.toggle("foldable", hasFoldable);
            field.classList.toggle("open", hasFoldable && !folded);
        }

        if (folded) {
            // Force close the add-input when folding
            if (expanded) {
                expanded = false;
                container.classList.remove("chip-input--expanded");
                inputEl.value = "";
                inputEl.hidden = true;
                dropdownEl.hidden = true;
            }
            // Use inline style (not hidden attr) because display:contents ignores
            // the hidden attribute in some browsers — inline style wins reliably.
            chipsEl.style.display = "none";
            stubEl.hidden = true;
            previewEl.innerHTML = buildPreviewText();
            previewEl.hidden = false;
        } else {
            chipsEl.style.display = "";
            previewEl.hidden = true;
            if (expanded) {
                stubEl.hidden = true;
            } else {
                stubEl.hidden = false;
                syncStub();
            }
        }
    }

    function fold() { folded = true; applyFold(); }
    function unfold() { folded = false; applyFold(); }
    function toggleFold() { if (folded) unfold(); else fold(); }

    // Preview click → unfold to show chips + stub (does NOT auto-open search box)
    previewEl.addEventListener("click", unfold);

    // Label click is the primary fold toggle. Wire it self-contained here so
    // song_editor.js doesn't need to know about fold.
    const fieldEl = container.closest(".editor-field");
    if (fieldEl) {
        const labelEl = fieldEl.querySelector(".editor-label");
        if (labelEl) labelEl.addEventListener("click", toggleFold);
    }

    // ── Chip rendering ────────────────────────────────────────────────────────

    function renderChips() {
        chipsEl.innerHTML = "";
        for (const item of items) {
            const chip = document.createElement("span");
            chip.className = "chip-input__chip";

            const attrs = labelAttrs ? labelAttrs(item) : null;
            const attrStr = attrs
                ? Object.entries(attrs).map(([k, v]) => `${k}="${escapeHtml(String(v))}"`).join(" ")
                : "";
            const labelTag = attrs ? "button" : "span";
            const labelHtml = `<${labelTag} class="chip-input__chip-label" ${attrStr} type="button">${escapeHtml(item.label)}</${labelTag}>`;

            if (tagMode && item.category) {
                const color = categoryColors[item.category] || "var(--text-mute)";
                chip.innerHTML = `<span class="chip-input__tag-cat" style="color:${escapeHtml(color)}">${escapeHtml(item.category)}</span>${labelHtml}`;
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
                    applyFold();
                } catch {
                    removeBtn.disabled = false;
                }
            });
            chip.appendChild(removeBtn);

            chipsEl.appendChild(chip);
        }
        syncStub();
    }

    // ── Dropdown rendering ─────────────────────────────────────────────────

    function renderItem(opt, i, isCreate) {
        const el = document.createElement("div");
        el.className = `chip-input__option${isCreate ? " chip-input__option--create" : ""}`;
        el.dataset.acIndex = i;

        if (tagMode && opt.category && !isCreate) {
            const color = categoryColors[opt.category] || "var(--text-mute)";
            el.innerHTML = `<span class="chip-input__tag-cat" style="color:${escapeHtml(color)};border:none">${escapeHtml(opt.category)}</span>${escapeHtml(opt.label)}`;
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
            const newItem = await onAdd(opt);
            if (newItem) {
                items = [...items, newItem];
                renderChips();
                applyFold();
            }
        },
        renderItem,
        allowCreate,
        getCreateLabel,
        debounceMs: 180,
    });

    // ── Init ─────────────────────────────────────────────────────────────────

    renderChips();
    applyFold();

    return {
        setItems(newItems) {
            items = [...newItems];
            renderChips();
            // Re-sync preview/fold state without re-auto-folding (preserve user's
            // manual toggle for the life of this rendered editor).
            applyFold();
        },
        expand,
        fold,
        unfold,
        toggleFold,
    };
}
