/**
 * Type definitions for the ConfirmModal component.
 */

export interface ConfirmModalOptions {
  /** Modal title (default: "Confirm") */
  title?: string;
  /** Main message */
  message: string;
  /** Confirm button text (default: "Confirm") */
  confirmText?: string;
  /** Cancel button text (default: "Cancel") */
  cancelText?: string;
  /** Called when confirmed */
  onConfirm?: () => void;
  /** Called when cancelled */
  onCancel?: () => void;
}
