import { afterEach, expect, test } from "vitest";
import React from "react";
import { act } from "react";
import { mountReactApp, unmountReactApp } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/react/app/bridge/GenericMountPoint";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { act(() => unmountReactApp()); document.body.replaceChildren(); });

test("outgoing container cleanup preserves the next app's root", () => {
  const first = document.createElement("div");
  const second = document.createElement("div");
  document.body.append(first, second);
  act(() => mountReactApp(first, React.createElement("p", null, "First app")));
  expect(first.textContent).toBe("First app");
  act(() => mountReactApp(second, React.createElement("p", null, "Next app")));
  expect(first.textContent).toBe("");
  act(() => unmountReactApp(first));
  expect(second.textContent).toBe("Next app");
  act(() => unmountReactApp(second));
  expect(second.textContent).toBe("");
});

test("no-argument unmount retains the public cleanup contract", () => {
  const container = document.createElement("div");
  act(() => mountReactApp(container, React.createElement("p", null, "Mounted")));
  act(() => unmountReactApp());
  expect(container.textContent).toBe("");
});
