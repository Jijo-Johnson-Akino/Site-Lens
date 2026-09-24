import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { isThemePreference, nextTheme, resolveTheme } from "./theme";

describe("theme helpers", () => {
  it("accepts stored preferences", () => {
    assert.equal(isThemePreference("system"), true);
    assert.equal(isThemePreference("light"), true);
    assert.equal(isThemePreference("dark"), true);
    assert.equal(isThemePreference("auto"), false);
    assert.equal(isThemePreference(null), false);
  });

  it("cycles system → light → dark → system", () => {
    assert.equal(nextTheme("system"), "light");
    assert.equal(nextTheme("light"), "dark");
    assert.equal(nextTheme("dark"), "system");
  });

  it("resolves explicit light and dark without the OS setting", () => {
    assert.equal(resolveTheme("light"), "light");
    assert.equal(resolveTheme("dark"), "dark");
  });
});
