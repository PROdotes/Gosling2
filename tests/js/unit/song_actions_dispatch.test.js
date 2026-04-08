/**
 * SongActionsHandler.handle() — pure dispatch routing tests.
 * No mocks. Tests only the routing logic of handle(), not what handlers do.
 *
 * These tests use real jsdom DOM to exercise isModalOpen().
 */

import { describe, test, expect, beforeEach } from 'vitest';
import { SongActionsHandler } from '../../../src/static/js/dashboard/handlers/song_actions.js';

function makeHandler() {
    // ctx and _window are never called in these routing tests
    return new SongActionsHandler({}, {});
}

function makeBtn(action) {
    const btn = document.createElement('button');
    btn.dataset.action = action;
    document.body.appendChild(btn);
    return btn;
}

function makeEvent(target) {
    return { target, preventDefault: () => {}, stopPropagation: () => {} };
}

beforeEach(() => {
    document.body.innerHTML = '';
});

describe('handle() routing', () => {
    test('returns false when target has no [data-action]', async () => {
        const handler = makeHandler();
        const div = document.createElement('div');
        document.body.appendChild(div);
        const result = await handler.handle(makeEvent(div));
        expect(result).toBe(false);
    });

    test('returns false for a global action not in songActions', async () => {
        const handler = makeHandler();
        const btn = makeBtn('switch-mode');
        const result = await handler.handle(makeEvent(btn));
        expect(result).toBe(false);
    });

    test('returns false when a modal is open and action is not a close-* action', async () => {
        const handler = makeHandler();

        // Put a visible modal in the DOM
        const modal = document.createElement('div');
        modal.id = 'edit-modal';
        modal.style.display = 'flex';
        document.body.appendChild(modal);

        const btn = makeBtn('delete-song');
        const result = await handler.handle(makeEvent(btn));
        expect(result).toBe(false);
    });

    test('returns true for a close-* action even when a modal is open', async () => {
        const handler = makeHandler();

        const modal = document.createElement('div');
        modal.id = 'edit-modal';
        modal.style.display = 'flex';
        document.body.appendChild(modal);

        // close-edit-modal is in songActions and starts with "close-"
        const btn = makeBtn('close-edit-modal');
        const result = await handler.handle(makeEvent(btn));
        expect(result).toBe(true);
    });

    test('returns true for a recognised song action when no modal is open', async () => {
        const handler = makeHandler();
        // Stub out the actual handler so it doesn't do real work
        handler.handleDeleteSong = async () => {};

        const btn = makeBtn('delete-song');
        btn.dataset.id = '1';
        btn.classList.add('confirming'); // skip the first-click branch
        // classList.contains / classList.remove are real — jsdom handles them

        const result = await handler.handle(makeEvent(btn));
        expect(result).toBe(true);
    });
});

describe('handle() two-step delete — first click (no API)', () => {
    test('first click adds confirming class and changes text, does not call any API', async () => {
        const handler = makeHandler();

        const btn = document.createElement('button');
        btn.dataset.action = 'delete-song';
        btn.dataset.id = '42';
        btn.textContent = 'Delete';
        document.body.appendChild(btn);

        await handler.handle(makeEvent(btn));

        expect(btn.classList.contains('confirming')).toBe(true);
        expect(btn.textContent).toBe('Confirm Delete?');
        // No API was called — nothing to assert on, but handler must not throw
    });
});

describe('handle() toggle-active disabled guard (no API)', () => {
    test('does nothing when button has disabled class', async () => {
        const handler = makeHandler();

        const btn = document.createElement('button');
        btn.dataset.action = 'toggle-active';
        btn.classList.add('disabled');
        document.body.appendChild(btn);

        // If the guard works, no exception is thrown and we get true back
        // (handle() returns true once it dispatches, regardless of handler early-exit)
        const result = await handler.handle(makeEvent(btn));
        expect(result).toBe(true);
    });
});
