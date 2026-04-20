import * as api from "./api.js";
import { showConfirm } from "./components/confirm_modal.js";
import { openEditModal } from "./components/edit_modal.js";
import { openLinkModal } from "./components/link_modal.js";
import { openScrubberModal } from "./components/scrubber_modal.js";
import { syncAlbumWithSong } from "./handlers/song_actions.js";
import { parseTagInput } from "./utils/tag_input.js";

/**
 * GOSLING ORCHESTRATOR
 * Centered logic for all modal-based entity interactions.
 * This file replaces fragmented "managers" and keeps main.js lean.
 */

// ─── PLAYER MANAGEMENT ───────────────────────────────────────────────────────

export async function orchestrateScrubber(ctx, songId, title) {
    const state = ctx.getState();
    const autoPlay = state.validationRules?.scrubber_auto_play ?? true;

    openScrubberModal(songId, title, {
        autoPlay,
        onClose: () => {
            const s = state;
            if (
                s.activeSong &&
                s.currentMode === "songs" &&
                ctx.refreshActiveSongV2
            ) {
                ctx.refreshActiveSongV2(s.activeSong.id);
            }
        },
        onTagsClick: async (id, name) => {
            // Re-fetch or use state.activeSong to get freshest tags
            // If the song being scrubbed is the active one, use its tags
            let tags = [];
            if (
                state.activeSong &&
                String(state.activeSong.id) === String(id)
            ) {
                tags = state.activeSong.tags || [];
            } else {
                // Otherwise fetch them
                const detail = await api.getSongDetail(id);
                tags = detail.tags || [];
            }
            manageSongTags(ctx, id, name, tags);
        },
    });
}

// ─── UTILITIES ───────────────────────────────────────────────────────────────

function getUpdateCallback(ctx, songId) {
    return async () => {
        const state = ctx.getState();
        if (state.currentMode === "songs" && ctx.refreshActiveSongV2) {
            await ctx.refreshActiveSongV2(songId);
        } else if (ctx.refreshActiveDetail) {
            ctx.refreshActiveDetail();
        }
    };
}

// ─── RELATIONSHIP MANAGEMENT (LINK MODAL) ────────────────────────────────────

export function manageSongTags(ctx, songId, songTitle, currentTags) {
    const state = ctx.getState();
    const rules = state.validationRules?.tags || {};
    const delimiter = rules.delimiter || ":";
    const format = rules.input_format || "tag:category";
    openLinkModal({
        title: `Edit Tags: ${songTitle}`,
        placeholder: `Search or type (e.g. ${format})...`,
        items: currentTags.map((t) => ({ id: t.id, label: t.name })),
        onSearch: async (q) => {
            const { name: searchTerm, category: searchCategory } =
                parseTagInput(q, rules);
            const hasCategory = q.includes(delimiter);
            const results = await api.searchTags(searchTerm);
            if (results === api.ABORTED) return [];
            const mapped = (results || []).map((t) => ({
                id: t.id,
                label: t.category ? `${t.name} (${t.category})` : t.name,
                name: t.name,
                category: t.category || null,
            }));
            if (hasCategory) {
                const catLower = searchCategory.toLowerCase();
                mapped.sort((a, b) => {
                    const aMatch =
                        (a.category || "").toLowerCase() === catLower;
                    const bMatch =
                        (b.category || "").toLowerCase() === catLower;
                    return aMatch === bMatch ? 0 : aMatch ? -1 : 1;
                });
            }
            return mapped;
        },
        onAdd: async (opt) => {
            let name, category;
            if (opt.id != null) {
                name = null;
                category = null;
            } else {
                const parsed = parseTagInput(
                    opt.rawInput || opt.name || opt.label,
                    rules,
                );
                name = parsed.name;
                category = parsed.category;
            }
            const tag = await api.addSongTag(
                songId,
                name,
                category,
                opt.id != null ? opt.id : null,
            );
            opt.id = tag.id;
            opt.label = tag.name;
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await api.removeSongTag(songId, item.id);
            await getUpdateCallback(ctx, songId)();
        },
        createLabel: (q) => {
            const { name, category } = parseTagInput(q, rules);
            if (!name) return `Add tag (missing name)`;
            return `Add "${name}" in "${category}"`;
        },
        shouldCreate: (q, results) => {
            const { name, category } = parseTagInput(q, rules);
            if (!name) return false;
            const nameLower = name.toLowerCase();
            const categoryLower = category.toLowerCase();
            return !results.some(
                (r) =>
                    r.name != null &&
                    r.name.toLowerCase() === nameLower &&
                    (r.category == null ||
                        r.category.toLowerCase() === categoryLower),
            );
        },
    });
}

export function manageSongCredits(ctx, songId, role, currentCredits) {
    if (!role) throw new Error("manageSongCredits requires a role");

    openLinkModal({
        title: `Link ${role}`,
        placeholder: `Search for artist name...`,
        items: currentCredits.map((c) => ({
            id: c.credit_id,
            label: c.display_name,
        })),
        onSearch: async (q) => {
            const results = await api.searchArtists(q);
            if (results === api.ABORTED) return [];
            return (results || []).map((a) => ({
                id: a.id,
                label: a.display_name || a.legal_name || a.name,
            }));
        },
        onAdd: async (opt) => {
            const credit = await api.addSongCredit(
                songId,
                opt.rawInput || opt.label,
                role,
                opt.id,
            );
            opt.id = credit.credit_id;
            opt.label = credit.display_name;
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await api.removeSongCredit(songId, item.id);
            await getUpdateCallback(ctx, songId)();
        },
        createLabel: (q) => `Add "${q}" as ${role}`,
    });
}

export function manageSongAlbums(ctx, songId, songTitle, currentAlbums) {
    openLinkModal({
        title: `Link Album: ${songTitle}`,
        placeholder: "Search for album...",
        items: currentAlbums,
        onSearch: async (q) => {
            const results = await api.searchAlbums(q);
            if (results === api.ABORTED) return [];
            return (results || []).map((a) => ({ id: a.id, label: a.title }));
        },
        onAdd: async (opt) => {
            const isNew = !opt.id;
            const res = await api.addSongAlbum(
                songId,
                opt.id ?? null,
                opt.rawInput || opt.label,
                null,
                null,
            );
            if (isNew && res?.album_id) {
                try {
                    await syncAlbumWithSong(res.album_id, songId);
                } catch (err) {
                    console.warn("Auto-sync failed:", err);
                }
            }
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await api.removeSongAlbum(songId, item.id);
            await getUpdateCallback(ctx, songId)();
        },
        createLabel: (q) => `Add "${q}" as new album`,
    });
}

export function manageSongPublishers(ctx, songId, currentPublishers) {
    openLinkModal({
        title: "Song Publishers",
        items: currentPublishers,
        onSearch: async (q) => {
            const results = await api.searchPublishers(q);
            return (results || []).map((p) => ({ id: p.id, label: p.name }));
        },
        onAdd: async (opt) => {
            const publisher = await api.addSongPublisher(
                songId,
                opt.rawInput || opt.label,
                opt.id,
            );
            opt.id = publisher.id;
            opt.label = publisher.name;
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await api.removeSongPublisher(songId, item.id);
            await getUpdateCallback(ctx, songId)();
        },
        createLabel: (q) => `Add "${q}" as new publisher`,
    });
}

// ─── ALBUM RELATIONSHIP MANAGERS ─────────────────────────────────────────────

export function manageAlbumPublishers(ctx, albumId, songId, currentChips) {
    openLinkModal({
        title: "Album Publishers",
        items: currentChips,
        onSearch: async (q) => {
            const results = await api.searchPublishers(q);
            return (results || []).map((p) => ({ id: p.id, label: p.name }));
        },
        onAdd: async (opt) => {
            const publisher = await api.addAlbumPublisher(
                albumId,
                opt.rawInput || opt.label,
                opt.id ? Number(opt.id) : null,
            );
            opt.id = publisher.id;
            opt.label = publisher.name;
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await api.removeAlbumPublisher(albumId, item.id);
            await getUpdateCallback(ctx, songId)();
        },
        createLabel: (q) => `Add "${q}" as album publisher`,
    });
}

export function manageAlbumCredits(ctx, albumId, songId, currentChips) {
    openLinkModal({
        title: "Album Credits",
        placeholder: "Search for artist name...",
        items: currentChips,
        onSearch: async (q) => {
            const results = await api.searchArtists(q);
            if (results === api.ABORTED) return [];
            return (results || []).map((a) => ({
                id: a.id,
                label: a.display_name || a.legal_name || a.name,
            }));
        },
        onAdd: async (opt) => {
            const credit = await api.addAlbumCredit(
                albumId,
                opt.rawInput || opt.label,
                "Performer",
                opt.id,
            );
            opt.id = credit.name_id;
            opt.label = credit.display_name;
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await api.removeAlbumCredit(albumId, item.id);
            await getUpdateCallback(ctx, songId)();
        },
        createLabel: (q) => `Add "${q}" as Performer`,
    });
}

// ─── ENTITY EDITING (EDIT MODAL) ─────────────────────────────────────────────

export async function manageArtist(ctx, artistId, artistName) {
    const identity = await api.getArtistTree(artistId);
    if (!identity) return;

    const aliases = identity.aliases || [];
    const primary = aliases.find((a) => a.is_primary) || {
        id: artistId,
        display_name: artistName,
    };
    const otherAliases = aliases.filter((a) => !a.is_primary);
    const members = identity.members || [];
    const isGroup = identity.type === "group";
    const hasMembers = members.length > 0;

    openEditModal({
        title: `Edit Artist: ${primary.display_name}`,
        name: primary.display_name,
        toggle: {
            value: identity.type,
            options: ["person", "group"],
            disabledReason: hasMembers
                ? "Remove all members before converting to person"
                : null,
            onSave: async (newType) => {
                await api.setIdentityType(artistId, newType);
                if (ctx.refreshLayout) ctx.refreshLayout();
            },
        },
        onRename: async (newName) => {
            try {
                await api.updateCreditName(0, primary.id, newName);
                if (ctx.refreshLayout) ctx.refreshLayout();
            } catch (err) {
                if (err.detail?.code === "MERGE_REQUIRED") {
                    const { collision_name_id, source_identity_id: _sid } =
                        err.detail;
                    const confirmed = await showConfirm(
                        `"${newName}" already exists. Merge into existing identity?`,
                        { title: "Merge Identity", okLabel: "Merge" },
                    );
                    if (confirmed) {
                        await api.mergeIdentity(primary.id, collision_name_id);
                        if (ctx.refreshLayout) ctx.refreshLayout();
                    }
                } else if (err.detail?.code === "UNSAFE_MERGE") {
                    throw new Error(err.detail.message);
                } else {
                    throw err;
                }
            }
        },
        category: null,
        children: {
            label: "Aliases",
            items: otherAliases.map((a) => ({
                id: a.id,
                label: a.display_name,
            })),
            onSearch: async (q) => {
                const results = await api.searchArtists(q);
                return (results || []).map((a) => ({
                    id: a.id,
                    label: a.display_name || a.name,
                }));
            },
            onAdd: async (opt) => {
                const result = await api.addIdentityAlias(
                    artistId,
                    opt.rawInput || opt.label,
                    opt.id,
                );
                return { id: result.name_id, label: result.display_name };
            },
            onRemove: async (item) => {
                await api.removeIdentityAlias(artistId, item.id);
            },
            onRenameChild: async (item, newName) => {
                try {
                    await api.updateCreditName(0, item.id, newName);
                } catch (err) {
                    if (err.detail?.code === "MERGE_REQUIRED") {
                        const { collision_name_id } = err.detail;
                        const confirmed = await showConfirm(
                            `"${newName}" already exists. Merge into existing identity?`,
                            { title: "Merge Identity", okLabel: "Merge" },
                        );
                        if (confirmed) {
                            await api.mergeIdentity(item.id, collision_name_id);
                            if (ctx.refreshLayout) ctx.refreshLayout();
                        }
                    } else if (err.detail?.code === "UNSAFE_MERGE") {
                        throw new Error(err.detail.message);
                    } else {
                        throw err;
                    }
                }
            },
        },
        secondChildren: isGroup
            ? {
                  label: "Members",
                  items: members.map((m) => ({
                      id: m.id,
                      label: m.display_name,
                  })),
                  onSearch: async (q) => {
                      const results = await api.searchArtists(q);
                      return (results || [])
                          .filter((a) => a.type !== "group")
                          .map((a) => ({
                              id: a.id,
                              label: a.display_name || a.name,
                          }));
                  },
                  onAdd: async (opt) => {
                      await api.addIdentityMember(artistId, opt.id);
                      return { id: opt.id, label: opt.label };
                  },
                  onRemove: async (item) => {
                      await api.removeIdentityMember(artistId, item.id);
                  },
              }
            : null,
        onClose: () => {
            if (ctx.refreshActiveDetail) ctx.refreshActiveDetail();
        },
    });
}

export async function managePublisher(ctx, publisherId, publisherName) {
    const detail = await api.getPublisherDetail(publisherId).catch(() => null);
    const subPubs = detail?.sub_publishers || [];

    openEditModal({
        title: "Edit Publisher",
        name: detail ? detail.name : publisherName,
        onRename: async (newName) => {
            await api.updatePublisher(publisherId, newName);
        },
        category: null,
        children: {
            label: "Sub-publishers",
            items: subPubs.map((c) => ({ id: c.id, label: c.name })),
            onSearch: async (q) => {
                const results = await api.searchPublishers(q);
                return (results || []).map((p) => ({
                    id: p.id,
                    label: p.name,
                }));
            },
            onAdd: async (opt) => {
                await api.setPublisherParent(opt.id, Number(publisherId));
            },
            onRemove: async (item) => {
                await api.setPublisherParent(item.id, null);
            },
            onRenameChild: async (item, newName) => {
                await api.updatePublisher(item.id, newName);
            },
            createLabel: (q) => `Add "${q}" as sub-publisher`,
        },
        onClose: () => {
            if (ctx.refreshActiveDetail) ctx.refreshActiveDetail();
        },
    });
}

export async function manageTag(ctx, tagId) {
    const tagDetail = await api.getTagDetail(tagId).catch(() => null);
    if (!tagDetail) return;

    openEditModal({
        title: "Edit Tag",
        name: tagDetail.name,
        onRename: async (newName) => {
            await api.updateTag(tagId, newName, tagDetail.category);
            tagDetail.name = newName;
        },
        category: {
            label: "Category",
            value: tagDetail.category,
            editable: true,
            onSave: async (val) => {
                await api.updateTag(tagId, tagDetail.name, val);
                tagDetail.category = val;
            },
            onSearch: async (q) => {
                const all = await api.getTagCategories();
                return all.filter((c) =>
                    c.toLowerCase().includes(q.toLowerCase()),
                );
            },
        },
        children: null,
        onClose: () => {
            if (ctx.refreshActiveDetail) ctx.refreshActiveDetail();
        },
    });
}
