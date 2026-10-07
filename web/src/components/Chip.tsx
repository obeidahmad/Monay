import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import styles from "./Chip.module.css";

interface ChipProps {
  children: ReactNode;
  /** The chip is the current choice / an active filter. */
  selected?: boolean;
  /** A section accent shown as a leading dot. */
  accent?: string;
  /** An active filter shows a × and clears on click. */
  removable?: boolean;
  onClick: () => void;
}

/** A small pill you can press: a quick-pick in a form, or a filter above a list. */
export function Chip({
  children,
  selected = false,
  accent,
  removable = false,
  onClick,
}: ChipProps) {
  return (
    <button
      type="button"
      className={cx(styles.chip, selected && styles.selected)}
      aria-pressed={selected}
      onClick={onClick}
    >
      {accent && <i className={styles.dot} style={{ background: accent }} />}
      {children}
      {removable && selected && (
        <span className={styles.remove} aria-hidden="true">
          ×
        </span>
      )}
    </button>
  );
}

/** A wrapping row of chips. */
export function ChipRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.row} role="group" aria-label={label}>
      {children}
    </div>
  );
}
