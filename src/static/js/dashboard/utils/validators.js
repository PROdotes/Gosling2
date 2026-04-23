/**
 * Field validators for scalar song inputs.
 * Each validator takes (value, validationRules) and returns an error string or null.
 */

export const validators = {
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
