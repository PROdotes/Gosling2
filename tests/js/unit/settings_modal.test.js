import { JSDOM } from "jsdom";
import { beforeEach, describe, expect, it } from "vitest";

// Pure-logic unit tests for the Settings modal. No API mocks: renderSettingsForm,
// collectPatch, and renderWarnings are DOM-only with no network. The fetch ->
// save -> close round-trip is the Playwright layer (not installed in-repo).
let mod;

const FULL_SETTINGS = {
    library_root: "\\\\onair\\b\\Songs",
    wav_auto_convert: true,
    auto_move_on_approve: false,
    prompt_before_move: true,
    auto_save_id3: false,
    scrubber_auto_play: true,
    blur_saves_scalars: false,
    default_search_engine: "spotify",
};

const BOOL_KEYS = [
    "wav_auto_convert",
    "auto_move_on_approve",
    "prompt_before_move",
    "auto_save_id3",
    "scrubber_auto_play",
    "blur_saves_scalars",
];

// JSON Schema as emitted by Settings.model_json_schema(): typed properties in
// field order, the enum field as a $ref into $defs, labels in `title`.
const SCHEMA = {
    type: "object",
    title: "Settings",
    $defs: {
        SearchEngine: {
            type: "string",
            title: "SearchEngine",
            enum: ["spotify", "youtube", "musicbrainz"],
        },
    },
    properties: {
        library_root: { type: "string", title: "Library root", minLength: 1 },
        wav_auto_convert: { type: "boolean", title: "Auto-convert WAV to MP3 on ingest" },
        auto_move_on_approve: { type: "boolean", title: "Auto-move file to library on approve" },
        prompt_before_move: { type: "boolean", title: "Prompt before moving files" },
        auto_save_id3: { type: "boolean", title: "Auto-save ID3 tags on edit" },
        scrubber_auto_play: { type: "boolean", title: "Auto-play in the scrubber" },
        blur_saves_scalars: { type: "boolean", title: "Save scalar fields on blur" },
        default_search_engine: { $ref: "#/$defs/SearchEngine", title: "Default search engine" },
    },
};

function freshContainer() {
    const dom = new JSDOM("<div id='c'></div>");
    global.document = dom.window.document;
    global.window = dom.window;
    return dom.window.document.getElementById("c");
}

beforeEach(async () => {
    const c = freshContainer();
    mod = await import(
        "../../../src/static/js/dashboard/components/settings_modal.js"
    );
    return c;
});

describe("renderSettingsForm", () => {
    it("renders a checkbox per boolean key with checked state matching settings", () => {
        const c = document.getElementById("c");
        mod.renderSettingsForm(c, FULL_SETTINGS, SCHEMA);
        for (const key of BOOL_KEYS) {
            const box = c.querySelector(`input[type=checkbox][data-key="${key}"]`);
            expect(box, `missing checkbox for ${key}`).not.toBeNull();
            expect(box.checked, `checked mismatch for ${key}`).toBe(
                FULL_SETTINGS[key],
            );
        }
    });

    it("renders library_root as a text input carrying the path value", () => {
        const c = document.getElementById("c");
        mod.renderSettingsForm(c, FULL_SETTINGS, SCHEMA);
        const input = c.querySelector('input[type=text][data-key="library_root"]');
        expect(input).not.toBeNull();
        expect(input.value).toBe(FULL_SETTINGS.library_root);
    });

    it("renders default_search_engine as a select with one option per engine, current selected", () => {
        const c = document.getElementById("c");
        mod.renderSettingsForm(c, FULL_SETTINGS, SCHEMA);
        const select = c.querySelector('select[data-key="default_search_engine"]');
        expect(select).not.toBeNull();
        const optionValues = [...select.querySelectorAll("option")].map(
            (o) => o.value,
        );
        const engineOptions = SCHEMA.$defs.SearchEngine.enum;
        expect(optionValues.sort()).toEqual([...engineOptions].sort());
        expect(select.value).toBe("spotify");
    });

    it("renders an unchecked box for a false boolean", () => {
        const c = document.getElementById("c");
        mod.renderSettingsForm(c, FULL_SETTINGS, SCHEMA);
        const box = c.querySelector(
            'input[type=checkbox][data-key="auto_save_id3"]',
        );
        expect(box.checked).toBe(false);
    });
});

describe("collectPatch (changed-only)", () => {
    it("returns an empty object when nothing changed", () => {
        const c = document.getElementById("c");
        mod.renderSettingsForm(c, FULL_SETTINGS, SCHEMA);
        expect(mod.collectPatch(c, FULL_SETTINGS)).toEqual({});
    });

    it("includes only a flipped toggle, as a boolean", () => {
        const c = document.getElementById("c");
        mod.renderSettingsForm(c, FULL_SETTINGS, SCHEMA);
        const box = c.querySelector(
            'input[type=checkbox][data-key="auto_save_id3"]',
        );
        box.checked = true; // was false
        const patch = mod.collectPatch(c, FULL_SETTINGS);
        expect(patch).toEqual({ auto_save_id3: true });
        expect(typeof patch.auto_save_id3).toBe("boolean");
    });

    it("includes an edited library_root as a string", () => {
        const c = document.getElementById("c");
        mod.renderSettingsForm(c, FULL_SETTINGS, SCHEMA);
        const input = c.querySelector('input[type=text][data-key="library_root"]');
        input.value = "D:\\Music";
        expect(mod.collectPatch(c, FULL_SETTINGS)).toEqual({
            library_root: "D:\\Music",
        });
    });

    it("includes a changed search engine as a string", () => {
        const c = document.getElementById("c");
        mod.renderSettingsForm(c, FULL_SETTINGS, SCHEMA);
        const select = c.querySelector('select[data-key="default_search_engine"]');
        select.value = "youtube";
        expect(mod.collectPatch(c, FULL_SETTINGS)).toEqual({
            default_search_engine: "youtube",
        });
    });

    it("collects multiple independent changes in one patch", () => {
        const c = document.getElementById("c");
        mod.renderSettingsForm(c, FULL_SETTINGS, SCHEMA);
        c.querySelector('input[type=checkbox][data-key="prompt_before_move"]').checked = false;
        c.querySelector('input[type=text][data-key="library_root"]').value = "E:\\x";
        expect(mod.collectPatch(c, FULL_SETTINGS)).toEqual({
            prompt_before_move: false,
            library_root: "E:\\x",
        });
    });
});

describe("renderWarnings", () => {
    it("shows a warning banner with the error text when warnings are present", () => {
        const c = document.getElementById("c");
        mod.renderWarnings(c, [
            { kind: "settings_load", error: "settings.json is not valid JSON" },
        ]);
        const banner = c.querySelector(".ui-banner-warning");
        expect(banner).not.toBeNull();
        expect(banner.textContent).toContain("settings.json is not valid JSON");
    });

    it("renders no banner when warnings are empty", () => {
        const c = document.getElementById("c");
        mod.renderWarnings(c, []);
        expect(c.querySelector(".ui-banner-warning")).toBeNull();
    });
});
