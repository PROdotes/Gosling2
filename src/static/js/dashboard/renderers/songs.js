import {
    asArray,
    buildNavigateAttrs,
    escapeHtml,
    renderAuditTimeline,
    renderEmptyState,
    renderStatus,
    textOrDash,
} from "../components/utils.js";

function compareRow(label, dbValue, fileValue) {
    const left = dbValue === null || dbValue === undefined || dbValue === "" ? "-" : String(dbValue);
    const right = fileValue === null || fileValue === undefined || fileValue === "" ? "-" : String(fileValue);
    const matches = left.toLowerCase() === right.toLowerCase();
    const rightClass = matches ? "comparison-match" : "comparison-miss";

    return `
        <tr>
            <td>${escapeHtml(label)}</td>
            <td>${escapeHtml(left)}</td>
            <td class="${rightClass}">${escapeHtml(right)}</td>
        </tr>
    `;
}

function renderCreditsGroups(credits) {
    const items = asArray(credits);
    if (!items.length) {
        return '<div class="muted-note">No credits found</div>';
    }

    const roleGroups = {
        Producers: ["producer", "executive producer", "co-producer", "associate producer"],
        Writers: ["writer", "composer", "lyricist", "author"],
        Performers: ["artist", "performer", "vocals", "featuring", "featured artist"],
        Engineers: ["engineer", "mixing", "mixing engineer", "mastering", "mastering engineer", "recording"],
        Other: [],
    };

    const grouped = {
        Producers: [],
        Writers: [],
        Performers: [],
        Engineers: [],
        Other: [],
    };

    items.forEach((credit) => {
        const role = String(credit.role_name || "").toLowerCase();
        const target = Object.entries(roleGroups).find(([, keywords]) => keywords.some((keyword) => role.includes(keyword)));
        const bucket = target ? target[0] : "Other";
        grouped[bucket].push(credit);
    });

    return Object.entries(grouped)
        .filter(([, groupItems]) => groupItems.length)
        .map(([label, groupItems]) => `
            <div class="stack-list">
                <div class="mini-label">${escapeHtml(label)}</div>
                <div class="credits-list">
                    ${groupItems.map((credit) => `
                        <div class="credit-item">
                            <span class="credit-name">${credit.display_name ? `<button class="inline-link" ${buildNavigateAttrs("artists", credit.display_name)}>${escapeHtml(credit.display_name)}</button>` : "-"}</span>
                            <span class="credit-role">${escapeHtml(credit.role_name || "-")}</span>
                        </div>
                    `).join("")}
                </div>
            </div>
        `)
        .join("");
}

function renderAlbumCards(albums) {
    const items = asArray(albums);
    if (!items.length) {
        return '<div class="muted-note">No albums linked</div>';
    }

    return items.map((album) => {
        const title = album.album_title || album.display_title || "Unknown Album";
        const albumArtistNames = asArray(album.credits)
            .map((credit) => credit.display_name || credit.name)
            .filter(Boolean);

        return `
            <div class="album-card-detail">
                <div class="card-title"><button class="inline-link" ${buildNavigateAttrs("albums", title)}>${escapeHtml(title)}</button></div>
                <div class="card-meta">
                    ${album.album_type ? `<span class="pill">${escapeHtml(album.album_type)}</span>` : ""}
                    ${album.release_year ? `<span class="pill mono">${escapeHtml(album.release_year)}</span>` : ""}
                    ${album.display_publisher ? `<span class="pill publisher">${escapeHtml(album.display_publisher)}</span>` : ""}
                </div>
                ${albumArtistNames.length ? `<div class="card-subtitle">Album Artist: ${albumArtistNames.map((name) => `<button class="inline-link" ${buildNavigateAttrs("artists", name)}>${escapeHtml(name)}</button>`).join(", ")}</div>` : ""}
            </div>
        `;
    }).join("");
}

function renderTagCollection(tags, variant = "") {
    const items = asArray(tags);
    if (!items.length) {
        return '<div class="muted-note">None</div>';
    }

    return `
        <div class="tag-list">
            ${items.map((tag) => {
                const label = tag.name || tag.display_name || "-";
                const className = variant ? `tag ${variant}` : "tag";
                return `<span class="${className}">${escapeHtml(label)}</span>`;
            }).join("")}
        </div>
    `;
}

export function renderSongs(ctx, songs) {
    ctx.setState({ selectedIndex: -1 });
    ctx.updateResultsSummary(songs.length, "song");

    if (!songs.length) {
        ctx.elements.resultsContainer.innerHTML = renderEmptyState("No songs found");
        return;
    }

    ctx.elements.resultsContainer.innerHTML = songs.map((song, index) => `
        <article class="result-card song-card" data-action="select-result" data-index="${index}" data-selectable="true">
            <div class="card-icon">♪</div>
            <div class="card-body">
                <div class="card-title-row">
                    <div class="card-title">${escapeHtml(song.title || song.media_name || "Untitled")}</div>
                    <span class="pill mono">#${escapeHtml(song.id || "-")}</span>
                </div>
                <div class="card-subtitle">${escapeHtml(song.display_artist || "Unknown Artist")}</div>
                <div class="card-meta">
                    ${song.primary_genre ? `<span class="pill genre">${escapeHtml(song.primary_genre)}</span>` : ""}
                    <span class="pill mono">${escapeHtml(song.year || "-")}</span>
                    ${song.formatted_duration ? `<span class="pill mono">${escapeHtml(song.formatted_duration)}</span>` : ""}
                </div>
            </div>
        </article>
    `).join("");
}

export function renderSongDetailLoading(ctx, song) {
    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(song.title || song.media_name || "Untitled")} <span class="pill mono">#${escapeHtml(song.id || "-")}</span></div>
            <div class="detail-path">${escapeHtml(song.source_path || "No source path")}</div>
        </div>
        <div class="detail-content">
            ${renderStatus("loading", "Loading file info...")}
            <div class="meta-grid">
                <div class="meta-item"><div class="meta-label">Title</div><div class="meta-value">${escapeHtml(song.media_name || song.title || "-")}</div></div>
                <div class="meta-item"><div class="meta-label">Artist</div><div class="meta-value">${escapeHtml(song.display_artist || "-")}</div></div>
                <div class="meta-item"><div class="meta-label">Year</div><div class="meta-value">${textOrDash(song.year)}</div></div>
                <div class="meta-item"><div class="meta-label">BPM</div><div class="meta-value">${textOrDash(song.bpm)}</div></div>
                <div class="meta-item"><div class="meta-label">Duration</div><div class="meta-value">${textOrDash(song.formatted_duration)}</div></div>
                <div class="meta-item"><div class="meta-label">ISRC</div><div class="meta-value mono">${textOrDash(song.isrc)}</div></div>
            </div>
        </div>
    `);
}

export function renderSongDetailComplete(ctx, song, fileData, auditHistory) {
    const dbCredits = asArray(song.credits);
    const fileCredits = asArray(fileData && fileData.credits);
    const dbAlbums = asArray(song.albums);
    const fileAlbums = asArray(fileData && fileData.albums);
    const dbTags = asArray(song.tags);
    const fileTags = asArray(fileData && fileData.tags);
    const dbPublishers = asArray(song.publishers);
    const filePublishers = asArray(fileData && fileData.publishers);
    const dbGenres = dbTags.filter((tag) => String(tag.category || "").toLowerCase() === "genre");
    const fileGenres = fileTags.filter((tag) => String(tag.category || "").toLowerCase() === "genre");
    const dbOther = dbTags.filter((tag) => String(tag.category || "").toLowerCase() !== "genre");
    const fileOther = fileTags.filter((tag) => String(tag.category || "").toLowerCase() !== "genre");
    const statusHtml = fileData ? renderStatus("found", "File verified") : renderStatus("missing", "File not found");
    const rawTags = fileData && fileData.raw_tags ? Object.entries(fileData.raw_tags) : [];
    const artistValue = song.display_artist
        ? `<button class="inline-link" ${buildNavigateAttrs("artists", song.display_artist)}>${escapeHtml(song.display_artist)}</button>`
        : "-";

    ctx.showDetailPanel(`
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(song.title || song.media_name || "Untitled")} <span class="pill mono">#${escapeHtml(song.id || "-")}</span></div>
            <div class="detail-path">${escapeHtml(song.source_path || "No source path")}</div>
        </div>
        <div class="detail-content">
            ${statusHtml}

            <div class="detail-section">
                <div class="section-title">Core Metadata</div>
                <div class="surface-box">
                    <table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Field</th>
                                <th>Library</th>
                                <th>File</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${compareRow("Title", song.media_name, fileData && fileData.media_name)}
                            ${compareRow("Artist", song.display_artist, fileData && fileData.display_artist)}
                            ${compareRow("Year", song.year, fileData && fileData.year)}
                            ${compareRow("BPM", song.bpm, fileData && fileData.bpm)}
                            ${compareRow("Duration", song.formatted_duration, fileData && fileData.formatted_duration)}
                            ${compareRow("ISRC", song.isrc, fileData && fileData.isrc)}
                            ${compareRow("Publisher (Master)", song.display_master_publisher, fileData && fileData.display_master_publisher)}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Overview</div>
                <div class="meta-grid">
                    <div class="meta-item"><div class="meta-label">Artist</div><div class="meta-value">${artistValue}</div></div>
                    <div class="meta-item"><div class="meta-label">Year</div><div class="meta-value">${textOrDash(song.year)}</div></div>
                    <div class="meta-item"><div class="meta-label">Duration</div><div class="meta-value">${textOrDash(song.formatted_duration)}</div></div>
                    <div class="meta-item"><div class="meta-label">BPM</div><div class="meta-value mono">${textOrDash(song.bpm)}</div></div>
                    <div class="meta-item" style="grid-column: span 2">
                        <div class="meta-label">Audio Hash</div>
                        <div class="meta-value mono" style="font-size: 0.72rem; word-break: break-all">${textOrDash(song.audio_hash)}</div>
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Credits</div>
                <div class="two-column">
                    <div class="surface-box">
                        <div class="mini-label">Library (${dbCredits.length})</div>
                        ${renderCreditsGroups(dbCredits)}
                    </div>
                    <div class="surface-box">
                        <div class="mini-label">File (${fileCredits.length})</div>
                        ${renderCreditsGroups(fileCredits)}
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Albums</div>
                <div class="two-column">
                    <div class="surface-box">
                        <div class="mini-label">Library (${dbAlbums.length})</div>
                        <div class="stack-list">${renderAlbumCards(dbAlbums)}</div>
                    </div>
                    <div class="surface-box">
                        <div class="mini-label">File (${fileAlbums.length})</div>
                        <div class="stack-list">${renderAlbumCards(fileAlbums)}</div>
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Genres</div>
                <div class="two-column">
                    <div class="surface-box"><div class="mini-label">Library (${dbGenres.length})</div>${renderTagCollection(dbGenres, "genre")}</div>
                    <div class="surface-box"><div class="mini-label">File (${fileGenres.length})</div>${renderTagCollection(fileGenres, "genre")}</div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Other Tags</div>
                <div class="two-column">
                    <div class="surface-box"><div class="mini-label">Library (${dbOther.length})</div>${renderTagCollection(dbOther)}</div>
                    <div class="surface-box"><div class="mini-label">File (${fileOther.length})</div>${renderTagCollection(fileOther)}</div>
                </div>
            </div>

            <div class="detail-section">
                <div class="section-title">Publishers</div>
                <div class="two-column">
                    <div class="surface-box"><div class="mini-label">Library (${dbPublishers.length})</div>${renderTagCollection(dbPublishers, "publisher")}</div>
                    <div class="surface-box"><div class="mini-label">File (${filePublishers.length})</div>${renderTagCollection(filePublishers, "publisher")}</div>
                </div>
            </div>

            ${rawTags.length ? `
                <div class="detail-section">
                    <div class="section-title">Raw Tags (${rawTags.length})</div>
                    <div class="surface-box mono">
                        ${rawTags.map(([key, value]) => `<div><span class="comparison-label">${escapeHtml(key)}</span>: ${escapeHtml(asArray(value).join(", "))}</div>`).join("")}
                    </div>
                </div>
            ` : ""}

            <div class="detail-section">
                <div class="section-title">Lifecycle & History</div>
                ${renderAuditTimeline(auditHistory)}
            </div>
        </div>
    `);
}
