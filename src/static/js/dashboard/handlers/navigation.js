/**
 * GOSLING NAVIGATION HANDLER
 * Handles navigation, mode switching, and non-song click actions.
 */

import * as api from "../api.js";
import { openEditModal } from "../components/edit_modal.js";
import { isModalOpen } from "../components/utils.js";
import * as orch from "../orchestrator.js";
import { showConfirm } from "../components/confirm_modal.js";

export class NavigationHandler {
    constructor(ctx, elements, searchInput) {
        this.ctx = ctx;
        this.elements = elements;
        this.searchInput = searchInput;
        this.actions = new Set([
            "switch-mode",
            "refresh-results",
            "select-result",
            "navigate-search",
            "open-edit-modal",
            "open-link-modal",
            "delete-tag",
            "bulk-delete-unlinked-tags",
            "delete-album",
            "bulk-delete-unlinked-albums",
            "delete-publisher",
            "bulk-delete-unlinked-publishers",
            "delete-identity",
            "bulk-delete-unlinked-identities",
        ]);
    }

    async handle(event, songActions) {
        const actionTarget = event.target?.closest("[data-action]");
        if (!actionTarget) return false;

        const { action } = actionTarget.dataset;
        if (!this.actions.has(action)) return false;

        if (isModalOpen()) {
            const isModalComponent = actionTarget.closest(".link-modal");
            const isCloseAction = action.startsWith("close-");
            if (!isModalComponent && !isCloseAction) {
                return false;
            }
        }

        const methodName = `handle${action
            .split("-")
            .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
            .join("")}`;

        if (typeof this[methodName] === "function") {
            await this[methodName](actionTarget, event, songActions);
            return true;
        }

        return false;
    }

    async handleSwitchMode(actionTarget) {
        const { mode } = actionTarget.dataset;
        await this.ctx.switchMode?.(mode);
    }

    async handleRefreshResults(actionTarget) {
        const state = this.ctx.getState();
        actionTarget.classList.add("spinning");
        await api.resetIngestStatus().catch((e) =>
            console.error("Ingest reset failed", e),
        );
        await Promise.all([this.ctx.reloadFilters?.(), this.ctx.syncIngestBadges?.()]);
        this.ctx.performSearch?.(state.currentQuery).finally(() => {
            actionTarget.classList.remove("spinning");
        });
    }

    async handleSelectResult(actionTarget, event) {
        if (event.target.type === "checkbox") return;
        event.preventDefault();
        const { index } = actionTarget.dataset;
        const state = this.ctx.getState();
        state.selectedIndex = Number.isNaN(Number(index)) ? -1 : Number(index);
        this.ctx.updateSelection?.();

        const selected = state.displayedItems?.[state.selectedIndex];
        if (selected) {
            const cachedList = this.ctx.getActiveList?.();
            const actualIndex = cachedList?.findIndex(
                (item) => item.id === selected.id,
            );
            if (actualIndex >= 0) {
                this.ctx.openSelectedResult?.(actualIndex);
            }
        }
    }

    async handleNavigateSearch(actionTarget) {
        const { mode, query } = actionTarget.dataset;
        this.ctx.navigate?.(mode, query || "");
    }

    async handleOpenEditModal(actionTarget) {
        const { chipType, itemId } = actionTarget.dataset;
        const state = this.ctx.getState?.();
        const inV2Songs = state?.currentMode === "songs"
            && document.getElementById("song-list-panel")
            && state?.activeSong;
        const onClose = inV2Songs
            ? () => this.ctx.refreshActiveSongV2?.(state.activeSong.id)
            : this.ctx.refreshActiveDetail;

        if (chipType === "publisher") {
            const publisherName = actionTarget.textContent.trim();
            const publisherDetail = await api
                .getPublisherDetail(itemId)
                .catch(() => null);
            const childItems =
                publisherDetail?.sub_publishers?.map((c) => ({
                    id: c.id,
                    label: c.name,
                })) || [];

            openEditModal(
                {
                    title: "Edit Publisher",
                    name: publisherDetail?.name || publisherName,
                    onRename: async (newName) =>
                        api.updatePublisher(itemId, newName),
                    onClose,
                    category: null,
                    children: {
                        label: "Sub-publishers",
                        items: childItems,
                        onSearch: async (q) =>
                            (await api.searchPublishers(q))?.map((p) => ({
                                id: p.id,
                                label: p.name,
                            })) || [],
                        onAdd: async (opt) => {
                            await api.setPublisherParent(
                                opt.id,
                                Number(itemId),
                            );
                            childItems.push({ id: opt.id, label: opt.label });
                        },
                        onRemove: async (item) =>
                            api.setPublisherParent(item.id, null),
                        onRenameChild: async (item, newName) =>
                            api.updatePublisher(item.id, newName),
                        createLabel: (q) => `Add "${q}" as sub-publisher`,
                    },
                },
                actionTarget,
            );
        } else if (chipType === "tag") {
            const tagDetail = await api.getTagDetail(itemId).catch(() => null);
            if (!tagDetail) return;

            openEditModal(
                {
                    title: "Edit Tag",
                    name: tagDetail.name,
                    onRename: async (newName) =>
                        api.updateTag(itemId, newName, tagDetail.category),
                    onClose,
                    category: {
                        label: "Category",
                        value: tagDetail.category,
                        editable: true,
                        onSave: async (val) =>
                            api.updateTag(itemId, tagDetail.name, val),
                        onSearch: async (q) =>
                            (await api.getTagCategories()).filter((c) =>
                                c.toLowerCase().includes(q.toLowerCase()),
                            ),
                    },
                    children: null,
                },
                actionTarget,
            );
        } else if (chipType === "credit") {
            const identityId = actionTarget.dataset.identityId;
            if (!identityId) return;
            await orch.manageArtist(
                this.ctx,
                identityId,
                actionTarget.textContent.trim(),
            );
        }
    }

    async handleOpenLinkModal(actionTarget) {
        const { modalType, songId } = actionTarget.dataset;
        const state = this.ctx.getState();
        const activeSong = state.activeSong;

        if (modalType === "publishers") {
            const currentPublishers = (activeSong?.publishers || []).map(
                (p) => ({ id: p.id, label: p.name }),
            );
            orch.manageSongPublishers(this.ctx, songId, currentPublishers);
        } else if (modalType === "tags") {
            const currentTags = activeSong?.tags || [];
            const songTitle = activeSong?.title || "Song";
            orch.manageSongTags(this.ctx, songId, songTitle, currentTags);
        } else if (modalType === "credits") {
            const { role } = actionTarget.dataset;
            const currentCredits = (activeSong?.credits || []).filter(
                (c) => c.role_name === role,
            );
            orch.manageSongCredits(this.ctx, songId, role, currentCredits);
        } else if (modalType === "album") {
            const { songTitle } = actionTarget.dataset;
            const section = actionTarget.closest(".detail-section");
            const libraryBox = section?.querySelector(".surface-box");
            const currentAlbums = Array.from(
                libraryBox?.querySelectorAll(
                    `[data-action="remove-album"][data-song-id="${songId}"]`,
                ) || [],
            ).map((btn) => ({
                id: btn.dataset.albumId,
                label:
                    btn
                        .closest(".album-card-detail")
                        ?.querySelector(".editable-scalar")
                        ?.textContent?.trim() || "",
            }));
            orch.manageSongAlbums(this.ctx, songId, songTitle, currentAlbums);
        } else if (modalType === "album-publishers") {
            const { albumId } = actionTarget.dataset;
            const chips = Array.from(
                actionTarget
                    .closest(".album-card-detail")
                    ?.querySelectorAll(
                        "[data-action='remove-album-publisher']",
                    ) || [],
            ).map((btn) => ({
                id: btn.dataset.publisherId,
                label:
                    btn
                        .closest(".link-chip")
                        ?.querySelector(".link-chip-label")
                        ?.textContent.trim() || "",
            }));
            orch.manageAlbumPublishers(this.ctx, albumId, songId, chips);
        } else if (modalType === "album-credits") {
            const { albumId } = actionTarget.dataset;
            const chips = Array.from(
                actionTarget
                    .closest(".album-card-detail")
                    ?.querySelectorAll("[data-action='remove-album-credit']") ||
                    [],
            ).map((btn) => ({
                id: btn.dataset.creditId,
                label:
                    btn
                        .closest(".link-chip")
                        ?.querySelector(".link-chip-label")
                        ?.textContent.trim() || "",
            }));
            orch.manageAlbumCredits(this.ctx, albumId, songId, chips);
        }
    }

    setupKeyboardHandler(songActions) {
        document.addEventListener("keydown", (event) => {
            const modalOpen = isModalOpen();

            if (event.key === "Escape" && modalOpen) {
                const openModal = [
                    "edit-modal",
                    "link-modal",
                    "scrubber-modal",
                    "spotify-modal",
                    "splitter-modal",
                    "filename-parser-modal",
                ].find((id) => {
                    const el = document.getElementById(id);
                    return el && el.style.display === "flex";
                });

                if (openModal) {
                    songActions.handle({
                        target: { dataset: { action: `close-${openModal}` } },
                        stopPropagation: () => {},
                    });
                }
                return;
            }

            if (
                event.key === "Escape" &&
                this.elements.detailPanel.style.display === "flex" &&
                !modalOpen
            ) {
                this.ctx.abortDetailRequest?.();
                this.ctx.hideDetailPanel?.();

                const state = this.ctx.getState();
                if (state.currentMode === "ingest") {
                    state.actionCount = 0;
                    this.ctx.updateIngestBadges?.();
                }

                state.selectedIndex = -1;
                this.ctx.updateSelection?.();
                return;
            }

            if (modalOpen || document.activeElement === this.searchInput) {
                return;
            }

            const items = this.ctx.getState().displayedItems;
            if (!items.length) return;

            if (event.key === "ArrowDown") {
                event.preventDefault();
                const state = this.ctx.getState();
                state.selectedIndex = Math.min(
                    state.selectedIndex + 1,
                    items.length - 1,
                );
                this.ctx.updateSelection?.();

                const cachedList = this.ctx.getActiveList?.();
                const selected = items[state.selectedIndex];
                if (selected) {
                    const actualIndex = cachedList?.findIndex(
                        (item) => item.id === selected.id,
                    );
                    if (actualIndex >= 0)
                        this.ctx.openSelectedResult?.(actualIndex);
                }
                return;
            }

            if (event.key === "ArrowUp") {
                event.preventDefault();
                const state = this.ctx.getState();
                state.selectedIndex = Math.max(state.selectedIndex - 1, -1);
                this.ctx.updateSelection?.();

                const cachedList = this.ctx.getActiveList?.();
                const selected = items[state.selectedIndex];
                if (selected) {
                    const actualIndex = cachedList?.findIndex(
                        (item) => item.id === selected.id,
                    );
                    if (actualIndex >= 0)
                        this.ctx.openSelectedResult?.(actualIndex);
                }
                return;
            }

            if (
                (event.key === "+" || event.key === "Add") &&
                event.location === KeyboardEvent.DOM_KEY_LOCATION_NUMPAD
            ) {
                event.preventDefault();
                const state = this.ctx.getState();
                if (state.currentMode === "songs" && state.activeSong) {
                    const btn = document.querySelector(
                        `[data-action="sync-id3"][data-song-id="${state.activeSong.id}"]`,
                    );
                    if (btn) btn.click();
                }
                return;
            }

            if (
                event.key === "Enter" &&
                this.ctx.getState().selectedIndex >= 0
            ) {
                event.preventDefault();
                const state = this.ctx.getState();
                const selected = items[state.selectedIndex];
                if (!selected) return;

                const isSongDetailOpen =
                    state.currentMode === "songs" &&
                    this.elements.detailPanel.style.display === "flex";
                const isActiveSongDetail =
                    isSongDetailOpen &&
                    state.activeSong &&
                    String(state.activeSong.id) === String(selected.id);

                if (isActiveSongDetail) {
                    orch.orchestrateScrubber(
                        this.ctx,
                        state.activeSong.id,
                        state.activeSong.media_name || state.activeSong.title,
                    );
                    return;
                }

                const cachedList = this.ctx.getActiveList?.();
                const actualIndex = cachedList?.findIndex(
                    (item) => item.id === selected.id,
                );
                if (actualIndex >= 0)
                    this.ctx.openSelectedResult?.(actualIndex);
            }
        });
    }

    async handleDeleteTag(actionTarget) {
        const tagId = actionTarget.dataset.tagId;
        if (!await showConfirm("Delete this tag? This cannot be undone.")) return;
        try {
            await api.deleteTag(tagId);
            this.ctx.closeDetailPanel?.();
            this.ctx.performSearch?.(this.ctx.getState().currentQuery);
        } catch (err) {
            await showConfirm(`Delete failed: ${err.message}`, { title: "Error", okLabel: "OK" });
        }
    }

    async handleBulkDeleteUnlinkedTags() {
        if (!await showConfirm("Delete all unlinked tags? This cannot be undone.")) return;
        try {
            await api.bulkDeleteUnlinkedTags();
            this.ctx.performSearch?.(this.ctx.getState().currentQuery);
        } catch (err) {
            await showConfirm(`Bulk delete failed: ${err.message}`, { title: "Error", okLabel: "OK" });
        }
    }

    async handleDeleteAlbum(actionTarget) {
        const { albumId, songId } = actionTarget.dataset;
        if (!await showConfirm("Delete this album? This cannot be undone.")) return;
        try {
            await api.deleteAlbum(albumId);
            if (songId && this.ctx.refreshActiveSongV2 && this.ctx.getState().currentMode === "songs") {
                await this.ctx.refreshActiveSongV2(songId);
            } else {
                this.ctx.closeDetailPanel?.();
                this.ctx.performSearch?.(this.ctx.getState().currentQuery);
            }
        } catch (err) {
            await showConfirm(`Delete failed: ${err.message}`, { title: "Error", okLabel: "OK" });
        }
    }

    async handleBulkDeleteUnlinkedAlbums() {
        if (!await showConfirm("Delete all unlinked albums? This cannot be undone.")) return;
        try {
            await api.bulkDeleteUnlinkedAlbums();
            this.ctx.performSearch?.(this.ctx.getState().currentQuery);
        } catch (err) {
            await showConfirm(`Bulk delete failed: ${err.message}`, { title: "Error", okLabel: "OK" });
        }
    }

    async handleDeletePublisher(actionTarget) {
        const publisherId = actionTarget.dataset.publisherId;
        if (!await showConfirm("Delete this publisher? This cannot be undone.")) return;
        try {
            await api.deletePublisher(publisherId);
            this.ctx.closeDetailPanel?.();
            this.ctx.performSearch?.(this.ctx.getState().currentQuery);
        } catch (err) {
            await showConfirm(`Delete failed: ${err.message}`, { title: "Error", okLabel: "OK" });
        }
    }

    async handleBulkDeleteUnlinkedPublishers() {
        if (!await showConfirm("Delete all unlinked publishers? This cannot be undone.")) return;
        try {
            await api.bulkDeleteUnlinkedPublishers();
            this.ctx.performSearch?.(this.ctx.getState().currentQuery);
        } catch (err) {
            await showConfirm(`Bulk delete failed: ${err.message}`, { title: "Error", okLabel: "OK" });
        }
    }

    async handleDeleteIdentity(actionTarget) {
        const identityId = actionTarget.dataset.identityId;
        if (!await showConfirm("Delete this identity? This cannot be undone.")) return;
        try {
            await api.deleteIdentity(identityId);
            this.ctx.closeDetailPanel?.();
            this.ctx.performSearch?.(this.ctx.getState().currentQuery);
        } catch (err) {
            await showConfirm(`Delete failed: ${err.message}`, { title: "Error", okLabel: "OK" });
        }
    }

    async handleBulkDeleteUnlinkedIdentities() {
        if (!await showConfirm("Delete all unlinked identities? This cannot be undone.")) return;
        try {
            await api.bulkDeleteUnlinkedIdentities();
            this.ctx.performSearch?.(this.ctx.getState().currentQuery);
        } catch (err) {
            await showConfirm(`Bulk delete failed: ${err.message}`, { title: "Error", okLabel: "OK" });
        }
    }
}
