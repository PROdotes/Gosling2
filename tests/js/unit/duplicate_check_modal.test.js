import { JSDOM } from "jsdom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../../src/static/js/dashboard/api.js", () => ({
    findDuplicates: vi.fn(),
}));

describe("DuplicateCheckModal", () => {
    let modalModule;
    let apiModule;
    let overlay;
    let statusEl;
    let resultsEl;

    beforeEach(async () => {
        const dom = new JSDOM(`
            <div id="dup-check-modal" style="display:none">
                <div id="dup-check-status"></div>
                <div id="dup-check-results"></div>
            </div>
        `);
        global.document = dom.window.document;
        global.window = dom.window;

        vi.resetModules();
        apiModule = await import("../../../src/static/js/dashboard/api.js");
        modalModule = await import(
            "../../../src/static/js/dashboard/components/duplicate_check_modal.js"
        );

        overlay = document.getElementById("dup-check-modal");
        statusEl = document.getElementById("dup-check-status");
        resultsEl = document.getElementById("dup-check-results");
    });

    it("shows the overlay and a loading state on open", () => {
        apiModule.findDuplicates.mockReturnValue(new Promise(() => {}));
        modalModule.openDuplicateCheckModal({ songId: 1 });
        expect(overlay.style.display).toBe("flex");
        expect(statusEl.textContent).toMatch(/Scanning/i);
    });

    it("renders matches as readable cards, not raw JSON", async () => {
        apiModule.findDuplicates.mockResolvedValue({
            comparable: true,
            matches: [
                {
                    song_id: 2,
                    score: 0.98,
                    title: "Everlong",
                    artist: "Foo Fighters",
                    path: "Z:\\Songs\\Everlong.mp3",
                },
            ],
        });

        await modalModule.openDuplicateCheckModal({ songId: 1 });

        expect(resultsEl.textContent).toContain("Everlong");
        expect(resultsEl.textContent).toContain("Foo Fighters");
        expect(resultsEl.textContent).toContain("98%");
        expect(resultsEl.innerHTML).not.toContain('"song_id"');
    });

    it("shows a clear message when the song has no fingerprint yet", async () => {
        apiModule.findDuplicates.mockResolvedValue({
            comparable: false,
            matches: [],
        });

        await modalModule.openDuplicateCheckModal({ songId: 1 });

        expect(statusEl.textContent).toMatch(/no fingerprint/i);
        expect(resultsEl.innerHTML).toBe("");
    });

    it("shows a clear message when there are no matches", async () => {
        apiModule.findDuplicates.mockResolvedValue({
            comparable: true,
            matches: [],
        });

        await modalModule.openDuplicateCheckModal({ songId: 1 });

        expect(statusEl.textContent).toMatch(/no possible duplicates/i);
    });

    it("shows an error message when the request fails", async () => {
        apiModule.findDuplicates.mockRejectedValue(new Error("Song ID 1 not found"));

        await modalModule.openDuplicateCheckModal({ songId: 1 });

        expect(statusEl.textContent).toMatch(/duplicate check failed/i);
        expect(statusEl.textContent).toContain("Song ID 1 not found");
    });

    it("clears status and results on close", async () => {
        apiModule.findDuplicates.mockResolvedValue({
            comparable: true,
            matches: [],
        });
        await modalModule.openDuplicateCheckModal({ songId: 1 });

        modalModule.closeDuplicateCheckModal();

        expect(overlay.style.display).toBe("none");
        expect(statusEl.textContent).toBe("");
        expect(resultsEl.innerHTML).toBe("");
    });
});
