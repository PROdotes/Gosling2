/**
 * Global stackable toast notification system.
 * Call initToastSystem() once at app startup before any showToast() calls.
 */

const CONTAINER_ID = "toast-container";

export function initToastSystem() {
    if (document.getElementById(CONTAINER_ID)) return;
    const container = document.createElement("div");
    container.id = CONTAINER_ID;
    container.className = "toast-container";
    document.body.appendChild(container);
}

/**
 * Show a toast notification.
 *
 * @param {string} message - Text to display.
 * @param {"success"|"warning"|"error"} type - Visual variant.
 * @param {number} durationMs - Auto-dismiss delay in ms. 0 = sticky (requires manual dismiss).
 * @param {{ label: string, onClick: () => void }|null} action - Optional action button.
 * @returns {HTMLElement|null} The toast DOM element, or null if container not found.
 */
export function showToast(
    message,
    type = "success",
    durationMs = 3000,
    action = null,
) {
    const container = document.getElementById(CONTAINER_ID);
    if (!container) return null;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");

    const prefixMap = { success: "OK", warning: "!", error: "!!" };
    const prefix = prefixMap[type] ?? "?";

    const escapeHtml = (str) =>
        String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

    let html = `
        <span class="toast-prefix">[${prefix}]</span>
        <span class="toast-message">${escapeHtml(message)}</span>
    `;

    if (action) {
        html += `<button class="toast-action-btn">${escapeHtml(action.label)}</button>`;
    }

    html += `<button class="toast-dismiss-btn" aria-label="Dismiss">x</button>`;

    toast.innerHTML = html;

    let dismissed = false;
    const dismiss = () => {
        if (dismissed) return;
        dismissed = true;
        toast.classList.add("toast-exit");
        toast.addEventListener("animationend", () => toast.remove(), {
            once: true,
        });
    };

    toast
        .querySelector(".toast-dismiss-btn")
        .addEventListener("click", dismiss);

    if (action) {
        toast
            .querySelector(".toast-action-btn")
            .addEventListener("click", () => {
                action.onClick();
                dismiss();
            });
    }

    container.appendChild(toast);

    if (durationMs > 0) {
        setTimeout(dismiss, durationMs);
    }

    return toast;
}
