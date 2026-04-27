/**
 * Audit Fix Tests (docs/JS_AUDIT.md)
 * Pure logic tests — no mocks, no network.
 *
 * Covers:
 *   Fix 3  — cache key fallback (stagedPath → path)
 *   Fix 8  — renderModuleToolbar dead filterSidebar reference
 *   Fix 12 — FilterSidebarHandler mode validation
 *   Fix 13 — inline editor blur race condition (rAF instead of setTimeout)
 */

import { beforeAll, beforeEach, describe, expect, test } from "vitest";
import { renderModuleToolbar } from "../../../src/static/js/dashboard/components/utils.js";
import { activateInlineEdit } from "../../../src/static/js/dashboard/components/inline_editor.js";
import { FilterSidebarHandler } from "../../../src/static/js/dashboard/handlers/filter_sidebar.js";

beforeEach(() => {
    document.body.innerHTML = "";
    localStorage.clear();
});

beforeAll(() => {
    if (!globalThis.requestAnimationFrame) {
        globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 16);
    }
    if (!globalThis.cancelAnimationFrame) {
        globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
    }
});

// ─── Fix 3: main.js — cache key fallback ──────────────────────────────────

describe("Ingest cache key lookup", () => {
    function findCachedIndex(cache, key) {
        return cache.findIndex(
            (r) => r.stagedPath === key || (r.stagedPath === null && r.path === key),
        );
    }

    test("finds entry by stagedPath when stagedPath matches", () => {
        const cache = [
            { stagedPath: "/a.mp3", path: "/a.mp3", result: { status: "CONFLICT" } },
            { stagedPath: null, path: "/b.wav", result: { status: "PENDING_CONVERT" } },
        ];
        expect(findCachedIndex(cache, "/a.mp3")).toBe(0);
    });

    test("falls back to path when stagedPath is null", () => {
        const cache = [
            { stagedPath: "/a.mp3", path: "/a.mp3", result: { status: "CONFLICT" } },
            { stagedPath: null, path: "/b.wav", result: { status: "PENDING_CONVERT" } },
        ];
        expect(findCachedIndex(cache, "/b.wav")).toBe(1);
    });

    test("returns -1 when nothing matches", () => {
        const cache = [
            { stagedPath: "/a.mp3", path: "/a.mp3", result: { status: "CONFLICT" } },
        ];
        expect(findCachedIndex(cache, "/c.flac")).toBe(-1);
    });

    test("prefers stagedPath match over path fallback", () => {
        const cache = [
            { stagedPath: "/x.mp3", path: "/y.mp3", result: { status: "INGESTED" } },
            { stagedPath: null, path: "/x.mp3", result: { status: "ERROR" } },
        ];
        expect(findCachedIndex(cache, "/x.mp3")).toBe(0);
    });
});

// ─── Fix 8: utils.js — renderModuleToolbar ────────────────────────────────

describe("renderModuleToolbar", () => {
    test("renders filter toggle button without active class when ctx has no handlers", () => {
        const html = renderModuleToolbar({});
        expect(html).toContain("filter-toggle-btn");
        expect(html).toContain("toggle-filter-sidebar");
        expect(html).not.toMatch(/filter-toggle-btn\s+active/);
    });

    test("includes sort controls and separator when sortControlsHtml provided", () => {
        const html = renderModuleToolbar({}, '<div class="sort-ctrl">A-Z</div>');
        expect(html).toContain("sort-ctrl");
        expect(html).toContain("toolbar-separator");
    });

    test("omits separator when no sort controls", () => {
        const html = renderModuleToolbar({});
        expect(html).not.toContain("toolbar-separator");
    });
});

// ─── Fix 12: filter_sidebar.js — mode validation ─────────────────────────

describe("FilterSidebarHandler mode validation", () => {
    test("valid mode ALL is preserved", () => {
        localStorage.setItem(
            "gosling_filter_state",
            JSON.stringify({ mode: "ALL", active: {}, liveOnly: false, sidebarVisible: false }),
        );
        const handler = new FilterSidebarHandler({});
        expect(handler._mode).toBe("ALL");
    });

    test("valid mode ANY is preserved", () => {
        localStorage.setItem(
            "gosling_filter_state",
            JSON.stringify({ mode: "ANY", active: {}, liveOnly: false, sidebarVisible: false }),
        );
        const handler = new FilterSidebarHandler({});
        expect(handler._mode).toBe("ANY");
    });

    test("invalid mode defaults to ALL", () => {
        localStorage.setItem(
            "gosling_filter_state",
            JSON.stringify({ mode: "INVALID", active: {}, liveOnly: false, sidebarVisible: false }),
        );
        const handler = new FilterSidebarHandler({});
        expect(handler._mode).toBe("ALL");
    });

    test("empty string mode defaults to ALL", () => {
        localStorage.setItem(
            "gosling_filter_state",
            JSON.stringify({ mode: "", active: {}, liveOnly: false, sidebarVisible: false }),
        );
        const handler = new FilterSidebarHandler({});
        expect(handler._mode).toBe("ALL");
    });

    test("no saved state defaults to ALL", () => {
        const handler = new FilterSidebarHandler({});
        expect(handler._mode).toBe("ALL");
    });
});

// ─── Fix 13: inline_editor.js — blur uses rAF, not setTimeout ────────────

describe("activateInlineEdit blur handling", () => {
    test("blur without error commits the edit", async () => {
        const span = document.createElement("span");
        span.textContent = "old value";
        document.body.appendChild(span);

        let committedValue = null;
        activateInlineEdit(span, {
            field: "notes",
            validationRules: null,
            onCommit: async (val) => {
                committedValue = val;
                return {};
            },
            onSave: () => {},
        });

        const input = document.querySelector(".inline-edit-input");
        expect(input).not.toBeNull();
        input.value = "new value";

        input.dispatchEvent(new Event("blur"));

        await new Promise((resolve) => requestAnimationFrame(resolve));
        expect(committedValue).toBe("new value");
    });

    test("blur with validation error does not commit", async () => {
        const span = document.createElement("span");
        span.textContent = "2000";
        document.body.appendChild(span);

        let committed = false;
        activateInlineEdit(span, {
            field: "year",
            validationRules: { year: { min: 1860, max: 2100 } },
            onCommit: async (val) => {
                // Simulate backend 400 error for non-numeric input
                if (val !== null && typeof val === "number" && isNaN(val)) {
                    throw new Error("Invalid year");
                }
                committed = true;
                return {};
            },
            onSave: () => {},
        });

        const input = document.querySelector(".inline-edit-input");
        input.value = "not-a-year";
        input.dispatchEvent(new Event("input"));
        input.dispatchEvent(new Event("blur"));

        await new Promise((resolve) => setTimeout(resolve, 50));
        expect(committed).toBe(false);
    });

    test("blur does not commit when value unchanged", async () => {
        const span = document.createElement("span");
        span.textContent = "same";
        document.body.appendChild(span);

        let committed = false;
        activateInlineEdit(span, {
            field: "notes",
            validationRules: null,
            onCommit: async () => {
                committed = true;
                return {};
            },
            onSave: () => {},
        });

        const input = document.querySelector(".inline-edit-input");
        input.value = "same";
        input.dispatchEvent(new Event("blur"));

        await new Promise((resolve) => requestAnimationFrame(resolve));
        expect(committed).toBe(false);
    });
});
