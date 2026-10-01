/**
 * Tooltip — React tooltip wrapper component.
 * Mirrors: ts/app/tooltip/_Tooltip.ts
 */

import React, { useState, useRef, useCallback } from "react";
import type { BaseProps } from "../../_base/types";

const CLS = "stx-app-tooltip";

export interface TooltipProps extends BaseProps {
  /** Tooltip text */
  text: string;
  /** Position (default: "bottom") */
  position?: "top" | "bottom" | "left" | "right";
  /** Delay in ms (default: 300) */
  delay?: number;
  /** Content to wrap */
  children: React.ReactNode;
}

export const Tooltip: React.FC<TooltipProps> = ({
  text,
  position = "bottom",
  delay = 300,
  children,
  className,
}) => {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    timeoutRef.current = setTimeout(() => setVisible(true), delay);
  }, [delay]);

  const hide = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  }, []);

  return (
    <span
      className={className}
      style={{ position: "relative", display: "inline-block" }}
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      {children}
      {visible && (
        <span
          className={CLS}
          data-position={position}
          style={{
            display: "block",
            opacity: 1,
            position: "absolute",
            whiteSpace: "nowrap",
            zIndex: 10000,
            ...(position === "bottom" && {
              top: "100%",
              left: "50%",
              transform: "translateX(-50%)",
              marginTop: 8,
            }),
            ...(position === "top" && {
              bottom: "100%",
              left: "50%",
              transform: "translateX(-50%)",
              marginBottom: 8,
            }),
            ...(position === "right" && {
              left: "100%",
              top: "50%",
              transform: "translateY(-50%)",
              marginLeft: 8,
            }),
            ...(position === "left" && {
              right: "100%",
              top: "50%",
              transform: "translateY(-50%)",
              marginRight: 8,
            }),
          }}
        >
          {text}
        </span>
      )}
    </span>
  );
};
