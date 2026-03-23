interface ConfirmDialogProps {
  /** Controls whether the dialog is visible */
  open: boolean;
  /** Dialog heading */
  title: string;
  /** Body message explaining what will happen */
  message: string;
  /** Label for the confirm button */
  confirmLabel: string;
  /** Visual variant — danger shows red confirm button, warning shows amber */
  variant: "danger" | "warning";
  /** Called when the user confirms the action */
  onConfirm: () => void;
  /** Called when the user cancels or clicks outside */
  onCancel: () => void;
}

const ICONS: Record<"danger" | "warning", string> = {
  danger: "🗑️",
  warning: "⚠️",
};

/**
 * Accessible confirmation modal with an overlay backdrop.
 * Pressing Escape triggers onCancel; clicking the overlay also cancels.
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  variant,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onCancel();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Escape") onCancel();
  }

  return (
    <div
      className="confirm-dialog-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-message"
      onClick={handleOverlayClick}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      <div className="confirm-dialog">
        <div className={`confirm-dialog-icon confirm-dialog-icon--${variant}`}>
          {ICONS[variant]}
        </div>

        <h3 id="confirm-dialog-title">{title}</h3>
        <p id="confirm-dialog-message">{message}</p>

        <div className="confirm-dialog-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className={`btn ${variant === "danger" ? "btn-danger" : "btn-secondary"} btn-sm`}
            onClick={onConfirm}
            autoFocus
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
