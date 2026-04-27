/**
 * Shared entity renderer utilities.
 * Eliminates ~80 lines of duplicated boilerplate across entity renderers.
 */

import { renderStatus } from "../components/utils.js";

/**
 * Renders the entity list with common wrapper logic.
 * Handles setState, results summary, list title, actions slot, and empty state.
 *
 * @param {object} ctx - The application context
 * @param {Array} items - The entities to render
 * @param {object} options
 * @param {string} options.entityType - The entity type ("song", "album", "artist", "publisher", "tag")
 * @param {string} options.listTitle - The list title (e.g., "Albums", "Artists")
 * @param {string} options.emptyMessage - Message to show when no items
 * @param {Function} options.renderRow - Function to render a single row (item, index) => html
 * @param {Function} [options.getUnlinkedCount] - Function to get unlinked count (items) => count
 * @param {string} [options.deleteAction] - The bulk delete action name
 */
export function renderEntityList(ctx, items, {
    entityType,
    listTitle,
    emptyMessage,
    renderRow,
    getUnlinkedCount,
    deleteAction,
}) {
    ctx.setState({ selectedIndex: -1, displayedItems: items });
    ctx.updateResultsSummary(items.length, entityType);

    const listTitleEl = document.getElementById("entity-list-title");
    if (listTitleEl) listTitleEl.textContent = `${listTitle} (${items.length})`;

    const actionsSlot = document.getElementById("entity-list-actions");
    if (actionsSlot && getUnlinkedCount && deleteAction) {
        const unlinkedCount = getUnlinkedCount(items);
        actionsSlot.innerHTML = unlinkedCount > 0
            ? `<button type="button" class="btn danger small" data-action="${deleteAction}">Delete ${unlinkedCount} unlinked</button>`
            : "";
    }

    if (!items.length) {
        ctx.elements.resultsContainer.innerHTML = `<div class="entity-empty-state">${emptyMessage}</div>`;
        return true; // returned as empty signal
    }

    ctx.elements.resultsContainer.innerHTML = items
        .map((item, index) => renderRow(item, index))
        .join("");

    return false; // not empty
}

/**
 * Renders the entity detail loading state.
 *
 * @param {object} ctx - The application context
 * @param {object} entity - The entity (with id, name/title)
 * @param {string} entityType - The entity type label (e.g., "ALBUM", "TAG")
 * @param {string} entityName - The entity display name
 * @param {string} [subtitle] - Optional subtitle
 */
export function renderDetailLoading(ctx, entity, entityType, entityName, subtitle = "") {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${entityName} <span class="pill mono">#${entity.id || "-"}</span></div>
            <div class="detail-subtitle">${entityType}${subtitle}</div>
        </div>
        <div class="detail-content">
            ${renderStatus("loading", `Loading ${entityType.toLowerCase()}...`)}
        </div>
    `);
}

/**
 * Common detail section: Delete button.
 */
export function renderDeleteSection(action, entityId, canDelete, reason = "") {
    return `
        <div class="detail-section">
            <button
                type="button"
                class="btn danger"
                data-action="${action}"
                data-${action.split("-")[1]}-id="${entityId}"
                ${!canDelete ? `disabled title="${reason}"` : ""}
            >Delete ${action.split("-")[1].charAt(0).toUpperCase() + action.split("-")[1].slice(1)}</button>
        </div>
    `;
}
