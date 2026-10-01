/** ts/_base/gettext.ts — Django-compatible client translations.
 *
 *   node --experimental-strip-types tests/scitex_sdk/ui/ts/gettext.render.test.ts
 */

// @ts-nocheck — Node-executed script with a minimal document stub.
import assert from "node:assert/strict";
import test from "node:test";

import {
  evaluatePluralExpression,
  gettext,
  installCatalog,
  interpolate,
  loadCatalogsFromDocument,
  ngettext,
  npgettext,
  pgettext,
  resetCatalog,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/_base/gettext.ts";

const JAPANESE = {
  language: "ja",
  plural: "0",
  catalog: {
    Save: "保存",
    "%s figure": ["%s 個の図"],
    "verb\x04Export": "書き出す",
  },
};

function withCatalog(payload) {
  resetCatalog();
  if (payload) installCatalog(payload);
}

test("gettext passes English through when no catalog is loaded", () => {
  // Arrange
  withCatalog({ catalog: {} });
  // Act
  const text = gettext("Save");
  // Assert
  assert.equal(text, "Save");
});

test("gettext returns the Japanese translation from the catalog", () => {
  // Arrange
  withCatalog(JAPANESE);
  // Act
  const text = gettext("Save");
  // Assert
  assert.equal(text, "保存");
});

test("gettext passes an unknown msgid through", () => {
  // Arrange
  withCatalog(JAPANESE);
  // Act
  const text = gettext("Open");
  // Assert
  assert.equal(text, "Open");
});

test("ngettext picks the English plural without a catalog", () => {
  // Arrange
  withCatalog({ catalog: {} });
  // Act
  const text = ngettext("%s figure", "%s figures", 3);
  // Assert
  assert.equal(text, "%s figures");
});

test("ngettext uses the Japanese single plural form", () => {
  // Arrange
  withCatalog(JAPANESE);
  // Act
  const text = ngettext("%s figure", "%s figures", 3);
  // Assert
  assert.equal(text, "%s 個の図");
});

test("pgettext resolves a context-qualified message", () => {
  // Arrange
  withCatalog(JAPANESE);
  // Act
  const text = pgettext("verb", "Export");
  // Assert
  assert.equal(text, "書き出す");
});

test("pgettext passes the bare msgid through when the context is missing", () => {
  // Arrange
  withCatalog(JAPANESE);
  // Act
  const text = pgettext("noun", "Export");
  // Assert
  assert.equal(text, "Export");
});

test("npgettext passes the English plural through when the context is missing", () => {
  // Arrange
  withCatalog(JAPANESE);
  // Act
  const text = npgettext("noun", "%s axis", "%s axes", 2);
  // Assert
  assert.equal(text, "%s axes");
});

test("interpolate fills positional %s placeholders", () => {
  // Arrange
  const format = "%s of %s";
  // Act
  const text = interpolate(format, [2, 5]);
  // Assert
  assert.equal(text, "2 of 5");
});

test("interpolate fills named %(name)s placeholders", () => {
  // Arrange
  const format = "%(count)s 個の図";
  // Act
  const text = interpolate(format, { count: 4 }, true);
  // Assert
  assert.equal(text, "4 個の図");
});

test("evaluatePluralExpression handles the English rule", () => {
  // Arrange
  const expression = "(n != 1)";
  // Act
  const index = evaluatePluralExpression(expression, 1);
  // Assert
  assert.equal(index, 0);
});

test("evaluatePluralExpression handles a three-form ternary rule", () => {
  // Arrange
  const russian =
    "(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)";
  // Act
  const index = evaluatePluralExpression(russian, 22);
  // Assert
  assert.equal(index, 1);
});

test("loadCatalogsFromDocument installs every json_script catalog on the page", () => {
  // Arrange
  resetCatalog();
  const doc = {
    querySelectorAll: () => [
      { textContent: JSON.stringify({ catalog: { Save: "保存" } }) },
      { textContent: JSON.stringify({ catalog: { Gallery: "ギャラリー" } }) },
    ],
  };
  loadCatalogsFromDocument(doc);
  // Act
  const text = gettext("Gallery");
  // Assert
  assert.equal(text, "ギャラリー");
});
