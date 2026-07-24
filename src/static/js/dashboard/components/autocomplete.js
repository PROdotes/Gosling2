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
    getPinnedOption = null,
    debounceMs = 200,
    onEnterEmpty = null,
    activeClass = "link-dropdown-item--active",
}) {
    let options = [];
    let activeIndex = -1;
    let searchTimeout = null;
    let pendingSelect = false;
    let lastQuery = "";

    // Shown in place of search results while the query is empty — a fast
    // path pinned to the input itself instead of a separate always-visible
    // button. Disappears the moment the user types, same as a normal search.
    function showPinned() {
        const pinned = getPinnedOption();
        if (!pinned) {
            hideDropdown();
            return;
        }
        options = [{ ...pinned, isPinned: true }];
        dropdownEl.innerHTML = renderItem(options[0], 0, false, true);
        dropdownEl.style.display = "block";
        highlightIndex(0);
        attachOptionHandlers();
    }

    function handleFocus() {
        if (!inputEl.value.trim() && getPinnedOption) showPinned();
    }

    function showDropdown(opts) {
        // onSearch results may carry a suppressCreate flag (e.g. the typed
        // text exactly matches something that can't be created/added again)
        // to veto this dropdown's own free-text create row.
        const showCreate = allowCreate && lastQuery.trim() && !opts.suppressCreate;

        if (opts.length === 0 && !showCreate) {
            hideDropdown();
            return;
        }

        const html = opts.map((opt, i) => renderItem(opt, i, false)).join("");

        if (showCreate) {
            const createOpt = { id: null, label: lastQuery.trim(), isCreate: true };
            options = [...opts, createOpt];
            const createHtml = renderItem(createOpt, opts.length, true);
            dropdownEl.innerHTML = html + createHtml;
        } else {
            options = opts;
            dropdownEl.innerHTML = html;
        }

        dropdownEl.style.display = "block";
        if (options.length > 0) highlightIndex(0);
        attachOptionHandlers();
    }

    function hideDropdown() {
        dropdownEl.style.display = "none";
        dropdownEl.innerHTML = "";
        options = [];
        activeIndex = -1;
    }

    function highlightIndex(index) {
        const opts = dropdownEl.querySelectorAll("[data-ac-index]");
        opts.forEach((o, i) => {
            const isActive = i === index;
            o.classList.toggle(activeClass, isActive);
            if (isActive) o.scrollIntoView({ block: "nearest" });
        });
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
            } else if (!inputEl.value.trim() && onEnterEmpty) {
                onEnterEmpty();
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
            if (getPinnedOption) showPinned();
            else hideDropdown();
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
    inputEl.addEventListener("focus", handleFocus);

    return {
        destroy() {
            clearTimeout(searchTimeout);
            inputEl.removeEventListener("focus", handleFocus);
            inputEl.removeEventListener("input", handleInput);
            inputEl.removeEventListener("keydown", handleKeydown);
            inputEl.removeEventListener("blur", handleBlur);
        },
        setOptions(opts) {
            if (opts && opts.length) showDropdown(opts);
        },
    };
}