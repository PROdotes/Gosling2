export const ABORTED = Symbol("ABORTED");

const searchControllers = new Map();

function isAbortError(error) {
    return error && error.name === "AbortError";
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        let errorMsg = `Request failed: ${response.status}`;
        let errorDetail = null;
        try {
            const errorData = await response.json();
            if (errorData && errorData.detail) {
                errorDetail = errorData.detail;
                errorMsg =
                    typeof errorDetail === "string"
                        ? errorDetail
                        : `Request failed: ${response.status}`;
            }
        } catch (e) {
            // No JSON body
        }
        const err = new Error(errorMsg);
        err.detail = errorDetail;
        throw err;
    }
    return response.json();
}


export async function fetchValidationRules() {
    return fetchJson("/api/v1/validation-rules");
}

export async function fetchAppConfig() {
    return fetchJson("/api/v1/config");
}

async function runSearch(key, url) {
    const previous = searchControllers.get(key);
    if (previous) {
        previous.abort();
    }

    const controller = new AbortController();
    searchControllers.set(key, controller);

    try {
        return await fetchJson(url, { signal: controller.signal });
    } catch (error) {
        if (isAbortError(error)) {
            return ABORTED;
        }
        throw error;
    } finally {
        if (searchControllers.get(key) === controller) {
            searchControllers.delete(key);
        }
    }
}

export function abortAllSearches() {
    for (const controller of searchControllers.values()) {
        controller.abort();
    }
    searchControllers.clear();
}

export { isAbortError };

export function searchSongs(query = "", deep = false) {
    let url = "/api/v1/songs/search";
    if (query) {
        url = `/api/v1/songs/search?q=${encodeURIComponent(query)}`;
        if (deep) {
            url += "&deep=true";
        }
    }
    return runSearch("songs", url);
}

export function searchAlbums(query = "") {
    const url = query
        ? `/api/v1/albums/search?q=${encodeURIComponent(query)}`
        : "/api/v1/albums";
    return runSearch("albums", url);
}

export function searchArtists(query = "", { excludeGroups = false } = {}) {
    let url;
    if (query) {
        url = `/api/v1/identities/search?q=${encodeURIComponent(query)}`;
        if (excludeGroups) url += "&exclude_groups=true";
    } else {
        url = "/api/v1/identities";
    }
    return runSearch("artists", url);
}

export function searchPublishers(query = "") {
    const url = query
        ? `/api/v1/publishers/search?q=${encodeURIComponent(query)}`
        : "/api/v1/publishers";
    return runSearch("publishers", url);
}

export function getCatalogSong(id, options = {}) {
    return fetchJson(`/api/v1/songs/${id}`, options);
}

export function getSongWebSearch(id, engine = null) {
    let url = `/api/v1/songs/${id}/web-search`;
    if (engine) {
        url += `?engine=${encodeURIComponent(engine)}`;
    }
    return fetchJson(url);
}

export async function getSongDetail(id, options = {}) {
    const response = await fetch(
        `/api/v1/metabolic/inspect-file/${id}`,
        options,
    );
    if (response.ok) {
        return response.json();
    }
    if (response.status === 404 || response.status === 500) {
        return null;
    }
    throw new Error(`Request failed: ${response.status}`);
}

export function getAlbumDetail(id, options = {}) {
    return fetchJson(`/api/v1/albums/${id}`, options);
}

export function getArtistTree(id, options = {}) {
    return fetchJson(`/api/v1/identities/${id}`, options);
}

export function getArtistSongs(id, options = {}) {
    return fetchJson(`/api/v1/identities/${id}/songs`, options);
}

export function addIdentityAlias(identityId, displayName, nameId = null) {
    return mutate({ add: [{ type: "identity_alias", identity_id: identityId, display_name: displayName, name_id: nameId }] });
}

export function removeIdentityAlias(identityId, nameId) {
    return mutate({ remove: [{ type: "identity_alias", identity_id: identityId, name_id: nameId }] });
}

export function setIdentityType(identityId, identityType) {
    return mutate({ update: [{ type: "identity", id: identityId, identity_type: identityType }] });
}

export function addIdentityMember(groupId, memberId) {
    return mutate({ add: [{ type: "identity_member", group_id: groupId, member_id: memberId }] });
}

export function removeIdentityMember(groupId, memberId) {
    return mutate({ remove: [{ type: "identity_member", group_id: groupId, member_id: memberId }] });
}

export function getPublisherDetail(id, options = {}) {
    return fetchJson(`/api/v1/publishers/${id}`, options);
}

export function getPublisherSongs(id, options = {}) {
    return fetchJson(`/api/v1/publishers/${id}/songs`, options);
}


export function checkIngestion(filePath) {
    return fetchJson("/api/v1/catalog/ingest/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: filePath }),
    });
}

export async function getDownloadsFolder() {
    const result = await fetchJson("/api/v1/ingest/downloads-folder");
    return result.path;
}

export async function getAcceptedFormats() {
    const result = await fetchJson("/api/v1/ingest/formats");
    return result.extensions;
}

export function uploadFiles(files) {
    const formData = new FormData();
    const fileArray = Array.isArray(files) ? files : [files];
    for (const file of fileArray) {
        formData.append("files", file);
    }
    return fetch("/api/v1/ingest/upload", { method: "POST", body: formData });
}

export function getIngestStatus() {
    return fetchJson("/api/v1/ingest/status");
}

export function resetIngestStatus() {
    return mutate({ update: [{ type: "ingest_status", reset: true }] });
}

export function resolveConflict(ghostId, stagedPath) {
    return fetchJson(`/api/v1/ingest/resolve-conflict?ghost_id=${ghostId}&staged_path=${encodeURIComponent(stagedPath)}`, { method: "POST" });
}

/**
 * Reads a streaming NDJSON response line-by-line, calling onUpdate for each parsed object.
 * Handles chunked delivery and partial-line buffering.
 */
export async function readNdjsonStream(response, onUpdate) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
            if (!line.trim()) continue;
            try {
                onUpdate(JSON.parse(line));
            } catch (e) {
                console.error("NDJSON parse error:", line, e);
            }
        }
    }
}

export function scanFolder(folderPath, recursive = true, inPlace = false) {
    return fetch("/api/v1/ingest/scan-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder_path: folderPath, recursive, in_place: inPlace }),
    });
}

export function addSongPublisher(songId, publisherName, publisherId = null) {
    return mutate({ add: [{ type: "publisher", song_id: songId, name: publisherName, id: publisherId }] });
}

export function removeSongPublisher(songId, publisherId) {
    return mutate({ remove: [{ type: "publisher", song_id: songId, id: publisherId }] });
}

export function fetchRoles() {
    return fetchJson("/api/v1/roles");
}

export function addSongCredit(songId, displayName, roleName, identityId = null) {
    return mutate({ add: [{ type: "credit", song_id: songId, name: displayName, id: identityId, role: roleName }] });
}

export function removeSongCredit(songId, creditId) {
    return mutate({ remove: [{ type: "credit", song_id: songId, id: creditId }] });
}

export function updateCreditName(nameId, displayName) {
    return mutate({ update: [{ type: "credit", id: nameId, display_name: displayName }] });
}

export function patchSongScalars(songId, fields) {
    return mutate({ update: [{ type: "song", id: songId, ...fields }] });
}

export function mutate(command) {
    return fetchJson("/api/v1/mutate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(command),
    });
}

export function formatText(text, type) {
    return fetchJson("/api/v1/tools/format-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, type }),
    });
}

export function deleteSong(id, deleteFile = false) {
    return mutate({ delete: [{ type: "song", id: Number(id), delete_file: deleteFile }] });
}

export function rejectSong(id) {
    return mutate({
        update: [{ type: "song", id: Number(id), notes: "REJECTED" }],
        delete: [{ type: "song", id: Number(id) }],
    });
}

export function moveSongToLibrary(id) {
    return mutate({ update: [{ type: "song", id: Number(id), move_to_library: true }] });
}

export function mergeIdentity(sourceNameId, targetNameId) {
    return mutate({ update: [{ type: "identity", source_name_id: sourceNameId, target_name_id: targetNameId, merge: true }] });
}

export function syncSongId3(id) {
    return fetchJson(`/api/v1/songs/${id}/sync-id3`);
}

export function getSongSyncStatus(id) {
    return fetchJson(`/api/v1/songs/${id}/sync-status`);
}

export function setPublisherParent(publisherId, parentId) {
    return mutate({ update: [{ type: "publisher", id: publisherId, parent_id: parentId }] });
}

export function updatePublisher(publisherId, name) {
    return mutate({ update: [{ type: "publisher", id: publisherId, name }] });
}

export function searchTags(query = "") {
    const url = query
        ? `/api/v1/tags/search?q=${encodeURIComponent(query)}`
        : "/api/v1/tags";
    return runSearch("tags", url);
}

export function getTagDetail(id, options = {}) {
    return fetchJson(`/api/v1/tags/${id}`, options);
}

export function getTagSongs(id, options = {}) {
    return fetchJson(`/api/v1/tags/${id}/songs`, options);
}

export function getTagCategories() {
    return fetchJson("/api/v1/tags/categories");
}

export function updateTag(tagId, name, category) {
    return mutate({ update: [{ type: "tag", id: tagId, name, category }] });
}

export function deleteTag(tagId) {
    return mutate({ delete: [{ type: "tag", id: tagId }] });
}

export function bulkDeleteUnlinkedTags() {
    return mutate({ delete: [{ type: "tag", unlinked: true }] });
}

export function deleteAlbum(albumId) {
    return mutate({ delete: [{ type: "album", id: albumId }] });
}

export function bulkDeleteUnlinkedAlbums() {
    return mutate({ delete: [{ type: "album", unlinked: true }] });
}

export function deletePublisher(publisherId) {
    return mutate({ delete: [{ type: "publisher", id: publisherId }] });
}

export function bulkDeleteUnlinkedPublishers() {
    return mutate({ delete: [{ type: "publisher", unlinked: true }] });
}

export function deleteIdentity(identityId) {
    return mutate({ delete: [{ type: "identity", id: identityId }] });
}

export function bulkDeleteUnlinkedIdentities() {
    return mutate({ delete: [{ type: "identity", unlinked: true }] });
}

export function addSongTag(songId, tagName, category, tagId = null, rawTag = null) {
    return mutate({ add: [{ type: "tag", song_id: songId, name: tagName, category, id: tagId, raw_tag: rawTag }] });
}

export function removeSongTag(songId, tagId) {
    return mutate({ remove: [{ type: "tag", song_id: songId, id: tagId }] });
}

export function setPrimarySongTag(songId, tagId) {
    return mutate({ update: [{ type: "song_tag", song_id: songId, tag_id: tagId, is_primary: true }] });
}

export function addSongAlbum(songId, albumId, title, trackNumber, discNumber) {
    return mutate({ add: [{ type: "album", song_id: songId, id: albumId, name: title, track_number: trackNumber, disc_number: discNumber }] });
}

export function removeSongAlbum(songId, albumId) {
    return mutate({ remove: [{ type: "album", song_id: songId, id: albumId }] });
}

export function updateSongAlbumLink(songId, albumId, trackNumber, discNumber) {
    return mutate({ update: [{ type: "song_album", song_id: songId, album_id: albumId, track_number: trackNumber, disc_number: discNumber }] });
}

export async function syncAlbumFromSong(albumId, songId) {
    const payload = await fetchJson(`/api/v1/albums/${albumId}/sync-from-song/${songId}`);
    if (!payload.add && !payload.update) return {};
    return mutate(payload);
}

export async function quickCreateAlbum(songId, title = null) {
    const payload = await fetchJson("/api/v1/albums/prepare-from-song", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ song_id: songId, title }),
    });
    if (!payload.add && !payload.update) return {};
    const result = await mutate(payload);
    const song = result?.songs?.[0];
    const albumTitle = title || song?.media_name;
    const newAlbum = song?.albums?.find(a => a.album_title === albumTitle);
    if (newAlbum?.album_id) {
        await syncAlbumFromSong(newAlbum.album_id, songId);
    }
    return result;
}

export function updateAlbum(albumId, fields) {
    return mutate({ update: [{ type: "album", id: albumId, ...fields }] });
}

export function addAlbumCredit(albumId, displayName, roleName = "Performer", identityId = null) {
    return mutate({ add: [{ type: "credit", album_id: albumId, name: displayName, role: roleName, id: identityId }] });
}

export function removeAlbumCredit(albumId, nameId) {
    return mutate({ remove: [{ type: "credit", album_id: albumId, id: nameId }] });
}

export function addAlbumPublisher(albumId, publisherName, publisherId = null) {
    return mutate({ add: [{ type: "publisher", album_id: albumId, name: publisherName, id: publisherId }] });
}

export function removeAlbumPublisher(albumId, publisherId) {
    return mutate({ remove: [{ type: "publisher", album_id: albumId, id: publisherId }] });
}

export async function fetchId3Frames() {
    const resp = await fetch("/api/v1/metabolic/id3-frames");
    if (!resp.ok) throw new Error("Failed to fetch ID3 frame mapping");
    return await resp.json();
}

export function parseSpotifyCredits(rawText, referenceTitle) {
    return fetchJson("/api/v1/spotify/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            raw_text: rawText,
            reference_title: referenceTitle,
        }),
    });
}

export function importSpotifyCredits(songId, credits, publishers) {
    const add = [
        ...credits.map(c => ({ type: "credit", song_id: songId, name: c.name, id: c.id ?? null, role: c.role })),
        ...publishers.map(p => ({ type: "publisher", song_id: songId, name: p, id: null })),
    ];
    return mutate({ add });
}

export function splitterTokenize(text, separators) {
    return fetchJson("/api/v1/tools/splitter/tokenize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, separators }),
    });
}

export function splitterPreview(names, target) {
    return fetchJson("/api/v1/tools/splitter/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ names, target }),
    });
}

export async function splitterConfirm(songId, tokens, target, classification, remove) {
    const payload = await fetchJson("/api/v1/tools/splitter/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ song_id: songId, tokens, target, classification, remove }),
    });
    return mutate(payload);
}

export function previewFilenameParsing(filenames, pattern) {
    return fetchJson("/api/v1/tools/filename-parser/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filenames, pattern }),
    });
}

export function applyFilenameParsing(items, pattern) {
    return fetchJson("/api/v1/tools/filename-parser/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items, pattern }),
    });
}

export function cleanupOriginalFile(filePath = null, songId = null) {
    return mutate({ remove: [{ type: "original_file", file_path: filePath, song_id: songId }] });
}

export function getPendingConvert() {
    return fetchJson("/api/v1/ingest/pending-convert");
}

export function getStagingOrphans() {
    return fetchJson("/api/v1/ingest/staging-orphans");
}

export function deleteStagingOrphan(filePath) {
    return fetchJson(
        `/api/v1/ingest/staging-orphans?path=${encodeURIComponent(filePath)}`,
        { method: "DELETE" },
    );
}

export function getFilterValues() {
    return fetchJson("/api/v1/songs/filter-values");
}

export function filterSongs(filters, mode = "ALL", liveOnly = false) {
    const params = new URLSearchParams();
    params.set("mode", mode);
    if (liveOnly) params.set("live_only", "true");
    for (const [key, values] of Object.entries(filters)) {
        for (const v of values) {
            params.append(key, v);
        }
    }
    return runSearch("songs", `/api/v1/songs/filter?${params.toString()}`);
}
