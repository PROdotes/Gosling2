const getOverlay = () => document.getElementById("confirm-modal");
const getTitleEl = () => document.getElementById("confirm-modal-title");
const getMessageEl = () => document.getElementById("confirm-modal-message");
const getOkBtn = () => document.getElementById("confirm-modal-ok");
const getCancelBtn = () => document.getElementById("confirm-modal-cancel");

let _resolve = null;
let _listenersBound = false;

function close(result) {
    const overlay = getOverlay();
    if (overlay) overlay.style.display = "none";
    if (_resolve) {
        _resolve(result);
        _resolve = null;
    }
}

function bindListeners() {
    if (_listenersBound) return;
    const okBtn = getOkBtn();
    const cancelBtn = getCancelBtn();
    const overlay = getOverlay();

    if (!okBtn || !cancelBtn || !overlay) return;

    okBtn.addEventListener("click", () => close(true));
    cancelBtn.addEventListener("click", () => close(false));
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) close(false);
    });
    document.addEventListener("keydown", (e) => {
        const currentOverlay = getOverlay();
        if (currentOverlay && currentOverlay.style.display !== "none" && e.key === "Escape") close(false);
    });

    _listenersBound = true;
}

// Try binding on load if elements exist
bindListeners();

/**
 * Show a styled confirmation dialog.
 * @param {string} message
 * @param {object} [options]
 * @param {string} [options.title]
 * @param {string} [options.okLabel]
 * @returns {Promise<boolean>}
 */
export function showConfirm(
    message,
    { title = "Confirm", okLabel = "Delete" } = {},
) {
    bindListeners(); // Ensure bound if elements were added later

    const titleEl = getTitleEl();
    const messageEl = getMessageEl();
    const okBtn = getOkBtn();
    const overlay = getOverlay();

    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;
    if (okBtn) {
        okBtn.textContent = okLabel;
        okBtn.focus();
    }
    if (overlay) overlay.style.display = "flex";

    return new Promise((resolve) => {
        _resolve = resolve;
    });
}
