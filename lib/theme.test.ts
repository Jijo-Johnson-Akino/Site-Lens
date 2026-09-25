import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { isThemePreference, nextTheme, normalizeTheme, resolveTheme } from "./theme";

describe("theme helpers", () => {
  it("treats light as system and only stores system or dark", () => {
    assert.equal(isThemePreference("system"), true);
    assert.equal(isThemePreference("dark"), true);
    assert.equal(isThemePreference("light"), false);
    assert.equal(normalizeTheme("light"), "system");
    assert.equal(normalizeTheme("system"), "system");
    assert.equal(normalizeTheme("dark"), "dark");
    assert.equal(normalizeTheme(null), "system");
  });

  it("cycles light/system ↔ dark", () => {
    assert.equal(nextTheme("system"), "dark");
    assert.equal(nextTheme("dark"), "system");
  });

  it("resolves dark without the OS setting", () => {
    assert.equal(resolveTheme("dark"), "dark");
  });
});
