/**
 * Activates an inline text editor on a <span> element.
 *
 * Options:
 *   field: string (media_name, year, release_year, bpm, isrc, title, etc.)
 *   validationRules: object (from state)
 *   onCommit: async (value) => { ... } returns the updated entity
 *   onSave: (updatedEntity, field) => { ... } called after successful commit
 */
export function activateInlineEdit(span, { field, validationRules, onCommit, onSave }) {
    const currentValue = span.textContent === "-" ? "" : span.textContent;

    const rules = validationRules;
    const validators = {
        media_name: (v) => v ? null : "Title cannot be empty",
        title: (v) => v ? null : "Title cannot be empty",
        year: (v) => {
            if (!v) return null;
            const n = Number(v);
            const min = rules?.year?.min ?? 1860;
            const max = rules?.year?.max ?? (new Date().getFullYear() + 1);
            if (!Number.isInteger(n) || n < min || n > max) return `Year must be between ${min}–${max}`;
            return null;
        },
        release_year: (v) => {
            if (!v) return null;
            const n = Number(v);
            const max = new Date().getFullYear() + 1;
            if (!Number.isInteger(n) || n < 1860 || n > max) return `Year must be between 1860–${max}`;
            return null;
        },
        bpm: (v) => {
            if (!v) return null;
            const n = Number(v);
            const min = rules?.bpm?.min ?? 1;
            const max = rules?.bpm?.max ?? 300;
            if (!Number.isInteger(n) || n < min || n > max) return `BPM must be between ${min}–${max}`;
            return null;
        },
        isrc: (v) => {
            if (!v) return null;
            const stripped = v.replace(/-/g, "").toUpperCase();
            const pattern = rules?.isrc?.pattern ? new RegExp(rules.isrc.pattern) : /^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$/;
            if (!pattern.test(stripped)) return "ISRC format: CC-XXX-YY-NNNNN (2 letters, 3 alphanumeric, 2 digits, 5 digits)";
            return null;
        },
        track_number: (v) => {
            if (!v) return null;
            const n = Number(v);
            if (!Number.isInteger(n) || n < 1) return "Must be a positive integer";
            return null;
        },
        disc_number: (v) => {
            if (!v) return null;
            const n = Number(v);
            if (!Number.isInteger(n) || n < 1) return "Must be a positive integer";
            return null;
        }
    };

    const input = document.createElement("input");
    input.type = "text";
    input.value = currentValue;
    input.className = "inline-edit-input";
    if (field === "track_number" || field === "disc_number") {
        input.style.width = "3rem";
    }

    const errorEl = document.createElement("div");
    errorEl.className = "inline-edit-error";

    span.replaceWith(input);
    input.after(errorEl);
    input.focus();
    input.select();

    let hasError = false;

    async function commitEdit() {
        const rawValue = input.value.trim();
        errorEl.textContent = "";
        input.classList.remove("inline-edit-input--error");
        hasError = false;

        const validate = validators[field];
        const error = validate ? validate(rawValue) : null;
        if (error) {
            hasError = true;
            input.classList.add("inline-edit-input--error");
            errorEl.textContent = error;
            input.focus();
            return;
        }

        if (rawValue === currentValue) {
            input.replaceWith(span);
            errorEl.remove();
            return;
        }

        let payload;
        if (["year", "release_year", "bpm", "track_number", "disc_number"].includes(field)) {
            payload = rawValue === "" ? null : Number(rawValue);
        } else {
            payload = rawValue === "" ? null : rawValue;
        }

        input.disabled = true;
        try {
            const updated = await onCommit(payload);
            if (onSave) onSave(updated, field);
        } catch (err) {
            input.disabled = false;
            input.classList.add("inline-edit-input--error");
            errorEl.textContent = `Save failed: ${err.message}`;
            input.focus();
        }
    }

    input.addEventListener("input", () => {
        const validate = validators[field];
        if (!validate) return;
        const error = validate(input.value.trim());
        if (error) {
            hasError = true;
            input.classList.add("inline-edit-input--error");
            errorEl.textContent = error;
        } else {
            hasError = false;
            input.classList.remove("inline-edit-input--error");
            errorEl.textContent = "";
        }
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); commitEdit(); }
        if (e.key === "Escape") {
            e.stopPropagation();
            input.replaceWith(span);
            errorEl.remove();
        }
    });

    input.addEventListener("blur", () => {
        if (hasError) return;
        setTimeout(() => {
            if (document.contains(input)) commitEdit();
        }, 100);
    });
}
