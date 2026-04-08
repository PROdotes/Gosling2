import {
    ABORTED,
    abortAllSearches,
    addSongPublisher,
    fetchValidationRules,
    getAlbumDetail,
    getArtistSongs,
    addIdentityAlias,
    removeIdentityAlias,
    getArtistTree,
    getAuditHistory,
    getCatalogSong,
    getPublisherDetail,
    getPublisherSongs,
    getSongDetail,
    getTagDetail,
    getTagSongs,
    isAbortError,
    patchSongScalars,
    removeSongPublisher,
    searchAlbums,
    searchArtists,
    searchPublishers,
    searchSongs,
    searchTags,
    updatePublisher,
    setPublisherParent,
    updateTag,
    getTagCategories,
    addSongTag,
    removeSongTag,
    fetchId3Frames,
    addSongCredit,
    removeSongCredit,
    updateCreditName,
    fetchRoles,
    formatMetadataCase,
    setPrimarySongTag,
    uploadFiles,
    getAcceptedFormats,
} from "./api.js";
import { initToastSystem, showToast } from "./components/toast.js";
import { collectFilesFromItems } from "./renderers/ingestion.js";
import { openLinkModal, closeLinkModal } from "./components/link_modal.js";
import { openEditModal, closeEditModal } from "./components/edit_modal.js";
import { openScrubberModal, closeScrubberModal } from "./components/scrubber_modal.js";
import { openSpotifyModal, closeSpotifyModal } from "./components/spotify_modal.js";
import { openSplitterModal, closeSplitterModal } from "./components/splitter_modal.js";
import * as orch from "./orchestrator.js";
import { activateInlineEdit } from "./components/inline_editor.js";
import { SongActionsHandler } from "./handlers/song_actions.js";
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
    totalCount: document.getElementById("total-count"),
    totalLabel: document.getElementById("total-label"),
    matchCount: document.getElementById("match-count"),
    statSep: document.getElementById("stat-sep"),
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
    totalLibraryCount: 0,
    selectedIndex: -1,
    isDeep: false,
    validationRules: null,
    id3Frames: null,
    allRoles: [],
    activeSong: null,
    allowedExtensions: [],
    successCount: 0,
    actionCount: 0,
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
        if (!state.currentQuery) {
            state.totalLibraryCount = count;
        }
        const isFiltered = state.currentQuery && count !== state.totalLibraryCount;
        elements.matchCount.textContent = String(count);
        elements.totalCount.textContent = String(state.totalLibraryCount);
        elements.totalLabel.textContent = `${singular.charAt(0).toUpperCase()}${singular.slice(1)}s`;
        elements.totalCount.style.display = isFiltered ? "" : "none";
        elements.statSep.style.display = isFiltered ? "" : "none";
    },
    openSongDetail: (...args) => openSongDetail(...args),
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
    }
};

const songActions = new SongActionsHandler(ctx);

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
    const { fetcher, renderer } = modeConfig[mode];
    state.currentQuery = query;
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
    
    // Aligned to Blueprint: Entering Ingest mode clears the action badge
    if (mode === "ingest") {
        state.actionCount = 0;
        updateIngestBadges();
    }
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

async function openSongDetail(song, { reuseFileData = false } = {}) {
    const existingContent = elements.detailPanel.querySelector(".detail-content");
    const savedScroll = existingContent ? existingContent.scrollTop : 0;
    const request = beginDetailRequest("songs", song.id);
    const isSameSong = state.activeSong?.id === song.id;
    if (!isSameSong) renderSongDetailLoading(ctx, song);

    const fetchFile = (!reuseFileData || cachedFileDataSongId !== String(song.id))
        ? getSongDetail(song.id, { signal: request.signal })
        : Promise.resolve(cachedFileData);

    const [catalogResult, fileResult, auditResult] = await Promise.allSettled([
        getCatalogSong(song.id, { signal: request.signal }),
        fetchFile,
        getAuditHistory("Songs", song.id, { signal: request.signal }),
    ]);

    if ([catalogResult, fileResult, auditResult].some(r => r.status === "rejected" && isAbortError(r.reason))) {
        return;
    }
    if (!isActiveDetail("songs", song.id)) {
        return;
    }

    const catalogSong = catalogResult.status === "fulfilled" && catalogResult.value ? catalogResult.value : song;
    const fileData = fileResult.status === "fulfilled" ? fileResult.value : null;
    cachedFileData = fileData;
    cachedFileDataSongId = String(song.id);
    state.activeSong = catalogSong;
    const auditHistory = auditResult.status === "fulfilled" ? auditResult.value : [];
    renderSongDetailComplete(ctx, catalogSong, fileData, auditHistory, state.id3Frames, state.allRoles);
    if (savedScroll) {
        const newContent = elements.detailPanel.querySelector(".detail-content");
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

function refreshActiveDetail() {
    if (!activeDetailKey) return;
    const [mode, id] = activeDetailKey.split(":");
    const list = getActiveList();
    const item = list.find(i => String(i.id) === id);
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

function isModalOpen() {
    const editModal = document.getElementById("edit-modal");
    if (editModal && editModal.style.display === "flex") return true;
    const linkModal = document.getElementById("link-modal");
    if (linkModal && linkModal.style.display === "flex") return true;
    const scrubberModal = document.getElementById("scrubber-modal");
    if (scrubberModal && scrubberModal.style.display === "flex") return true;
    const spotifyModal = document.getElementById("spotify-modal");
    if (spotifyModal && spotifyModal.style.display === "flex") return true;
    const splitterModal = document.getElementById("splitter-modal");
    if (splitterModal && splitterModal.style.display === "flex") return true;
    const filenameParserModal = document.getElementById("filename-parser-modal");
    if (filenameParserModal && filenameParserModal.style.display === "flex") return true;
    return false;
}

function updateIngestBadges(successDelta = 0, actionDelta = 0) {
    const tab = document.querySelector(".mode-tab[data-mode='ingest']");
    if (!tab) return;

    state.successCount += successDelta;
    state.actionCount += actionDelta;

    let badge = tab.querySelector(".ingest-badge");

    const total = state.actionCount + state.successCount;
    if (total <= 0) {
        if (badge) badge.remove();
        return;
    }

    if (!badge) {
        badge = document.createElement("span");
        badge.className = "ingest-badge";
        tab.appendChild(badge);
    }

    const isSuccess = state.actionCount === 0;
    // Red (action) trumps Green (success)
    badge.dataset.badgeType = isSuccess ? "success" : "action";

    if (isSuccess) {
        badge.textContent = `↺ ${total}`;
        badge.title = "New songs ingested — click to refresh library";
        badge.style.cursor = "pointer";
        badge.dataset.action = "refresh-results";
    } else {
        badge.textContent = String(total);
        badge.title = "";
        badge.style.cursor = "default";
        badge.removeAttribute("data-action");
    }
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

        try {
            const result = await uploadFiles(allFiles);
            let successes = 0;
            let actions = 0;

            for (const fileResult of result.results) {
                const title = fileResult.song?.media_name || fileResult.title || "Unknown";
                const fileName = fileResult.song?.source_path?.split(/[/\\]/).pop() || title;

                if (fileResult.status === "INGESTED") {
                    showToast(`Ingested: ${title}`, "success", 3000);
                    successes++;
                } else if (fileResult.status === "ALREADY_EXISTS") {
                    showToast(`Duplicate: ${title}`, "warning", 5000);
                } else if (fileResult.status === "CONFLICT") {
                    showToast(`Ghost record: ${title} — action needed`, "error", 0, { 
                        label: "Review", onClick: () => navigate("ingest") 
                    });
                    actions++;
                } else if (fileResult.status === "PENDING_CONVERT") {
                    showToast(`Conversion required: ${fileName}`, "warning", 0, { 
                        label: "Review", onClick: () => navigate("ingest") 
                    });
                    actions++;
                } else if (fileResult.status === "ERROR") {
                    showToast(`Error: ${fileResult.message || "Upload failed"}`, "error", 5000);
                }
            }
            updateIngestBadges(successes, actions);
        } catch (error) {
            showToast(`Upload failed: ${error.message}`, "error", 5000);
        }
    });
}

document.addEventListener("click", async (event) => {
    const actionTarget = event.target.closest("[data-action]");
    if (!actionTarget) return;

    // Protocol: Modals are top-level. Block global click actions if any modal is open,
    // UNLESS the action is actually inside a modal (edit-modal or link-modal)
    // or is a close-modal action.
    const { action } = actionTarget.dataset;
    const isModalComponent = actionTarget.closest(".link-modal");
    const isCloseAction = action === "close-edit-modal" || action === "close-link-modal" || action === "close-spotify-modal" || action === "close-splitter-modal" || action === "close-filename-parser-modal";

    if (isModalOpen() && !isModalComponent && !isCloseAction) {
        return;
    }

    // High-density delegation for Song Actions
    try {
        if (await songActions.handle(event)) return;
    } catch (err) {
        console.error(`[Main] SongActionsHandler CRASHED: ${err.message}`, err);
    }

    if (action === "switch-mode") {
        switchMode(actionTarget.dataset.mode);
        return;
    }

    if (action === "refresh-results") {
        actionTarget.classList.add("spinning");
        // Aligned to Blueprint: Refreshing the list clears the successful ingest badge
        state.successCount = 0;
        updateIngestBadges(); 
        performSearch(state.currentQuery).finally(() => {
            actionTarget.classList.remove("spinning");
        });
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

    if (action === "open-edit-modal") {
        const { chipType, itemId } = actionTarget.dataset;

        const onClose = refreshActiveDetail;

        if (chipType === "publisher") {
            const publisherName = actionTarget.textContent.trim();
            const publisherDetail = await getPublisherDetail(itemId).catch(() => null);
            const childItems = publisherDetail && publisherDetail.sub_publishers
                ? publisherDetail.sub_publishers.map(c => ({ id: c.id, label: c.name }))
                : [];

            openEditModal({
                title: "Edit Publisher",
                name: publisherDetail ? publisherDetail.name : publisherName,
                onRename: async (newName) => { await updatePublisher(itemId, newName); },
                onClose,
                category: null,
                children: {
                    label: "Sub-publishers",
                    items: childItems,
                    onSearch: async (q) => {
                        const results = await searchPublishers(q);
                        return (results || []).map(p => ({ id: p.id, label: p.name }));
                    },
                    onAdd: async (opt) => {
                        await setPublisherParent(opt.id, Number(itemId));
                        childItems.push({ id: opt.id, label: opt.label });
                    },
                    onRemove: async (item) => {
                        await setPublisherParent(item.id, null);
                    },
                    onRenameChild: async (item, newName) => { await updatePublisher(item.id, newName); },
                    createLabel: (q) => `Add "${q}" as sub-publisher`,
                },
            }, actionTarget);
        } else if (chipType === "tag") {
            const tagDetail = await getTagDetail(itemId).catch(() => null);
            if (!tagDetail) {
                console.error(`Tag ${itemId} not found`);
                return;
            }

            openEditModal({
                title: "Edit Tag",
                name: tagDetail.name,
                onRename: async (newName) => {
                    await updateTag(itemId, newName, tagDetail.category);
                    tagDetail.name = newName;
                },
                onClose,
                category: {
                    label: "Category",
                    value: tagDetail.category,
                    editable: true,
                    onSave: async (val) => {
                        await updateTag(itemId, tagDetail.name, val);
                        tagDetail.category = val;
                    },
                    onSearch: async (q) => {
                        const all = await getTagCategories();
                        return all.filter(c => c.toLowerCase().includes(q.toLowerCase()));
                    },
                },
                children: null,
            }, actionTarget);
        } else if (chipType === "credit") {
            const identityId = actionTarget.dataset.identityId;
            if (!identityId) return;

            const identity = await getArtistTree(identityId).catch(() => null);
            if (!identity) return;

            const primaryAlias = (identity.aliases || []).find(a => a.is_primary);
            const aliases = (identity.aliases || []).filter(a => !a.is_primary);
            const childItems = aliases.map(a => ({ id: a.id, label: a.display_name }));

            openEditModal({
                title: "Edit Artist",
                name: primaryAlias?.display_name || identity.display_name,
                onRename: async (newName) => {
                    await updateCreditName(0, primaryAlias.id, newName);
                },
                onClose,
                category: null,
                children: {
                    label: "Aliases",
                    items: childItems,
                    onSearch: async (q) => {
                        const results = await searchArtists(q);
                        return (results || []).map(i => ({ id: i.id, label: i.display_name }));
                    },
                    onAdd: async (opt) => {
                        const result = await addIdentityAlias(identityId, opt.rawInput || opt.label, opt.id);
                        childItems.push({ id: result.name_id, label: result.display_name });
                    },
                    onRemove: async (item) => {
                        await removeIdentityAlias(identityId, item.id);
                    },
                    onRenameChild: async (item, newName) => {
                        await updateCreditName(0, item.id, newName);
                    },
                    createLabel: (q) => `Add "${q}" as alias`,
                },
            }, actionTarget);
        }
        return;
    }

    if (action === "open-link-modal") {
        const { modalType, songId } = actionTarget.dataset;

        if (modalType === "publishers") {
            const currentPublishers = (state.activeSong?.publishers || []).map(p => ({ id: p.id, label: p.name }));
            orch.manageSongPublishers(ctx, songId, currentPublishers);
        } else if (modalType === "tags") {
            const currentTags = state.activeSong?.tags || [];
            const songTitle = state.activeSong?.title || "Song";
            orch.manageSongTags(ctx, songId, songTitle, currentTags);
        } else if (modalType === "credits") {
            const { role } = actionTarget.dataset;
            if (!role) throw new Error("credits button is missing data-role");
            const currentCredits = (state.activeSong?.credits || []).filter(c => c.role_name === role);
            orch.manageSongCredits(ctx, songId, role, currentCredits);
        } else if (modalType === "album") {
            const { songTitle } = actionTarget.dataset;
            const section = actionTarget.closest(".detail-section");
            const libraryBox = section?.querySelector(".surface-box");
            const currentAlbums = Array.from(
                libraryBox ? libraryBox.querySelectorAll(`[data-action="remove-album"][data-song-id="${songId}"]`) : []
            ).map(btn => ({ id: btn.dataset.albumId, label: btn.closest(".album-card-detail")?.querySelector(".editable-scalar")?.textContent?.trim() ?? "" }));
            orch.manageSongAlbums(ctx, songId, songTitle, currentAlbums);
        } else if (modalType === "album-publishers") {
            const { albumId } = actionTarget.dataset;
            const chips = Array.from(
                actionTarget.closest(".album-card-detail")?.querySelectorAll("[data-action='remove-album-publisher']") || []
            ).map(btn => ({ id: btn.dataset.publisherId, label: btn.closest(".link-chip")?.querySelector(".link-chip-label")?.textContent.trim() ?? "" }));
            orch.manageAlbumPublishers(ctx, albumId, songId, chips);
        } else if (modalType === "album-credits") {
            const { albumId } = actionTarget.dataset;
            const chips = Array.from(
                actionTarget.closest(".album-card-detail")?.querySelectorAll("[data-action='remove-album-credit']") || []
            ).map(btn => ({ id: btn.dataset.creditId, label: btn.closest(".link-chip")?.querySelector(".link-chip-label")?.textContent.trim() ?? "" }));
            orch.manageAlbumCredits(ctx, albumId, songId, chips);
        }
        return;
    }



});

document.addEventListener("keydown", (event) => {
    // Protocol: Modals are top-level. Block global keyboard navigation if any modal is open.
    // (Local Escape handling for detail-panel should only fire if no modal is active)
    const modalOpen = isModalOpen();

    if (event.key === "Escape" && modalOpen) {
        // Universal modal drainage
        if (typeof songActions.handle === "function") {
            const openModal = ["edit-modal", "link-modal", "scrubber-modal", "spotify-modal", "splitter-modal", "filename-parser-modal"]
                .find(id => {
                    const el = document.getElementById(id);
                    return el && el.style.display === "flex";
                });
            
            if (openModal) {
                const action = `close-${openModal}`;
                // Dispatch a virtual event to the handler to reuse closing logic
                songActions.handle({ target: { dataset: { action } }, stopPropagation: () => {} });
            }
        }
        return;
    }

    if (event.key === "Escape" && elements.detailPanel.style.display === "flex" && !modalOpen) {
        abortDetailRequest();
        ctx.hideDetailPanel();
        
        // If we were resolving items in Ingest mode, clear the action badge
        if (state.currentMode === "ingest") {
            state.actionCount = 0;
            updateIngestBadges();
        }
        
        state.selectedIndex = -1;
        updateSelection();
        return;
    }

    // Don't intercept arrow keys when a modal is open or when typing in search
    if (modalOpen || document.activeElement === elements.searchInput) {
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
        const selected = items[state.selectedIndex];
        if (!selected) return;

        // Pattern: If detail panel is already open for this song, 'Enter' triggers the scrubber
        const isSongDetailOpen = state.currentMode === "songs" && elements.detailPanel.style.display === "flex";
        const isActiveSongDetail = isSongDetailOpen && state.activeSong && String(state.activeSong.id) === String(selected.id);

        if (isActiveSongDetail) {
            orch.orchestrateScrubber(ctx, state.activeSong.id, state.activeSong.media_name || state.activeSong.title);
            return;
        }

        // Otherwise open the detail panel
        const cachedList = getActiveList();
        const actualIndex = cachedList.findIndex(item => item.id === selected.id);
        if (actualIndex >= 0) {
            openSelectedResult(actualIndex);
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
initToastSystem();
Promise.all([
    fetchValidationRules().catch(() => null),
    fetchId3Frames().catch(() => null),
    fetchRoles(),
    getAcceptedFormats().catch(() => []),
]).then(([rules, frames, roles, exts]) => {
    state.validationRules = rules;
    state.id3Frames = frames;
    state.allRoles = roles;
    state.allowedExtensions = exts;
});
setupHeaderDropZone();
performSearch("");
