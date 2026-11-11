/** The shared helper can be imported and called without a browser document. */
import assert from "node:assert/strict";
import { csrfToken } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/_base/csrf.ts";

assert.equal(typeof document, "undefined");
assert.equal(csrfToken(), "");
console.log("csrfToken: document-free import and lookup passed");
