/**
 * Dropdown — React context menu.
 * Mirrors: ts/app/dropdown/_Dropdown.ts
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
import type { BaseProps } from "../../_base/types";

const CLS = "stx-app-dropdown";

export interface DropdownItem {
  id: string;
  label: string;
  icon?: string;
  disabled?: boolean;
  separator?: boolean;
  onClick?: () => void;
}

export interface DropdownProps extends BaseProps {
  /** Menu items */
  items: DropdownItem[];
  /** Trigger element */
  children: React.ReactNode;
  /** Alignment (default: "left") */
  align?: "left" | "right";
  /** Called when item selected */
  onSelect?: (item: DropdownItem) => void;
}

export const Dropdown: React.FC<DropdownProps> = ({
  items,
  children,
  align = "left",
  onSelect,
  className,
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const handleOutsideClick = useCallback((e: MouseEvent) => {
    if (ref.current && !ref.current.contains(e.target as Node)) {
      setOpen(false);
    }
  }, []);

  useEffect(() => {
    if (open) document.addEventListener("click", handleOutsideClick);
    return () => document.removeEventListener("click", handleOutsideClick);
  }, [open, handleOutsideClick]);

  return (
    <div
      ref={ref}
      className={className}
      style={{ position: "relative", display: "inline-block" }}
    >
      <div onClick={() => setOpen(!open)}>{children}</div>
      {open && (
        <ul
          className={`${CLS}__menu`}
          style={{
            position: "absolute",
            top: "100%",
            [align === "right" ? "right" : "left"]: 0,
            zIndex: 100,
          }}
        >
          {items.map((item) =>
            item.separator ? (
              <li key={item.id} className={`${CLS}__separator`} />
            ) : (
              <li
                key={item.id}
                className={`${CLS}__item${item.disabled ? ` ${CLS}__item--disabled` : ""}`}
                onClick={() => {
                  if (item.disabled) return;
                  setOpen(false);
                  item.onClick?.();
                  onSelect?.(item);
                }}
              >
                {item.icon && <i className={item.icon} />}
                <span>{item.label}</span>
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  );
};
