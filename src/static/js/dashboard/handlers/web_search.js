/**
 * GOSLING WEB SEARCH HANDLER
 * Handles web search functionality including long-press engine picker and search execution.
 */

import { getSongWebSearch } from "../api.js";

export class WebSearchHandler {
    constructor(ctx, _window = typeof window !== "undefined" ? window : null) {
        this.ctx = ctx;
        this._window = _window;
        this._longPressTimer = null;
        this._longPressTriggered = false;
    }

    /**
     * Sets up long-press event listeners for web search buttons.
     * Should be called during initialization.
     */
    setupListeners() {
        document.addEventListener(
            "pointerdown",
            this.handlePointerDown.bind(this),
        );
        document.addEventListener("pointerup", this.handlePointerUp.bind(this));
        document.addEventListener(
            "pointercancel",
            this.handlePointerUp.bind(this),
        );
        document.addEventListener("click", this.handleClick.bind(this), true);
    }

    /**
     * Handles pointer down events for long-press detection.
     * @param {PointerEvent} event
     */
    handlePointerDown(event) {
        const btn = event.target.closest(".web-search-main");
        if (!btn) return;

        this._longPressTriggered = false;
        this._longPressTimer = setTimeout(() => {
            this._longPressTriggered = true;
            this.showOneTimeEnginePicker(btn);
        }, 500);
    }

    /**
     * Handles pointer up/cancel events to clear long-press timer.
     * @param {PointerEvent} event
     */
    handlePointerUp() {
        clearTimeout(this._longPressTimer);
    }

    /**
     * Handles click events to prevent interference with long-press.
     * @param {MouseEvent} event
     */
    handleClick(event) {
        if (
            this._longPressTriggered &&
            event.target.closest(".web-search-main")
        ) {
            event.stopImmediatePropagation();
            this._longPressTriggered = false;
        }
    }

    /**
     * Shows the one-time engine picker dropdown.
     * @param {HTMLElement} btn - The web-search-main button
     */
    showOneTimeEnginePicker(btn) {
        const splitEl = btn.closest(".web-search-split");
        if (!splitEl) return;

        const dropdown = splitEl.querySelector(".web-search-dropdown");
        if (!dropdown) return;

        // Show ALL engines (including current default) for one-time pick
        const songId = btn.dataset.songId;
        const engines = this.ctx.getState().searchEngines;
        dropdown.innerHTML = Object.entries(engines)
            .map(
                ([id, label]) =>
                    `<button class="web-search-option web-search-once" data-engine="${id}" data-song-id="${songId}">${label}</button>`,
            )
            .join("");
        dropdown.hidden = false;

        dropdown.querySelectorAll(".web-search-once").forEach((opt) => {
            opt.onclick = async (e) => {
                e.stopPropagation();
                dropdown.hidden = true;
                dropdown.innerHTML = "";

                // Restore normal set-engine options on next open
                const activeEngine = btn.dataset.engine;
                const otherEngines = Object.entries(engines).filter(
                    ([id]) => id !== activeEngine,
                );
                dropdown.innerHTML = otherEngines
                    .map(
                        ([id, label]) =>
                            `<button class="web-search-option" data-engine="${id}">${label}</button>`,
                    )
                    .join("");

                try {
                    const data = await getSongWebSearch(
                        songId,
                        opt.dataset.engine,
                    );
                    if (data && data.url) {
                        this._window.open(data.url, "_blank");
                    }
                } catch (err) {
                    this.ctx.showBanner?.(
                        `Search failed: ${err.message}`,
                        "error",
                    );
                }
            };
        });

        const close = (e) => {
            if (!splitEl.contains(e.target)) {
                dropdown.hidden = true;
                // Restore normal options
                const activeEngine = btn.dataset.engine;
                const otherEngines = Object.entries(
                    this.ctx.getState().searchEngines,
                ).filter(([id]) => id !== activeEngine);
                dropdown.innerHTML = otherEngines
                    .map(
                        ([id, label]) =>
                            `<button class="web-search-option" data-engine="${id}">${label}</button>`,
                    )
                    .join("");
                document.removeEventListener("click", close, true);
            }
        };
        document.addEventListener("click", close, true);
    }
}
