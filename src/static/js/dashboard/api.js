export const ABORTED = Symbol("ABORTED");

const searchControllers = new Map();

function isAbortError(error) {
    return error && error.name === "AbortError";
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        let errorMsg = `Request failed: ${response.status}`;
        try {
            const errorData = await response.json();
            if (errorData && errorData.detail) {
                errorMsg = errorData.detail;
            }
        } catch (e) {
            // No JSON body
        }
        throw new Error(errorMsg);
    }
    return response.json();
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

export function searchSongs(query = "") {
    const url = query
        ? `/api/v1/songs/search?q=${encodeURIComponent(query)}`
        : "/api/v1/songs/search";
    return runSearch("songs", url);
}

export function searchAlbums(query = "") {
    const url = query
        ? `/api/v1/albums/search?q=${encodeURIComponent(query)}`
        : "/api/v1/albums";
    return runSearch("albums", url);
}

export function searchArtists(query = "") {
    const url = query
        ? `/api/v1/identities/search?q=${encodeURIComponent(query)}`
        : "/api/v1/identities";
    return runSearch("artists", url);
}

export function searchPublishers(query = "") {
    const url = query
        ? `/api/v1/publishers/search?q=${encodeURIComponent(query)}`
        : "/api/v1/publishers";
    return runSearch("publishers", url);
}

export async function getSongDetail(id, options = {}) {
    const response = await fetch(`/api/v1/metabolic/inspect-file/${id}`, options);
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

export function getPublisherDetail(id, options = {}) {
    return fetchJson(`/api/v1/publishers/${id}`, options);
}

export function getPublisherSongs(id, options = {}) {
    return fetchJson(`/api/v1/publishers/${id}/songs`, options);
}

export function getAuditHistory(table, id, options = {}) {
    return fetchJson(`/api/v1/audit/history/${table}/${id}`, options);
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
