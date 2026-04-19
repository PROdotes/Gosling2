import { expect, test } from "vitest";
import { PROCESSING_STATUS } from "../../../src/static/js/dashboard/constants.js";

test("REVIEWED is 0", () => {
    expect(PROCESSING_STATUS.REVIEWED).toBe(0);
});

test("NEEDS_REVIEW is 1", () => {
    expect(PROCESSING_STATUS.NEEDS_REVIEW).toBe(1);
});

test("PENDING_ENRICHMENT is 2", () => {
    expect(PROCESSING_STATUS.PENDING_ENRICHMENT).toBe(2);
});

test("CONVERTING is 3", () => {
    expect(PROCESSING_STATUS.CONVERTING).toBe(3);
});

test("object is frozen", () => {
    expect(Object.isFrozen(PROCESSING_STATUS)).toBe(true);
});

test("has exactly 4 keys", () => {
    expect(Object.keys(PROCESSING_STATUS)).toHaveLength(4);
});
