/** DOM-first token lookup supports protected and standalone cookie policies. */
import { afterEach, expect, it } from "vitest";
import { csrfToken } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/_base/csrf";

afterEach(() => {
  document.body.innerHTML = "";
  document.cookie = "csrftoken=; Max-Age=0; Path=/";
});

it.each([
  ['<input name="csrfmiddlewaretoken" value="rendered-token">', "", "rendered-token"],
  ['<input name="csrfmiddlewaretoken" value="rendered-token">', "old-token", "rendered-token"],
  ['<input name="csrfmiddlewaretoken" value="">', "visible%2Btoken", "visible+token"],
  ["", "", ""],
])("reads rendered input %s with cookie %s", (html, cookie, expected) => {
  // Arrange
  document.body.innerHTML = html;
  if (cookie) document.cookie = `csrftoken=${cookie}; Path=/`;
  // Act
  const token = csrfToken();
  // Assert
  expect(token).toBe(expected);
});
