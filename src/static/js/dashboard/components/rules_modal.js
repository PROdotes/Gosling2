/**
 * Filing rules editor modal — Gap #2 of the settings/rules parity backlog.
 *
 * Mirrors settings_modal.js: pure state-mutation functions and renderRulesForm
 * are DOM/state-only and unit-tested; orchestration (open/save/close) is the
 * thin shell that talks to GET/POST /api/v1/rules. Whole-list replace, not
 * per-rule CRUD (matches the backend contract) -- edits accumulate in a local
 * working copy with zero network calls until the explicit Save button POSTs
 * the whole array once.
 */

import { fetchRules, saveRules } from "../api.js";
import { createModalLifecycle } from "./modal_lifecycle.js";
import { escapeHtml } from "./utils.js";

// ─── Pure state mutation ──────────────────────────────────────────────────

export function cloneWorkingState(rulesFile) {
    return {
        routing_rules: (rulesFile.routing_rules || []).map((r) => ({
            match_genres: [...(r.match_genres || [])],
            target_path: r.target_path || "",
        })),
        default_rule: rulesFile.default_rule || "",
    };
}

export function toRulesPayload(state) {
    return {
        routing_rules: state.routing_rules.map((r) => ({
            match_genres: r.match_genres,
            target_path: r.target_path,
        })),
        default_rule: state.default_rule.trim() || null,
    };
}

export function addRule(state) {
    state.routing_rules.push({ match_genres: [], target_path: "" });
}

export function removeRule(state, ruleIndex) {
    state.routing_rules.splice(ruleIndex, 1);
}

export function moveRule(state, ruleIndex, direction) {
    const target = ruleIndex + direction;
    if (target < 0 || target >= state.routing_rules.length) return;
    const [row] = state.routing_rules.splice(ruleIndex, 1);
    state.routing_rules.splice(target, 0, row);
}

export function addGenre(state, ruleIndex, genre) {
    const trimmed = genre.trim();
    if (!trimmed) return;
    const rule = state.routing_rules[ruleIndex];
    if (!rule) return;
    const exists = rule.match_genres.some(
        (g) => g.toLowerCase() === trimmed.toLowerCase(),
    );
    if (!exists) rule.match_genres.push(trimmed);
}

export function removeGenre(state, ruleIndex, genre) {
    const rule = state.routing_rules[ruleIndex];
    if (!rule) return;
    rule.match_genres = rule.match_genres.filter((g) => g !== genre);
}

export function setPath(state, ruleIndex, path) {
    const rule = state.routing_rules[ruleIndex];
    if (!rule) return;
    rule.target_path = path;
}

export function setDefaultRule(state, path) {
    state.default_rule = path;
}

// ─── Render (pure) ─────────────────────────────────────────────────────────

function renderGenreChips(ruleIndex, genres) {
    if (!genres.length) return '<span class="link-modal-empty">None</span>';
    return genres
        .map(
            (g) => `
        <span class="link-chip">
            <span class="link-chip-label">${escapeHtml(g)}</span>
            <button type="button" class="link-chip-remove" data-rule-index="${ruleIndex}" data-genre="${escapeHtml(g)}" title="Remove">x</button>
        </span>
    `,
        )
        .join("");
}

function renderRuleRow(rule, ruleIndex, total) {
    return `
        <div class="rule-row" data-rule-index="${ruleIndex}">
            <div class="rule-row-header">
                <span class="rule-row-title">Rule ${ruleIndex + 1}</span>
                <div class="rule-row-actions">
                    <button type="button" class="ingest-btn-secondary" data-action="move-rule-up" data-rule-index="${ruleIndex}" ${ruleIndex === 0 ? "disabled" : ""}>Up</button>
                    <button type="button" class="ingest-btn-secondary" data-action="move-rule-down" data-rule-index="${ruleIndex}" ${ruleIndex === total - 1 ? "disabled" : ""}>Down</button>
                    <button type="button" class="ingest-btn-secondary" data-action="remove-rule" data-rule-index="${ruleIndex}">Remove</button>
                </div>
            </div>
            <div class="rule-row-body">
                <label>If genre is</label>
                <div class="link-chip-list rule-genre-list" data-rule-index="${ruleIndex}">
                    ${renderGenreChips(ruleIndex, rule.match_genres)}
                </div>
                <input type="text" class="link-modal-input rule-genre-input" data-rule-index="${ruleIndex}"
                    placeholder="Add genre, Enter to add" autocomplete="off">
                <label>Route to</label>
                <input type="text" class="link-modal-input rule-path-input" data-rule-index="${ruleIndex}"
                    value="${escapeHtml(rule.target_path)}" placeholder="{genre}/{artist} - {title}" autocomplete="off">
            </div>
        </div>
    `;
}

export function renderRulesForm(container, state) {
    const rows = state.routing_rules
        .map((rule, i) => renderRuleRow(rule, i, state.routing_rules.length))
        .join("");

    container.innerHTML = `
        <div class="rules-list">${rows}</div>
        <button type="button" class="ingest-btn-secondary" data-action="add-rule">+ Add Rule</button>
        <div class="rules-default-row">
            <label>Default (no rule matches)</label>
            <input type="text" class="link-modal-input rules-default-input"
                value="${escapeHtml(state.default_rule)}" placeholder="{genre}/{year}/{artist} - {title}" autocomplete="off">
        </div>
    `;
}

export function renderWarnings(container, warnings) {
    container.innerHTML = "";
    if (!warnings || warnings.length === 0) return null;
    const banner = document.createElement("div");
    banner.className = "ui-banner ui-banner-warning";
    banner.textContent = warnings
        .map((w) => w.error || w.kind || "Unknown warning")
        .join("; ");
    container.appendChild(banner);
    return banner;
}

// ─── Orchestration ────────────────────────────────────────────────────────

let _modal = null;
let _ctx = null;
let _state = null;

function ensureModal(overlay) {
    if (!_modal) _modal = createModalLifecycle(overlay);
    return _modal;
}

function renderAndWire() {
    const form = document.getElementById("rules-modal-form");
    if (!form) return;
    renderRulesForm(form, _state);
    wireForm(form);
}

function wireForm(form) {
    form.querySelectorAll(".link-chip-remove").forEach((btn) => {
        btn.addEventListener("click", () => {
            removeGenre(_state, Number(btn.dataset.ruleIndex), btn.dataset.genre);
            renderAndWire();
        });
    });

    form.querySelectorAll(".rule-genre-input").forEach((input) => {
        input.addEventListener("keydown", (e) => {
            if (e.key !== "Enter") return;
            e.preventDefault();
            const ruleIndex = Number(input.dataset.ruleIndex);
            addGenre(_state, ruleIndex, input.value);
            renderAndWire();
            const refocused = form.querySelector(
                `.rule-genre-input[data-rule-index="${ruleIndex}"]`,
            );
            refocused?.focus();
        });
    });

    form.querySelectorAll(".rule-path-input").forEach((input) => {
        input.addEventListener("input", () => {
            setPath(_state, Number(input.dataset.ruleIndex), input.value);
        });
    });

    form.querySelector(".rules-default-input")?.addEventListener("input", (e) => {
        setDefaultRule(_state, e.target.value);
    });

    form.querySelectorAll('[data-action="move-rule-up"]').forEach((btn) => {
        btn.addEventListener("click", () => {
            moveRule(_state, Number(btn.dataset.ruleIndex), -1);
            renderAndWire();
        });
    });

    form.querySelectorAll('[data-action="move-rule-down"]').forEach((btn) => {
        btn.addEventListener("click", () => {
            moveRule(_state, Number(btn.dataset.ruleIndex), 1);
            renderAndWire();
        });
    });

    form.querySelectorAll('[data-action="remove-rule"]').forEach((btn) => {
        btn.addEventListener("click", () => {
            removeRule(_state, Number(btn.dataset.ruleIndex));
            renderAndWire();
        });
    });

    form.querySelector('[data-action="add-rule"]')?.addEventListener("click", () => {
        addRule(_state);
        renderAndWire();
    });
}

export async function openRulesModal(ctx) {
    _ctx = ctx;
    const overlay = document.getElementById("rules-modal");
    if (!overlay) return;
    const warn = document.getElementById("rules-modal-warning");
    const saveBtn = document.getElementById("rules-save-btn");

    let data;
    try {
        data = await fetchRules();
    } catch (e) {
        ctx.showBanner(e.message || "Failed to load rules", "error");
        return;
    }

    _state = cloneWorkingState(data.rules);
    renderAndWire();
    renderWarnings(warn, data.warnings || []);
    saveBtn.onclick = handleSave;
    ensureModal(overlay).open();
}

async function handleSave() {
    const warn = document.getElementById("rules-modal-warning");
    try {
        const data = await saveRules(toRulesPayload(_state));
        _state = cloneWorkingState(data.rules);
        closeRulesModal();
        _ctx.showBanner("Rules saved", "success");
    } catch (e) {
        renderWarnings(warn, [
            { kind: "save_error", error: e.message || "Failed to save rules" },
        ]);
    }
}

export function closeRulesModal() {
    const overlay = document.getElementById("rules-modal");
    if (overlay) ensureModal(overlay).close();
}
