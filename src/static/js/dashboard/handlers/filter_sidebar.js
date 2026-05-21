/**
 * GOSLING FILTER SIDEBAR HANDLER
 * Manages filter sidebar state, rendering, and song filtering.
 * Filter values are fetched from the server on every search — no client-side text normalization.
 */

import { ABORTED, getFilterValues, filterSongs } from "../api.js";

const FILTER_STORAGE_KEY = "gosling_filter_state";

function loadSavedFilterState() {
    try {
        const saved = localStorage.getItem(FILTER_STORAGE_KEY);
        return saved ? JSON.parse(saved) : null;
    } catch {
        return null;
    }
}

function saveFilterState(active, liveOnly, hasOriginal, mode, sidebarVisible) {
    try {
        localStorage.setItem(
            FILTER_STORAGE_KEY,
            JSON.stringify({ active, liveOnly, hasOriginal, mode, sidebarVisible }),
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
        this._hasOriginal = saved?.hasOriginal ?? false;
        this._mode =
            saved?.mode === "ALL" || saved?.mode === "ANY" ? saved.mode : "ALL";
        this._sidebarVisible = saved?.sidebarVisible ?? false;

        // Restore sidebar visibility immediately (before async load)
        if (this._sidebarVisible) {
            const sidebar = document.getElementById("filter-sidebar");
            if (sidebar) sidebar.style.display = "flex";
        }
        this._collapsed = {}; // { sectionKey: bool }
    }

    // ─── INIT ─────────────────────────────────────────────────────────────────

    async load(query = "") {
        try {
            const result = await getFilterValues(query);
            if (result === ABORTED) {
                return;
            }
            this._filterValues = result;
            this._render();
            if (!query && this.hasActiveFilters()) {
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
        saveFilterState(this._active, this._liveOnly, this._hasOriginal, this._mode, true);
    }

    hide() {
        this._sidebarVisible = false;
        const sidebar = document.getElementById("filter-sidebar");
        if (sidebar) sidebar.style.display = "none";
        saveFilterState(this._active, this._liveOnly, this._hasOriginal, this._mode, false);
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
            this._liveOnly ||
            this._hasOriginal
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
        this._hasOriginal = false;
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

        // Has original toggle
        if (target.closest("#filter-has-original-toggle")) {
            this._hasOriginal = !this._hasOriginal;
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
            } else if (key === "has_original") {
                this._hasOriginal = false;
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
            this._hasOriginal,
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

        const result = filterSongs(filters, this._mode, this._liveOnly, this._hasOriginal);
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

        const renderSection = (key, label, values, renderValue) => {
            if (values.length === 0) return "";
            const isCollapsed = this._collapsed[key];
            return `
                <div class="filter-section" data-filter-section="${key}">
                    <div class="filter-section-header">
                        <span class="filter-section-label">${label}</span>
                        <span class="filter-section-toggle">${isCollapsed ? "&#9654;" : "&#9660;"}</span>
                    </div>
                    ${
                        isCollapsed
                            ? ""
                            : `
                    <div class="filter-section-body">
                        ${values
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

        // Status section — always shown in full (static values, no server filtering)
        const isCollapsed = this._collapsed["statuses"];
        sectionsHtml += `
            <div class="filter-section" data-filter-section="statuses">
                <div class="filter-section-header">
                    <span class="filter-section-label">Status</span>
                    <span class="filter-section-toggle">${isCollapsed ? "&#9654;" : "&#9660;"}</span>
                </div>
                ${
                    isCollapsed
                        ? ""
                        : `
                <div class="filter-section-body">
                    ${STATUS_FILTERS
                        .map((s) => {
                            const active = this._isActive("statuses", s.key);
                            return `<button class="filter-value${active ? " active" : ""}"
                            data-filter-key="statuses"
                            data-filter-value="${s.key}">${s.label}</button>`;
                        })
                        .join("")}
                    <button id="filter-live-toggle" class="filter-value${this._liveOnly ? " active" : ""}" data-filter-key="live">Live Only</button>
                    <button id="filter-has-original-toggle" class="filter-value${this._hasOriginal ? " active" : ""}" data-filter-key="has_original">Has Original</button>
                </div>`
                }
            </div>`;

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
            if (vals.length === 0) continue;
            const sectionKey = `tag_cat_${cat}`;
            const isCatCollapsed = this._collapsed[sectionKey];
            sectionsHtml += `
                <div class="filter-section" data-filter-section="${sectionKey}">
                    <div class="filter-section-header">
                        <span class="filter-section-label">${cat}</span>
                        <span class="filter-section-toggle">${isCatCollapsed ? "&#9654;" : "&#9660;"}</span>
                    </div>
                    ${
                        isCatCollapsed
                            ? ""
                            : `
                    <div class="filter-section-body">
                        ${vals
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
                    `<span class="filter-chip" data-filter-key="${key}" data-filter-value="${v}">${label(v)} <button class="filter-chip-remove" data-filter-key="${key}" data-filter-value="${v}">&#x2715;</button></span>`,
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
                    `<span class="filter-chip" data-filter-key="tag_categories" data-filter-value="${v}" data-filter-cat="${cat}">${v} <button class="filter-chip-remove" data-filter-key="tag_categories" data-filter-value="${v}" data-filter-cat="${cat}">&#x2715;</button></span>`,
                );
            }
        }
        if (this._liveOnly) {
            chips.push(
                `<span class="filter-chip" data-filter-key="live">Live Only <button class="filter-chip-remove" data-filter-key="live">&#x2715;</button></span>`,
            );
        }
        if (this._hasOriginal) {
            chips.push(
                `<span class="filter-chip" data-filter-key="has_original">Has Original <button class="filter-chip-remove" data-filter-key="has_original">&#x2715;</button></span>`,
            );
        }

        sidebar.innerHTML = `
            <div class="filter-header">
                <button id="filter-expand-all" class="filter-ctrl-btn" title="Expand all">ALL +</button>
                <button id="filter-collapse-all" class="filter-ctrl-btn" title="Collapse all">ALL &#8722;</button>
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
