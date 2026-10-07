import { percentGap } from "../lib/budget";
import { formatMoney } from "../lib/money";
import styles from "./AllocationBar.module.css";

export interface AllocationSegment {
  name: string;
  /** A bare percentage, e.g. `"50"`. */
  percent: string;
  /** The section's own accent — the colour means the section, here as everywhere. */
  accent: string;
}

interface AllocationBarProps {
  pool: string;
  /** The exact sum of the percentages, as the engine reports it. */
  total: string;
  segments: AllocationSegment[];
}

/**
 * How the post pool splits across the post-sections: a stacked pill bar in the
 * sections' accents, with a legend that repeats each name and share so the
 * colours never carry the meaning alone. If the shares don't reach 100, the
 * remainder shows as a labelled "unassigned" segment.
 */
export function AllocationBar({ pool, total, segments }: AllocationBarProps) {
  const gap = percentGap(total);
  // Widths are geometry, so plain numbers will do; the *words* use `gap`.
  const sum = Number(total);
  const scale = sum > 100 ? 100 / sum : 1; // over 100%: still draw a full bar
  const summary = segments.map((s) => `${s.name} ${s.percent}%`).join(", ");

  return (
    <div className={styles.wrap}>
      <p className="label">post pool {formatMoney(pool)}</p>
      <div className={styles.bar} role="img" aria-label={`Post pool split: ${summary}`}>
        {segments
          .filter((segment) => Number(segment.percent) > 0)
          .map((segment) => (
            <i
              key={segment.name}
              style={{ width: `${Number(segment.percent) * scale}%`, background: segment.accent }}
            />
          ))}
        {gap.state === "under" && (
          <i className={styles.unassigned} style={{ width: `${100 - sum}%` }} />
        )}
      </div>
      <ul className={styles.legend}>
        {segments.map((segment) => (
          <li key={segment.name}>
            <b style={{ background: segment.accent }} />
            {segment.name} {segment.percent}%
          </li>
        ))}
        {gap.state === "under" && (
          <li className={styles.warn}>
            <b className={styles.unassigned} />
            unassigned {gap.by}%
          </li>
        )}
        {gap.state === "over" && <li className={styles.warn}>⚠ over by {gap.by}%</li>}
      </ul>
    </div>
  );
}
