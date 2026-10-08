/**
 * Deleted-song view reason controls. The selected state comes from the
 * backend's is_rejected / reject_reason (DeletedSongView), never from parsing
 * notes here. jsdom, no mocks.
 */

import { beforeEach, describe, expect, test } from "vitest";
import { renderDeletedSongView } from "../../../src/static/js/dashboard/renderers/song_editor.js";

function mountPanel() {
    document.body.innerHTML = `
<div id="editor-panel">
  <div class="editor-scroll"></div>
  <div class="action-sidebar"></div>
</div>`;
}

function makeDeleted(overrides = {}) {
    return {
        id: 7,
        media_name: "Song",
        source_path: null,
        year: null,
        bpm: null,
        isrc: null,
        is_rejected: false,
        reject_reason: null,
        estimated_original_path: null,
        original_exists: false,
        ...overrides,
    };
}

const clearBtn = () =>
    document.querySelector('[data-action="clear-reject-reason"]');
const reasonBtn = (reason) =>
    document.querySelector(
        `[data-action="change-reject-reason"][data-reason="${reason}"]`,
    );

describe("renderDeletedSongView reason controls", () => {
    beforeEach(mountPanel);

    test("plain delete: Not rejected is selected, no reason is", () => {
        renderDeletedSongView(makeDeleted());
        expect(clearBtn().classList.contains("active")).toBe(true);
        expect(clearBtn().disabled).toBe(true);
        expect(document.querySelectorAll(".reason-toggle-group .active")).toHaveLength(0);
    });

    test("rejected with a reason: that reason is selected, Not rejected is clickable", () => {
        renderDeletedSongView(
            makeDeleted({ is_rejected: true, reject_reason: "DUPLICATE" }),
        );
        expect(reasonBtn("DUPLICATE").classList.contains("active")).toBe(true);
        expect(reasonBtn("DUPLICATE").disabled).toBe(true);
        expect(clearBtn().classList.contains("active")).toBe(false);
        expect(clearBtn().disabled).toBe(false);
    });

    test("legacy bare REJECTED: no reason selected but still clearable", () => {
        renderDeletedSongView(
            makeDeleted({ is_rejected: true, reject_reason: null }),
        );
        expect(document.querySelectorAll(".reason-toggle-group .active")).toHaveLength(0);
        expect(clearBtn().classList.contains("active")).toBe(false);
        expect(clearBtn().disabled).toBe(false);
    });

    test("row carries the song id for the stale-render guard", () => {
        renderDeletedSongView(makeDeleted({ id: 42 }));
        expect(document.querySelector('[data-deleted-song-id="42"]')).not.toBeNull();
    });
});
