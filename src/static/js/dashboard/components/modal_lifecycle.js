/**
 * Modal Lifecycle Helper — extracts common open/close/escape/overlay-click patterns.
 *
 * Eliminates ~100 lines of duplicated boilerplate across 7 modal files.
 *
 * Usage:
 *   const modal = createModalLifecycle(overlayEl, {
 *       onOpen: () => { ... },   // custom open logic (focus, render, etc.)
 *       onClose: () => { ... },  // custom close logic (state cleanup, callbacks)
 *       onBeforeClose: () => boolean,  // return false to cancel close
 *       overlayClickCheck: (e) => boolean,  // custom check for overlay click
 *   });
 *
 *   modal.open(config);   // calls onOpen() after showing overlay
 *   modal.close();        // calls onBeforeClose(), then hides overlay + onClose()
 */

export function createModalLifecycle(overlayEl, { onOpen, onClose, onBeforeClose, overlayClickCheck } = {}) {
    function open(...args) {
        overlayEl.style.display = "flex";
        if (onOpen) onOpen(...args);
    }

    function close(...args) {
        if (onBeforeClose && onBeforeClose(...args) === false) {
            return;
        }
        overlayEl.style.display = "none";
        if (onClose) onClose(...args);
    }

    // Escape key handler — closes modal if open
    function handleKeydown(e) {
        if (e.key === "Escape" && overlayEl.style.display === "flex") {
            e.stopImmediatePropagation();
            close();
        }
    }

    // Overlay click handler — closes if click is on overlay (not modal box)
    function handleOverlayClick(e) {
        if (overlayClickCheck ? overlayClickCheck(e) : e.target === overlayEl) {
            close();
        }
    }

    // Setup (once per modal)
    document.addEventListener("keydown", handleKeydown);
    overlayEl.addEventListener("click", handleOverlayClick);

    return { open, close };
}
