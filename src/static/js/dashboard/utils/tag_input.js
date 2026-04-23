/**
 * Parses a raw tag input string into {name, category} using validation rules.
 *
 * @param {string} raw - e.g. "French::Language" or "Jazz"
 * @param {object} rules - state.validationRules.tags
 * @returns {{name: string, category: string}}
 */
export function parseTagInput(raw, rules = {}) {
    const delimiter = rules.delimiter;
    const defaultCategory = rules.default_category || "Genre";
    const format = rules.input_format || "tag:category";
    const nameFirst = format.toLowerCase().startsWith("tag");

    if (!raw.includes(delimiter)) {
        return { name: raw.trim(), category: defaultCategory };
    }

    const idx = raw.indexOf(delimiter);
    const a = raw.slice(0, idx).trim();
    const b = raw.slice(idx + delimiter.length).trim();
    const name = nameFirst ? a : b;
    const category = nameFirst ? b : a;
    return { name, category };
}
