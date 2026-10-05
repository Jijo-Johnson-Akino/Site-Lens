import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { isThemePreference, nextTheme, normalizeTheme, resolveTheme } from "./theme";

describe("theme helpers", () => {
  it("stores only explicit light or dark", () => {
    assert.equal(isThemePreference("light"), true);
    assert.equal(isThemePreference("dark"), true);
    assert.equal(isThemePreference("system"), false);
    assert.equal(normalizeTheme("light"), "light");
    assert.equal(normalizeTheme("system"), "light");
    assert.equal(normalizeTheme("dark"), "dark");
    assert.equal(normalizeTheme(null), "light");
  });

  it("cycles light ↔ dark", () => {
    assert.equal(nextTheme("light"), "dark");
    assert.equal(nextTheme("dark"), "light");
  });

  it("does not follow the OS for either preference", () => {
    assert.equal(resolveTheme("light"), "light");
    assert.equal(resolveTheme("dark"), "dark");
  });
});
