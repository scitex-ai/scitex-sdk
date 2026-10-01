/**
 * ConfirmModal — React confirmation dialog.
 * Mirrors: ts/app/confirm-modal/_showConfirm.ts
 */

import React, { useEffect, useRef, useCallback } from "react";

const CLS = "stx-app-confirm-modal";

export interface ConfirmModalProps {
  /** Whether the modal is visible */
  open: boolean;
  /** Modal title */
  title?: string;
  /** Main message */
  message: string;
  /** Confirm button text */
  confirmText?: string;
  /** Cancel button text */
  cancelText?: string;
  /** Called on confirm */
  onConfirm?: () => void;
  /** Called on cancel or close */
  onCancel?: () => void;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  open,
  title = "Confirm",
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  onConfirm,
  onCancel,
}) => {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) confirmRef.current?.focus();
  }, [open]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") onCancel?.();
    },
    [onCancel],
  );

  if (!open) return null;

  return (
    <div
      className={`${CLS}__overlay ${CLS}__overlay--visible`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel?.();
      }}
      onKeyDown={handleKeyDown}
    >
      <div className={`${CLS}__content`}>
        <div className={`${CLS}__header`}>
          <h3>{title}</h3>
          <button
            className={`${CLS}__close`}
            aria-label="Close"
            onClick={onCancel}
          >
            &times;
          </button>
        </div>
        <div className={`${CLS}__body`}>
          <p>{message}</p>
        </div>
        <div className={`${CLS}__footer`}>
          <button
            className={`${CLS}__btn ${CLS}__btn--cancel`}
            onClick={onCancel}
          >
            {cancelText}
          </button>
          <button
            ref={confirmRef}
            className={`${CLS}__btn ${CLS}__btn--confirm`}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};
