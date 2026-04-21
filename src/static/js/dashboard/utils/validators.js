/**
 * Field validators for scalar song inputs.
 * Each validator takes (value, validationRules) and returns an error string or null.
 */

export const validators = {
    media_name: (v) => (v ? null : "Title cannot be empty"),
    title: (v) => (v ? null : "Title cannot be empty"),

    year: (v, rules) => {
        if (!v) return null;
        const n = Number(v);
        const min = rules?.year?.min ?? 1860;
        const max = rules?.year?.max ?? new Date().getFullYear() + 1;
        if (!Number.isInteger(n) || n < min || n > max)
            return `Year must be between ${min}–${max}`;
        return null;
    },

    release_year: (v) => {
        if (!v) return null;
        const n = Number(v);
        const max = new Date().getFullYear() + 1;
        if (!Number.isInteger(n) || n < 1860 || n > max)
            return `Year must be between 1860–${max}`;
        return null;
    },

    bpm: (v, rules) => {
        if (!v) return null;
        const n = Number(v);
        const min = rules?.bpm?.min ?? 1;
        const max = rules?.bpm?.max ?? 300;
        if (!Number.isInteger(n) || n < min || n > max)
            return `BPM must be between ${min}–${max}`;
        return null;
    },

    isrc: (v, rules) => {
        if (!v) return null;
        const stripped = v.replace(/-/g, "").toUpperCase();
        const pattern = rules?.isrc?.pattern
            ? new RegExp(rules.isrc.pattern)
            : /^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$/;
        if (!pattern.test(stripped))
            return "ISRC must be 12 characters (e.g., US-ABC-12-12345)";
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
    },
};
