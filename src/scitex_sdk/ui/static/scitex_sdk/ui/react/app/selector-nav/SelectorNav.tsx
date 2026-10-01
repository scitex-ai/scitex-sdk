/**
 * SelectorNav — shared vertical icon+label navigation strip.
 *
 * Fixed-width nav with optional pass-through resizer on the right border.
 * The resizer doesn't change the nav width — it propagates force to
 * adjacent panels.
 *
 * Ported from scitex-cloud's selector-nav component.
 * Used by: App Selector (frame-level), Writer Mode Selector, PlotTypeNav, etc.
 *
 * Usage:
 *   <SelectorNav
 *     items={[{ id: "line", icon: "fas fa-chart-line", label: "Line" }]}
 *     activeId={selected}
 *     onSelect={(id) => setSelected(id)}
 *     indicator="left"
 *   />
 */

import React from "react";

export interface SelectorNavItem {
  id: string;
  icon: string;
  label: string;
  disabled?: boolean;
  badge?: string;
}

export interface SelectorNavProps {
  items: SelectorNavItem[];
  activeId: string | null;
  onSelect: (id: string) => void;
  /** Active indicator position: "left", "right", or none */
  indicator?: "left" | "right";
  /** Additional CSS class */
  className?: string;
  style?: React.CSSProperties;
  /** Footer content (e.g., count badge) */
  footer?: React.ReactNode;
}

export const SelectorNav: React.FC<SelectorNavProps> = ({
  items,
  activeId,
  onSelect,
  indicator,
  className,
  style,
  footer,
}) => {
  return (
    <nav
      className={`stx-app-selector-nav${className ? ` ${className}` : ""}`}
      data-indicator={indicator}
      style={style}
    >
      <div className="stx-app-selector-nav__items">
        {items.map((item) => (
          <button
            key={item.id}
            className={`stx-app-selector-nav__item${item.id === activeId ? " active" : ""}${item.disabled ? " disabled" : ""}`}
            onClick={() => !item.disabled && onSelect(item.id)}
            disabled={item.disabled}
            type="button"
          >
            <i className={item.icon} />
            <span className="stx-app-selector-nav__label">{item.label}</span>
          </button>
        ))}
      </div>
      {footer && <div className="stx-app-selector-nav__footer">{footer}</div>}
    </nav>
  );
};
