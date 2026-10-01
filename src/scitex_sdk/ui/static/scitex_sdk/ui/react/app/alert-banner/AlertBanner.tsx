/**
 * AlertBanner — dismissible alert / error banner.
 *
 * Controlled component (like ConfirmModal): the host app renders it from its
 * own state to surface failures to the user (e.g. "failed to render canvas")
 * instead of failing silently. Sits fixed at the top, above modals.
 */

import React, { useEffect, useCallback } from "react";

const CLS = "stx-app-alert-banner";

export type AlertBannerType = "error" | "warning" | "info" | "success";

export interface AlertBannerProps {
  /** Whether the banner is visible. */
  open: boolean;
  /** The message to show. */
  message: string;
  /** Severity — drives colour + icon. Defaults to "error". */
  type?: AlertBannerType;
  /** Optional bold title shown above the message. */
  title?: string;
  /** Called when the user dismisses (close button / Escape) or auto-close fires.
   *  When omitted, no close button is shown and the banner is not dismissible. */
  onDismiss?: () => void;
  /** Auto-dismiss after N milliseconds. Omit to keep until dismissed. */
  autoCloseMs?: number;
}

const ICONS: Record<AlertBannerType, string> = {
  error: "⚠", // ⚠
  warning: "⚠", // ⚠
  info: "ℹ", // ℹ
  success: "✓", // ✓
};

export const AlertBanner: React.FC<AlertBannerProps> = ({
  open,
  message,
  type = "error",
  title,
  onDismiss,
  autoCloseMs,
}) => {
  // Auto-dismiss timer; re-armed when the message changes so a new alert resets
  // the countdown rather than inheriting the previous one's remaining time.
  useEffect(() => {
    if (!open || !autoCloseMs || !onDismiss) return undefined;
    const timer = setTimeout(onDismiss, autoCloseMs);
    return () => clearTimeout(timer);
  }, [open, autoCloseMs, onDismiss, message]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") onDismiss?.();
    },
    [onDismiss],
  );

  if (!open || !message) return null;

  return (
    <div
      className={`${CLS} ${CLS}--${type}`}
      role="alert"
      aria-live="assertive"
      tabIndex={-1}
      onKeyDown={handleKeyDown}
    >
      <span className={`${CLS}__icon`} aria-hidden="true">
        {ICONS[type]}
      </span>
      <div className={`${CLS}__body`}>
        {title ? <span className={`${CLS}__title`}>{title}</span> : null}
        <span className={`${CLS}__message`}>{message}</span>
      </div>
      {onDismiss ? (
        <button
          className={`${CLS}__close`}
          aria-label="Dismiss"
          onClick={onDismiss}
        >
          &times;
        </button>
      ) : null}
    </div>
  );
};
