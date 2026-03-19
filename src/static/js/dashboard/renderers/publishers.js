import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderEmptyState,
    renderSongList,
    renderStatus,
} from "../components/utils.js";

function renderSubPublishers(items) {
    const publishers = asArray(items);
    if (!publishers.length) {
        return '<div class="muted-note">No sub-publishers linked</div>';
    }

    return `
        <div class="tag-list">
            ${publishers.map((publisher) => `
                <button class="tag publisher link" ${buildNavigateAttrs("publishers", publisher.name || "")}>${escapeHtml(publisher.name || "-")}</button>
            `).join("")}
        </div>
    `;
}

export function renderPublishers(ctx, publishers) {
    ctx.setState({ selectedIndex: -1 });
    ctx.updateResultsSummary(publishers.length, "publisher");

    if (!publishers.length) {
        ctx.elements.resultsContainer.innerHTML = renderEmptyState("No publishers found");
        return;
    }

    ctx.elements.resultsContainer.innerHTML = publishers.map((publisher, index) => `
        <article class="result-card publisher-card" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="card-icon">PUB</div>
            <div class="card-body">
                <div class="card-title-row">
                    <div class="card-title">${escapeHtml(publisher.name || "Unnamed Publisher")}</div>
                    <span class="pill mono">#${escapeHtml(publisher.id || "-")}</span>
                </div>
                <div class="card-subtitle">${escapeHtml(publisher.parent_name || "Independent / top level")}</div>
            </div>
        </article>
    `).join("");
}

export function renderPublisherDetailLoading(ctx, publisher) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(publisher.name || "Unnamed Publisher")} <span class="pill mono">#${escapeHtml(publisher.id || "-")}</span></div>
            <div class="detail-path">PUBLISHER</div>
        </div>
        <div class="detail-content">
            ${renderStatus("loading", "Loading repertoire...")}
        </div>
    `);
}

export function renderPublisherDetailComplete(ctx, publisher, repertoire) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(publisher.name || "Unnamed Publisher")} <span class="pill mono">#${escapeHtml(publisher.id || "-")}</span></div>
            <div class="detail-path">PUBLISHER</div>
        </div>
        <div class="detail-content">
            <div class="detail-section">
                <div class="section-title">Identity</div>
                <div class="meta-grid">
                    <div class="meta-item"><div class="meta-label">Name</div><div class="meta-value">${escapeHtml(publisher.name || "-")}</div></div>
                    <div class="meta-item"><div class="meta-label">Parent</div><div class="meta-value">${publisher.parent_name ? `<button class="inline-link" ${buildNavigateAttrs("publishers", publisher.parent_name)}>${escapeHtml(publisher.parent_name)}</button>` : "None"}</div></div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Sub-Publishers</div>
                ${renderSubPublishers(publisher.sub_publishers)}
            </div>

            <div class="detail-section">
                <div class="section-title">Repertoire (${asArray(repertoire).length})</div>
                ${renderSongList(repertoire, "No songs explicitly linked as master")}
            </div>
        </div>
    `);
}
