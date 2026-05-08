import {
    getCatalogSong,
    searchTags,
    ABORTED,
    addSongTag,
    removeSongTag,
    searchArtists,
    addSongCredit,
    removeSongCredit,
    searchAlbums,
    addSongAlbum,
    removeSongAlbum,
    searchPublishers,
    addSongPublisher,
    removeSongPublisher,
    addAlbumPublisher,
    removeAlbumPublisher,
    addAlbumCredit,
    removeAlbumCredit,
    getArtistTree,
    updateCreditName,
    mergeIdentity,
    setIdentityType,
    addIdentityAlias,
    removeIdentityAlias,
    addIdentityMember,
    removeIdentityMember,
    getPublisherDetail,
    updatePublisher,
    mergePublisher,
    setPublisherParent,
    getTagDetail,
    updateTag,
    mergeTag,
    getTagCategories,
    syncAlbumFromSong,
} from "./api.js";
import { showConfirm } from "./components/confirm_modal.js";
import { openEditModal } from "./components/edit_modal.js";
import { openLinkModal } from "./components/link_modal.js";
import { openScrubberModal } from "./components/scrubber_modal.js";
import { parseTagInput } from "./utils/tag_input.js";

/**
 * GOSLING ORCHESTRATOR
 * Centered logic for all modal-based entity interactions.
 * This file replaces fragmented "managers" and keeps main.js lean.
 */

// ─── HELPERS ─────────────────────────────────────────────────────────────────

async function withMergeConfirm(updateFn, mergeFn, confirmMsg, confirmTitle, onMerged) {
    try {
        await updateFn();
    } catch (err) {
        if (err.detail?.code === "MERGE_REQUIRED") {
            const confirmed = await showConfirm(confirmMsg, { title: confirmTitle, okLabel: "Merge" });
            if (confirmed) {
                await mergeFn(err.detail.collision_id);
                if (onMerged) onMerged();
            }
        } else if (err.detail?.code === "UNSAFE_MERGE") {
            throw new Error(err.detail.message);
        } else {
            throw err;
        }
    }
}

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
                const detail = await getCatalogSong(id);
                tags = detail?.tags || [];
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
    const delimiter = rules.delimiter;
    const format = rules.input_format || "tag:category";
    openLinkModal({
        title: `Edit Tags: ${songTitle}`,
        placeholder: `Search or type (e.g. ${format})...`,
        items: currentTags.map((t) => ({ id: t.id, label: t.name })),
        onSearch: async (q) => {
            const { name: searchTerm, category: searchCategory } =
                parseTagInput(q, rules);
            const hasCategory = q.includes(delimiter);
            const results = await searchTags(searchTerm);
            if (results === ABORTED) return [];
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
            const rawTag = opt.id == null ? (opt.rawInput || opt.name || opt.label) : null;
            const { name: parsedName, category: parsedCategory } = rawTag
                ? parseTagInput(rawTag, rules)
                : { name: null, category: null };
            const result = await addSongTag(
                songId,
                opt.id == null ? parsedName : null,
                opt.id == null ? parsedCategory : null,
                opt.id ?? null,
            );
            const song = result?.songs?.[0];
            if (song) {
                const { name: parsedName } = parseTagInput(rawTag || opt.label, rules);
                const matched = song.tags.find(
                    (t) => t.name.toLowerCase() === parsedName.toLowerCase()
                );
                if (matched) {
                    opt.id = matched.id;
                    opt.label = matched.name;
                }
            }
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await removeSongTag(songId, item.id);
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
            const results = await searchArtists(q);
            if (results === ABORTED) return [];
            return (results || []).map((a) => ({
                id: a.id,
                label: a.resolved_name,
            }));
        },
        onAdd: async (opt) => {
            const credit = await addSongCredit(
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
            await removeSongCredit(songId, item.id);
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
            const results = await searchAlbums(q);
            if (results === ABORTED) return [];
            return (results || []).map((a) => ({ id: a.id, label: a.title }));
        },
        onAdd: async (opt) => {
            const isNew = !opt.id;
            const res = await addSongAlbum(
                songId,
                opt.id ?? null,
                opt.rawInput || opt.label,
                null,
                null,
            );
            if (isNew && res?.album_id) {
                try {
                    await syncAlbumFromSong(res.album_id, songId);
                } catch (err) {
                    console.warn("Auto-sync failed:", err);
                }
            }
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await removeSongAlbum(songId, item.id);
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
            const results = await searchPublishers(q);
            return (results || []).map((p) => ({ id: p.id, label: p.name }));
        },
        onAdd: async (opt) => {
            const publisher = await addSongPublisher(
                songId,
                opt.rawInput || opt.label,
                opt.id,
            );
            opt.id = publisher.id;
            opt.label = publisher.name;
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await removeSongPublisher(songId, item.id);
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
            const results = await searchPublishers(q);
            return (results || []).map((p) => ({ id: p.id, label: p.name }));
        },
        onAdd: async (opt) => {
            const publisher = await addAlbumPublisher(
                albumId,
                opt.rawInput || opt.label,
                opt.id ? Number(opt.id) : null,
            );
            opt.id = publisher.id;
            opt.label = publisher.name;
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await removeAlbumPublisher(albumId, item.id);
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
            const results = await searchArtists(q);
            if (results === ABORTED) return [];
            return (results || []).map((a) => ({
                id: a.id,
                label: a.resolved_name,
            }));
        },
        onAdd: async (opt) => {
            const credit = await addAlbumCredit(
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
            await removeAlbumCredit(albumId, item.id);
            await getUpdateCallback(ctx, songId)();
        },
        createLabel: (q) => `Add "${q}" as Performer`,
    });
}

// ─── ENTITY EDITING (EDIT MODAL) ─────────────────────────────────────────────

export async function manageArtist(ctx, artistId, artistName) {
    const identity = await getArtistTree(artistId);
    if (!identity) return;

    const aliases = identity.aliases || [];
    const primary = aliases.find((a) => a.is_primary) || {
        id: artistId,
        display_name: artistName,
    };
    const otherAliases = aliases.filter((a) => !a.is_primary);
    const members = identity.members || [];
    const groups = identity.groups || [];
    const isGroup = identity.type === "group";
    const hasMembers = members.length > 0;

    const fields = {
        name: {
            type: "text",
            label: "Name",
            value: primary.display_name,
            caseButton: true,
            onSave: async (val) => {
                await withMergeConfirm(
                    async () => {
                        await updateCreditName(primary.id, val);
                        if (ctx.refreshLayout) ctx.refreshLayout();
                    },
                    (collisionId) => mergeIdentity(primary.id, collisionId),
                    `"${val}" already exists. Merge into existing identity?`,
                    "Merge Identity",
                    () => { if (ctx.refreshLayout) ctx.refreshLayout(); },
                );
            },
        },
        type: {
            type: "toggle",
            label: "Type",
            value: identity.type,
            options: ["person", "group"],
            disabledReason: hasMembers ? "Remove all members before converting to person" : null,
            onSave: async (val) => {
                await setIdentityType(artistId, val);
                if (ctx.refreshLayout) ctx.refreshLayout();
            },
        },
        aliases: {
            type: "chipList",
            label: "Aliases",
            items: otherAliases.map((a) => ({ id: a.id, label: a.display_name })),
            createLabel: (q) => `Add "${q}" as new alias`,
            onSearch: async (q) => {
                const results = await searchArtists(q);
                return (results || []).map((a) => ({ id: a.id, label: a.resolved_name }));
            },
            onAdd: async (opt) => {
                const displayName = opt.rawInput || opt.label;
                await addIdentityAlias(artistId, displayName, opt.id);
                const fresh = await getArtistTree(artistId);
                const added = (fresh.aliases || []).find((a) => a.display_name === displayName);
                return added ? { id: added.id, label: added.display_name } : { id: opt.id, label: displayName };
            },
            onRemove: async (item) => {
                await removeIdentityAlias(artistId, item.id);
            },
            onRename: async (item, newName) => {
                await withMergeConfirm(
                    () => updateCreditName(item.id, newName),
                    (collisionId) => mergeIdentity(item.id, collisionId),
                    `"${newName}" already exists. Merge into existing identity?`,
                    "Merge Identity",
                    () => { if (ctx.refreshLayout) ctx.refreshLayout(); },
                );
            },
        },
    };

    if (!isGroup && groups.length > 0) {
        fields.groups = {
            type: "readOnlyList",
            label: "Member Of",
            items: groups.map((g) => ({ id: g.id, label: g.display_name })),
        };
    }

    if (isGroup) {
        fields.members = {
            type: "chipList",
            label: "Members",
            items: members.map((m) => ({ id: m.id, label: m.display_name })),
            onSearch: async (q) => {
                const results = await searchArtists(q, { excludeGroups: true });
                return (results || []).map((a) => ({ id: a.id, label: a.display_name || a.name }));
            },
            onAdd: async (opt) => {
                await addIdentityMember(artistId, opt.id);
                return { id: opt.id, label: opt.label };
            },
            onRemove: async (item) => {
                await removeIdentityMember(artistId, item.id);
            },
        };
    }

    openEditModal({
        title: `Edit Artist: ${primary.display_name}`,
        fields,
        onClose: () => {
            if (ctx.refreshActiveDetail) ctx.refreshActiveDetail();
        },
    });
}

export async function managePublisher(ctx, publisherId, publisherName) {
    const detail = await getPublisherDetail(publisherId).catch(() => null);
    const subPubs = detail?.sub_publishers || [];

    openEditModal({
        title: "Edit Publisher",
        fields: {
            name: {
                type: "text",
                label: "Name",
                value: detail ? detail.name : publisherName,
                caseButton: true,
                onSave: async (val) => {
                    await withMergeConfirm(
                        () => updatePublisher(publisherId, val),
                        (collisionId) => mergePublisher(publisherId, collisionId),
                        `"${val}" already exists. Merge into existing publisher?`,
                        "Merge Publisher",
                        () => { if (ctx.refreshActiveDetail) ctx.refreshActiveDetail(); },
                    );
                },
            },
            subPublishers: {
                type: "chipList",
                label: "Sub-publishers",
                items: subPubs.map((c) => ({ id: c.id, label: c.name })),
                onSearch: async (q) => {
                    const results = await searchPublishers(q);
                    return (results || []).map((p) => ({
                        id: p.id,
                        label: p.name,
                    }));
                },
                onAdd: async (opt) => {
                    await setPublisherParent(opt.id, Number(publisherId));
                },
                onRemove: async (item) => {
                    await setPublisherParent(item.id, null);
                },
                onRename: async (item, newName) => {
                    await withMergeConfirm(
                        () => updatePublisher(item.id, newName),
                        (collisionId) => mergePublisher(item.id, collisionId),
                        `"${newName}" already exists. Merge into existing publisher?`,
                        "Merge Publisher",
                        () => { if (ctx.refreshActiveDetail) ctx.refreshActiveDetail(); },
                    );
                },
                createLabel: (q) => `Add "${q}" as sub-publisher`,
            },
        },
        onClose: () => {
            if (ctx.refreshActiveDetail) ctx.refreshActiveDetail();
        },
    });
}

export async function manageTag(ctx, tagId) {
    const tagDetail = await getTagDetail(tagId).catch(() => null);
    if (!tagDetail) return;

    openEditModal({
        title: "Edit Tag",
        fields: {
            name: {
                type: "text",
                label: "Name",
                value: tagDetail.name,
                onSave: async (val) => {
                    await withMergeConfirm(
                        async () => {
                            await updateTag(tagId, val, tagDetail.category);
                            tagDetail.name = val;
                        },
                        (collisionId) => mergeTag(tagId, collisionId),
                        `"${val}" already exists in this category. Merge into existing tag?`,
                        "Merge Tag",
                        () => { if (ctx.refreshActiveDetail) ctx.refreshActiveDetail(); },
                    );
                },
            },
            category: {
                type: "search",
                label: "Category",
                value: tagDetail.category,
                editable: true,
                onSave: async (val) => {
                    await withMergeConfirm(
                        async () => {
                            await updateTag(tagId, tagDetail.name, val);
                            tagDetail.category = val;
                        },
                        (collisionId) => mergeTag(tagId, collisionId),
                        `"${tagDetail.name}" already exists in category "${val}". Merge into existing tag?`,
                        "Merge Tag",
                        () => { if (ctx.refreshActiveDetail) ctx.refreshActiveDetail(); },
                    );
                },
                onSearch: async (q) => {
                    const all = await getTagCategories();
                    return all.filter((c) =>
                        c.toLowerCase().includes(q.toLowerCase()),
                    );
                },
            },
        },
        onClose: () => {
            if (ctx.refreshActiveDetail) ctx.refreshActiveDetail();
        },
    });
}
