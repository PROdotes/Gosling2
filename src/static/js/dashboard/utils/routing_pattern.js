import { escapeHtml } from "../components/utils.js";

const ROUTING_TOKEN_LABELS = {
    artist: "Artist",
    title: "Title",
    year: "Year",
    genre: "Genre",
};

/**
 * Splits a routing pattern into literal text and {token} pieces, rendering
 * each token as a styled chip (distinct color/font from literal path text)
 * with a hover title spelling out what it means -- literal segments come
 * from rules.json (arbitrary text) and are escaped; token labels come only
 * from the fixed lookup table above. See feedback_placeholder_vs_literal_display:
 * humanizing the token name as plain text alone is not enough, it still
 * reads as a literal value rather than a placeholder.
 */
export function renderRoutingPatternHtml(pattern) {
    return pattern
        .split(/(\{\w+\})/g)
        .map((part) => {
            const match = /^\{(\w+)\}$/.exec(part);
            if (!match) return escapeHtml(part);
            const label = ROUTING_TOKEN_LABELS[match[1]] ?? match[1];
            return `<span class="routing-token" title="Replaced with this song's ${escapeHtml(label)}">${escapeHtml(label)}</span>`;
        })
        .join("");
}
