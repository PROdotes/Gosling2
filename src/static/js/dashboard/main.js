import {
    ABORTED,
    abortAllSearches,
    addSongCredit,
    addSongPublisher,
    addSongTag,
    fetchAppConfig,
    fetchId3Frames,
    fetchRoles,
    fetchValidationRules,
    formatMetadataCase,
    getAcceptedFormats,
    getAlbumDetail,
    getArtistSongs,
    getArtistTree,
    getAuditHistory,
    getCatalogSong,
    getPublisherDetail,
    getPublisherSongs,
    getSongDetail,
    getSongWebSearch,
    getTagCategories,
    getTagDetail,
    getTagSongs,
    isAbortError,
    patchSongScalars,
    removeSongCredit,
    removeSongPublisher,
    removeSongTag,
    searchAlbums,
    searchArtists,
    searchPublishers,
    searchSongs,
    searchTags,
    setPrimarySongTag,
    setPublisherParent,
    updatePublisher,
    updateTag,
    getIngestStatus,
    readNdjsonStream,
    uploadFiles,
} from "./api.js";
import { openEditModal } from "./components/edit_modal.js";
import { activateInlineEdit } from "./components/inline_editor.js";
import { closeLinkModal, openLinkModal } from "./components/link_modal.js";
import {
    closeScrubberModal,
    openScrubberModal,
} from "./components/scrubber_modal.js";
import {
    closeSplitterModal,
    openSplitterModal,
} from "./components/splitter_modal.js";
import {
    closeSpotifyModal,
    openSpotifyModal,
} from "./components/spotify_modal.js";
import { initToastSystem, showToast } from "./components/toast.js";
import {
    basename,
    formatCountLabel,
    isModalOpen,
    renderEmptyState,
} from "./components/utils.js";
import { FilterSidebarHandler } from "./handlers/filter_sidebar.js";
import { NavigationHandler } from "./handlers/navigation.js";
import { SongActionsHandler, updateSyncLed } from "./handlers/song_actions.js";
import { WebSearchHandler } from "./handlers/web_search.js";
import * as orch from "./orchestrator.js";
import { renderSongEditorEmpty, renderSongEditorV2, renderSongEditorMultiSelect, renderActionSidebar, wireScalarInputs, wireChipInputs, wireDriftIndicators, wireAuditHistory } from "./renderers/song_editor.js";
import {
    renderAlbumDetailComplete,
    renderAlbumDetailLoading,
    renderAlbums,
} from "./renderers/albums.js";
import {
    renderArtistDetailComplete,
    renderArtistDetailLoading,
    renderArtists,
} from "./renderers/artists.js";
import { collectFilesFromItems } from "./renderers/ingestion.js";
import {
    renderPublisherDetailComplete,
    renderPublisherDetailLoading,
    renderPublishers as renderPublisherResults,
} from "./renderers/publishers.js";
import {
    renderSongDetailComplete,
    renderSongDetailLoading,
    renderSongs,
} from "./renderers/songs.js";
import {
    renderTagDetailComplete,
    renderTagDetailLoading,
    renderTags,
} from "./renderers/tags.js";

const elements = {
    searchInput: document.getElementById("searchInput"),
    resultsContainer: document.getElementById("results-container"),
    detailPanel: document.getElementById("detail-panel"),
    totalCount: document.getElementById("total-count"),
    totalLabel: document.getElementById("total-label"),
    matchCount: document.getElementById("match-count"),
    statSep: document.getElementById("stat-sep"),
    deepSearchToggle: document.getElementById("deepSearchToggle"),
    sortControlsBox: document.getElementById("sort-controls-box"),
    songsWorkspace: document.getElementById("songs-workspace"),
    legacyMain: document.querySelector("main"),
};

const state = {
    currentMode: "songs",
    cachedSongs: [],
    cachedIdentities: [],
    cachedAlbums: [],
    cachedPublishers: [],
    cachedTags: [],
    cachedIngestResults: [], // Persistent storage for ingestion results
    displayedItems: [], // Track currently displayed items in visual order (for keyboard nav)
    debounceTimer: null,
    currentQuery: "",
    totalLibraryCount: 0,
    selectedIndex: -1,
    isDeep: false,
    validationRules: null,
    id3Frames: null,
    allRoles: [],
    activeSong: null,
    activeSongFile: null,
    currentMode: "songs", // Renaming activeView to currentMode for consistency
    successCount: 0,
    actionCount: 0,
    pendingCount: 0,
    lastSearch: "",
    allowedExtensions: [],
    searchEngines: {},
    defaultSearchEngine: null,
    chipHandles: null,
};

const modeConfig = {
    songs: {
        placeholder: "Search songs, artists, albums...",
        noun: "song",
        fetcher: searchSongs,
        renderer: renderSongs,
    },
    albums: {
        placeholder: "Search albums...",
        noun: "album",
        fetcher: searchAlbums,
        renderer: renderAlbums,
    },
    artists: {
        placeholder: "Search artists and aliases...",
        noun: "artist",
        fetcher: searchArtists,
        renderer: renderArtists,
    },
    publishers: {
        placeholder: "Search music publishers...",
        noun: "publisher",
        fetcher: searchPublishers,
        renderer: renderPublisherResults,
    },
    tags: {
        placeholder: "Search tags...",
        noun: "tag",
        fetcher: searchTags,
        renderer: renderTags,
    },
    ingest: {
        placeholder: "Enter absolute file path...",
        noun: "ingestion task",
        fetcher: async () => [],
        renderer: (ctx) => {
            import("./renderers/ingestion.js").then((m) =>
                m.renderIngestionPanel(ctx),
            );
        },
    },
};

let detailController = null;
let activeDetailKey = null;
let cachedFileData = null;
let cachedFileDataSongId = null;

const ctx = {
    elements,
    getState: () => state,
    setState(patch) {
        Object.assign(state, patch);
    },
    refreshActiveDetail,
    updateResultsSummary(count, singular) {
        if (!state.currentQuery && !filterSidebar.hasActiveFilters()) {
            state.totalLibraryCount = count;
        } else if (state.totalLibraryCount === 0) {
            // Filters active on load — fetch unfiltered total in background
            searchSongs("").then((items) => {
                if (Array.isArray(items)) {
                    state.totalLibraryCount = items.length;
                    elements.totalCount.textContent = String(items.length);
                    elements.totalCount.style.display = "";
                    elements.statSep.style.display = "";
                }
            }).catch(() => { });
        }
        const isFiltered =
            (state.currentQuery || filterSidebar.hasActiveFilters()) &&
            count !== state.totalLibraryCount;
        elements.matchCount.textContent = String(count);
        elements.totalCount.textContent = String(state.totalLibraryCount);
        elements.totalLabel.textContent = `${singular.charAt(0).toUpperCase()}${singular.slice(1)}s`;
        elements.totalCount.style.display = isFiltered ? "" : "none";
        elements.statSep.style.display = isFiltered ? "" : "none";
    },
    openSongDetail: (...args) => openSongDetail(...args),
    clearSongEditorV2() {
        state.activeSong = null;
        state.activeSongFile = null;
        renderSongEditorEmpty();
    },
    async refreshActiveSongV2(songId) {
        const fresh = await getCatalogSong(songId);
        state.activeSong = fresh;
        // Only refresh sidebar + LED — avoid re-rendering the editor which would
        // wipe chip inputs and lose the onSplit handlers wired at initial load.
        renderActionSidebar(fresh, {
            searchEngines: state.searchEngines,
            defaultSearchEngine: state.defaultSearchEngine,
        });
        updateSyncLed(fresh.id);
        // Fix: Refresh drift indicators to reflect changes (e.g. after confirmation)
        wireDriftIndicators(fresh, state.activeSongFile);

        // Aligned to V2 Audit: Sync chip inputs for properties changed via global actions (like primary tag)
        if (state.chipHandles?.updateField) {
            state.chipHandles.updateField("tags", fresh);
        }
    },
    performSearch: (query) => performSearch(query),
    showDetailPanel(html) {
        elements.detailPanel.innerHTML = html;
        elements.detailPanel.style.display = "flex";
    },
    hideDetailPanel() {
        elements.detailPanel.style.display = "none";
        elements.detailPanel.innerHTML = "";
    },
    showBanner(msg, type = "error") {
        const banner = document.createElement("div");
        banner.className = `ui-banner ui-banner-${type}`;
        banner.textContent = msg;

        // Find existing banner and remove it
        const existing = elements.detailPanel.querySelector(".ui-banner");
        if (existing) existing.remove();

        elements.detailPanel.prepend(banner);

        // Auto-remove if success
        if (type === "success") {
            setTimeout(() => banner.remove(), 4000);
        }
    },
    switchMode,
    navigate,
    getActiveList,
    openSelectedResult,
    updateSelection,
    updateIngestBadges,
    updateCachedIngestResult(path, patch) {
        const state = getState();
        const idx = state.cachedIngestResults.findIndex(r => r.path === path);
        if (idx >= 0) {
            state.cachedIngestResults[idx].result = {
                ...state.cachedIngestResults[idx].result,
                ...patch
            };
        }
    },
    abortDetailRequest,
};

const songActions = new SongActionsHandler(ctx);
const navigationHandler = new NavigationHandler(
    ctx,
    elements,
    elements.searchInput,
);
navigationHandler.setupKeyboardHandler(songActions);
const webSearchHandler = new WebSearchHandler(ctx);
webSearchHandler.setupListeners();

const filterSidebar = new FilterSidebarHandler({
    ...ctx,
    onFilterResults: async (resultPromise) => {
        try {
            const items = await resultPromise;
            setActiveCache("songs", items);
            renderSongs(ctx, items);
        } catch (err) {
            elements.resultsContainer.innerHTML = renderEmptyState(
                `Filter error: ${err.message}`,
            );
        }
    },
    onFilterCleared: () => performSearch(state.currentQuery),
});
filterSidebar.setupListeners();
filterSidebar.load();

function getActiveList() {
    if (state.currentMode === "songs") {
        return state.cachedSongs;
    }
    if (state.currentMode === "albums") {
        return state.cachedAlbums;
    }
    if (state.currentMode === "artists") {
        return state.cachedIdentities;
    }
    if (state.currentMode === "tags") {
        return state.cachedTags;
    }
    return state.cachedPublishers;
}

function setActiveCache(mode, items) {
    if (mode === "songs") {
        state.cachedSongs = items;
    } else if (mode === "albums") {
        state.cachedAlbums = items;
    } else if (mode === "artists") {
        state.cachedIdentities = items;
    } else if (mode === "tags") {
        state.cachedTags = items;
    } else {
        state.cachedPublishers = items;
    }
}

function syncModeUi() {
    document.querySelectorAll(".mode-tab").forEach((button) => {
        button.classList.toggle(
            "active",
            button.dataset.mode === state.currentMode,
        );
    });
    elements.searchInput.placeholder =
        modeConfig[state.currentMode].placeholder;

    const isSongs = state.currentMode === "songs";
    elements.songsWorkspace?.classList.toggle("active", isSongs);
    if (elements.legacyMain) {
        // Aligned to V2 Audit: Other modes still use legacy card results container
        elements.legacyMain.style.display = isSongs ? "none" : "block";
    }
    if (isSongs) renderSongEditorEmpty();
}

function updateSelection() {
    const songListPanel = document.getElementById("song-list-panel");
    const songsWorkspaceActive = document.getElementById("songs-workspace")?.classList.contains("active");
    if (songListPanel && songsWorkspaceActive) {
        const rows = songListPanel.querySelectorAll("[data-selectable='true']");
        rows.forEach((row, index) => {
            row.classList.toggle("selected", index === state.selectedIndex);
        });
        if (state.selectedIndex >= 0 && state.selectedIndex < rows.length) {
            rows[state.selectedIndex].scrollIntoView({ block: "nearest" });
        }
        return;
    }

    const cards = elements.resultsContainer.querySelectorAll(
        "[data-selectable='true']",
    );
    cards.forEach((card, index) => {
        card.classList.toggle("active", index === state.selectedIndex);
    });

    if (state.selectedIndex >= 0 && state.selectedIndex < cards.length) {
        cards[state.selectedIndex].scrollIntoView({ block: "nearest" });
    }
}

function abortDetailRequest() {
    if (detailController) {
        detailController.abort();
    }
    detailController = null;
    activeDetailKey = null;
}

function beginDetailRequest(mode, id) {
    abortDetailRequest();
    detailController = new AbortController();
    activeDetailKey = `${mode}:${id}`;
    return { signal: detailController.signal };
}

function isActiveDetail(mode, id) {
    return state.currentMode === mode && activeDetailKey === `${mode}:${id}`;
}

async function performSearch(query = state.currentQuery) {
    const mode = state.currentMode;
    const { fetcher, renderer } = modeConfig[mode];
    state.currentQuery = query;
    try {
        const items = await fetcher(query, state.isDeep);
        if (
            items === ABORTED ||
            mode !== state.currentMode ||
            query !== state.currentQuery
        ) {
            return;
        }

        setActiveCache(mode, items);
        renderer(ctx, items);
    } catch (error) {
        if (isAbortError(error)) {
            return;
        }
        elements.resultsContainer.innerHTML = renderEmptyState(
            `Error: ${error.message}`,
        );
        elements.totalCount.textContent = "0";
        elements.matchCount.textContent = "0";
    }
}

async function switchMode(mode) {
    if (!modeConfig[mode]) {
        return;
    }

    clearTimeout(state.debounceTimer);
    abortAllSearches();
    abortDetailRequest();
    state.currentMode = mode;
    state.currentQuery = "";
    state.selectedIndex = -1;

    // Aligned to Blueprint: Entering Ingest mode clears the session counters
    if (mode === "ingest" && state.pendingCount > 0) {
        try {
            const status = await getIngestStatus();
            updateIngestBadges({ success: status.success, action: status.action, pending: status.pending });
        } catch (e) {
            console.error("Failed to sync ingest status:", e);
        }
    }
    elements.searchInput.value = "";
    syncModeUi();
    ctx.hideDetailPanel();
    if (mode === "songs" && filterSidebar.hasActiveFilters()) {
        filterSidebar.reapply();
    } else {
        performSearch("");
    }
}

function navigate(mode, query = "") {
    clearTimeout(state.debounceTimer);
    abortAllSearches();
    abortDetailRequest();
    state.currentMode = mode;
    state.currentQuery = String(query || "").trim();
    state.selectedIndex = -1;
    elements.searchInput.value = state.currentQuery;
    syncModeUi();
    ctx.hideDetailPanel();
    performSearch(state.currentQuery);
    elements.searchInput.focus();
}

async function openSongDetail(song, { reuseFileData = false } = {}) {
    const existingContent =
        elements.detailPanel.querySelector(".detail-content");
    const savedScroll = existingContent ? existingContent.scrollTop : 0;
    const request = beginDetailRequest("songs", song.id);
    const isSameSong = state.activeSong?.id === song.id;
    if (!isSameSong) renderSongDetailLoading(ctx, song);

    const fetchFile =
        !reuseFileData || cachedFileDataSongId !== String(song.id)
            ? getSongDetail(song.id, { signal: request.signal })
            : Promise.resolve(cachedFileData);

    const [catalogResult, fileResult, auditResult] = await Promise.allSettled([
        getCatalogSong(song.id, { signal: request.signal }),
        fetchFile,
        getAuditHistory("Songs", song.id, { signal: request.signal }),
    ]);

    if (
        [catalogResult, fileResult, auditResult].some(
            (r) => r.status === "rejected" && isAbortError(r.reason),
        )
    ) {
        return;
    }
    if (!isActiveDetail("songs", song.id)) {
        return;
    }

    const catalogSong =
        catalogResult.status === "fulfilled" && catalogResult.value
            ? catalogResult.value
            : song;
    const fileData =
        fileResult.status === "fulfilled" ? fileResult.value : null;
    cachedFileData = fileData;
    cachedFileDataSongId = String(song.id);
    state.activeSong = catalogSong;
    const auditHistory =
        auditResult.status === "fulfilled" ? auditResult.value : [];
    renderSongDetailComplete(
        ctx,
        catalogSong,
        fileData,
        auditHistory,
        state.id3Frames,
        state.allRoles,
        state.searchEngines,
        state.defaultSearchEngine,
    );
    updateSyncLed(catalogSong.id);
    if (savedScroll) {
        const newContent =
            elements.detailPanel.querySelector(".detail-content");
        if (newContent) {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    newContent.scrollTop = savedScroll;
                });
            });
        }
    }
}

async function openAlbumDetail(album) {
    const request = beginDetailRequest("albums", album.id);
    renderAlbumDetailLoading(ctx, album);

    const [albumResult, auditResult] = await Promise.allSettled([
        getAlbumDetail(album.id, { signal: request.signal }),
        getAuditHistory("Albums", album.id, { signal: request.signal }),
    ]);

    if (
        (albumResult.status === "rejected" &&
            isAbortError(albumResult.reason)) ||
        (auditResult.status === "rejected" && isAbortError(auditResult.reason))
    ) {
        return;
    }
    if (!isActiveDetail("albums", album.id)) {
        return;
    }
    if (albumResult.status === "rejected") {
        ctx.showDetailPanel(
            '<div class="detail-content"><div class="file-status missing">Failed to load album details.</div></div>',
        );
        return;
    }

    renderAlbumDetailComplete(
        ctx,
        albumResult.value,
        auditResult.status === "fulfilled" ? auditResult.value : [],
    );
}

async function openArtistDetail(artist) {
    const request = beginDetailRequest("artists", artist.id);
    renderArtistDetailLoading(ctx, artist);

    const [treeResult, songsResult, auditResult] = await Promise.allSettled([
        getArtistTree(artist.id, { signal: request.signal }),
        getArtistSongs(artist.id, { signal: request.signal }),
        getAuditHistory("Identities", artist.id, { signal: request.signal }),
    ]);

    if (
        (treeResult.status === "rejected" && isAbortError(treeResult.reason)) ||
        (songsResult.status === "rejected" &&
            isAbortError(songsResult.reason)) ||
        (auditResult.status === "rejected" && isAbortError(auditResult.reason))
    ) {
        return;
    }
    if (!isActiveDetail("artists", artist.id)) {
        return;
    }
    if (songsResult.status === "rejected") {
        ctx.showDetailPanel(
            '<div class="detail-content"><div class="file-status missing">Failed to load artist details.</div></div>',
        );
        return;
    }

    const tree = treeResult.status === "fulfilled" ? treeResult.value : artist;
    renderArtistDetailComplete(
        ctx,
        tree,
        songsResult.value,
        auditResult.status === "fulfilled" ? auditResult.value : [],
    );
}

async function openPublisherDetail(publisher) {
    const request = beginDetailRequest("publishers", publisher.id);
    renderPublisherDetailLoading(ctx, publisher);

    const [publisherResult, songsResult] = await Promise.allSettled([
        getPublisherDetail(publisher.id, { signal: request.signal }),
        getPublisherSongs(publisher.id, { signal: request.signal }),
    ]);

    if (
        (publisherResult.status === "rejected" &&
            isAbortError(publisherResult.reason)) ||
        (songsResult.status === "rejected" && isAbortError(songsResult.reason))
    ) {
        return;
    }
    if (!isActiveDetail("publishers", publisher.id)) {
        return;
    }
    if (songsResult.status === "rejected") {
        ctx.showDetailPanel(
            '<div class="detail-content"><div class="file-status missing">Failed to load repertoire.</div></div>',
        );
        return;
    }

    const fullPublisher =
        publisherResult.status === "fulfilled"
            ? publisherResult.value
            : publisher;
    renderPublisherDetailComplete(ctx, fullPublisher, songsResult.value);
}

async function openTagDetail(tag) {
    const request = beginDetailRequest("tags", tag.id);
    renderTagDetailLoading(ctx, tag);

    const [tagResult, songsResult] = await Promise.allSettled([
        getTagDetail(tag.id, { signal: request.signal }),
        getTagSongs(tag.id, { signal: request.signal }),
    ]);

    if (
        (tagResult.status === "rejected" && isAbortError(tagResult.reason)) ||
        (songsResult.status === "rejected" && isAbortError(songsResult.reason))
    ) {
        return;
    }
    if (!isActiveDetail("tags", tag.id)) {
        return;
    }
    if (songsResult.status === "rejected") {
        ctx.showDetailPanel(
            '<div class="detail-content"><div class="file-status missing">Failed to load songs.</div></div>',
        );
        return;
    }

    const fullTag = tagResult.status === "fulfilled" ? tagResult.value : tag;
    renderTagDetailComplete(ctx, fullTag, songsResult.value);
}

function refreshActiveDetail() {
    if (!activeDetailKey) return;
    const [mode, id] = activeDetailKey.split(":");
    const list = getActiveList();
    const item = list.find((i) => String(i.id) === id);
    if (!item) return;
    if (mode === "songs") openSongDetail(item, { reuseFileData: true });
    else if (mode === "albums") openAlbumDetail(item);
    else if (mode === "artists") openArtistDetail(item);
    else if (mode === "tags") openTagDetail(item);
    else if (mode === "publishers") openPublisherDetail(item);
}

async function openSelectedResult(index) {
    const items = getActiveList();
    const selected = items[index];
    if (!selected) {
        return;
    }

    if (state.currentMode === "songs" && document.getElementById("songs-workspace")?.classList.contains("active")) {
        const request = beginDetailRequest("songs", selected.id);
        const [result, fileData] = await Promise.all([
            getCatalogSong(selected.id, { signal: request.signal }).catch((e) => { if (!isAbortError(e)) throw e; return null; }),
            getSongDetail(selected.id, { signal: request.signal }).catch(() => null),
        ]);
        if (!result || !isActiveDetail("songs", selected.id)) return;
        state.activeSong = result;
        state.activeSongFile = fileData;
        renderSongEditorV2(result, fileData);
        wireDriftIndicators(result, fileData);
        wireAuditHistory(result.id, () => getAuditHistory("Songs", result.id));
        renderActionSidebar(result, {
            searchEngines: state.searchEngines,
            defaultSearchEngine: state.defaultSearchEngine,
        });
        updateSyncLed(result.id);
        wireScalarInputs(result, state.validationRules, (fresh) => {
            state.activeSong = fresh;
            wireDriftIndicators(fresh, state.activeSongFile);
            renderActionSidebar(fresh, { searchEngines: state.searchEngines, defaultSearchEngine: state.defaultSearchEngine });
        });
        state.chipHandles = wireChipInputs(
            result,
            (fresh) => {
                state.activeSong = fresh;
                wireDriftIndicators(fresh, state.activeSongFile);
                renderActionSidebar(fresh, { searchEngines: state.searchEngines, defaultSearchEngine: state.defaultSearchEngine });
            },
            async ({ songId, text, role, creditId }) => {
                const { openSplitterModal } = await import("./components/splitter_modal.js");
                openSplitterModal({
                    songId,
                    text,
                    target: "credits",
                    classification: role,
                    remove: { type: "credit", id: creditId },
                    separators: state.validationRules?.credit_separators || [],
                    onConfirm: async () => {
                        const fresh = await getCatalogSong(songId);
                        state.activeSong = fresh;
                        state.chipHandles?.updateField(role, fresh);
                        // Fixed: wireDriftIndicators is now called in refreshActiveSongV2 path, 
                        // but keeping here for explicit confirmation logic.
                        wireDriftIndicators(fresh, state.activeSongFile);
                        renderActionSidebar(fresh, {
                            searchEngines: state.searchEngines,
                            defaultSearchEngine: state.defaultSearchEngine,
                        });
                    },
                });
            },
            state.validationRules,
        );
    } else if (state.currentMode === "songs") {
        await openSongDetail(selected);
    } else if (state.currentMode === "albums") {
        await openAlbumDetail(selected);
    } else if (state.currentMode === "artists") {
        await openArtistDetail(selected);
    } else if (state.currentMode === "tags") {
        await openTagDetail(selected);
    } else {
        await openPublisherDetail(selected);
    }
}

/**
 * Updates the Triple-Badge system on the Ingest tab.
 * @param {Object} counts - {success?, action?, pending?} deltas or absolute values
 * @param {boolean} replace - If true, replaces the counts instead of adding
 */
function updateIngestBadges(counts = {}) {
    const tab = document.querySelector(".mode-tab[data-mode='ingest']");
    if (!tab) return;

    // Sync state (Absolute only, NO MATH)
    state.successCount = counts.success ?? state.successCount;
    state.actionCount = counts.action ?? state.actionCount;
    state.pendingCount = counts.pending ?? state.pendingCount;

    // Remove old badge container
    tab.querySelector(".ingest-badge-container")?.remove();

    const total = state.pendingCount + state.successCount + state.actionCount;
    if (total === 0) return;

    const container = document.createElement("div");
    container.className = "ingest-badge-container";

    if (state.pendingCount > 0) {
        const b = document.createElement("span");
        b.className = "ingest-badge pending";
        b.title = `${state.pendingCount} files currently processing`;
        b.textContent = String(state.pendingCount);
        container.appendChild(b);
    }

    if (state.successCount > 0) {
        const b = document.createElement("span");
        b.className = "ingest-badge success";
        b.title = `${state.successCount} songs newly ingested — click to refresh library`;
        b.dataset.action = "refresh-results";
        b.textContent = `↺ ${state.successCount}`;
        container.appendChild(b);
    }

    if (state.actionCount > 0) {
        const b = document.createElement("span");
        b.className = "ingest-badge danger";
        b.title = `${state.actionCount} songs need review (Conflicts/Errors)`;
        b.textContent = String(state.actionCount);
        container.appendChild(b);
    }

    tab.appendChild(container);
}

async function setupHeaderDropZone() {
    const tab = document.querySelector(".mode-tab[data-mode='ingest']");
    if (!tab) return;

    tab.addEventListener("dragover", (e) => {
        e.preventDefault();
        tab.classList.add("drop-target");
    });

    tab.addEventListener("dragleave", (e) => {
        if (!tab.contains(e.relatedTarget)) {
            tab.classList.remove("drop-target");
        }
    });

    tab.addEventListener("drop", async (e) => {
        e.preventDefault();
        e.stopPropagation();
        tab.classList.remove("drop-target");

        const items = e.dataTransfer?.items;
        if (!items || items.length === 0) return;

        const allFiles = await collectFilesFromItems(items, state.allowedExtensions);
        if (allFiles.length === 0) {
            showToast("No valid audio files found in drop", "error", 3000);
            return;
        }

        const formData = new FormData();
        allFiles.forEach(f => formData.append("files", f));

        try {
            const response = await uploadFiles(allFiles);
            if (!response.ok) throw new Error("Upload failed");

            await readNdjsonStream(response, (update) => {
                if (update.error) { showToast(update.error, "error"); return; }

                updateIngestBadges({ success: update.success, action: update.action, pending: update.pending });

                const res = update.last_result;
                if (res) {
                    const title = res.song?.media_name || res.title || basename(res.staged_path) || "Unknown File";
                    if (res.status === "INGESTED") showToast(`Ingested: ${title}`, "success", 2000);
                    else if (res.status === "ALREADY_EXISTS") showToast(`Already exists: ${title}`, "info", 2000);
                    else if (res.status === "CONFLICT") showToast(`Conflict: ${title}`, "error", 5000);
                    else if (res.status === "ERROR") showToast(`Error: ${res.message || title}`, "error", 5000);
                    else if (res.status === "PENDING_CONVERT") showToast(`WAV Staged: ${title}`, "info", 3000);
                }
            });
        } catch (error) {
            console.error("Ingestion failed:", error);
            showToast("Ingestion failed: " + error.message, "error", 5000);
        }
    });
}

document.addEventListener("checkchange", () => {
    if (state.currentMode !== "songs") return;
    const panel = document.getElementById("song-list-panel");
    if (!panel) return;
    const checked = panel.querySelectorAll(".col-check input[type=checkbox]:checked");
    if (checked.length > 1) {
        renderSongEditorMultiSelect(checked.length);
    } else if (checked.length === 0) {
        renderSongEditorEmpty();
        state.activeSong = null;
        state.activeSongFile = null;
    }
    // If exactly 1 checked, the row click already opened the editor — do nothing
});

document.addEventListener("click", async (event) => {
    const actionTarget = event.target.closest("[data-action]");
    if (!actionTarget) return;

    // Protocol: Modals are top-level. Block global click actions if any modal is open,
    // UNLESS the action is actually inside a modal (edit-modal or link-modal)
    // or is a close-modal action.
    const { action } = actionTarget.dataset;
    const isModalComponent = actionTarget.closest(".link-modal");
    const isCloseAction =
        action === "close-edit-modal" ||
        action === "close-link-modal" ||
        action === "close-spotify-modal" ||
        action === "close-splitter-modal" ||
        action === "close-filename-parser-modal";

    if (isModalOpen() && !isModalComponent && !isCloseAction) {
        return;
    }

    // High-density delegation for Song Actions
    try {
        if (await songActions.handle(event)) return;
    } catch (err) {
        console.error(`[Main] SongActionsHandler CRASHED: ${err.message}`, err);
    }

    // Navigation actions
    if (await navigationHandler.handle(event, songActions)) {
        return;
    }

    if (action === "toggle-filter-sidebar") {
        filterSidebar.toggle();
        document
            .getElementById("filter-toggle-btn")
            ?.classList.toggle("active", filterSidebar._sidebarVisible);
        return;
    }
});

elements.searchInput.addEventListener("input", (event) => {
    clearTimeout(state.debounceTimer);
    state.currentQuery = event.target.value.trim();
    filterSidebar.setSearchText(state.currentQuery);
    state.debounceTimer = setTimeout(() => {
        performSearch(state.currentQuery);
    }, 250);
});

elements.deepSearchToggle.addEventListener("change", (event) => {
    state.isDeep = event.target.checked;
    performSearch(state.currentQuery);
});

syncModeUi();
initToastSystem();
Promise.all([
    fetchValidationRules().catch(() => null),
    fetchId3Frames().catch(() => null),
    fetchRoles(),
    getAcceptedFormats().catch(() => []),
    fetchAppConfig().catch(() => null),
]).then(([rules, frames, roles, exts, appConfig]) => {
    state.validationRules = rules;
    state.id3Frames = frames;
    state.allRoles = roles;
    state.allowedExtensions = exts;
    if (appConfig) {
        state.searchEngines = appConfig.search_engines || {};
        state.defaultSearchEngine = appConfig.default_search_engine || null;
    }
});
setupHeaderDropZone();
performSearch("");

// Restore in-progress badges on page reload
(async () => {
    try {
        const status = await getIngestStatus();
        if (status.pending > 0) {
            updateIngestBadges({ success: status.success, action: status.action, pending: status.pending });
        }
    } catch (e) {
        console.error("Initial ingest sync failed", e);
    }
})();
