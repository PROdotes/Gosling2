import { JSDOM } from "jsdom";
import { beforeEach, describe, expect, it } from "vitest";

// Pure-logic unit test for renderRoutingPatternHtml (utils/routing_pattern.js)
// -- the helper behind the "Routes to" line in the Edit Tag modal's genre
// routing preview. Verifies literal path segments render as plain escaped
// text while {token}s render as distinct styled chips, per
// feedback_placeholder_vs_literal_display.
let mod;

function freshContainer() {
    const dom = new JSDOM("<div id='c'></div>");
    global.document = dom.window.document;
    global.window = dom.window;
    return dom.window.document.getElementById("c");
}

beforeEach(async () => {
    freshContainer();
    mod = await import(
        "../../../src/static/js/dashboard/utils/routing_pattern.js"
    );
});

describe("renderRoutingPatternHtml", () => {
    it("wraps each {token} in a routing-token span with a humanized label", () => {
        const c = document.getElementById("c");
        c.innerHTML = mod.renderRoutingPatternHtml("{genre}/{artist} - {title}");
        const spans = [...c.querySelectorAll(".routing-token")].map(
            (el) => el.textContent,
        );
        expect(spans).toEqual(["Genre", "Artist", "Title"]);
    });

    it("keeps literal path segments as plain text outside any span", () => {
        const c = document.getElementById("c");
        c.innerHTML = mod.renderRoutingPatternHtml("latin/{artist} - {title}");
        expect(c.querySelectorAll(".routing-token")).toHaveLength(2);
        expect(c.textContent).toBe("latin/Artist - Title");
        expect(c.firstChild.nodeType).toBe(3); // literal "latin/" is a bare text node, not a span
    });

    it("adds a hover title spelling out the substitution", () => {
        const c = document.getElementById("c");
        c.innerHTML = mod.renderRoutingPatternHtml("{year}");
        const span = c.querySelector(".routing-token");
        expect(span.title).toBe("Replaced with this song's Year");
    });

    it("falls back to the raw token name for an unknown token", () => {
        const c = document.getElementById("c");
        c.innerHTML = mod.renderRoutingPatternHtml("{bogus}/{artist}");
        const spans = [...c.querySelectorAll(".routing-token")].map(
            (el) => el.textContent,
        );
        expect(spans).toEqual(["bogus", "Artist"]);
    });

    it("escapes literal text that contains HTML-significant characters", () => {
        const c = document.getElementById("c");
        const html = mod.renderRoutingPatternHtml('a<b>&"/{artist}');
        expect(html).not.toContain("<b>");
        c.innerHTML = html;
        expect(c.textContent.startsWith('a<b>&"')).toBe(true);
    });
});
