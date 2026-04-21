import { validators } from "../utils/validators.js";

/**
 * Activates an inline text editor on a <span> element.
 *
 * Options:
 *   field: string (media_name, year, release_year, bpm, isrc, title, etc.)
 *   validationRules: object (from state)
 *   onCommit: async (value) => { ... } returns the updated entity
 *   onSave: (updatedEntity, field) => { ... } called after successful commit
 */
export function activateInlineEdit(
    span,
    { field, validationRules, onCommit, onSave },
) {
    const currentValue = span.textContent === "-" ? "" : span.textContent;

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
        const error = validate ? validate(rawValue, validationRules) : null;
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
        if (
            [
                "year",
                "release_year",
                "bpm",
                "track_number",
                "disc_number",
            ].includes(field)
        ) {
            payload = rawValue === "" ? null : Number(rawValue);
        } else {
            payload = rawValue === "" ? null : rawValue;
        }

        input.disabled = true;
        try {
            const updated = await onCommit(payload);
            input.replaceWith(span);
            span.textContent = rawValue === "" ? "-" : rawValue;
            errorEl.remove();
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
        const error = validate(input.value.trim(), validationRules);
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
        if (e.key === "Enter") {
            e.preventDefault();
            e.stopPropagation();
            commitEdit();
        }
        if (e.key === "Escape") {
            e.stopPropagation();
            input.replaceWith(span);
            errorEl.remove();
        }
    });

    input.addEventListener("blur", () => {
        if (hasError) return;
        requestAnimationFrame(() => {
            if (document.contains(input)) commitEdit();
        });
    });
}
