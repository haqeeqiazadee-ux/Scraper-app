interface EmptyStateProps {
  /** Emoji or short string displayed as the central icon */
  icon: string;
  /** Bold heading below the icon */
  title: string;
  /** Descriptive text below the heading */
  description: string;
  /** Label for the optional call-to-action button */
  actionLabel?: string;
  /** Handler called when the action button is clicked */
  onAction?: () => void;
}

/**
 * Centered empty-state card used when a list or data view has no content.
 * Optionally shows a call-to-action button.
 */
export default function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon" role="img" aria-label={title}>
        {icon}
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {actionLabel && onAction && (
        <div className="empty-state-action">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={onAction}
          >
            {actionLabel}
          </button>
        </div>
      )}
    </div>
  );
}
