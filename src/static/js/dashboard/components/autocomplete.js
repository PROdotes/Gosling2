/**
 * Autocomplete Helper — shared dropdown behavior.
 *
 * Extracts debounce, keyboard nav, blur timing, mousedown prevention.
 * Each consumer provides its own rendering via renderItem.
 *
 * Usage:
 *   const ac = createAutocomplete({
 *     inputEl,
 *     dropdownEl,
 *     onSearch: async (q) => [{id, label}, ...],
 *     onSelect: async (opt) => {},
 *     renderItem: (opt, i, isCreate) => `html string`,
 *     allowCreate: true,
 *     getCreateLabel: (q) => `+ Add "${q}"`,
 *     debounceMs: 200,
 *   });
 *
 *   Returns: { destroy, setOptions }
 */

export function createAutocomplete({
    inputEl,
    dropdownEl,
    onSearch,
    onSelect,
    renderItem,
    allowCreate = false,
    getCreateLabel = null,
    debounceMs = 200,
}) {
    let options = [];
    let activeIndex = -1;
    let searchTimeout = null;
    let pendingSelect = false;
    let lastQuery = "";

    function showDropdown(opts) {
        options = opts;
        activeIndex = opts.length > 0 ? 0 : -1;

        if (opts.length === 0 && !allowCreate) {
            hideDropdown();
            return;
        }

        const html = opts.map((opt, i) => renderItem(opt, i, false)).join("");

        if (allowCreate && lastQuery.trim()) {
            const createHtml = renderItem(
                { id: null, label: lastQuery.trim(), isCreate: true },
                opts.length,
                true,
            );
            dropdownEl.innerHTML = html + createHtml;
        } else {
            dropdownEl.innerHTML = html;
        }

        dropdownEl.hidden = false;
        if (options.length > 0) highlightIndex(0);
        attachOptionHandlers();
    }

    function hideDropdown() {
        dropdownEl.hidden = true;
        dropdownEl.innerHTML = "";
        options = [];
        activeIndex = -1;
    }

    function highlightIndex(index) {
        const opts = dropdownEl.querySelectorAll("[data-ac-index]");
        opts.forEach((o, i) => o.classList.toggle("ac-option--active", i === index));
        activeIndex = index;
    }

    function attachOptionHandlers() {
        dropdownEl.querySelectorAll("[data-ac-index]").forEach((el) => {
            el.addEventListener("mousedown", (e) => {
                e.preventDefault();
                const idx = Number(el.dataset.acIndex);
                selectByIndex(idx);
            });
        });
    }

    async function selectByIndex(index) {
        const opt = options[index];
        if (!opt || pendingSelect) return;

        pendingSelect = true;
        inputEl.value = "";
        hideDropdown();

        try {
            await onSelect(opt);
        } finally {
            pendingSelect = false;
        }
    }

    function handleKeydown(e) {
        const opts = dropdownEl.querySelectorAll("[data-ac-index]");
        const count = opts.length;

        if (e.key === "ArrowDown") {
            e.preventDefault();
            highlightIndex((activeIndex + 1) % count);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            highlightIndex((activeIndex - 1 + count) % count);
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (activeIndex >= 0 && activeIndex < count) {
                selectByIndex(activeIndex);
            } else if (allowCreate && inputEl.value.trim()) {
                onSelect({ id: null, label: inputEl.value.trim(), isCreate: true });
            }
        } else if (e.key === "Escape") {
            hideDropdown();
        }
    }

    function handleInput() {
        clearTimeout(searchTimeout);
        const q = inputEl.value.trim();
        lastQuery = q;

        if (!q) {
            hideDropdown();
            return;
        }

        searchTimeout = setTimeout(async () => {
            const results = await onSearch(q);
            if (results === undefined || results === null) return;
            showDropdown(results);
        }, debounceMs);
    }

    function handleBlur() {
        setTimeout(hideDropdown, 150);
    }

    inputEl.addEventListener("input", handleInput);
    inputEl.addEventListener("keydown", handleKeydown);
    inputEl.addEventListener("blur", handleBlur);

    return {
        destroy() {
            clearTimeout(searchTimeout);
            inputEl.removeEventListener("input", handleInput);
            inputEl.removeEventListener("keydown", handleKeydown);
            inputEl.removeEventListener("blur", handleBlur);
        },
        setOptions(opts) {
            if (opts && opts.length) showDropdown(opts);
        },
    };
}