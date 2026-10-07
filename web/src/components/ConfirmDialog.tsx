import { useId, type ReactNode } from "react";
import { cx } from "../lib/cx";
import { Button } from "./Button";
import styles from "./ConfirmDialog.module.css";
import { useModal } from "./useModal";

export interface SummaryRow {
  label: string;
  value: ReactNode;
}

interface ConfirmDialogProps {
  /** A one-line question: "Close January 2025?" */
  title: string;
  /** The figures that matter to the decision, as label/value rows. */
  rows?: SummaryRow[];
  /** What becomes locked or lost — shown as the warning note. */
  consequence: string;
  /** Named after the action ("Close month"), never "OK" or "Yes". */
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
  /** Why the action can't go ahead; replaces the note and disables confirm. */
  blocker?: string | null;
  error?: string | null;
}

/**
 * Asks before the two actions that can't be taken back: closing a month and
 * deleting a profile. Everything else just happens and offers Undo.
 */
export function ConfirmDialog({
  title,
  rows = [],
  consequence,
  confirmLabel,
  onConfirm,
  onCancel,
  busy = false,
  blocker,
  error,
}: ConfirmDialogProps) {
  const modal = useModal(onCancel);
  const titleId = useId();

  return (
    <dialog
      {...modal}
      className={cx("glass-strong", styles.dialog)}
      role="alertdialog"
      aria-labelledby={titleId}
    >
      <div className={styles.content}>
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        {rows.length > 0 && (
          <dl className={styles.rows}>
            {rows.map((row) => (
              <div key={row.label} className={styles.row}>
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className={styles.note}>
          <span aria-hidden="true">⚠ </span>
          {blocker ?? consequence}
        </p>
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        <div className={styles.actions}>
          {/* Focus starts on the safe choice. */}
          <Button onClick={onCancel} data-autofocus>
            Cancel
          </Button>
          <Button variant="primary" onClick={onConfirm} disabled={busy || Boolean(blocker)}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>
  );
}
