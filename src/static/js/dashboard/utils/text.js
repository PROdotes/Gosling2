// Mirrors json/transliterations.json + src/utils/text.py::normalize_for_search.
// Keep in sync if the JSON map changes.
const TRANSLITERATIONS = {
    "Đ": "Dj", "đ": "dj", "Ć": "C", "ć": "c", "Č": "C", "č": "c",
    "Š": "S", "š": "s", "Ž": "Z", "ž": "z", "ß": "ss",
    "Æ": "Ae", "æ": "ae", "Œ": "Oe", "œ": "oe",
};

export function normalizeForSearch(text) {
    let out = String(text);
    for (const [ch, repl] of Object.entries(TRANSLITERATIONS)) {
        if (out.includes(ch)) out = out.split(ch).join(repl);
    }
    return out.normalize("NFKD").replace(/[\u0300-\u036F]/g, "").toLowerCase();
}