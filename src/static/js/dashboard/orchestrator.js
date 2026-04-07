import * as api from "./api.js";
import { openScrubberModal } from "./components/scrubber_modal.js";
import { openLinkModal } from "./components/link_modal.js";
import { openEditModal } from "./components/edit_modal.js";

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
        onTagsClick: async (id, name) => {
            // Re-fetch or use state.activeSong to get freshest tags
            // If the song being scrubbed is the active one, use its tags
            let tags = [];
            if (state.activeSong && String(state.activeSong.id) === String(id)) {
                tags = state.activeSong.tags || [];
            } else {
                // Otherwise fetch them
                const detail = await api.getSongDetail(id);
                tags = detail.tags || [];
            }
            manageSongTags(ctx, id, name, tags);
        }
    });
}

// ─── UTILITIES ───────────────────────────────────────────────────────────────

function getUpdateCallback(ctx, songId) {
    return async () => {
        const state = ctx.getState();
        const song = state.cachedSongs.find(s => String(s.id) === String(songId));
        if (song && ctx.openSongDetail) {
            ctx.openSongDetail(song, { reuseFileData: true });
        }
    };
}

// ─── RELATIONSHIP MANAGEMENT (LINK MODAL) ────────────────────────────────────

export function manageSongTags(ctx, songId, songTitle, currentTags) {
    const state = ctx.getState();
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
        title: `Edit Tags: ${songTitle}`,
        placeholder: `Search or type (e.g. ${format})...`,
        items: currentTags.map(t => ({ id: t.id, label: t.name })),
        onSearch: async (q) => {
            const results = await api.searchTags(q);
            if (results === api.ABORTED) return [];
            return (results || []).map(t => ({ 
                id: t.id, 
                label: t.category ? `${t.name} (${t.category})` : t.name, 
                name: t.name 
            }));
        },
        onAdd: async (opt) => {
            let name, category;
            if (opt.id != null) {
                name = null; category = null;
            } else {
                const parsed = parseTagInput(opt.rawInput || opt.name || opt.label);
                name = parsed.name; category = parsed.category;
            }
            const tag = await api.addSongTag(songId, name, category, opt.id != null ? opt.id : null);
            opt.id = tag.id;
            opt.label = tag.name;
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await api.removeSongTag(songId, item.id);
            await getUpdateCallback(ctx, songId)();
        },
        createLabel: (q) => {
            const { name, category } = parseTagInput(q);
            if (!name) return `Add tag (missing name)`;
            return `Add "${name}" in "${category}"`;
        },
    });
}

export function manageSongCredits(ctx, songId, role, currentCredits) {
    if (!role) throw new Error("manageSongCredits requires a role");

    openLinkModal({
        title: `Link ${role}`,
        placeholder: `Search for artist name...`,
        items: currentCredits.map(c => ({ id: c.credit_id, label: c.display_name })),
        onSearch: async (q) => {
            const results = await api.searchArtists(q);
            if (results === api.ABORTED) return [];
            return (results || []).map(a => ({ id: a.id, label: a.display_name || a.legal_name || a.name }));
        },
        onAdd: async (opt) => {
            const credit = await api.addSongCredit(songId, opt.rawInput || opt.label, role, opt.id);
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
            return (results || []).map(a => ({ id: a.id, label: a.title }));
        },
        onAdd: async (opt) => {
            const isNew = !opt.id;
            const res = await api.addSongAlbum(songId, opt.id ?? null, opt.rawInput || opt.label, null, null);
            if (isNew && res && res.album_id) {
                try { await api.syncAlbumWithSong(res.album_id, songId); }
                catch (err) { console.warn("Auto-sync failed:", err); }
            }
            await getUpdateCallback(ctx, songId)();
        },
        onRemove: async (item) => {
            await api.removeSongAlbum(songId, item.id);
            await getUpdateCallback(ctx, songId)();
        },
        createLabel: (q) => `Add "${q}" as new album`,
        quickAdd: songTitle ? { label: `New album: "${songTitle}"`, rawInput: songTitle } : null,
    });
}

export function manageSongPublishers(ctx, songId, currentPublishers) {
    openLinkModal({
        title: "Song Publishers",
        items: currentPublishers,
        onSearch: async (q) => {
            const results = await api.searchPublishers(q);
            return (results || []).map(p => ({ id: p.id, label: p.name }));
        },
        onAdd: async (opt) => {
            const publisher = await api.addSongPublisher(songId, opt.rawInput || opt.label, opt.id);
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
            return (results || []).map(p => ({ id: p.id, label: p.name }));
        },
        onAdd: async (opt) => {
            const publisher = await api.addAlbumPublisher(albumId, opt.rawInput || opt.label, opt.id ? Number(opt.id) : null);
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
            return (results || []).map(a => ({ id: a.id, label: a.display_name || a.legal_name || a.name }));
        },
        onAdd: async (opt) => {
            const credit = await api.addAlbumCredit(albumId, opt.rawInput || opt.label, "Performer", opt.id);
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

// ─── SCALAR EDITS (EDIT MODAL) ───────────────────────────────────────────────

export async function editArtist(ctx, artistId, artistName) {
    const tree = await api.getArtistTree(artistId);

    openEditModal({
        title: `Edit Artist: ${artistName}`,
        name: artistName,
        onRename: async (newName) => {
            await api.patchIdentityName(artistId, newName);
            if (ctx.refreshLayout) ctx.refreshLayout();
        },
        category: null,
        children: {
            label: "Aliases & Identities",
            items: tree.map(identity => ({ id: identity.id, label: identity.name })),
            onSearch: async (q) => {
                const results = await api.searchArtists(q);
                return (results || []).map(a => ({ id: a.id, label: a.display_name || a.legal_name || a.name }));
            },
            onAdd: async (opt) => {
                await api.addIdentityAlias(artistId, opt.id);
            },
            onRemove: async (item) => {
                await api.removeIdentityAlias(artistId, item.id);
            }
        },
        onClose: () => {
            if (ctx.refreshLayout) ctx.refreshLayout();
        }
    });
}
