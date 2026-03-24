import {
    ABORTED,
    abortAllSearches,
    getAlbumDetail,
    getArtistSongs,
    getArtistTree,
    getAuditHistory,
    getPublisherDetail,
    getPublisherSongs,
    getSongDetail,
    isAbortError,
    searchAlbums,
    searchArtists,
    searchPublishers,
    searchSongs,
} from "./api.js";
import { renderAlbums, renderAlbumDetailComplete, renderAlbumDetailLoading } from "./renderers/albums.js";
import { renderArtists, renderArtistDetailComplete, renderArtistDetailLoading } from "./renderers/artists.js";
import { renderPublishers as renderPublisherResults, renderPublisherDetailComplete, renderPublisherDetailLoading } from "./renderers/publishers.js";
import { renderSongDetailComplete, renderSongDetailLoading, renderSongs } from "./renderers/songs.js";
import { formatCountLabel, renderEmptyState } from "./components/utils.js";

const elements = {
    searchInput: document.getElementById("searchInput"),
    resultsContainer: document.getElementById("results-container"),
    detailPanel: document.getElementById("detail-panel"),
    resultsCount: document.getElementById("results-count"),
    totalCount: document.getElementById("total-count"),
    totalLabel: document.getElementById("total-label"),
    matchCount: document.getElementById("match-count"),
    matchLabel: document.getElementById("match-label"),
};

const state = {
    currentMode: "songs",
    cachedSongs: [],
    cachedIdentities: [],
    cachedAlbums: [],
    cachedPublishers: [],
    debounceTimer: null,
    currentQuery: "",
    selectedIndex: -1,
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
    ingest: {
        placeholder: "Enter absolute file path...",
        noun: "ingestion task",
        fetcher: async () => [],
        renderer: (ctx) => {
            import("./renderers/ingestion.js").then((m) => m.renderIngestionPanel(ctx));
        },
    },
};

let detailController = null;
let activeDetailKey = null;

const ctx = {
    elements,
    getState: () => state,
    setState(patch) {
        Object.assign(state, patch);
    },
    updateResultsSummary(count, singular) {
        elements.resultsCount.textContent = formatCountLabel(count, singular);
        elements.totalCount.textContent = String(count);
        elements.totalLabel.textContent = `${singular.charAt(0).toUpperCase()}${singular.slice(1)}s Loaded`;
        elements.matchCount.textContent = String(count);
        elements.matchLabel.textContent = state.currentQuery ? "Matches" : "Visible";
    },
    showDetailPanel(html) {
        elements.detailPanel.innerHTML = html;
        elements.detailPanel.style.display = "flex";
    },
    hideDetailPanel() {
        elements.detailPanel.style.display = "none";
        elements.detailPanel.innerHTML = "";
    },
};

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
    return state.cachedPublishers;
}

function setActiveCache(mode, items) {
    if (mode === "songs") {
        state.cachedSongs = items;
    } else if (mode === "albums") {
        state.cachedAlbums = items;
    } else if (mode === "artists") {
        state.cachedIdentities = items;
    } else {
        state.cachedPublishers = items;
    }
}

function syncModeUi() {
    document.querySelectorAll(".mode-tab").forEach((button) => {
        button.classList.toggle("active", button.dataset.mode === state.currentMode);
    });
    elements.searchInput.placeholder = modeConfig[state.currentMode].placeholder;
    elements.matchLabel.textContent = state.currentQuery ? "Matches" : "Visible";
}

function updateSelection() {
    const cards = elements.resultsContainer.querySelectorAll("[data-selectable='true']");
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
    const { fetcher, renderer, noun } = modeConfig[mode];
    state.currentQuery = query;
    elements.matchLabel.textContent = query ? "Matches" : "Visible";

    try {
        const items = await fetcher(query);
        if (items === ABORTED || mode !== state.currentMode || query !== state.currentQuery) {
            return;
        }

        setActiveCache(mode, items);
        renderer(ctx, items);
    } catch (error) {
        if (isAbortError(error)) {
            return;
        }
        elements.resultsContainer.innerHTML = renderEmptyState(`Error: ${error.message}`);
        elements.resultsCount.textContent = `0 ${noun}s`;
        elements.totalCount.textContent = "0";
        elements.matchCount.textContent = "0";
    }
}

function switchMode(mode) {
    if (!modeConfig[mode]) {
        return;
    }

    clearTimeout(state.debounceTimer);
    abortAllSearches();
    abortDetailRequest();
    state.currentMode = mode;
    state.currentQuery = "";
    state.selectedIndex = -1;
    elements.searchInput.value = "";
    syncModeUi();
    ctx.hideDetailPanel();
    performSearch("");
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

async function openSongDetail(song) {
    const request = beginDetailRequest("songs", song.id);
    renderSongDetailLoading(ctx, song);

    const [fileResult, auditResult] = await Promise.allSettled([
        getSongDetail(song.id, { signal: request.signal }),
        getAuditHistory("Songs", song.id, { signal: request.signal }),
    ]);

    if ((fileResult.status === "rejected" && isAbortError(fileResult.reason)) || (auditResult.status === "rejected" && isAbortError(auditResult.reason))) {
        return;
    }
    if (!isActiveDetail("songs", song.id)) {
        return;
    }

    const fileData = fileResult.status === "fulfilled" ? fileResult.value : null;
    const auditHistory = auditResult.status === "fulfilled" ? auditResult.value : [];
    renderSongDetailComplete(ctx, song, fileData, auditHistory);
}

async function openAlbumDetail(album) {
    const request = beginDetailRequest("albums", album.id);
    renderAlbumDetailLoading(ctx, album);

    const [albumResult, auditResult] = await Promise.allSettled([
        getAlbumDetail(album.id, { signal: request.signal }),
        getAuditHistory("Albums", album.id, { signal: request.signal }),
    ]);

    if ((albumResult.status === "rejected" && isAbortError(albumResult.reason)) || (auditResult.status === "rejected" && isAbortError(auditResult.reason))) {
        return;
    }
    if (!isActiveDetail("albums", album.id)) {
        return;
    }
    if (albumResult.status === "rejected") {
        ctx.showDetailPanel('<div class="detail-content"><div class="file-status missing">Failed to load album details.</div></div>');
        return;
    }

    renderAlbumDetailComplete(ctx, albumResult.value, auditResult.status === "fulfilled" ? auditResult.value : []);
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
        (songsResult.status === "rejected" && isAbortError(songsResult.reason)) ||
        (auditResult.status === "rejected" && isAbortError(auditResult.reason))
    ) {
        return;
    }
    if (!isActiveDetail("artists", artist.id)) {
        return;
    }
    if (songsResult.status === "rejected") {
        ctx.showDetailPanel('<div class="detail-content"><div class="file-status missing">Failed to load artist details.</div></div>');
        return;
    }

    const tree = treeResult.status === "fulfilled" ? treeResult.value : artist;
    renderArtistDetailComplete(ctx, tree, songsResult.value, auditResult.status === "fulfilled" ? auditResult.value : []);
}

async function openPublisherDetail(publisher) {
    const request = beginDetailRequest("publishers", publisher.id);
    renderPublisherDetailLoading(ctx, publisher);

    const [publisherResult, songsResult] = await Promise.allSettled([
        getPublisherDetail(publisher.id, { signal: request.signal }),
        getPublisherSongs(publisher.id, { signal: request.signal }),
    ]);

    if ((publisherResult.status === "rejected" && isAbortError(publisherResult.reason)) || (songsResult.status === "rejected" && isAbortError(songsResult.reason))) {
        return;
    }
    if (!isActiveDetail("publishers", publisher.id)) {
        return;
    }
    if (songsResult.status === "rejected") {
        ctx.showDetailPanel('<div class="detail-content"><div class="file-status missing">Failed to load repertoire.</div></div>');
        return;
    }

    const fullPublisher = publisherResult.status === "fulfilled" ? publisherResult.value : publisher;
    renderPublisherDetailComplete(ctx, fullPublisher, songsResult.value);
}

async function openSelectedResult(index) {
    const items = getActiveList();
    const selected = items[index];
    if (!selected) {
        return;
    }

    if (state.currentMode === "songs") {
        await openSongDetail(selected);
    } else if (state.currentMode === "albums") {
        await openAlbumDetail(selected);
    } else if (state.currentMode === "artists") {
        await openArtistDetail(selected);
    } else {
        await openPublisherDetail(selected);
    }
}

document.addEventListener("click", (event) => {
    const actionTarget = event.target.closest("[data-action]");
    if (!actionTarget) {
        return;
    }

    const { action } = actionTarget.dataset;
    if (action === "switch-mode") {
        switchMode(actionTarget.dataset.mode);
        return;
    }

    if (action === "select-result") {
        const index = Number(actionTarget.dataset.index);
        state.selectedIndex = Number.isNaN(index) ? -1 : index;
        updateSelection();
        openSelectedResult(state.selectedIndex);
        return;
    }

    if (action === "navigate-search") {
        navigate(actionTarget.dataset.mode, actionTarget.dataset.query || "");
        return;
    }

    if (action === "delete-song") {
        const { id, title } = actionTarget.dataset;
        if (confirm(`Are you sure you want to permanently delete "${title}"? This cannot be undone.`)) {
            import("./api.js").then(async (m) => {
                try {
                    await m.deleteSong(id);
                    ctx.hideDetailPanel();
                    performSearch(); // Refresh the current view
                } catch (err) {
                    alert(`Deletion failed: ${err.message}`);
                }
            });
        }
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && elements.detailPanel.style.display === "flex") {
        abortDetailRequest();
        ctx.hideDetailPanel();
        state.selectedIndex = -1;
        updateSelection();
        return;
    }

    const items = getActiveList();
    if (document.activeElement !== elements.searchInput || !items.length) {
        return;
    }

    if (event.key === "ArrowDown") {
        event.preventDefault();
        state.selectedIndex = Math.min(state.selectedIndex + 1, items.length - 1);
        updateSelection();
        return;
    }

    if (event.key === "ArrowUp") {
        event.preventDefault();
        state.selectedIndex = Math.max(state.selectedIndex - 1, -1);
        updateSelection();
        return;
    }

    if (event.key === "Enter" && state.selectedIndex >= 0) {
        event.preventDefault();
        openSelectedResult(state.selectedIndex);
    }
});

elements.searchInput.addEventListener("input", (event) => {
    clearTimeout(state.debounceTimer);
    state.currentQuery = event.target.value.trim();
    state.debounceTimer = setTimeout(() => {
        performSearch(state.currentQuery);
    }, 250);
});

syncModeUi();
performSearch("");
