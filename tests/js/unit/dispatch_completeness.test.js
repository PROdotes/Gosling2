/**
 * Dispatch Completeness Test
 * Verifies every action in songActions has a corresponding handle* method.
 * No mocks. Pure structural check.
 */

import { test, expect } from 'vitest';
import { SongActionsHandler } from '../../../src/static/js/dashboard/handlers/song_actions.js';

test('every action in songActions has a handler method', () => {
    const handler = new SongActionsHandler({}, {});
    const missing = [];
    for (const action of handler.songActions) {
        const methodName = `handle${action.split("-").map(p => p.charAt(0).toUpperCase() + p.slice(1)).join("")}`;
        if (typeof handler[methodName] !== "function") {
            missing.push(`${action} → ${methodName}`);
        }
    }
    expect(missing, `Missing handler methods:\n${missing.join("\n")}`).toHaveLength(0);
});
