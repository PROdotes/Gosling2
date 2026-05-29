import { getChangelog } from "../api.js";

function formatTimestamp(ts) {
    if (!ts) return "";
    return ts.replace("T", " ").substring(0, 19);
}

function renderValue(val, type) {
    if (val === null || val === undefined) {
        return '<span class="audit-val-null">null</span>';
    }
    const cls = type === "old" ? "audit-val-old" : type === "new" ? "audit-val-new" : "audit-val-plain";
    return `<span class="${cls}">${String(val)}</span>`;
}

function getLabelClass(label) {
    if (label === "UI") return "audit-label audit-label-ui";
    if (label === "ingest") return "audit-label audit-label-ingest";
    return "audit-label audit-label-other";
}

function inferAction(rows) {
    const allOldNull = rows.every(r => r.old_value === null || r.old_value === undefined);
    const allNewNull = rows.every(r => r.new_value === null || r.new_value === undefined);
    if (allOldNull) return "CREATE";
    if (allNewNull) return "DELETE";
    return "UPDATE";
}

function groupConsecutive(rows) {
    const groups = [];
    let current = null;
    for (const row of rows) {
        const key = `${row.table_name}\0${row.entity_id}`;
        if (!current || current.key !== key) {
            current = { key, table_name: row.table_name, entity_id: row.entity_id, rows: [] };
            groups.push(current);
        }
        current.rows.push(row);
    }
    return groups;
}

function renderBatch(batch) {
    const batchEl = document.createElement("div");
    batchEl.className = "audit-batch";

    const rowWord = batch.rows.length === 1 ? "row" : "rows";
    const header = document.createElement("div");
    header.className = "audit-batch-header";
    header.innerHTML = `
        <span class="${getLabelClass(batch.batch_label)}">${batch.batch_label || "?"}</span>
        <span class="audit-timestamp">${formatTimestamp(batch.timestamp)}</span>
        <span class="audit-row-count">${batch.rows.length} ${rowWord}</span>
        <span class="audit-chevron">&#9654;</span>
    `;

    const body = document.createElement("div");
    body.className = "audit-batch-body";

    const table = document.createElement("table");
    table.className = "audit-table";
    table.innerHTML = `
        <colgroup>
            <col class="col-table">
            <col class="col-id">
            <col class="col-field">
            <col class="col-old">
            <col class="col-new">
        </colgroup>
        <thead>
            <tr>
                <th>Table</th>
                <th>ID</th>
                <th>Field</th>
                <th>Old</th>
                <th>New</th>
            </tr>
        </thead>
    `;
    const tbody = document.createElement("tbody");

    for (const group of groupConsecutive(batch.rows)) {
        const action = inferAction(group.rows);
        const fieldWord = group.rows.length === 1 ? "field" : "fields";

        const groupHeader = document.createElement("tr");
        groupHeader.className = `audit-group-header audit-group-action-${action.toLowerCase()}`;
        groupHeader.innerHTML = `
            <td class="audit-group-table">${group.table_name}</td>
            <td class="audit-group-id">#${group.entity_id}</td>
            <td class="audit-group-action">${action}</td>
            <td colspan="2" class="audit-group-count">${group.rows.length} ${fieldWord}</td>
        `;
        tbody.appendChild(groupHeader);

        for (const row of group.rows) {
            const tr = document.createElement("tr");

            const oldVal = row.old_value != null ? String(row.old_value) : "";
            const newVal = row.new_value != null ? String(row.new_value) : "";

            const tdTable = document.createElement("td");
            tdTable.className = "audit-col-table";
            tdTable.textContent = row.table_name;

            const tdId = document.createElement("td");
            tdId.className = "audit-col-id";
            tdId.textContent = `#${row.entity_id}`;

            const tdField = document.createElement("td");
            tdField.className = "audit-col-field";
            tdField.textContent = row.field_name;

            const tdOld = document.createElement("td");
            tdOld.title = oldVal;
            tdOld.innerHTML = renderValue(row.old_value, "old");

            const tdNew = document.createElement("td");
            tdNew.title = newVal;
            tdNew.innerHTML = renderValue(row.new_value, "new");

            tr.appendChild(tdTable);
            tr.appendChild(tdId);
            tr.appendChild(tdField);
            tr.appendChild(tdOld);
            tr.appendChild(tdNew);
            tbody.appendChild(tr);
        }
    }

    table.appendChild(tbody);
    body.appendChild(table);

    header.addEventListener("click", () => {
        const open = body.classList.toggle("open");
        batchEl.classList.toggle("is-open", open);
        header.querySelector(".audit-chevron").style.transform = open ? "rotate(90deg)" : "";
    });

    batchEl.appendChild(header);
    batchEl.appendChild(body);
    return batchEl;
}

export async function renderAuditLog(ctx) {
    const container = document.getElementById("log-container");
    if (!container) return;

    container.innerHTML = '<div class="audit-state">Loading...</div>';

    let data;
    try {
        data = await getChangelog();
    } catch (err) {
        container.innerHTML = `<div class="audit-state audit-state-error">Failed to load changelog: ${err.message}</div>`;
        return;
    }

    const { batches } = data;
    if (!batches || batches.length === 0) {
        container.innerHTML = '<div class="audit-state">No audit entries found.</div>';
        return;
    }

    container.innerHTML = "";

    const batchWord = batches.length === 1 ? "batch" : "batches";
    const header = document.createElement("div");
    header.className = "audit-log-header";
    header.innerHTML = `
        <span class="audit-log-title">Audit Log</span>
        <span class="audit-log-count">${batches.length} ${batchWord}</span>
        <div class="audit-log-actions">
            <button id="log-expand-all-btn" type="button" class="audit-btn">Expand All</button>
            <button id="log-collapse-all-btn" type="button" class="audit-btn">Collapse All</button>
            <button id="log-refresh-btn" type="button" class="audit-btn">Refresh</button>
        </div>
    `;
    container.appendChild(header);

    document.getElementById("log-expand-all-btn")?.addEventListener("click", () => {
        container.querySelectorAll(".audit-batch-body").forEach(b => {
            b.classList.add("open");
            b.closest(".audit-batch")?.classList.add("is-open");
        });
        container.querySelectorAll(".audit-chevron").forEach(ch => { ch.style.transform = "rotate(90deg)"; });
    });
    document.getElementById("log-collapse-all-btn")?.addEventListener("click", () => {
        container.querySelectorAll(".audit-batch-body").forEach(b => {
            b.classList.remove("open");
            b.closest(".audit-batch")?.classList.remove("is-open");
        });
        container.querySelectorAll(".audit-chevron").forEach(ch => { ch.style.transform = ""; });
    });
    document.getElementById("log-refresh-btn")?.addEventListener("click", () => renderAuditLog(ctx));

    const list = document.createElement("div");
    for (const batch of batches) {
        list.appendChild(renderBatch(batch));
    }
    container.appendChild(list);
}
