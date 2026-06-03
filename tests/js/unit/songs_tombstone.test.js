/**
 * Songs list tombstone + sweep tests (feature shipped 2026-06-03).
 * Pure logic / DOM tests via jsdom — no mocks, no network.
 *
 * Covers:
 *   - patchSongRow refreshes a row's blocker pills without a full re-fetch
 *   - status-filter membership: an edit that leaves the filter tombstones the
 *     row (+ one-shot flash); re-entering the filter clears the tombstone
 *   - flushTombstones (on mouseleave) never sweeps the selected row
 *
 * The status predicates under test mirror song_repository.filter_slim SQL — this
 * suite is the guard against that hand-copy drifting.
 */

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { PROCESSING_STATUS } from "../../../src/static/js/dashboard/constants.js";
import {
    patchSongRow,
    renderSongs,
    setActiveStatusFilters,
} from "../../../src/static/js/dashboard/renderers/songs.js";

let state;
const ctx = {
    getState: () => state,
    setState: (patch) => Object.assign(state, patch),
    updateResultsSummary: () => {},
};

function makeSong(overrides = {}) {
    return {
        id: 1,
        display_title: "Song",
        display_artist: "Artist",
        formatted_duration: "3:00",
        review_blockers: [],
        processing_status: PROCESSING_STATUS.NEEDS_REVIEW,
        media_name: "Song",
        title: "Song",
        year: 2020,
        ...overrides,
    };
}

function rowEl(id) {
    return document.querySelector(`.song-row[data-id="${id}"]`);
}

beforeEach(() => {
    document.body.innerHTML = '<div id="song-list-panel"></div>';
    state = { displayedItems: [], selectedIndex: -1 };
    setActiveStatusFilters([], "ALL"); // reset module-level filter context
});

describe("patchSongRow — live row refresh", () => {
    test("re-renders blocker pills from the fresh song", () => {
        setActiveStatusFilters([], "ALL"); // no status filter => no tombstoning
        const song = makeSong({
            review_blockers: [{ name: "composers", pill: "CMP" }],
        });
        renderSongs(ctx, [song]);
        expect(rowEl(1).querySelectorAll(".pill.miss")).toHaveLength(1);

        // Edit cleared the composer blocker — patch with empty blockers.
        patchSongRow(ctx, makeSong({ review_blockers: [] }));
        expect(rowEl(1).querySelectorAll(".pill.miss")).toHaveLength(0);
    });

    test("returns false when the song isn't in the list", () => {
        renderSongs(ctx, [makeSong({ id: 1 })]);
        expect(patchSongRow(ctx, makeSong({ id: 999 }))).toBe(false);
    });
});

describe("status-filter membership / tombstone", () => {
    test("marking reviewed under Not Done tombstones + flashes the row", () => {
        setActiveStatusFilters(["not_done"], "ALL");
        renderSongs(ctx, [
            makeSong({ processing_status: PROCESSING_STATUS.NEEDS_REVIEW }),
        ]);
        expect(rowEl(1).classList.contains("tombstoned")).toBe(false);

        patchSongRow(
            ctx,
            makeSong({ processing_status: PROCESSING_STATUS.REVIEWED }),
        );
        const row = rowEl(1);
        expect(row.classList.contains("tombstoned")).toBe(true);
        expect(row.classList.contains("flash-done")).toBe(true);
    });

    test("re-entering the filter (un-review) clears the tombstone", () => {
        setActiveStatusFilters(["not_done"], "ALL");
        renderSongs(ctx, [makeSong()]);
        patchSongRow(
            ctx,
            makeSong({ processing_status: PROCESSING_STATUS.REVIEWED }),
        );
        expect(rowEl(1).classList.contains("tombstoned")).toBe(true);

        patchSongRow(
            ctx,
            makeSong({ processing_status: PROCESSING_STATUS.NEEDS_REVIEW }),
        );
        expect(rowEl(1).classList.contains("tombstoned")).toBe(false);
    });

    test("filling the last blocker leaves the Missing Data bucket", () => {
        setActiveStatusFilters(["missing_data"], "ALL");
        renderSongs(ctx, [
            makeSong({ review_blockers: [{ name: "year", pill: "YR" }] }),
        ]);
        patchSongRow(ctx, makeSong({ review_blockers: [] }));
        expect(rowEl(1).classList.contains("tombstoned")).toBe(true);
    });

    test("no status filter => marking reviewed does not tombstone", () => {
        setActiveStatusFilters([], "ALL");
        renderSongs(ctx, [makeSong()]);
        patchSongRow(
            ctx,
            makeSong({ processing_status: PROCESSING_STATUS.REVIEWED }),
        );
        expect(rowEl(1).classList.contains("tombstoned")).toBe(false);
    });
});

describe("flushTombstones — sweep on mouseleave", () => {
    afterEach(() => vi.useRealTimers());

    test("sweeps unselected tombstones but never the selected row", () => {
        vi.useFakeTimers();
        setActiveStatusFilters(["not_done"], "ALL");
        const s1 = makeSong({ id: 1 });
        const s2 = makeSong({ id: 2 });
        renderSongs(ctx, [s1, s2]);
        // Select row 1 (the song the user is working on).
        state.selectedIndex = 0;

        // Both get marked reviewed -> both tombstoned.
        patchSongRow(
            ctx,
            makeSong({ id: 1, processing_status: PROCESSING_STATUS.REVIEWED }),
        );
        patchSongRow(
            ctx,
            makeSong({ id: 2, processing_status: PROCESSING_STATUS.REVIEWED }),
        );
        expect(rowEl(1).classList.contains("tombstoned")).toBe(true);
        expect(rowEl(2).classList.contains("tombstoned")).toBe(true);

        // Pointer leaves the list -> flush. Selected row (1) must survive.
        document
            .getElementById("song-list-panel")
            .dispatchEvent(new Event("mouseleave"));
        vi.advanceTimersByTime(400); // past the 320ms collapse

        expect(rowEl(2)).toBeNull(); // unselected tombstone swept
        expect(rowEl(1)).not.toBeNull(); // selected row exempt, stays
        expect(rowEl(1).classList.contains("tombstoned")).toBe(true);
        expect(state.displayedItems.map((s) => s.id)).toEqual([1]);
    });

    test("flush keeps the selected row's tombstone if it is the only one", () => {
        vi.useFakeTimers();
        setActiveStatusFilters(["not_done"], "ALL");
        renderSongs(ctx, [makeSong({ id: 1 })]);
        state.selectedIndex = 0;
        patchSongRow(
            ctx,
            makeSong({ id: 1, processing_status: PROCESSING_STATUS.REVIEWED }),
        );

        document
            .getElementById("song-list-panel")
            .dispatchEvent(new Event("mouseleave"));
        vi.advanceTimersByTime(400);

        expect(rowEl(1)).not.toBeNull();
        expect(state.displayedItems.map((s) => s.id)).toEqual([1]);
    });
});
