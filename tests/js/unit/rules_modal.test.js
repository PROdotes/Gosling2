import { JSDOM } from "jsdom";
import { beforeEach, describe, expect, it } from "vitest";

// Pure-logic unit tests for the Rules modal. No API mocks: the state mutators
// and renderRulesForm/renderWarnings are DOM/state-only with no network. The
// fetch -> save -> close round-trip is the Playwright layer (not installed
// in-repo), mirroring settings_modal.test.js.
let mod;

const RULES_FILE = {
    routing_rules: [
        { match_genres: ["samba"], target_path: "latin/{artist} - {title}" },
        { match_genres: ["rock", "metal"], target_path: "{genre}/{artist} - {title}" },
    ],
    default_rule: "{genre}/{year}/{artist} - {title}",
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
        "../../../src/static/js/dashboard/components/rules_modal.js"
    );
    return c;
});

describe("cloneWorkingState / toRulesPayload", () => {
    it("clones routing_rules and default_rule into an independent working copy", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        state.routing_rules[0].match_genres.push("bossa");
        expect(RULES_FILE.routing_rules[0].match_genres).toEqual(["samba"]);
        expect(state.default_rule).toBe("{genre}/{year}/{artist} - {title}");
    });

    it("defaults a null default_rule to an empty string for the text input", () => {
        const state = mod.cloneWorkingState({ routing_rules: [], default_rule: null });
        expect(state.default_rule).toBe("");
    });

    it("round-trips back to null when default_rule is blank", () => {
        const state = mod.cloneWorkingState({ routing_rules: [], default_rule: null });
        expect(mod.toRulesPayload(state).default_rule).toBeNull();
    });

    it("trims a whitespace-only default_rule to null on payload", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        state.default_rule = "   ";
        expect(mod.toRulesPayload(state).default_rule).toBeNull();
    });
});

describe("rule list mutators", () => {
    it("addRule appends an empty rule", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.addRule(state);
        expect(state.routing_rules).toHaveLength(3);
        expect(state.routing_rules[2]).toEqual({ match_genres: [], target_path: "" });
    });

    it("removeRule drops the rule at the given index", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.removeRule(state, 0);
        expect(state.routing_rules).toHaveLength(1);
        expect(state.routing_rules[0].match_genres).toEqual(["rock", "metal"]);
    });

    it("moveRule swaps a rule with its predecessor when moving up", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.moveRule(state, 1, -1);
        expect(state.routing_rules[0].match_genres).toEqual(["rock", "metal"]);
        expect(state.routing_rules[1].match_genres).toEqual(["samba"]);
    });

    it("moveRule is a no-op past the array bounds", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.moveRule(state, 0, -1);
        expect(state.routing_rules[0].match_genres).toEqual(["samba"]);
        mod.moveRule(state, 1, 1);
        expect(state.routing_rules[1].match_genres).toEqual(["rock", "metal"]);
    });
});

describe("genre chip mutators", () => {
    it("addGenre appends a trimmed genre to the rule", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.addGenre(state, 0, "  bossa  ");
        expect(state.routing_rules[0].match_genres).toEqual(["samba", "bossa"]);
    });

    it("addGenre ignores a blank entry", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.addGenre(state, 0, "   ");
        expect(state.routing_rules[0].match_genres).toEqual(["samba"]);
    });

    it("addGenre is case-insensitively deduped against existing entries", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.addGenre(state, 0, "SAMBA");
        expect(state.routing_rules[0].match_genres).toEqual(["samba"]);
    });

    it("removeGenre drops the exact genre from the rule", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.removeGenre(state, 1, "rock");
        expect(state.routing_rules[1].match_genres).toEqual(["metal"]);
    });
});

describe("setPath / setDefaultRule", () => {
    it("setPath updates only the target rule's target_path", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.setPath(state, 1, "{artist}/{title}");
        expect(state.routing_rules[1].target_path).toBe("{artist}/{title}");
        expect(state.routing_rules[0].target_path).toBe("latin/{artist} - {title}");
    });

    it("setDefaultRule replaces the default rule text", () => {
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.setDefaultRule(state, "{artist}/{title}");
        expect(state.default_rule).toBe("{artist}/{title}");
    });
});

describe("renderRulesForm", () => {
    it("renders one rule-row per routing rule with its path and genre chips", () => {
        const c = document.getElementById("c");
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.renderRulesForm(c, state);

        const rows = c.querySelectorAll(".rule-row");
        expect(rows).toHaveLength(2);

        const firstPathInput = c.querySelector(
            '.rule-path-input[data-rule-index="0"]',
        );
        expect(firstPathInput.value).toBe("latin/{artist} - {title}");

        const chipLabels = [
            ...c.querySelectorAll(
                '.rule-genre-list[data-rule-index="1"] .link-chip-label',
            ),
        ].map((el) => el.textContent);
        expect(chipLabels).toEqual(["rock", "metal"]);
    });

    it("renders the default_rule value in its own input", () => {
        const c = document.getElementById("c");
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.renderRulesForm(c, state);
        const input = c.querySelector(".rules-default-input");
        expect(input.value).toBe("{genre}/{year}/{artist} - {title}");
    });

    it("disables the Up button on the first row and the Down button on the last row", () => {
        const c = document.getElementById("c");
        const state = mod.cloneWorkingState(RULES_FILE);
        mod.renderRulesForm(c, state);
        expect(
            c.querySelector('[data-action="move-rule-up"][data-rule-index="0"]').disabled,
        ).toBe(true);
        expect(
            c.querySelector('[data-action="move-rule-down"][data-rule-index="1"]').disabled,
        ).toBe(true);
        expect(
            c.querySelector('[data-action="move-rule-down"][data-rule-index="0"]').disabled,
        ).toBe(false);
    });

    it("renders 'None' for a rule with no genres yet", () => {
        const c = document.getElementById("c");
        const state = mod.cloneWorkingState({
            routing_rules: [{ match_genres: [], target_path: "" }],
            default_rule: null,
        });
        mod.renderRulesForm(c, state);
        expect(c.querySelector(".rule-genre-list").textContent).toContain("None");
    });
});

describe("renderWarnings", () => {
    it("shows a warning banner with the error text when warnings are present", () => {
        const c = document.getElementById("c");
        mod.renderWarnings(c, [{ kind: "rules_load", error: "rules.json is not valid JSON" }]);
        const banner = c.querySelector(".ui-banner-warning");
        expect(banner).not.toBeNull();
        expect(banner.textContent).toContain("rules.json is not valid JSON");
    });

    it("renders no banner when warnings are empty", () => {
        const c = document.getElementById("c");
        mod.renderWarnings(c, []);
        expect(c.querySelector(".ui-banner-warning")).toBeNull();
    });
});
