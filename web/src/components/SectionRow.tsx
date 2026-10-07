import { useId, type ReactNode } from "react";
import { cx } from "../lib/cx";
import { isNegative } from "../lib/money";
import { Amount } from "./Amount";
import styles from "./SectionRow.module.css";

interface SectionListProps {
  children: ReactNode;
}

/**
 * The accordion's frame: one glass widget on desktop with a column header; on
 * a phone the frame disappears and each row becomes its own glass card.
 */
export function SectionList({ children }: SectionListProps) {
  return (
    <div className={cx("glass", styles.list)}>
      <div className={styles.head} aria-hidden="true">
        <span className="label">sections</span>
        <span className="label num">avail</span>
        <span className="label num">rest</span>
        <span className="label">routing</span>
      </div>
      {children}
    </div>
  );
}

interface SectionRowProps {
  /** The row's one accent: its bar and its name, nowhere else. */
  accent: string;
  name: string;
  /** Kind and share, e.g. "post · 50%". The income row has none. */
  share?: string;
  avail: string;
  /** REST; omitted for the income row. */
  rest?: string;
  /** Where REST goes at close, e.g. "→ income". */
  routing?: string;
  open: boolean;
  onToggle: () => void;
  /** The trailing `⋯` menu. */
  menu?: ReactNode;
  /** What opens in place beneath the row. */
  children?: ReactNode;
}

/**
 * One accordion row — a section, or the income row. The whole row is the
 * target and expands in place; any number can be open at once.
 */
export function SectionRow({
  accent,
  name,
  share,
  avail,
  rest,
  routing,
  open,
  onToggle,
  menu,
  children,
}: SectionRowProps) {
  const bodyId = useId();
  const negative = rest !== undefined && isNegative(rest);

  return (
    <div className={styles.item}>
      <div className={styles.row}>
        <button
          type="button"
          className={styles.main}
          aria-expanded={open}
          aria-controls={bodyId}
          onClick={onToggle}
        >
          <i className={styles.bar} style={{ background: accent }} />
          <span className={styles.name}>
            <span className={styles.title} style={{ color: accent }}>
              <span className={styles.marker} aria-hidden="true">
                {open ? "▼" : "▶"}
              </span>
              {name}
            </span>
            {(share || routing) && (
              <small className={styles.share}>
                {share}
                {routing && <span className={styles.onPhone}> · {routing}</span>}
              </small>
            )}
          </span>
          <span className={cx(styles.avail, "num")}>
            <Amount value={avail} tone="plain" />
            {rest !== undefined && (
              <span className={styles.onPhone}>
                {negative && <span className={styles.warn}>⚠ </span>}
                rest <Amount value={rest} />
              </span>
            )}
          </span>
          <span className={cx(styles.rest, "num")}>
            {rest !== undefined && <Amount value={rest} />}
          </span>
          <span className={styles.routing}>
            {negative && (
              <span className={styles.warn} title="Negative rest">
                ⚠{" "}
              </span>
            )}
            {routing}
          </span>
        </button>
        <span className={styles.menu}>{menu}</span>
      </div>
      {open && (
        <div id={bodyId} className={styles.body}>
          {children}
        </div>
      )}
    </div>
  );
}
