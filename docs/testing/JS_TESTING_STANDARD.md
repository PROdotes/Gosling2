# JS Testing Standard

**Same rule as Python: tests are reviewed and approved before any implementation is written.**

---

## Philosophy

**No mocks.** If you mock the thing you're testing, you're not testing it.

- No `vi.mock()` on API modules — if the API is called, the call must reach a real endpoint or a real in-memory handler
- No `vi.fn()` substituting real DOM elements — use `jsdom` or a real browser
- Exception: `window.open`, `window.location` — these are environment boundaries, not app logic

The JS test suite has two layers only:

| Layer | Tool | What it tests |
|-------|------|---------------|
| Unit | Vitest + jsdom | Pure logic with no network: dispatch tables, string transforms, validation rules |
| Integration | Playwright | Real browser, real server, real DB — clicking buttons and asserting outcomes |

If a test requires mocking a module to pass, that is a sign the code needs to be restructured, not that the mock is acceptable.

---

## Vitest (Unit) — What Belongs Here

Only pure logic that has **no network, no server, no real DOM interaction**:

- The dispatch table: every action in `songActions` set maps to a real handler method
- String formatters, case converters, validation functions
- Sort logic: given input array, assert output order

### Dispatch Completeness Test (mandatory — catches Gemini-style regressions)

Every action in `SongActionsHandler.songActions` must have a corresponding `handle<ActionName>` method. This test must exist and must run on every PR.

```js
import { SongActionsHandler } from '../../src/static/js/dashboard/handlers/song_actions.js';

test('every action in songActions set has a handler method', () => {
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
```

This test requires **no mocks** and would have caught every broken action from today's refactor.

---

## Playwright (Integration) — What Belongs Here

Everything that touches the UI, the network, or the database. This is the primary test layer.

### Setup

- Start a real server against a **test database** (copy of `gosling2.db` with known fixture data)
- Run tests against `http://127.0.0.1:8001` (separate port from dev)
- Reset DB to fixture state before each test (or use transactions that roll back)

### What to test

- Clicking a button produces a visible DOM change
- Submitting a form writes to the database (assert via API read-back, not DOM)
- Error states: API failure shows a banner, not silence
- Modal open → interact → close → state is correct

### Example shape

```js
test('adding a tag to a song appears in the detail panel', async ({ page }) => {
    await page.goto('/');
    await page.fill('#searchInput', 'Tko sam ja');
    await page.click('.song-card');
    await page.click('[data-action="open-link-modal"][data-modal-type="tags"]');
    await page.fill('#link-modal-input', 'Cro');
    await page.click('.link-dropdown-item');
    await expect(page.locator('.tag-chip', { hasText: 'Cro' })).toBeVisible();
});
```

### Rules

- Assert the **outcome**, not the implementation path
- Never assert `console.log` output
- One scenario per test
- If a test is flaky, fix the app — do not add `waitForTimeout`

---

## What Does NOT Get Tested

- That `api.deleteSong` was called with the right arguments — test that the song is gone from the DB
- That a mock function was invoked — test that the UI reflects the change
- Internal state of `ctx` or `state` objects — test what the user sees

---

## File Placement

```
tests/
  js/
    unit/
      dispatch_completeness.test.js   ← always exists, no mocks
      sort_logic.test.js
      validation.test.js
    integration/
      song_actions.spec.js            ← Playwright
      album_management.spec.js
      ingest_flow.spec.js
```

---

## Checklist Before Submitting Tests for Review

- [ ] No `vi.mock()` on app modules (API, handlers, orchestrator)
- [ ] Dispatch completeness test exists and passes
- [ ] Integration tests assert DB or DOM outcomes, not internal calls
- [ ] One scenario per test
- [ ] No `waitForTimeout` in Playwright tests
- [ ] Test database is isolated from dev database
