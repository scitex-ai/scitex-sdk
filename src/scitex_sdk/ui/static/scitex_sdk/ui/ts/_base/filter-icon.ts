/** Decorative filter glyph shared by SDK filter surfaces. */
export function createFilterIcon(className: string): SVGSVGElement {
  const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icon.classList.add(className);
  icon.setAttribute("viewBox", "0 0 24 24");
  icon.setAttribute("aria-hidden", "true");
  icon.setAttribute("focusable", "false");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M3 4h18l-7 8v7l-4 2v-9z");
  icon.append(path);
  return icon;
}
