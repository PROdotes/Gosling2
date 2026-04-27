let _elements = null;
let _resolve = null;

function getElements() {
    if (_elements) return _elements;

    const overlay = document.getElementById("confirm-modal");
    if (!overlay) return null;

    _elements = {
        overlay,
        titleEl: document.getElementById("confirm-modal-title"),
        messageEl: document.getElementById("confirm-modal-message"),
        okBtn: document.getElementById("confirm-modal-ok"),
        cancelBtn: document.getElementById("confirm-modal-cancel"),
    };

    _elements.okBtn.addEventListener("click", () => close(true));
    _elements.cancelBtn.addEventListener("click", () => close(false));
    _elements.overlay.addEventListener("click", (e) => {
        if (e.target === _elements.overlay) close(false);
    });

    document.addEventListener("keydown", (e) => {
        if (
            _elements.overlay.style.display !== "none" &&
            e.key === "Escape"
        ) {
            close(false);
        }
    });

    return _elements;
}

function close(result) {
    const els = getElements();
    if (els) els.overlay.style.display = "none";
    if (_resolve) {
        _resolve(result);
        _resolve = null;
    }
}

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
    const els = getElements();
    if (!els) {
        console.warn("confirm-modal elements not found in DOM");
        return Promise.resolve(false);
    }

    els.titleEl.textContent = title;
    els.messageEl.textContent = message;
    els.okBtn.textContent = okLabel;
    els.overlay.style.display = "flex";
    els.okBtn.focus();

    return new Promise((resolve) => {
        _resolve = resolve;
    });
}
