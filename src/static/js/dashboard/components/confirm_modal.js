const overlay = document.getElementById("confirm-modal");
const titleEl = document.getElementById("confirm-modal-title");
const messageEl = document.getElementById("confirm-modal-message");
const okBtn = document.getElementById("confirm-modal-ok");
const cancelBtn = document.getElementById("confirm-modal-cancel");

let _resolve = null;

function close(result) {
    overlay.style.display = "none";
    if (_resolve) {
        _resolve(result);
        _resolve = null;
    }
}

okBtn.addEventListener("click", () => close(true));
cancelBtn.addEventListener("click", () => close(false));
overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close(false);
});
document.addEventListener("keydown", (e) => {
    if (overlay.style.display !== "none" && e.key === "Escape") close(false);
});

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
    titleEl.textContent = title;
    messageEl.textContent = message;
    okBtn.textContent = okLabel;
    overlay.style.display = "flex";
    okBtn.focus();
    return new Promise((resolve) => {
        _resolve = resolve;
    });
}
