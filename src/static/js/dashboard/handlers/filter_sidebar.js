/**
 * GOSLING FILTER SIDEBAR HANDLER
 * Manages filter sidebar state, rendering, and song filtering.
 */

import { getFilterValues, filterSongs } from "../api.js";

const FILTER_STORAGE_KEY = "gosling_filter_state";

function loadSavedFilterState() {
    try {
        const saved = localStorage.getItem(FILTER_STORAGE_KEY);
        return saved ? JSON.parse(saved) : null;
    } catch {
        return null;
    }
}

function saveFilterState(active, liveOnly, mode, sidebarVisible) {
    try {
        localStorage.setItem(
            FILTER_STORAGE_KEY,
            JSON.stringify({ active, liveOnly, mode, sidebarVisible }),
        );
    } catch {}
}

const STATUS_FILTERS = [
    { key: "not_done", label: "Not Done" },
    { key: "ready_to_finalize", label: "Ready to Finalize" },
    { key: "missing_data", label: "Missing Data" },
    { key: "done", label: "Done" },
];

export class FilterSidebarHandler {
    constructor(ctx) {
        this.ctx = ctx;

        // Filter state
        this._filterValues = null; // populated on load
        const saved = loadSavedFilterState();
        this._active = saved?.active ?? {
            artists: [],
            contributors: [],
            years: [],
            decades: [],
            genres: [],
            albums: [],
            publishers: [],
            statuses: [],
            tag_categories: {},
        };
        this._liveOnly = saved?.liveOnly ?? false;
        this._mode =
            saved?.mode === "ALL" || saved?.mode === "ANY" ? saved.mode : "ALL";
        this._sidebarVisible = saved?.sidebarVisible ?? false;

        // Restore sidebar visibility immediately (before async load)
        if (this._sidebarVisible) {
            const sidebar = document.getElementById("filter-sidebar");
            if (sidebar) sidebar.style.display = "flex";
        }
        this._collapsed = {}; // { sectionKey: bool }
        this._searchText = ""; // driven by main search bar
    }

    setSearchText(text) {
        this._searchText = text.toLowerCase();
        this._render();
    }

    // ─── INIT ─────────────────────────────────────────────────────────────────

    async load() {
        try {
            this._filterValues = await getFilterValues();
            this._render();
            if (this.hasActiveFilters()) {
                this._applyFilters();
            }
        } catch (err) {
            console.error("[FilterSidebar] Failed to load filter values:", err);
        }
    }

    setupListeners() {
        const sidebar = document.getElementById("filter-sidebar");
        if (!sidebar) return;
        sidebar.addEventListener("click", (e) => this._handleClick(e));
    }

    // ─── PUBLIC API ───────────────────────────────────────────────────────────

    show() {
        this._sidebarVisible = true;
        const sidebar = document.getElementById("filter-sidebar");
        if (sidebar) sidebar.style.display = "flex";
        saveFilterState(this._active, this._liveOnly, this._mode, true);
    }

    hide() {
        this._sidebarVisible = false;
        const sidebar = document.getElementById("filter-sidebar");
        if (sidebar) sidebar.style.display = "none";
        saveFilterState(this._active, this._liveOnly, this._mode, false);
    }

    toggle() {
        this._sidebarVisible ? this.hide() : this.show();
    }

    reapply() {
        if (this.hasActiveFilters()) {
            this._applyFilters();
        }
    }

    hasActiveFilters() {
        return (
            this._active.artists.length > 0 ||
            this._active.contributors.length > 0 ||
            this._active.years.length > 0 ||
            this._active.decades.length > 0 ||
            this._active.genres.length > 0 ||
            this._active.albums.length > 0 ||
            this._active.publishers.length > 0 ||
            this._active.statuses.length > 0 ||
            Object.values(this._active.tag_categories).some(
                (v) => v.length > 0,
            ) ||
            this._liveOnly
        );
    }

    clearAll() {
        this._active = {
            artists: [],
            contributors: [],
            years: [],
            decades: [],
            genres: [],
            albums: [],
            publishers: [],
            statuses: [],
            tag_categories: {},
        };
        this._liveOnly = false;
        this._render();
        this._applyFilters();
    }

    // ─── CLICK HANDLER ────────────────────────────────────────────────────────

    _handleClick(e) {
        const target = e.target;

        // Logic mode toggle
        if (target.closest("#filter-mode-all")) {
            this._mode = "ALL";
            this._render();
            if (this.hasActiveFilters()) this._applyFilters();
            return;
        }
        if (target.closest("#filter-mode-any")) {
            this._mode = "ANY";
            this._render();
            if (this.hasActiveFilters()) this._applyFilters();
            return;
        }

        // Expand/collapse all
        if (target.closest("#filter-expand-all")) {
            this._collapsed = {};
            this._render();
            return;
        }
        if (target.closest("#filter-collapse-all")) {
            for (const key of this._allSectionKeys()) {
                this._collapsed[key] = true;
            }
            this._render();
            return;
        }

        // Clear all filters
        if (target.closest("#filter-clear-all")) {
            this.clearAll();
            return;
        }

        // Live toggle
        if (target.closest("#filter-live-toggle")) {
            this._liveOnly = !this._liveOnly;
            this._render();
            this._applyFilters();
            return;
        }

        // Section collapse toggle
        const sectionHeader = target.closest("[data-filter-section]");
        if (sectionHeader && target.closest(".filter-section-header")) {
            const key = sectionHeader.dataset.filterSection;
            this._collapsed[key] = !this._collapsed[key];
            this._render();
            return;
        }

        // Chip remove click
        const chipRemove = target.closest(".filter-chip-remove");
        if (chipRemove) {
            const key = chipRemove.dataset.filterKey;
            const value = chipRemove.dataset.filterValue;
            const cat = chipRemove.dataset.filterCat;
            if (key === "live") {
                this._liveOnly = false;
            } else {
                this._toggleValue(key, value, cat);
            }
            this._render();
            this._applyFilters();
            return;
        }

        // Filter value click
        const item = target.closest("[data-filter-key][data-filter-value]");
        if (item && !item.classList.contains("filter-chip")) {
            const key = item.dataset.filterKey;
            const value = item.dataset.filterValue;
            const cat = item.dataset.filterCat;
            this._toggleValue(key, value, cat);
            this._render();
            this._applyFilters();
            return;
        }
    }

    _toggleValue(key, value, cat = null) {
        if (key === "tag_categories") {
            const arr = this._active.tag_categories[cat] || [];
            const idx = arr.indexOf(value);
            if (idx >= 0) arr.splice(idx, 1);
            else arr.push(value);
            this._active.tag_categories[cat] = arr;
        } else {
            const arr = this._active[key];
            const idx = arr.indexOf(value);
            if (idx >= 0) arr.splice(idx, 1);
            else arr.push(value);
        }
    }

    _isActive(key, value, cat = null) {
        if (key === "tag_categories") {
            return (this._active.tag_categories[cat] || []).includes(value);
        }
        return this._active[key].includes(value);
    }

    // ─── APPLY ────────────────────────────────────────────────────────────────

    _applyFilters() {
        saveFilterState(
            this._active,
            this._liveOnly,
            this._mode,
            this._sidebarVisible,
        );
        if (!this.hasActiveFilters()) {
            // No filters — hand back to normal search
            this.ctx.onFilterCleared?.();
            return;
        }

        const filters = {};
        const add = (key, arr) => {
            if (arr.length) filters[key] = arr;
        };
        add("artists", this._active.artists);
        add("contributors", this._active.contributors);
        add("years", this._active.years);
        add("decades", this._active.decades);
        add("genres", this._active.genres);
        add("albums", this._active.albums);
        add("publishers", this._active.publishers);
        add("statuses", this._active.statuses);
        const tagPairs = [];
        for (const [cat, vals] of Object.entries(this._active.tag_categories)) {
            for (const v of vals) tagPairs.push(`${cat}:${v}`);
        }
        if (tagPairs.length) filters["tags"] = tagPairs;

        const result = filterSongs(filters, this._mode, this._liveOnly);
        this.ctx.onFilterResults?.(result);
    }

    // ─── RENDER ───────────────────────────────────────────────────────────────

    _allSectionKeys() {
        if (!this._filterValues) return [];
        const keys = [
            "statuses",
            "artists",
            "contributors",
            "live",
            "years",
            "decades",
            "genres",
            "albums",
            "publishers",
        ];
        for (const cat of Object.keys(
            this._filterValues.tag_categories || {},
        )) {
            keys.push(`tag_cat_${cat}`);
        }
        return keys;
    }

    _render() {
        const sidebar = document.getElementById("filter-sidebar");
        if (!sidebar) return;

        const q = this._searchText;

        const matchesSearch = (val) =>
            !q || String(val).toLowerCase().includes(q);

        const renderSection = (key, label, values, renderValue) => {
            const filtered = values.filter((v) =>
                matchesSearch(renderValue(v)),
            );
            if (q && filtered.length === 0) return "";
            const isCollapsed = this._collapsed[key];
            return `
                <div class="filter-section" data-filter-section="${key}">
                    <div class="filter-section-header">
                        <span class="filter-section-label">${label}</span>
                        <span class="filter-section-toggle">${isCollapsed ? "▶" : "▼"}</span>
                    </div>
                    ${
                        isCollapsed
                            ? ""
                            : `
                    <div class="filter-section-body">
                        ${filtered
                            .map((v) => {
                                const display = renderValue(v);
                                const active = this._isActive(key, String(v));
                                return `<button class="filter-value${active ? " active" : ""}"
                                data-filter-key="${key}"
                                data-filter-value="${v}">${display}</button>`;
                            })
                            .join("")}
                    </div>`
                    }
                </div>`;
        };

        const fv = this._filterValues || {};

        let sectionsHtml = "";

        // Status (always shown, no DB values needed)
        const statusFiltered = STATUS_FILTERS.filter((s) =>
            matchesSearch(s.label),
        );
        const liveMatches = !q || "live only".includes(q.toLowerCase());
        if (!q || statusFiltered.length || liveMatches) {
            const isCollapsed = this._collapsed["statuses"];
            sectionsHtml += `
                <div class="filter-section" data-filter-section="statuses">
                    <div class="filter-section-header">
                        <span class="filter-section-label">Status</span>
                        <span class="filter-section-toggle">${isCollapsed ? "▶" : "▼"}</span>
                    </div>
                    ${
                        isCollapsed
                            ? ""
                            : `
                    <div class="filter-section-body">
                        ${statusFiltered
                            .map((s) => {
                                const active = this._isActive(
                                    "statuses",
                                    s.key,
                                );
                                return `<button class="filter-value${active ? " active" : ""}"
                                data-filter-key="statuses"
                                data-filter-value="${s.key}">${s.label}</button>`;
                            })
                            .join("")}
                        ${liveMatches ? `<button id="filter-live-toggle" class="filter-value${this._liveOnly ? " active" : ""}" data-filter-key="live">Live Only</button>` : ""}
                    </div>`
                    }
                </div>`;
        }

        sectionsHtml += renderSection(
            "artists",
            "Artist",
            fv.artists || [],
            (v) => v,
        );
        sectionsHtml += renderSection(
            "contributors",
            "All Contributors",
            fv.contributors || [],
            (v) => v,
        );
        sectionsHtml += renderSection(
            "years",
            "Year",
            fv.years || [],
            (v) => v,
        );
        sectionsHtml += renderSection(
            "decades",
            "Decade",
            fv.decades || [],
            (v) => `${v}s`,
        );
        sectionsHtml += renderSection(
            "genres",
            "Genre",
            fv.genres || [],
            (v) => v,
        );
        sectionsHtml += renderSection(
            "albums",
            "Album",
            fv.albums || [],
            (v) => v,
        );
        sectionsHtml += renderSection(
            "publishers",
            "Publisher",
            fv.publishers || [],
            (v) => v,
        );

        for (const [cat, vals] of Object.entries(fv.tag_categories || {})) {
            const sectionKey = `tag_cat_${cat}`;
            const filtered = vals.filter((v) => matchesSearch(v));
            if (q && filtered.length === 0) continue;
            const isCollapsed = this._collapsed[sectionKey];
            sectionsHtml += `
                <div class="filter-section" data-filter-section="${sectionKey}">
                    <div class="filter-section-header">
                        <span class="filter-section-label">${cat}</span>
                        <span class="filter-section-toggle">${isCollapsed ? "▶" : "▼"}</span>
                    </div>
                    ${
                        isCollapsed
                            ? ""
                            : `
                    <div class="filter-section-body">
                        ${filtered
                            .map((v) => {
                                const active = this._isActive(
                                    "tag_categories",
                                    v,
                                    cat,
                                );
                                return `<button class="filter-value${active ? " active" : ""}"
                                data-filter-key="tag_categories"
                                data-filter-value="${v}"
                                data-filter-cat="${cat}">${v}</button>`;
                            })
                            .join("")}
                    </div>`
                    }
                </div>`;
        }

        // Build active filter chips
        const chips = [];
        const addChips = (key, arr, label = (v) => v) => {
            for (const v of arr) {
                chips.push(
                    `<span class="filter-chip" data-filter-key="${key}" data-filter-value="${v}">${label(v)} <button class="filter-chip-remove" data-filter-key="${key}" data-filter-value="${v}">✕</button></span>`,
                );
            }
        };
        addChips(
            "statuses",
            this._active.statuses,
            (v) => STATUS_FILTERS.find((s) => s.key === v)?.label ?? v,
        );
        addChips("artists", this._active.artists);
        addChips("contributors", this._active.contributors);
        addChips("years", this._active.years);
        addChips("decades", this._active.decades, (v) => `${v}s`);
        addChips("genres", this._active.genres);
        addChips("albums", this._active.albums);
        addChips("publishers", this._active.publishers);
        for (const [cat, vals] of Object.entries(this._active.tag_categories)) {
            for (const v of vals) {
                chips.push(
                    `<span class="filter-chip" data-filter-key="tag_categories" data-filter-value="${v}" data-filter-cat="${cat}">${v} <button class="filter-chip-remove" data-filter-key="tag_categories" data-filter-value="${v}" data-filter-cat="${cat}">✕</button></span>`,
                );
            }
        }
        if (this._liveOnly) {
            chips.push(
                `<span class="filter-chip" data-filter-key="live">Live Only <button class="filter-chip-remove" data-filter-key="live">✕</button></span>`,
            );
        }

        sidebar.innerHTML = `
            <div class="filter-header">
                <button id="filter-expand-all" class="filter-ctrl-btn" title="Expand all">ALL +</button>
                <button id="filter-collapse-all" class="filter-ctrl-btn" title="Collapse all">ALL −</button>
                <button id="filter-mode-all" class="filter-ctrl-btn${this._mode === "ALL" ? " active" : ""}" title="AND logic">ALL</button>
                <button id="filter-mode-any" class="filter-ctrl-btn${this._mode === "ANY" ? " active" : ""}" title="OR logic">ANY</button>
            </div>
            <div class="filter-sections">
                ${sectionsHtml}
            </div>
            <div class="filter-active-chips">
                ${chips.length ? chips.join("") : '<span class="filter-chips-empty">No active filters</span>'}
            </div>`;
    }
}
