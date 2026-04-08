/**
 * GOSLING SONG ACTIONS HANDLER
 * Offloads business logic for song-related click actions from main.js.
 */

import * as api from "../api.js";
import { activateInlineEdit } from "../components/inline_editor.js";

export async function syncAlbumWithSong(albumId, songId) {
    const [song, albumDetail] = await Promise.all([
        api.getCatalogSong(songId),
        api.getAlbumDetail(albumId),
    ]);
    const ops = [];
    if (!albumDetail.release_year && song.year) {
        ops.push(api.updateAlbum(albumId, { release_year: song.year }));
    }
    const existingNameIds = new Set((albumDetail.credits || []).map(c => String(c.name_id)));
    for (const credit of (song.credits || [])) {
        if (credit.role_name !== "Performer") continue;
        if (!existingNameIds.has(String(credit.name_id))) {
            ops.push(api.addAlbumCredit(albumId, credit.display_name, credit.role_name, credit.identity_id ?? null));
        }
    }
    const existingPubIds = new Set((albumDetail.publishers || []).map(p => String(p.id)));
    for (const pub of (song.publishers || [])) {
        if (!existingPubIds.has(String(pub.id))) {
            ops.push(api.addAlbumPublisher(albumId, pub.name, pub.id));
        }
    }
    await Promise.all(ops);
}
import { showConfirm } from "../components/confirm_modal.js";

export class SongActionsHandler {
    constructor(ctx, _window = typeof window !== 'undefined' ? window : null) {
        this.ctx = ctx;
        this._window = _window;
        // List of actions this handler is responsible for.
        // If an action is NOT here, it's considered a "Global" navigation/system action.
        this.songActions = new Set([
            "convert-wav",
            "resolve-conflict",
            "format-case",
            "remove-publisher",
            "open-spotify-modal",
            "open-splitter-modal",
            "open-filename-parser-single",
            "set-primary-tag",
            "remove-tag",
            "remove-credit",
            "remove-album",
            "remove-album-publisher",
            "remove-album-credit",
            "cleanup-original",
            "start-edit-album-scalar",
            "start-edit-album-link",
            "sync-album-from-song",
            "change-album-type",
            "close-edit-modal",
            "open-scrubber",
            "web-search",
            "web-search-set-engine",
            "close-link-modal",
            "start-edit-scalar",
            "move-to-library",
            "mark-reviewed",
            "unreview-song",
            "toggle-active",
            "delete-song",
            "close-spotify-modal",
            "close-splitter-modal",
            "close-filename-parser-modal",
            "close-scrubber-modal"
        ]);
    }

    /**
     * Dispatcher for click events.
     * @param {Event} event 
     * @returns {Promise<boolean>} True if action was handled
     */
    async handle(event) {
        // Support both real DOM events and virtual dispatch objects
        const actionTarget = (event.target && typeof event.target.closest === "function") 
            ? event.target.closest("[data-action]") 
            : event.target;

        if (!actionTarget) return false;

        const { action } = actionTarget.dataset;
        if (!this.songActions.has(action)) return false;

        // Protocol: Modals are top-level. Block actions if any modal is open,
        // UNLESS the action is specifically a close-modal action or inside a modal.
        const isInsideModal = (typeof actionTarget.closest === "function") && actionTarget.closest(".link-modal");
        if (this.isModalOpen() && !isInsideModal && !action.startsWith("close-")) {
            return false;
        }

        // Method dispatch pattern: handleActionName
        const methodName = `handle${action.split("-").map(p => p.charAt(0).toUpperCase() + p.slice(1)).join("")}`;
        
        if (typeof this[methodName] === "function") {
            try {
                await this[methodName](actionTarget, event);
                return true;
            } catch (err) {
                console.error(`[Handler] Method ${methodName} failed: ${err.message}`, err);
                return true;
            }
        }

        return false;
    }

    /**
     * Checks if any dashboard modal is currently open into the DOM.
     * Replicates logic from main.js:isModalOpen()
     */
    isModalOpen() {
        const modals = [
            "edit-modal", "link-modal", "scrubber-modal", 
            "spotify-modal", "splitter-modal", "filename-parser-modal"
        ];
        return modals.some(id => {
            const el = document.getElementById(id);
            return el && el.style.display === "flex";
        });
    }

    // ─── ACTION HANDLERS ───────────────────────────────────────────────────────

    async handleDeleteSong(actionTarget) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        const { title } = actionTarget.dataset;

        // Two-stage confirmation
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

        try {
            await api.deleteSong(id);
            // Integration: Call the search refresh passed via context
            if (this.ctx.hideDetailPanel) this.ctx.hideDetailPanel();
            
            // Allow main.js or other systems to refresh the list
            // In Gosling v3, we prefer performSearch()
            if (typeof performSearch === "function") {
                performSearch();
            } else if (this.ctx.performSearch) {
                this.ctx.performSearch();
            }
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.classList.remove("confirming");
            actionTarget.textContent = "Delete";
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Deletion failed: ${err.message}`, "error");
            }
        }
    }

    async handleToggleActive(actionTarget, event) {
        // Prevent card selection when toggling
        if (event) event.stopPropagation();

        if (actionTarget.classList.contains("disabled")) {
            return;
        }

        const input = actionTarget.querySelector("input");
        if (!input) return;

        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        const isChecked = input.checked;

        try {
            await api.patchSongScalars(id, { is_active: isChecked });
            
            // Sync current items in any list results
            const state = this.ctx.getState();
            state.cachedSongs = state.cachedSongs.map(s => 
                String(s.id) === String(id) ? { ...s, is_active: isChecked } : s
            );
            
            // If the song detail pane is open, refresh it
            // Compatibility: main.js uses activeDetailKey global
            const activeKey = typeof activeDetailKey !== "undefined" ? activeDetailKey : null;
            if (activeKey === `songs:${id}`) {
                this.ctx.refreshActiveDetail();
            }
        } catch (err) {
            // Revert state if failed (validation error, etc.)
            input.checked = !isChecked;
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Failed to toggle activation: ${err.message}`, "error");
            }
        }
    }

    async handleMarkReviewed(actionTarget) {
        return this._handleReviewStatus(actionTarget, 0); // 0 = REVIEWED
    }

    async handleUnreviewSong(actionTarget) {
        return this._handleReviewStatus(actionTarget, 1); // 1 = NEEDS_REVIEW
    }

    async _handleReviewStatus(actionTarget, newStatus) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        try {
            const updatedSong = await api.patchSongScalars(id, { processing_status: newStatus });
            if (this.ctx.openSongDetail) {
                this.ctx.openSongDetail(updatedSong, { reuseFileData: true });
            }
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Failed to update status: ${err.message}`, "error");
            }
        }
    }

    async handleMoveToLibrary(actionTarget) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        actionTarget.disabled = true;
        const originalText = actionTarget.textContent;
        actionTarget.textContent = "Organizing...";

        try {
            await api.moveSongToLibrary(id);
            if (this.ctx.showBanner) {
                this.ctx.showBanner("Organized successfully!", "success");
            }
            if (this.ctx.openSongDetail) {
                this.ctx.openSongDetail({ id }, { reuseFileData: false });
            }
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.textContent = originalText;
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Organization failed: ${err.message}`, "error");
            }
        }
    }

    async handleStartEditScalar(actionTarget) {
        const { songId, field } = actionTarget.dataset;
        const state = this.ctx.getState();

        activateInlineEdit(actionTarget, {
            field,
            validationRules: state.validationRules,
            onCommit: async (val) => {
                return await api.patchSongScalars(songId, { [field]: val });
            },
            onSave: (updatedSong, savedField) => {
                if (savedField === "media_name" || savedField === "title") {
                    const cached = state.cachedSongs.find(s => String(s.id) === String(songId));
                    if (cached) {
                        cached.media_name = updatedSong.media_name;
                        cached.title = updatedSong.media_name;
                    }
                }
                if (this.ctx.openSongDetail) {
                    this.ctx.openSongDetail(updatedSong, { reuseFileData: true });
                }
            },
        });
    }

    async handleSetPrimaryTag(actionTarget) {
        const { songId, tagId } = actionTarget.dataset;
        try {
            await api.setPrimarySongTag(songId, tagId);
            this.ctx.refreshActiveDetail();
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Failed to set primary tag: ${err.message}`, "error");
            }
        }
    }

    async handleRemoveTag(actionTarget) {
        const { songId, tagId } = actionTarget.dataset;
        try {
            await api.removeSongTag(songId, tagId);
            this.ctx.refreshActiveDetail();
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Failed to remove tag: ${err.message}`, "error");
            }
        }
    }

    async handleRemoveCredit(actionTarget) {
        const { songId, creditId } = actionTarget.dataset;
        try {
            await api.removeSongCredit(songId, creditId);
            this.ctx.refreshActiveDetail();
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Failed to remove credit: ${err.message}`, "error");
            }
        }
    }

    async handleRemoveAlbum(actionTarget) {
        const { songId, albumId } = actionTarget.dataset;
        try {
            await api.removeSongAlbum(songId, albumId);
            this.ctx.refreshActiveDetail();
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Failed to remove album: ${err.message}`, "error");
            }
        }
    }

    async handleOpenScrubber(actionTarget) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        const { title } = actionTarget.dataset;
        const orch = await import("../orchestrator.js");
        orch.orchestrateScrubber(this.ctx, id, title);
    }

    async handleFormatCase(actionTarget) {
        const { entityId, entityType, field, type } = actionTarget.dataset; // type = title or sentence
        try {
            const updatedSong = await api.formatMetadataCase(entityType, entityId, field, type);
            if (this.ctx.openSongDetail) {
                this.ctx.openSongDetail(updatedSong, { reuseFileData: true });
            }
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Formatting failed: ${err.message}`, "error");
            }
        }
    }

    async handleWebSearch(actionTarget) {
        const { songId, engine } = actionTarget.dataset;
        try {
            const data = await api.getSongWebSearch(songId, engine || null);
            if (data && data.url) {
                this._window.open(data.url, "_blank");
            }
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Search failed: ${err.message}`, "error");
            }
        }
    }

    async handleWebSearchSetEngine(actionTarget) {
        const splitEl = actionTarget.closest(".web-search-split");
        if (!splitEl) return;
        const dropdown = splitEl.querySelector(".web-search-dropdown");
        if (!dropdown) return;
        const isOpen = !dropdown.hidden;
        dropdown.hidden = isOpen;
        if (isOpen) return;

        // Close on outside click
        const close = (e) => {
            if (!splitEl.contains(e.target)) {
                dropdown.hidden = true;
                document.removeEventListener("click", close, true);
            }
        };
        document.addEventListener("click", close, true);

        dropdown.querySelectorAll(".web-search-option").forEach(btn => {
            btn.onclick = () => {
                const newEngine = btn.dataset.engine;
                const newLabel = btn.textContent.trim();
                const mainBtn = splitEl.querySelector(".web-search-main");
                const oldEngine = mainBtn.dataset.engine;
                const oldLabel = mainBtn.textContent.trim();

                // Swap main button
                mainBtn.dataset.engine = newEngine;
                mainBtn.textContent = newLabel;

                // Swap this option to show the old engine
                btn.dataset.engine = oldEngine;
                btn.textContent = oldLabel;

                dropdown.hidden = true;
                document.removeEventListener("click", close, true);
            };
        });
    }

    async handleConvertWav(actionTarget) {
        const { stagedPath } = actionTarget.dataset;
        actionTarget.disabled = true;
        const originalText = actionTarget.textContent;
        actionTarget.textContent = "Converting...";

        try {
            const res = await fetch(`/api/v1/ingest/convert-wav?staged_path=${encodeURIComponent(stagedPath)}`, { method: "POST" });
            const data = await res.json();
            const card = actionTarget.closest(".result-card");
            if ((data.status === "INGESTED" || data.status === "ALREADY_EXISTS") && card) {
                card.style.background = "rgba(76, 175, 80, 0.1)";
                card.style.borderLeft = "3px solid #4CAF50";
                const box = card.querySelector(".pending-convert-box");
                const msg = data.status === "ALREADY_EXISTS"
                    ? `✓ Already in library as "${data.song?.media_name || "Unknown"}"`
                    : `✓ Converted & Ingested as "${data.song?.media_name || "Unknown"}"`;
                if (box) box.innerHTML = `<div style="color: #4CAF50; font-weight: 600;">${msg}</div>`;
            } else {
                actionTarget.disabled = false;
                actionTarget.textContent = originalText;
                console.error("Conversion failed:", data.message);
            }
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.textContent = originalText;
            console.error("Error:", err.message);
        }
    }

    async handleResolveConflict(actionTarget) {
        const { ghostId, stagedPath } = actionTarget.dataset;
        actionTarget.disabled = true;
        const originalText = actionTarget.textContent;
        actionTarget.textContent = "Processing...";

        try {
            const res = await fetch(`/api/v1/ingest/resolve-conflict?ghost_id=${ghostId}&staged_path=${encodeURIComponent(stagedPath)}`, {
                method: "POST",
            });
            const data = await res.json();
            if (data.status === "INGESTED") {
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
                actionTarget.textContent = originalText;
                console.error("Failed to reactivate:", data.message);
            }
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.textContent = originalText;
            console.error("Error:", err.message);
        }
    }

    async handleCleanupOriginal(actionTarget) {
        const { path } = actionTarget.dataset;
        if (!await showConfirm(`Permanently delete the original file?\n\nPath: ${path}`, { title: "Delete Original File" })) {
            return;
        }

        actionTarget.style.opacity = "0.5";
        actionTarget.style.pointerEvents = "none";
        try {
            await api.cleanupOriginalFile(path);
            this.ctx.refreshActiveDetail();
            if (this.ctx.showBanner) {
                this.ctx.showBanner("Original file deleted successfully", "success");
            }
        } catch (err) {
            actionTarget.style.opacity = "1";
            actionTarget.style.pointerEvents = "auto";
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Cleanup failed: ${err.message}`, "error");
            }
        }
    }

    async handleOpenSplitterModal(actionTarget) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        const { text, target, classification, removeType, removeId } = actionTarget.dataset;
        const state = this.ctx.getState();
        const { openSplitterModal } = await import("../components/splitter_modal.js");
        
        openSplitterModal({
            songId: id,
            text,
            target,
            classification: classification || null,
            remove: { type: removeType, id: Number(removeId) },
            separators: state.validationRules?.credit_separators || [],
            onConfirm: () => {
                const song = state.cachedSongs.find(s => String(s.id) === String(id));
                if (song && this.ctx.openSongDetail) this.ctx.openSongDetail(song, { reuseFileData: true });
            },
        });
    }

    async handleOpenFilenameParserSingle(actionTarget) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        const { filename } = actionTarget.dataset;
        const { openFilenameParserModal } = await import("../components/filename_parser_modal.js");
        
        openFilenameParserModal({
            entries: [{ id: Number(id), filename }],
            onApply: async () => {
                const state = this.ctx.getState();
                const song = state.cachedSongs.find(s => String(s.id) === String(id));
                if (song && this.ctx.openSongDetail) this.ctx.openSongDetail(song, { reuseFileData: true });
                if (this.ctx.showBanner) this.ctx.showBanner("Metadata applied", "success");
            },
            onError: (msg) => {
                if (this.ctx.showBanner) this.ctx.showBanner(msg, "error");
            },
        });
    }
    async handleStartEditAlbumScalar(actionTarget) {
        const { albumId, songId, field } = actionTarget.dataset;
        const state = this.ctx.getState();
        
        activateInlineEdit(actionTarget, {
            field,
            validationRules: state.validationRules,
            onCommit: async (val) => {
                return await api.updateAlbum(albumId, { [field]: val });
            },
            onSave: () => {
                const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                if (song && this.ctx.openSongDetail) this.ctx.openSongDetail(song, { reuseFileData: true });
            }
        });
    }

    async handleStartEditAlbumLink(actionTarget) {
        const { albumId, songId, field } = actionTarget.dataset;
        const state = this.ctx.getState();
        
        activateInlineEdit(actionTarget, {
            field,
            validationRules: state.validationRules,
            onCommit: async (val) => {
                const card = actionTarget.closest(".album-card-detail");
                const otherField = field === "track_number" ? "disc_number" : "track_number";
                const otherSpan = card?.querySelector(`[data-field="${otherField}"]`);
                const otherVal = otherSpan ? (otherSpan.textContent === "-" ? null : Number(otherSpan.textContent)) : null;

                const track = field === "track_number" ? val : otherVal;
                const disc = field === "disc_number" ? val : otherVal;
                return await api.updateSongAlbumLink(songId, albumId, track, disc);
            },
            onSave: () => {
                const song = state.cachedSongs.find(s => String(s.id) === String(songId));
                if (song && this.ctx.openSongDetail) this.ctx.openSongDetail(song, { reuseFileData: true });
            }
        });
    }

    async handleOpenSpotifyModal(actionTarget) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        const { title } = actionTarget.dataset;
        const state = this.ctx.getState();
        const { openSpotifyModal } = await import("../components/spotify_modal.js");
        
        // Truth-First: Use the hydrated active song if it matches, otherwise fallback to cache
        let song = state.cachedSongs.find(s => String(s.id) === String(id));
        if (state.activeSong && String(state.activeSong.id) === String(id)) {
            song = state.activeSong;
        }

        openSpotifyModal({
            songId: id,
            title,
            existingCredits: song?.credits || [],
            existingPublishers: song?.publishers || [],
            onClose: () => {
                if (this.ctx.refreshActiveDetail) this.ctx.refreshActiveDetail();
            },
            onComplete: () => {
                if (this.ctx.refreshActiveDetail) this.ctx.refreshActiveDetail();
                if (this.ctx.showBanner) this.ctx.showBanner("Spotify credits imported successfully", "success");
            }
        });
    }

    handleCloseEditModal() {
        if (typeof closeEditModal === "function") {
            closeEditModal();
        } else {
            const el = document.getElementById("edit-modal");
            if (el) el.style.display = "none";
        }
    }

    handleCloseLinkModal() {
        if (typeof closeLinkModal === "function") {
            closeLinkModal();
        } else {
            const el = document.getElementById("link-modal");
            if (el) el.style.display = "none";
        }
    }

    async handleCloseSpotifyModal() {
        const { closeSpotifyModal } = await import("../components/spotify_modal.js");
        closeSpotifyModal();
    }

    async handleCloseSplitterModal() {
        const { closeSplitterModal } = await import("../components/splitter_modal.js");
        closeSplitterModal();
    }

    async handleCloseFilenameParserModal() {
        const { closeFilenameParserModal } = await import("../components/filename_parser_modal.js");
        closeFilenameParserModal();
    }

    async handleCloseScrubberModal() {
        const { closeScrubberModal } = await import("../components/scrubber_modal.js");
        closeScrubberModal();
    }

    async handleRemovePublisher(actionTarget) {
        const { songId, publisherId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await api.removeSongPublisher(songId, publisherId);
            this.ctx.refreshActiveDetail();
        } catch (err) {
            actionTarget.disabled = false;
            if (this.ctx.showBanner) this.ctx.showBanner(`Failed to remove publisher: ${err.message}`, "error");
        }
    }

    async handleRemoveAlbumPublisher(actionTarget) {
        const { albumId, publisherId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await api.removeAlbumPublisher(albumId, publisherId);
            this.ctx.refreshActiveDetail();
        } catch (err) {
            actionTarget.disabled = false;
            if (this.ctx.showBanner) this.ctx.showBanner(`Failed to remove album publisher: ${err.message}`, "error");
        }
    }

    async handleRemoveAlbumCredit(actionTarget) {
        const { albumId, creditId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await api.removeAlbumCredit(albumId, creditId);
            this.ctx.refreshActiveDetail();
        } catch (err) {
            actionTarget.disabled = false;
            if (this.ctx.showBanner) this.ctx.showBanner(`Failed to remove album credit: ${err.message}`, "error");
        }
    }

    async handleSyncAlbumFromSong(actionTarget) {
        const { albumId, songId } = actionTarget.dataset;
        actionTarget.disabled = true;
        actionTarget.textContent = "syncing...";
        try {
            await syncAlbumWithSong(albumId, songId);
            this.ctx.refreshActiveDetail();
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.textContent = "↓ sync from song";
            if (this.ctx.showBanner) this.ctx.showBanner(`Sync failed: ${err.message}`, "error");
        }
    }

    async handleChangeAlbumType(actionTarget) {
        const { albumId } = actionTarget.dataset;
        const newType = actionTarget.value;
        try {
            await api.updateAlbum(albumId, { album_type: newType });
        } catch (err) {
            if (this.ctx.showBanner) this.ctx.showBanner(`Update failed: ${err.message}`, "error");
            this.ctx.refreshActiveDetail();
        }
    }
}
