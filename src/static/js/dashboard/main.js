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
    getTagDetail,
    getTagSongs,
    isAbortError,
    searchAlbums,
    searchArtists,
    searchPublishers,
    searchSongs,
    searchTags,
} from "./api.js";
import { renderAlbums, renderAlbumDetailComplete, renderAlbumDetailLoading } from "./renderers/albums.js";
import { renderArtists, renderArtistDetailComplete, renderArtistDetailLoading } from "./renderers/artists.js";
import { renderPublishers as renderPublisherResults, renderPublisherDetailComplete, renderPublisherDetailLoading } from "./renderers/publishers.js";
import { renderTags, renderTagDetailComplete, renderTagDetailLoading } from "./renderers/tags.js";
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
    deepSearchToggle: document.getElementById("deepSearchToggle"),
};

const state = {
    currentMode: "songs",
    cachedSongs: [],
    cachedIdentities: [],
    cachedAlbums: [],
    cachedPublishers: [],
    cachedTags: [],
    displayedItems: [], // Track currently displayed items in visual order (for keyboard nav)
    debounceTimer: null,
    currentQuery: "",
    selectedIndex: -1,
    isDeep: false,
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
        const items = await fetcher(query, state.isDeep);
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

async function openTagDetail(tag) {
    const request = beginDetailRequest("tags", tag.id);
    renderTagDetailLoading(ctx, tag);

    const [tagResult, songsResult] = await Promise.allSettled([
        getTagDetail(tag.id, { signal: request.signal }),
        getTagSongs(tag.id, { signal: request.signal }),
    ]);

    if ((tagResult.status === "rejected" && isAbortError(tagResult.reason)) || (songsResult.status === "rejected" && isAbortError(songsResult.reason))) {
        return;
    }
    if (!isActiveDetail("tags", tag.id)) {
        return;
    }
    if (songsResult.status === "rejected") {
        ctx.showDetailPanel('<div class="detail-content"><div class="file-status missing">Failed to load songs.</div></div>');
        return;
    }

    const fullTag = tagResult.status === "fulfilled" ? tagResult.value : tag;
    renderTagDetailComplete(ctx, fullTag, songsResult.value);
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
    } else if (state.currentMode === "tags") {
        await openTagDetail(selected);
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
        event.preventDefault(); // Prevent focus change to keep keyboard nav working
        const index = Number(actionTarget.dataset.index);
        state.selectedIndex = Number.isNaN(index) ? -1 : index;
        updateSelection();

        // Use displayedItems + ID lookup to handle sorting correctly
        const selected = state.displayedItems[index];
        if (selected) {
            const cachedList = getActiveList();
            const actualIndex = cachedList.findIndex(item => item.id === selected.id);
            if (actualIndex >= 0) {
                openSelectedResult(actualIndex);
            }
        }
        return;
    }

    if (action === "navigate-search") {
        navigate(actionTarget.dataset.mode, actionTarget.dataset.query || "");
        return;
    }

    if (action === "resolve-conflict") {
        const { ghostId, stagedPath } = actionTarget.dataset;

        // Disable the button to prevent double-clicks
        actionTarget.disabled = true;
        actionTarget.textContent = "Processing...";

        fetch(`/api/v1/ingest/resolve-conflict?ghost_id=${ghostId}&staged_path=${encodeURIComponent(stagedPath)}`, {
            method: "POST",
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.status === "INGESTED") {
                    // Success - replace the conflict card with success message
                    const card = actionTarget.closest(".result-card");
                    if (card) {
                        card.style.background = "rgba(76, 175, 80, 0.1)";
                        card.style.borderLeft = "3px solid #4CAF50";
                        const conflictBox = card.querySelector('[style*="rgba(255, 149, 0"]');
                        if (conflictBox) {
                            conflictBox.innerHTML = `
                                <div style="color: #4CAF50; font-weight: 600; margin-bottom: 0.5rem;">✓ Ghost Record Reactivated</div>
                                <div class="muted-note" style="font-size: 0.85rem;">
                                    Song "${data.song?.media_name || "Unknown"}" has been restored with new metadata.
                                </div>
                            `;
                        }
                    }
                } else {
                    actionTarget.disabled = false;
                    actionTarget.textContent = "Re-ingest & Activate";
                    console.error("Failed to reactivate:", data.message);
                }
            })
            .catch((err) => {
                actionTarget.disabled = false;
                actionTarget.textContent = "Re-ingest & Activate";
                console.error("Error:", err.message);
            });
        return;
    }

    if (action === "delete-song") {
        const { id, title } = actionTarget.dataset;

        // Two-stage confirmation to avoid popup blockers
        if (!actionTarget.classList.contains("confirming")) {
            const originalText = actionTarget.textContent;
            actionTarget.classList.add("confirming");
            actionTarget.textContent = "Confirm Delete?";

            // Reset after 3 seconds if not clicked again
            setTimeout(() => {
                if (actionTarget.classList.contains("confirming") && !actionTarget.disabled) {
                    actionTarget.classList.remove("confirming");
                    actionTarget.textContent = originalText;
                }
            }, 3000);
            return;
        }

        // Second click - proceed with deletion
        actionTarget.disabled = true;
        actionTarget.textContent = "Deleting...";

        import("./api.js").then(async (m) => {
            try {
                await m.deleteSong(id);
                ctx.hideDetailPanel();
                performSearch(); // Refresh the current view
            } catch (err) {
                actionTarget.disabled = false;
                actionTarget.classList.remove("confirming");
                actionTarget.textContent = "Delete";
                console.error(`Deletion failed: ${err.message}`);
                alert(`Deletion failed: ${err.message}`);
            }
        });
    }
});

document.addEventListener("keydown", (event) => {
    // Escape always works to close detail panel
    if (event.key === "Escape" && elements.detailPanel.style.display === "flex") {
        abortDetailRequest();
        ctx.hideDetailPanel();
        state.selectedIndex = -1;
        updateSelection();
        return;
    }

    // Don't intercept arrow keys when actively typing in search
    if (document.activeElement === elements.searchInput) {
        return;
    }

    // Arrow key navigation works globally (even after clicking buttons)
    const items = state.displayedItems;
    if (!items.length) {
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
        // Use displayedItems + ID lookup to handle sorting
        const selected = items[state.selectedIndex];
        if (selected) {
            const cachedList = getActiveList();
            const actualIndex = cachedList.findIndex(item => item.id === selected.id);
            if (actualIndex >= 0) {
                openSelectedResult(actualIndex);
            }
        }
    }
});

elements.searchInput.addEventListener("input", (event) => {
    clearTimeout(state.debounceTimer);
    state.currentQuery = event.target.value.trim();
    state.debounceTimer = setTimeout(() => {
        performSearch(state.currentQuery);
    }, 250);
});

elements.deepSearchToggle.addEventListener("change", (event) => {
    state.isDeep = event.target.checked;
    performSearch(state.currentQuery);
});

syncModeUi();
performSearch("");
