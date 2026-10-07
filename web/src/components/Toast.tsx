import { cx } from "../lib/cx";
import { Button } from "./Button";
import styles from "./Toast.module.css";

export type ToastKind = "ok" | "warn" | "info";

interface ToastProps {
  kind: ToastKind;
  message: string;
  /** Offers an Undo button; destructive actions use this instead of asking first. */
  onUndo?: () => void;
  onDismiss: () => void;
}

const GLYPH: Record<ToastKind, string> = { ok: "✓", warn: "⚠", info: "•" };

/**
 * One short message after an action — what the terminal app's feedback line
 * used to say. Bottom-centre on desktop, above the tab bar on a phone, one at
 * a time. Form errors never come here: they belong under their field.
 */
export function Toast({ kind, message, onUndo, onDismiss }: ToastProps) {
  return (
    <div className={styles.viewport}>
      <div
        className={cx("glass-strong", styles.toast)}
        role={kind === "warn" ? "alert" : "status"}
        onClick={onDismiss}
      >
        <span className={cx(styles.glyph, styles[kind])} aria-hidden="true">
          {GLYPH[kind]}
        </span>
        <span className={styles.message}>{message}</span>
        {onUndo && (
          <Button
            variant="ghost"
            onClick={(event) => {
              event.stopPropagation();
              onUndo();
            }}
          >
            Undo
          </Button>
        )}
      </div>
    </div>
  );
}
