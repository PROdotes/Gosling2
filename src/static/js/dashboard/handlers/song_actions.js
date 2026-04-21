/**
 * GOSLING SONG ACTIONS HANDLER
 * Offloads business logic for song-related click actions from main.js.
 */

import * as api from "../api.js";
import { showToast } from "../components/toast.js";
import { isModalOpen } from "../components/utils.js";
import { PROCESSING_STATUS } from "../constants.js";

export async function updateSyncLed(songId) {
    const led = document.querySelector(`.sync-led[data-song-id="${songId}"]`);
    if (!led) return;
    led.title = "Checking sync...";
    led.style.background = "#888";
    const mismatchEl = document.querySelector(
        `.sync-mismatch-list[data-song-id="${songId}"]`,
    );
    if (mismatchEl) mismatchEl.textContent = "";
    try {
        const result = await api.getSongSyncStatus(songId);
        led.style.background = result.in_sync ? "#4caf50" : "#f44336";
        led.title = result.in_sync
            ? "In sync"
            : `Out of sync:\n${result.mismatches.join("\n")}`;
        if (mismatchEl) {
            const labels = result.mismatches.map((m) =>
                m.replace(/^credit:/, ""),
            );
            mismatchEl.textContent = result.in_sync ? "" : labels.join(" · ");
        }
    } catch {
        led.style.background = "#888";
        led.title = "Sync status unavailable";
    }
}

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
    const existingNameIds = new Set(
        (albumDetail.credits || []).map((c) => String(c.name_id)),
    );
    for (const credit of song.credits || []) {
        if (credit.role_name !== "Performer") continue;
        if (!existingNameIds.has(String(credit.name_id))) {
            ops.push(
                api.addAlbumCredit(
                    albumId,
                    credit.display_name,
                    credit.role_name,
                    credit.identity_id ?? null,
                ),
            );
        }
    }
    const existingPubIds = new Set(
        (albumDetail.publishers || []).map((p) => String(p.id)),
    );
    for (const pub of song.publishers || []) {
        if (!existingPubIds.has(String(pub.id))) {
            ops.push(api.addAlbumPublisher(albumId, pub.name, pub.id));
        }
    }
    await Promise.all(ops);
}

import { showConfirm } from "../components/confirm_modal.js";

export class SongActionsHandler {
    constructor(ctx, _window = typeof window !== "undefined" ? window : null) {
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
            "close-scrubber-modal",
            "sync-id3",
            "quick-create-album",
        ]);
    }

    /**
     * Dispatcher for click events.
     * @param {Event} event
     * @returns {Promise<boolean>} True if action was handled
     */
    async handle(event) {
        // Support both real DOM events and virtual dispatch objects
        const actionTarget =
            event.target && typeof event.target.closest === "function"
                ? event.target.closest("[data-action]")
                : event.target;

        if (!actionTarget) return false;

        const { action } = actionTarget.dataset;
        if (!this.songActions.has(action)) return false;

        // Protocol: Modals are top-level. Block actions if any modal is open,
        // UNLESS the action is specifically a close-modal action or inside a modal.
        const isInsideModal =
            typeof actionTarget.closest === "function" &&
            actionTarget.closest(".link-modal");
        if (isModalOpen() && !isInsideModal && !action.startsWith("close-")) {
            return false;
        }

        // Method dispatch pattern: handleActionName
        const methodName = `handle${action
            .split("-")
            .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
            .join("")}`;

        if (typeof this[methodName] === "function") {
            try {
                await this[methodName](actionTarget, event);
                return true;
            } catch (err) {
                console.error(
                    `[Handler] Method ${methodName} failed: ${err.message}`,
                    err,
                );
                return true;
            }
        }

        return false;
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
                if (
                    actionTarget.classList.contains("confirming") &&
                    !actionTarget.disabled
                ) {
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
            if (
                this.ctx.getState().currentMode === "songs" &&
                this.ctx.clearSongEditorV2
            ) {
                this.ctx.clearSongEditorV2();
            } else if (this.ctx.hideDetailPanel) {
                this.ctx.hideDetailPanel();
            }

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
        // When event.target is the <input> itself the browser has already toggled it,
        // so checked reflects the new value. When target is the <label> or <span>
        // the browser hasn't toggled yet, so we invert.
        const isChecked =
            event?.target === input ? input.checked : !input.checked;

        try {
            await api.patchSongScalars(id, { is_active: isChecked });

            // Sync current items in any list results
            const state = this.ctx.getState();
            state.cachedSongs = state.cachedSongs.map((s) =>
                String(s.id) === String(id)
                    ? { ...s, is_active: isChecked }
                    : s,
            );

            // Refresh V2 editor if in V2 songs mode and this song is active
            if (
                this.ctx.refreshActiveSongV2 &&
                state.currentMode === "songs" &&
                state.activeSong &&
                String(state.activeSong.id) === String(id)
            ) {
                await this.ctx.refreshActiveSongV2(id);
            } else {
                const activeKey = this.ctx.getActiveDetailKey?.() ?? null;
                if (activeKey === `songs:${id}`) {
                    this.ctx.refreshActiveDetail();
                }
            }
        } catch (err) {
            // Revert state if failed (validation error, etc.)
            input.checked = !isChecked;
            if (this.ctx.showBanner) {
                this.ctx.showBanner(
                    `Failed to toggle activation: ${err.message}`,
                    "error",
                );
            }
        }
    }

    async handleMarkReviewed(actionTarget) {
        return this._handleReviewStatus(
            actionTarget,
            PROCESSING_STATUS.REVIEWED,
        );
    }

    async handleUnreviewSong(actionTarget) {
        return this._handleReviewStatus(
            actionTarget,
            PROCESSING_STATUS.NEEDS_REVIEW,
        );
    }

    async _handleReviewStatus(actionTarget, newStatus) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        try {
            await api.patchSongScalars(id, { processing_status: newStatus });
            if (this.ctx.refreshActiveSongV2) {
                await this.ctx.refreshActiveSongV2(id);
            }
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(
                    `Failed to update status: ${err.message}`,
                    "error",
                );
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
            
            // Check for original file cleanup reminder
            const state = this.ctx.getState();
            const song = state.activeSong;
            const hadOriginal = song && song.original_exists && song.id == id;

            if (this.ctx.showBanner) {
                this.ctx.showBanner("Organized successfully!", "success");
            }
            if (this.ctx.refreshActiveSongV2) {
                await this.ctx.refreshActiveSongV2(id);
            }

            if (hadOriginal) {
                // Fetch fresh song to see if it still exists (it should, move just copies in some cases or moves staged)
                const fresh = this.ctx.getState().activeSong;
                if (fresh && fresh.original_exists) {
                    const cleanNow = await showConfirm(
                        "Song organized! However, the original source file still exists in your Downloads folder.\n\nWould you like to delete the original copy now?",
                        {
                            title: "Cleanup Original File",
                            okLabel: "Yes, Delete Original",
                            cancelLabel: "Not Now"
                        }
                    );
                    if (cleanNow) {
                        try {
                            await api.cleanupOriginalFile(null, id);
                            showToast("Original file deleted.", "success");
                            await this.ctx.refreshActiveSongV2(id);
                        } catch (cleanErr) {
                            showToast(`Cleanup failed: ${cleanErr.message}`, "error");
                        }
                    }
                }
            }
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.textContent = originalText;

            const msg = `Organization failed: ${err.message}`;
            // 409 Conflict - File already exists at target
            if (
                err.message &&
                (err.message.includes("already exists") ||
                    err.message.includes("409"))
            ) {
                await showConfirm(
                    "Conflict detected: A file with this name already exists in the destination library folder. Please check for duplicates.",
                    {
                        title: "Organization Conflict",
                        okLabel: "OK",
                        cancelLabel: null,
                    },
                );
                return;
            }

            if (this.ctx.showBanner) {
                this.ctx.showBanner(msg, "error");
            }
        }
    }

    async handleSyncId3(actionTarget) {
        const id = actionTarget.dataset.songId;
        actionTarget.disabled = true;
        const originalText = actionTarget.textContent;
        actionTarget.textContent = "Syncing...";
        try {
            await api.syncSongId3(id);
            if (this.ctx.showBanner)
                this.ctx.showBanner("ID3 tags updated.", "success");
            await updateSyncLed(id);
        } catch (err) {
            if (this.ctx.showBanner)
                this.ctx.showBanner(`ID3 sync failed: ${err.message}`, "error");
        } finally {
            actionTarget.disabled = false;
            actionTarget.textContent = originalText;
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
            onSave: async (updatedSong, savedField) => {
                if (savedField === "media_name" || savedField === "title") {
                    const cached = state.cachedSongs.find(
                        (s) => String(s.id) === String(songId),
                    );
                    if (cached) {
                        cached.media_name = updatedSong.media_name;
                        cached.title = updatedSong.media_name;
                    }
                }
                if (this.ctx.refreshActiveSongV2) {
                    await this.ctx.refreshActiveSongV2(songId);
                }
            },
        });
    }

    async handleSetPrimaryTag(actionTarget) {
        const { songId, tagId } = actionTarget.dataset;
        try {
            await api.setPrimarySongTag(songId, tagId);
            if (
                this.ctx.refreshActiveSongV2 &&
                this.ctx.getState().currentMode === "songs"
            ) {
                await this.ctx.refreshActiveSongV2(songId);
            } else {
                this.ctx.refreshActiveDetail();
            }
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(
                    `Failed to set primary tag: ${err.message}`,
                    "error",
                );
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
                this.ctx.showBanner(
                    `Failed to remove tag: ${err.message}`,
                    "error",
                );
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
                this.ctx.showBanner(
                    `Failed to remove credit: ${err.message}`,
                    "error",
                );
            }
        }
    }

    async handleRemoveAlbum(actionTarget) {
        const { songId, albumId } = actionTarget.dataset;
        try {
            await api.removeSongAlbum(songId, albumId);
            if (
                this.ctx.refreshActiveSongV2 &&
                this.ctx.getState().currentMode === "songs"
            ) {
                await this.ctx.refreshActiveSongV2(songId);
            } else {
                this.ctx.refreshActiveDetail();
            }
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(
                    `Failed to remove album: ${err.message}`,
                    "error",
                );
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
            const updatedSong = await api.formatMetadataCase(
                entityType,
                entityId,
                field,
                type,
            );
            if (this.ctx.refreshActiveSongV2 && entityType === "song") {
                await this.ctx.refreshActiveSongV2(entityId);
            } else {
                this.ctx.refreshActiveDetail();
            }
        } catch (err) {
            if (this.ctx.showBanner) {
                this.ctx.showBanner(
                    `Formatting failed: ${err.message}`,
                    "error",
                );
            }
        }
    }

    async handleWebSearch(actionTarget) {
        const { engine } = actionTarget.dataset;
        const songId =
            actionTarget.dataset.songId ||
            actionTarget
                .closest(".web-search-split")
                ?.querySelector(".web-search-main")?.dataset.songId;
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

        dropdown.querySelectorAll(".web-search-option").forEach((btn) => {
            btn.onclick = () => {
                const newEngine = btn.dataset.engine;
                const newLabel = btn.textContent.trim();
                const mainBtn = splitEl.querySelector(".web-search-main");
                const oldEngine = mainBtn.dataset.engine;
                const oldLabel = mainBtn.textContent.trim();

                // Swap main button (preserve songId)
                mainBtn.dataset.engine = newEngine;
                mainBtn.textContent = newLabel;

                // Swap this option to show the old engine
                btn.dataset.engine = oldEngine;
                btn.textContent = oldLabel;
                btn.dataset.songId = mainBtn.dataset.songId;

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
            const res = await fetch(
                `/api/v1/ingest/convert-wav?staged_path=${encodeURIComponent(stagedPath)}`,
                { method: "POST" },
            );
            if (!res.ok) throw new Error("Conversion failed");
            showToast("Conversion started...", "info");
            if (this.ctx.updateCachedIngestResult) {
                this.ctx.updateCachedIngestResult(stagedPath, {
                    status: "CONVERTING",
                });
            }
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.textContent = originalText;
            showToast(`Error: ${err.message}`, "error");
        }
    }

    async handleResolveConflict(actionTarget) {
        const { ghostId, stagedPath } = actionTarget.dataset;
        actionTarget.disabled = true;
        const originalText = actionTarget.textContent;
        actionTarget.textContent = "Processing...";

        try {
            const data = await api.resolveConflict(ghostId, stagedPath);

            showToast("Song reactivated successfully!", "success");

            if (data.status === "INGESTED") {
                const card = actionTarget.closest(".result-card");
                if (card) {
                    card.classList.remove("conflict");
                    card.classList.add("ingested");
                    card.innerHTML = `
                        <div class="card-icon ingest-icon">&#10003;</div>
                        <div class="card-body">
                            <div class="card-title-row">
                                <div class="card-title">Reactivated (Success)</div>
                                <div class="file-status found">Ingested</div>
                            </div>
                            <div class="muted-note">Record restored with new file mapping.</div>
                        </div>
                    `;
                }

                if (this.ctx.updateIngestBadges) {
                    const status = await api.getIngestStatus();
                    this.ctx.updateIngestBadges({
                        success: status.success,
                        action: status.action,
                        pending: status.pending,
                    });
                }
                if (this.ctx.updateCachedIngestResult) {
                    this.ctx.updateCachedIngestResult(stagedPath, {
                        status: "INGESTED",
                        song: data.song,
                    });
                }
            } else if (data.status === "PENDING_CONVERT") {
                const card = actionTarget.closest(".result-card");
                if (card) {
                    const conflictBox = card.querySelector("[data-ghost-box]");
                    if (conflictBox) {
                        conflictBox.className = "pending-convert-box";
                        conflictBox.innerHTML = `
                            <div class="muted-note" style="font-size: 0.75rem; margin-bottom: 0.75rem; font-style: italic;">
                                This WAV file needs to be converted to MP3 before ingestion.
                            </div>
                            <button style="padding: 0.5rem 1rem; background: #ff9500; color: white; border: none; border-radius: 4px; font-weight: 600; cursor: pointer;" data-action="convert-wav" data-staged-path="${stagedPath}">
                                Convert & Ingest
                            </button>
                        `;
                    }
                }
            }
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.textContent = originalText;
            showToast(`Error: ${err.message}`, "error");
        }
    }

    async handleCleanupOriginal(actionTarget) {
        const { path } = actionTarget.dataset;
        if (
            !(await showConfirm(
                `Permanently delete the original file?\n\nPath: ${path}`,
                { title: "Delete Original File" },
            ))
        ) {
            return;
        }

        actionTarget.style.opacity = "0.5";
        actionTarget.style.pointerEvents = "none";
        const songId = actionTarget.dataset.id || actionTarget.dataset.songId;
        try {
            await api.cleanupOriginalFile(path, songId);
            if (this.ctx.refreshActiveSongV2) {
                await this.ctx.refreshActiveSongV2(songId);
            } else {
                this.ctx.refreshActiveDetail();
            }
            if (this.ctx.showBanner) {
                this.ctx.showBanner(
                    "Original file deleted successfully",
                    "success",
                );
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
        const { text, target, classification, removeType, removeId } =
            actionTarget.dataset;
        const state = this.ctx.getState();
        const { openSplitterModal } = await import(
            "../components/splitter_modal.js"
        );

        openSplitterModal({
            songId: id,
            text,
            target,
            classification: classification || null,
            remove: { type: removeType, id: Number(removeId) },
            separators: state.validationRules?.credit_separators || [],
            onConfirm: async () => {
                const song = state.cachedSongs.find(
                    (s) => String(s.id) === String(id),
                );
                if (song && this.ctx.refreshActiveSongV2)
                    await this.ctx.refreshActiveSongV2(song.id);
            },
        });
    }

    async handleOpenFilenameParserSingle(actionTarget) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        const { filename } = actionTarget.dataset;
        const { openFilenameParserModal } = await import(
            "../components/filename_parser_modal.js"
        );

        openFilenameParserModal({
            entries: [{ id: Number(id), filename }],
            onApply: async () => {
                if (this.ctx.showBanner)
                    this.ctx.showBanner("Metadata applied", "success");
                if (this.ctx.refreshActiveSongV2) {
                    await this.ctx.refreshActiveSongV2(id);
                } else {
                    this.ctx.refreshActiveDetail();
                }
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
            onSave: async () => {
                if (
                    this.ctx.refreshActiveSongV2 &&
                    state.currentMode === "songs"
                ) {
                    await this.ctx.refreshActiveSongV2(songId);
                } else {
                    this.ctx.refreshActiveDetail();
                }
            },
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
                const otherField =
                    field === "track_number" ? "disc_number" : "track_number";
                const otherSpan = card?.querySelector(
                    `[data-field="${otherField}"]`,
                );
                const otherVal = otherSpan
                    ? otherSpan.textContent === "-"
                        ? null
                        : Number(otherSpan.textContent)
                    : null;

                const track = field === "track_number" ? val : otherVal;
                const disc = field === "disc_number" ? val : otherVal;
                return await api.updateSongAlbumLink(
                    songId,
                    albumId,
                    track,
                    disc,
                );
            },
            onSave: async () => {
                if (
                    this.ctx.refreshActiveSongV2 &&
                    state.currentMode === "songs"
                ) {
                    await this.ctx.refreshActiveSongV2(songId);
                } else {
                    this.ctx.refreshActiveDetail();
                }
            },
        });
    }

    async handleOpenSpotifyModal(actionTarget) {
        const id = actionTarget.dataset.id || actionTarget.dataset.songId;
        const { title } = actionTarget.dataset;
        const state = this.ctx.getState();
        const { openSpotifyModal } = await import(
            "../components/spotify_modal.js"
        );

        // Truth-First: Use the hydrated active song if it matches, otherwise fallback to cache
        let song = state.cachedSongs.find((s) => String(s.id) === String(id));
        if (state.activeSong && String(state.activeSong.id) === String(id)) {
            song = state.activeSong;
        }

        openSpotifyModal({
            songId: id,
            title,
            existingCredits: song?.credits || [],
            existingPublishers: song?.publishers || [],
            onComplete: async () => {
                if (this.ctx.showBanner)
                    this.ctx.showBanner(
                        "Spotify credits imported successfully",
                        "success",
                    );
                if (this.ctx.refreshActiveSongV2) {
                    await this.ctx.refreshActiveSongV2(id);
                } else {
                    this.ctx.refreshActiveDetail();
                }
            },
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
        const { closeSpotifyModal } = await import(
            "../components/spotify_modal.js"
        );
        closeSpotifyModal();
    }

    async handleCloseSplitterModal() {
        const { closeSplitterModal } = await import(
            "../components/splitter_modal.js"
        );
        closeSplitterModal();
    }

    async handleCloseFilenameParserModal() {
        const { closeFilenameParserModal } = await import(
            "../components/filename_parser_modal.js"
        );
        closeFilenameParserModal();
        await this._refreshActiveSong();
    }

    async handleCloseScrubberModal() {
        const { closeScrubberModal } = await import(
            "../components/scrubber_modal.js"
        );
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
            if (this.ctx.showBanner)
                this.ctx.showBanner(
                    `Failed to remove publisher: ${err.message}`,
                    "error",
                );
        }
    }

    async handleRemoveAlbumPublisher(actionTarget) {
        const { albumId, publisherId, songId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await api.removeAlbumPublisher(albumId, publisherId);
            if (
                songId &&
                this.ctx.refreshActiveSongV2 &&
                this.ctx.getState().currentMode === "songs"
            ) {
                await this.ctx.refreshActiveSongV2(songId);
            } else {
                this.ctx.refreshActiveDetail();
            }
        } catch (err) {
            actionTarget.disabled = false;
            if (this.ctx.showBanner)
                this.ctx.showBanner(
                    `Failed to remove album publisher: ${err.message}`,
                    "error",
                );
        }
    }

    async handleRemoveAlbumCredit(actionTarget) {
        const { albumId, creditId, songId } = actionTarget.dataset;
        actionTarget.disabled = true;
        try {
            await api.removeAlbumCredit(albumId, creditId);
            if (
                songId &&
                this.ctx.refreshActiveSongV2 &&
                this.ctx.getState().currentMode === "songs"
            ) {
                await this.ctx.refreshActiveSongV2(songId);
            } else {
                this.ctx.refreshActiveDetail();
            }
        } catch (err) {
            actionTarget.disabled = false;
            if (this.ctx.showBanner)
                this.ctx.showBanner(
                    `Failed to remove album credit: ${err.message}`,
                    "error",
                );
        }
    }

    async handleSyncAlbumFromSong(actionTarget) {
        const { albumId, songId } = actionTarget.dataset;
        actionTarget.disabled = true;
        actionTarget.classList.add("loading");
        const originalText = actionTarget.textContent;
        actionTarget.textContent = "Syncing...";

        try {
            await syncAlbumWithSong(albumId, songId);
            actionTarget.classList.remove("loading");
            actionTarget.classList.add("success");
            actionTarget.textContent = "✓ Synced";

            // Brief delay to show success before refreshing
            await new Promise((r) => setTimeout(r, 600));

            if (
                this.ctx.refreshActiveSongV2 &&
                this.ctx.getState().currentMode === "songs"
            ) {
                await this.ctx.refreshActiveSongV2(songId);
            } else {
                this.ctx.refreshActiveDetail();
            }
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.classList.remove("loading");
            actionTarget.textContent = originalText;
            if (this.ctx.showBanner)
                this.ctx.showBanner(`Sync failed: ${err.message}`, "error");
        }
    }

    async handleChangeAlbumType(actionTarget) {
        const { albumId } = actionTarget.dataset;
        const newType = actionTarget.value;
        try {
            await api.updateAlbum(albumId, { album_type: newType });
        } catch (err) {
            if (this.ctx.showBanner)
                this.ctx.showBanner(`Update failed: ${err.message}`, "error");
            this.ctx.refreshActiveDetail();
        }
    }

    async handleQuickCreateAlbum(actionTarget) {
        const { songId } = actionTarget.dataset;
        const state = this.ctx.getState();
        const song = state.activeSong;
        if (!song || !song.media_name) return;

        actionTarget.disabled = true;
        actionTarget.classList.add("loading");
        const originalHtml = actionTarget.innerHTML;
        actionTarget.innerHTML = "Creating...";

        try {
            // 1. Create and Link Album
            const res = await api.addSongAlbum(
                songId,
                null,           /* albumId (null for new) */
                song.media_name,/* albumTitle */
                1,              /* disc_number */
                1               /* track_number */
            );

            const albumId = res.album_id;

            // 2. Sync metadata (Artist, Publisher, Year)
            await syncAlbumWithSong(albumId, songId);

            // 3. Optional: Sync from Song logic often needs a refresh of the song detail
            if (this.ctx.refreshActiveSongV2) {
                await this.ctx.refreshActiveSongV2(songId);
            } else {
                this.ctx.refreshActiveDetail();
            }

            showToast(`Album "${song.media_name}" created & synced.`, "success");

            // Reset button state since surgical refresh doesn't overwrite this DOM node
            actionTarget.disabled = false;
            actionTarget.classList.remove("loading");
            actionTarget.innerHTML = originalHtml;
        } catch (err) {
            actionTarget.disabled = false;
            actionTarget.classList.remove("loading");
            actionTarget.innerHTML = originalHtml;
            if (this.ctx.showBanner) {
                this.ctx.showBanner(`Quick Create failed: ${err.message}`, "error");
            }
        }
    }

    async _refreshActiveSong() {
        const state = this.ctx.getState();
        const song = state.activeSong;
        if (!song) return;
        if (state.currentMode === "songs" && this.ctx.refreshActiveSongV2) {
            await this.ctx.refreshActiveSongV2(song.id);
        } else if (this.ctx.refreshActiveDetail) {
            this.ctx.refreshActiveDetail();
        }
    }
}
