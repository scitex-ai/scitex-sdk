import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";
import { DataTable } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/react/app/data-table/DataTable";
(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

it("column and row header selections highlight every corresponding cell and clear on cell selection", () => {
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(createElement(DataTable, {data:{columns:["x","y"],rows:[{x:1,y:2},{x:3,y:4}]},readOnly:true})));
  const selected = () => [...host.querySelectorAll("td.stx-app-data-table__cell--selected")]
    .map(cell => [cell.getAttribute("data-row"),cell.getAttribute("data-col")]);
  const down = (element: Element) => act(() => element.dispatchEvent(new MouseEvent("mousedown",{bubbles:true,button:0})));
  const up = () => act(() => document.dispatchEvent(new MouseEvent("mouseup",{bubbles:true})));
  down(host.querySelector("th[data-col='1']")!); up();
  expect(selected()).toEqual([["0","1"],["1","1"]]);
  expect(host.querySelectorAll("th.stx-app-data-table__header-cell--highlighted")).toHaveLength(1);
  down(host.querySelector("tbody .stx-app-data-table__row-num")!); up();
  expect(selected()).toEqual([["0","0"],["0","1"]]);
  expect(host.querySelectorAll(".stx-app-data-table__row-num--highlighted")).toHaveLength(1);
  down(host.querySelector("td[data-row='1'][data-col='0']")!); up();
  expect(selected()).toEqual([["1","0"]]);
  act(() => root.unmount()); host.remove();
});
