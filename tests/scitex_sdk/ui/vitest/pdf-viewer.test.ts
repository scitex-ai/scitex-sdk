/**
 * PdfViewer fit-width geometry: the page is sized to the container's CONTENT
 * box, never to `clientWidth`. `npx vitest run`
 *
 * THE DEFECT THIS PINS, measured by scitex-writer at 390x844 (chromium, their
 * PR #396 / v2.43.3 — the first app to render this primitive on a phone): with
 * `.pdf-viewer-host { padding: 16px }`, fit-width produced a 382px canvas at
 * x=16, i.e. a right edge of 398 on a 390px viewport and a container
 * scrollWidth of 414 against a clientWidth of 382. Writer removed the phone
 * gutter to work around it; the fix belongs here, where the geometry is
 * computed.
 *
 * jsdom has no layout engine (`clientWidth` is 0 and there is no canvas
 * geometry), so this file tests the ARITHMETIC that was wrong, which is why the
 * helper is a pure function. The end-to-end 390px measurement is recorded on
 * the card from a real browser.
 */

import { describe, expect, it } from "vitest";

import { contentBoxWidth } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/pdf-viewer";

describe("contentBoxWidth — the fit-width input", () => {
  it("subtracts BOTH horizontal paddings from clientWidth", () => {
    // Arrange
    const clientWidth = 390;
    const padding = 16;
    // Act
    const width = contentBoxWidth(clientWidth, padding, padding);
    // Assert
    expect(width).toBe(358);
  });

  it("leaves a padding-free container unchanged", () => {
    // Arrange
    const clientWidth = 390;
    // Act
    const width = contentBoxWidth(clientWidth, 0, 0);
    // Assert
    expect(width).toBe(390);
  });

  it("handles an asymmetric gutter", () => {
    // Arrange
    const clientWidth = 390;
    // Act
    const width = contentBoxWidth(clientWidth, 20, 4);
    // Assert
    expect(width).toBe(366);
  });

  it("never returns a negative width when the padding exceeds the box", () => {
    // Arrange
    const clientWidth = 20;
    // Act
    const width = contentBoxWidth(clientWidth, 16, 16);
    // Assert
    expect(width).toBe(0);
  });

  it("REFUSES TO BE THE PADDING-INCLUSIVE VALUE — the arm that can fail", () => {
    // Arrange — this is the exact arithmetic the defect produced: sizing to
    // clientWidth, which is why the canvas overflowed by 2x padding.
    const clientWidth = 390;
    const paddingInclusive = clientWidth;
    // Act
    const width = contentBoxWidth(clientWidth, 16, 16);
    // Assert
    expect(width).not.toBe(paddingInclusive);
  });

  it("shrinks monotonically as the gutter grows, so the direction cannot invert", () => {
    // Arrange
    const clientWidth = 390;
    // Act
    const narrow = contentBoxWidth(clientWidth, 24, 24);
    const wide = contentBoxWidth(clientWidth, 8, 8);
    // Assert
    expect(narrow < wide).toBe(true);
  });
});
