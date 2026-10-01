/** Fuzzy search and navigation URL of the SDK project picker.
 *
 *   node --experimental-strip-types tests/scitex_sdk/ui/ts/project-picker.fuzzy.test.ts
 */

// @ts-nocheck — Node-executed script over the compiled bundle, excluded from tsc.
import assert from "node:assert/strict";

import {
  fuzzyFilter,
  fuzzyScore,
  projectNavigationUrl,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/js/app/project-selector.js";

let passed = 0;
function ok(name, fn) {
  fn();
  passed++;
  console.log("  ok - " + name);
}

const NAMES = ["dotfiles", "neurovista-writer", "writer", "figures-2024"];

ok("a non-subsequence does not match", () => {
  // Arrange
  const query = "xyz";
  // Act
  const score = fuzzyScore(query, "writer");
  // Assert
  assert.equal(score, null);
});

ok("letters in order but apart still match", () => {
  // Arrange
  const query = "nvw";
  // Act
  const matches = fuzzyFilter(NAMES, query, (n) => n);
  // Assert
  assert.deepEqual(matches, ["neurovista-writer"]);
});

ok("the exact short name ranks first", () => {
  // Arrange
  const query = "writer";
  // Act
  const matches = fuzzyFilter(NAMES, query, (n) => n);
  // Assert
  assert.equal(matches[0], "writer");
});

ok("an empty query keeps the provider order", () => {
  // Arrange
  const query = "  ";
  // Act
  const matches = fuzzyFilter(NAMES, query, (n) => n);
  // Assert
  assert.deepEqual(matches, NAMES);
});

ok("the navigation URL carries the encoded project id", () => {
  // Arrange
  const template = "?project={id}";
  // Act
  const url = projectNavigationUrl(template, "alice/paper one");
  // Assert
  assert.equal(url, "?project=alice%2Fpaper%20one");
});

console.log("\n" + passed + " assertion-groups passed");
