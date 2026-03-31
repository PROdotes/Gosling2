import {
    ABORTED,
    abortAllSearches,
    addSongPublisher,
    fetchValidationRules,
    getAlbumDetail,
    getArtistSongs,
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
    addSongAlbum,
    removeSongAlbum,
    updateAlbum,
    updateSongAlbumLink,
    addAlbumPublisher,
    removeAlbumPublisher,
    addAlbumCredit,
    removeAlbumCredit,
    moveSongToLibrary,
} from "./api.js";
import { openLinkModal, closeLinkModal } from "./components/link_modal.js";
import { openEditModal, closeEditModal } from "./components/edit_modal.js";
import { openScrubberModal, closeScrubberModal } from "./components/scrubber_modal.js";
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
    validationRules: null,
    id3Frames: null,
    allRoles: [],
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

async function openSongDetail(song, { reuseFileData = false } = {}) {
    const existingContent = elements.detailPanel.querySelector(".detail-content");
    const savedScroll = existingContent ? existingContent.scrollTop : 0;
    const request = beginDetailRequest("songs", song.id);
    renderSongDetailLoading(ctx, song);

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
    return false;
}

document.addEventListener("click", async (event) => {
    const actionTarget = event.target.closest("[data-action]");
    if (!actionTarget) return;

    // Protocol: Modals are top-level. Block global click actions if any modal is open,
    // UNLESS the action is actually inside a modal (edit-modal or link-modal)
    // or is a close-modal action.
    const { action } = actionTarget.dataset;
    const isModalComponent = actionTarget.closest(".link-modal");
    const isCloseAction = action === "close-edit-modal" || action === "close-link-modal";

    if (isModalOpen() && !isModalComponent && !isCloseAction) {
        return;
    }

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

    if (action === "remove-publisher") {
        const { songId, publisherId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await removeSongPublisher(songId, publisherId);
            const song = state.cachedSongs.find(s => String(s.id) === String(songId));
            if (song) openSongDetail(song, { reuseFileData: true });
        } catch (err) {
            actionTarget.disabled = false;
            console.error(`Remove publisher failed: ${err.message}`);
        }
        return;
    }

    if (action === "remove-tag") {
        const { songId, tagId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await removeSongTag(songId, tagId);
            const song = state.cachedSongs.find(s => String(s.id) === String(songId));
            if (song) openSongDetail(song, { reuseFileData: true });
        } catch (err) {
            actionTarget.disabled = false;
            console.error(`Remove tag failed: ${err.message}`);
        }
        return;
    }

    if (action === "remove-credit") {
        const { songId, creditId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await removeSongCredit(songId, creditId);
            const song = state.cachedSongs.find(s => String(s.id) === String(songId));
            if (song) openSongDetail(song, { reuseFileData: true });
        } catch (err) {
            actionTarget.disabled = false;
            console.error(`Remove credit failed: ${err.message}`);
        }
        return;
    }

    if (action === "remove-album") {
        const { songId, albumId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await removeSongAlbum(songId, albumId);
            const song = state.cachedSongs.find(s => String(s.id) === String(songId));
            if (song) openSongDetail(song, { reuseFileData: true });
        } catch (err) {
            actionTarget.disabled = false;
            console.error(`Remove album failed: ${err.message}`);
        }
        return;
    }

    if (action === "remove-album-publisher") {
        const { albumId, publisherId, songId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await removeAlbumPublisher(albumId, publisherId);
            const song = state.cachedSongs.find(s => String(s.id) === String(songId));
            if (song) openSongDetail(song, { reuseFileData: true });
        } catch (err) {
            actionTarget.disabled = false;
            console.error(`Remove album publisher failed: ${err.message}`);
        }
        return;
    }

    if (action === "remove-album-credit") {
        const { albumId, creditId, songId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await removeAlbumCredit(albumId, creditId);
            const song = state.cachedSongs.find(s => String(s.id) === String(songId));
            if (song) openSongDetail(song, { reuseFileData: true });
        } catch (err) {
            actionTarget.disabled = false;
            console.error(`Remove album credit failed: ${err.message}`);
        }
        return;
    }

    if (action === "start-edit-album-scalar") {
        const span = actionTarget;
        const { albumId, songId, field } = span.dataset;
        const currentValue = span.textContent === "-" ? "" : span.textContent;

        const input = document.createElement("input");
        input.type = "text";
        input.value = currentValue;
        input.className = "inline-edit-input";

        const errorEl = document.createElement("div");
        errorEl.className = "inline-edit-error";

        span.replaceWith(input);
        input.after(errorEl);
        input.focus();
        input.select();

        async function commitAlbumScalar() {
            const rawValue = input.value.trim();
            errorEl.textContent = "";
            input.classList.remove("inline-edit-input--error");

            if (rawValue === currentValue) {
                input.replaceWith(span);
                errorEl.remove();
                return;
            }

            let payload;
            if (field === "release_year") {
                if (rawValue === "") {
                    payload = null;
                } else {
                    const n = Number(rawValue);
                    const year = new Date().getFullYear();
                    if (!Number.isInteger(n) || n < 1860 || n > year + 1) {
                        input.classList.add("inline-edit-input--error");
                        errorEl.textContent = `Year must be between 1860–${year + 1}`;
                        input.focus();
                        return;
                    }
                    payload = n;
                }
            } else {
                payload = rawValue === "" ? null : rawValue;
                if (field === "title" && !payload) {
                    input.classList.add("inline-edit-input--error");
                    errorEl.textContent = "Title cannot be empty";
                    input.focus();
                    return;
                }
            }

            input.disabled = true;
            try {
                await updateAlbum(albumId, { [field]: payload });
                const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                if (song) openSongDetail(song, { reuseFileData: true });
            } catch (err) {
                input.disabled = false;
                input.classList.add("inline-edit-input--error");
                errorEl.textContent = `Save failed: ${err.message}`;
                input.focus();
            }
        }

        input.addEventListener("input", () => {
            const v = input.value.trim();
            if (field === "release_year" && v) {
                const n = Number(v);
                const year = new Date().getFullYear();
                if (!Number.isInteger(n) || n < 1860 || n > year + 1) {
                    input.classList.add("inline-edit-input--error");
                    errorEl.textContent = `Year must be between 1860–${year + 1}`;
                    return;
                }
            }
            input.classList.remove("inline-edit-input--error");
            errorEl.textContent = "";
        });
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); commitAlbumScalar(); }
            if (e.key === "Escape") { input.replaceWith(span); errorEl.remove(); }
        });
        input.addEventListener("blur", () => { setTimeout(() => { if (document.contains(input)) commitAlbumScalar(); }, 100); });
        return;
    }

    if (action === "start-edit-album-link") {
        const span = actionTarget;
        const { albumId, songId, field } = span.dataset;
        const currentValue = span.textContent === "-" ? "" : span.textContent;

        const input = document.createElement("input");
        input.type = "text";
        input.value = currentValue;
        input.className = "inline-edit-input";
        input.style.width = "3rem";

        const errorEl = document.createElement("div");
        errorEl.className = "inline-edit-error";

        span.replaceWith(input);
        input.after(errorEl);
        input.focus();
        input.select();

        async function commitAlbumLink() {
            const rawValue = input.value.trim();
            errorEl.textContent = "";
            input.classList.remove("inline-edit-input--error");

            if (rawValue === currentValue) {
                input.replaceWith(span);
                errorEl.remove();
                return;
            }

            const n = rawValue === "" ? null : Number(rawValue);
            if (n !== null && (!Number.isInteger(n) || n < 1)) {
                input.classList.add("inline-edit-input--error");
                errorEl.textContent = "Must be a positive integer";
                input.focus();
                return;
            }

            // Read the sibling field value from the DOM to build the full patch
            const card = input.closest(".album-card-detail");
            const otherField = field === "track_number" ? "disc_number" : "track_number";
            const otherSpan = card?.querySelector(`[data-field="${otherField}"]`);
            const otherVal = otherSpan ? (otherSpan.textContent === "-" ? null : Number(otherSpan.textContent)) : null;

            const track = field === "track_number" ? n : otherVal;
            const disc = field === "disc_number" ? n : otherVal;

            input.disabled = true;
            try {
                await updateSongAlbumLink(songId, albumId, track, disc);
                const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                if (song) openSongDetail(song, { reuseFileData: true });
            } catch (err) {
                input.disabled = false;
                input.classList.add("inline-edit-input--error");
                errorEl.textContent = `Save failed: ${err.message}`;
                input.focus();
            }
        }

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); commitAlbumLink(); }
            if (e.key === "Escape") { input.replaceWith(span); errorEl.remove(); }
        });
        input.addEventListener("blur", () => { setTimeout(() => { if (document.contains(input)) commitAlbumLink(); }, 100); });
        return;
    }

    if (action === "sync-album-from-song") {
        const { albumId, songId } = actionTarget.dataset;
        actionTarget.disabled = true;
        actionTarget.textContent = "syncing...";
        try {
            const song = await getCatalogSong(songId);
            const albumDetail = await getAlbumDetail(albumId);

            const ops = [];

            // Title — only if album title looks like a placeholder or matches song title already (skip — title is intentional)
            // Year — only if missing
            if (!albumDetail.release_year && song.year) {
                ops.push(updateAlbum(albumId, { release_year: song.year }));
            }

            // Credits — add song performers not already on album (match by name_id)
            const existingNameIds = new Set((albumDetail.credits || []).map(c => String(c.name_id)));
            for (const credit of (song.credits || [])) {
                if (credit.role_name !== "Performer") continue;
                if (!existingNameIds.has(String(credit.name_id))) {
                    ops.push(addAlbumCredit(albumId, credit.display_name, credit.role_name, credit.identity_id ?? null));
                }
            }

            // Publishers — add song publishers not already on album (match by id)
            const existingPubIds = new Set((albumDetail.publishers || []).map(p => String(p.id)));
            for (const pub of (song.publishers || [])) {
                if (!existingPubIds.has(String(pub.id))) {
                    ops.push(addAlbumPublisher(albumId, pub.name, pub.id));
                }
            }

            await Promise.all(ops);
            const s = state.cachedSongs.find(s => String(s.id) === String(songId));
            if (s) openSongDetail(s, { reuseFileData: true });
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.textContent = "↓ sync from song";
            ctx.showBanner(`Sync failed: ${err.message}`, "error");
        }
        return;
    }

    if (action === "change-album-type") {
        const { albumId, songId } = actionTarget.dataset;
        const newType = actionTarget.value;
        try {
            await updateAlbum(albumId, { album_type: newType });
        } catch (err) {
            console.error(`Update album type failed: ${err.message}`);
            const song = state.cachedSongs.find(s => String(s.id) === String(songId));
            if (song) openSongDetail(song, { reuseFileData: true });
        }
        return;
    }

    if (action === "close-edit-modal") {
        closeEditModal();
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
            const songId = actionTarget.dataset.songId;
            const albumId = actionTarget.dataset.albumId;
            const displayName = actionTarget.textContent.trim();

            openEditModal({
                title: "Global Name Edit",
                name: displayName,
                onRename: async (newName) => {
                    await updateCreditName(songId || albumId, itemId, newName);
                },
                onClose,
                category: null,
                children: null,
            }, actionTarget);
        }
        return;
    }

    if (action === "open-scrubber") {
        const { songId, title } = actionTarget.dataset;
        openScrubberModal(songId, title);
        return;
    }

    if (action === "close-scrubber-modal") {
        closeScrubberModal();
        return;
    }

    if (action === "web-search") {
        const { songId } = actionTarget.dataset;
        import("./api.js").then(async (m) => {
            try {
                // Get the search URL from the backend (Truth-First)
                const data = await m.getSongWebSearch(songId);
                if (data && data.url) {
                    window.open(data.url, "_blank");
                }
            } catch (err) {
                ctx.showBanner(`Search failed: ${err.message}`, "error");
            }
        });
        return;
    }

    if (action === "close-link-modal") {
        closeLinkModal();
        return;
    }

    if (action === "open-link-modal") {
        const { modalType, songId } = actionTarget.dataset;

        if (modalType === "publishers") {
            const section = actionTarget.closest(".detail-section");
            const libraryBox = section?.querySelector(".surface-box");
            const chips = libraryBox ? libraryBox.querySelectorAll(`[data-action="remove-publisher"][data-song-id="${songId}"]`) : [];
            const currentItems = Array.from(chips).map(btn => ({
                id: btn.dataset.publisherId,
                label: btn.closest(".link-chip").querySelector(".link-chip-label")?.textContent.trim() ?? btn.closest(".link-chip").childNodes[0].textContent.trim(),
            }));

            openLinkModal({
                title: "Publishers",
                items: currentItems,
                onSearch: async (q) => {
                    const results = await searchPublishers(q);
                    return (results || []).map(p => ({ id: p.id, label: p.name }));
                },
                onAdd: async (opt) => {
                    // M2M Protocol: IDs are primary. Strings are for creation only.
                    const publisherId = opt.id ? Number(opt.id) : null;
                    const publisher = await addSongPublisher(songId, opt.rawInput || opt.label, publisherId);
                    opt.id = publisher.id;
                    opt.label = publisher.name;
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                onRemove: async (item) => {
                    await removeSongPublisher(songId, item.id);
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                createLabel: (q) => `Add "${q}" as new publisher`,
            });
        } else if (modalType === "tags") {
            const section = actionTarget.closest(".detail-section");
            const libraryBox = section?.querySelector(".surface-box");
            const chips = libraryBox ? libraryBox.querySelectorAll(`[data-action="remove-tag"][data-song-id="${songId}"]`) : [];
            const currentItems = Array.from(chips).map(btn => ({
                id: btn.dataset.tagId,
                label: btn.closest(".link-chip").querySelector(".link-chip-label")?.textContent.trim() ?? "",
            }));

            const rules = state.validationRules?.tags || {};
            const defaultCategory = rules.default_category || "Genre";
            const delimiter = rules.delimiter || ":";
            const format = rules.input_format || "tag:category";
            const nameFirst = format.toLowerCase().startsWith("tag");

            function parseTagInput(raw) {
                if (!raw.includes(delimiter)) return { name: raw.trim(), category: defaultCategory };
                const idx = raw.indexOf(delimiter);
                const a = raw.slice(0, idx).trim();
                const b = raw.slice(idx + delimiter.length).trim();
                const name = nameFirst ? a : b;
                const category = nameFirst ? b : a;
                return { name, category };
            }

            openLinkModal({
                title: "Tags",
                placeholder: `Search or type (e.g. ${format})...`,
                items: currentItems,
                onSearch: async (q) => {
                    const results = await searchTags(q);
                    if (results === ABORTED) return [];
                    return (results || []).map(t => ({ id: t.id, label: t.category ? `${t.name} (${t.category})` : t.name, name: t.name }));
                },
                onAdd: async (opt) => {
                    let name, category;
                    if (opt.id != null) {
                        // Priority 1: Link existing tag by ID
                        // We pass nulls for name/category as the backend resolves by ID
                        name = null;
                        category = null;
                    } else {
                        // Priority 2: Parse raw input for new tag creation
                        const parsed = parseTagInput(opt.rawInput || opt.name || opt.label);
                        name = parsed.name;
                        category = parsed.category;
                    }

                    const tag = await addSongTag(songId, name, category, opt.id != null ? opt.id : null);
                    opt.id = tag.id;
                    opt.label = tag.name;
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                onRemove: async (item) => {
                    await removeSongTag(songId, item.id);
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                createLabel: (q) => {
                    const { name, category } = parseTagInput(q);
                    if (!name) return `Add tag (missing name)`;
                    return `Add "${name}" in "${category}"`;
                },
            });
        } else if (modalType === "credits") {
            const { songId, role } = actionTarget.dataset;
            const group = actionTarget.closest(".stack-list");
            const chips = group ? group.querySelectorAll(`[data-action="remove-credit"][data-song-id="${songId}"]`) : [];
            const currentItems = Array.from(chips).map(btn => ({
                id: btn.dataset.creditId,
                label: btn.closest(".link-chip").querySelector(".link-chip-label")?.textContent.trim() ?? "",
            }));

            if (!role) throw new Error("credits button is missing data-role");

            openLinkModal({
                title: `Link ${role}`,
                placeholder: `Search for artist name...`,
                items: currentItems,
                onSearch: async (q) => {
                    const results = await searchArtists(q);
                    if (results === ABORTED) return [];
                    return (results || []).map(a => ({ id: a.id, label: a.display_name || a.legal_name || a.name }));
                },
                onAdd: async (opt) => {
                    // Logic: Use identityId (opt.id) from search results if available (Truth-First pattern)
                    const identityId = opt.id; 
                    const credit = await addSongCredit(songId, opt.rawInput || opt.label, role, identityId);
                    
                    // Sync the chip with the newly created/linked credit's IDs
                    opt.id = credit.credit_id;
                    opt.label = credit.display_name;
                    
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                onRemove: async (item) => {
                    await removeSongCredit(songId, item.id);
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                createLabel: (q) => `Add "${q}" as ${role}`,
            });
        } else if (modalType === "album") {
            const { songId } = actionTarget.dataset;
            const section = actionTarget.closest(".detail-section");
            const libraryBox = section?.querySelector(".surface-box");
            const currentCards = Array.from(
                libraryBox ? libraryBox.querySelectorAll(`[data-action="remove-album"][data-song-id="${songId}"]`) : []
            ).map(btn => ({ id: btn.dataset.albumId, label: btn.closest(".album-card-detail")?.querySelector(".editable-scalar")?.textContent?.trim() ?? "" }));

            openLinkModal({
                title: "Link Album",
                placeholder: "Search for album...",
                items: currentCards,
                onSearch: async (q) => {
                    const results = await searchAlbums(q);
                    if (results === ABORTED) return [];
                    return (results || []).map(a => ({ id: a.id, label: a.title }));
                },
                onAdd: async (opt) => {
                    await addSongAlbum(songId, opt.id ?? null, opt.rawInput || opt.label, null, null);
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                onRemove: async (item) => {
                    await removeSongAlbum(songId, item.id);
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                createLabel: (q) => `Add "${q}" as new album`,
            });
        } else if (modalType === "album-publishers") {
            const { albumId, songId } = actionTarget.dataset;
            const chips = Array.from(
                actionTarget.closest(".album-card-detail")?.querySelectorAll("[data-action='remove-album-publisher']") || []
            ).map(btn => ({ id: btn.dataset.publisherId, label: btn.closest(".link-chip")?.querySelector(".link-chip-label")?.textContent.trim() ?? "" }));

            openLinkModal({
                title: "Album Publishers",
                items: chips,
                onSearch: async (q) => {
                    const results = await searchPublishers(q);
                    return (results || []).map(p => ({ id: p.id, label: p.name }));
                },
                onAdd: async (opt) => {
                    const publisherId = opt.id ? Number(opt.id) : null;
                    const publisher = await addAlbumPublisher(albumId, opt.rawInput || opt.label, publisherId);
                    opt.id = publisher.id;
                    opt.label = publisher.name;
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                onRemove: async (item) => {
                    await removeAlbumPublisher(albumId, item.id);
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                createLabel: (q) => `Add "${q}" as album publisher`,
            });
        } else if (modalType === "album-credits") {
            const { albumId, songId } = actionTarget.dataset;
            const chips = Array.from(
                actionTarget.closest(".album-card-detail")?.querySelectorAll("[data-action='remove-album-credit']") || []
            ).map(btn => ({ id: btn.dataset.creditId, label: btn.closest(".link-chip")?.querySelector(".link-chip-label")?.textContent.trim() ?? "" }));

            openLinkModal({
                title: "Album Credits",
                placeholder: "Search for artist name...",
                items: chips,
                onSearch: async (q) => {
                    const results = await searchArtists(q);
                    if (results === ABORTED) return [];
                    return (results || []).map(a => ({ id: a.id, label: a.display_name || a.legal_name || a.name }));
                },
                onAdd: async (opt) => {
                    const identityId = opt.id;
                    const credit = await addAlbumCredit(albumId, opt.rawInput || opt.label, "Performer", identityId);
                    opt.id = credit.name_id;
                    opt.label = credit.display_name;
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                onRemove: async (item) => {
                    await removeAlbumCredit(albumId, item.id);
                    const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (song) openSongDetail(song, { reuseFileData: true });
                },
                createLabel: (q) => `Add "${q}" as Performer`,
            });
        }
        return;
    }

    if (action === "start-edit-scalar") {
        const span = actionTarget;
        const { songId, field } = span.dataset;
        const currentValue = span.textContent === "-" ? "" : span.textContent;

        const rules = state.validationRules;
        const validators = {
            media_name: (v) => v ? null : "Title cannot be empty",
            year: (v) => {
                if (!v) return null; // optional
                const n = Number(v);
                const min = rules?.year?.min ?? 1860;
                const max = rules?.year?.max ?? (new Date().getFullYear() + 1);
                if (!Number.isInteger(n) || n < min || n > max) return `Year must be between ${min}–${max}`;
                return null;
            },
            bpm: (v) => {
                if (!v) return null; // optional
                const n = Number(v);
                const min = rules?.bpm?.min ?? 1;
                const max = rules?.bpm?.max ?? 300;
                if (!Number.isInteger(n) || n < min || n > max) return `BPM must be between ${min}–${max}`;
                return null;
            },
            isrc: (v) => {
                if (!v) return null; // optional
                const stripped = v.replace(/-/g, "").toUpperCase();
                const pattern = rules?.isrc?.pattern ? new RegExp(rules.isrc.pattern) : /^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$/;
                if (!pattern.test(stripped)) return "ISRC format: CC-XXX-YY-NNNNN (2 letters, 3 alphanumeric, 2 digits, 5 digits)";
                return null;
            },
        };

        const input = document.createElement("input");
        input.type = "text";
        input.value = currentValue;
        input.className = "inline-edit-input";

        const errorEl = document.createElement("div");
        errorEl.className = "inline-edit-error";

        span.replaceWith(input);
        input.after(errorEl);
        input.focus();
        input.select();

        let hasError = false;

        async function commitEdit() {
            const rawValue = input.value.trim();
            errorEl.textContent = "";
            input.classList.remove("inline-edit-input--error");
            hasError = false;

            const validate = validators[field];
            const error = validate ? validate(rawValue) : null;
            if (error) {
                hasError = true;
                input.classList.add("inline-edit-input--error");
                errorEl.textContent = error;
                input.focus();
                return;
            }

            if (rawValue === currentValue) {
                input.replaceWith(span);
                errorEl.remove();
                return;
            }

            // Convert empty string to null for optional fields, numbers where needed
            let payload;
            if (field === "year" || field === "bpm") {
                payload = rawValue === "" ? null : Number(rawValue);
            } else {
                payload = rawValue === "" ? null : rawValue;
            }

            input.disabled = true;
            try {
                const updatedSong = await patchSongScalars(songId, { [field]: payload });
                // Keep list card in sync for title changes
                if (field === "media_name") {
                    const cached = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (cached) {
                        cached.media_name = updatedSong.media_name;
                        cached.title = updatedSong.media_name;
                    }
                }
                openSongDetail(updatedSong, { reuseFileData: true });
            } catch (err) {
                input.disabled = false;
                input.classList.add("inline-edit-input--error");
                errorEl.textContent = `Save failed: ${err.message}`;
                input.focus();
            }
        }

        input.addEventListener("input", () => {
            const validate = validators[field];
            if (!validate) return;
            const error = validate(input.value.trim());
            if (error) {
                hasError = true;
                input.classList.add("inline-edit-input--error");
                errorEl.textContent = error;
            } else {
                hasError = false;
                input.classList.remove("inline-edit-input--error");
                errorEl.textContent = "";
            }
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                commitEdit();
            }
            if (e.key === "Escape") {
                e.stopPropagation();
                input.replaceWith(span);
                errorEl.remove();
            }
        });

        input.addEventListener("blur", () => {
            if (hasError) return; // user must fix or press Escape to cancel
            // Small delay so Enter keydown can fire commitEdit first
            setTimeout(() => {
                if (document.contains(input)) {
                    commitEdit();
                }
            }, 100);
        });

        return;
    }

    if (action === "move-to-library") {
        const { id } = actionTarget.dataset;
        actionTarget.disabled = true;
        const originalText = actionTarget.textContent;
        actionTarget.textContent = "Organizing...";
        
        try {
            await moveSongToLibrary(id);
            ctx.showBanner("Organized successfully!", "success");
            openSongDetail({ id }, { reuseFileData: false });
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.textContent = originalText;
            ctx.showBanner(`Organization failed: ${err.message}`, "error");
        }
        return;
    }

    if (action === "mark-reviewed" || action === "unreview-song") {
        const { id } = actionTarget.dataset;
        const newStatus = action === "mark-reviewed" ? 0 : 1;
        try {
            const updatedSong = await patchSongScalars(id, { processing_status: newStatus });
            openSongDetail(updatedSong, { reuseFileData: true });
        } catch (err) {
            ctx.showBanner(`Failed to update status: ${err.message}`, "error");
        }
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
                ctx.showBanner(`Deletion failed: ${err.message}`, "error");
            }
        });
    }
});

document.addEventListener("keydown", (event) => {
    // Protocol: Modals are top-level. Block global keyboard navigation if any modal is open.
    // (Local Escape handling for detail-panel should only fire if no modal is active)
    const modalOpen = isModalOpen();

    if (event.key === "Escape" && modalOpen) {
        const scrubberModal = document.getElementById("scrubber-modal");
        if (scrubberModal && scrubberModal.style.display === "flex") {
            closeScrubberModal();
        }
        return;
    }

    if (event.key === "Escape" && elements.detailPanel.style.display === "flex" && !modalOpen) {
        abortDetailRequest();
        ctx.hideDetailPanel();
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
Promise.all([
    fetchValidationRules().catch(() => null),
    fetchId3Frames().catch(() => null),
    fetchRoles(),
]).then(([rules, frames, roles]) => {
    state.validationRules = rules;
    state.id3Frames = frames;
    state.allRoles = roles;
});
performSearch("");
