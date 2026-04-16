import fs from "fs";
import path from "path";
import { describe, expect, it } from "vitest";

describe("Dashboard Template Hygiene", () => {
    // We use __dirname which in Vitest/Node points to the test file location
    const htmlPath = path.resolve(
        __dirname,
        "../../../src/templates/dashboard.html",
    );
    const html = fs.readFileSync(htmlPath, "utf-8");

    it("every button tag in dashboard.html has an explicit type attribute", () => {
        // Find all buttons, then filter for those missing type="
        const buttonTags = html.match(/<button[^>]*>/g) || [];
        const missingType = buttonTags.filter((tag) => !tag.includes('type="'));

        expect(
            missingType,
            `Buttons missing 'type' attribute:\n${missingType.join("\n")}`,
        ).toHaveLength(0);
    });

    it("every svg tag in dashboard.html has an aria-hidden or a child title", () => {
        // Biome requires SVGs to have a title for a11y unless hidden
        const svgRegions = html.match(/<svg[\s\S]*?<\/svg>/g) || [];
        const missingA11y = svgRegions.filter((region) => {
            const hasHidden = region.includes('aria-hidden="true"');
            const hasTitle = region.includes("<title>");
            return !hasHidden && !hasTitle;
        });

        expect(
            missingA11y,
            `SVGs missing accessibility markers (aria-hidden or <title>):\n${missingA11y.join("\n")}`,
        ).toHaveLength(0);
    });
});
