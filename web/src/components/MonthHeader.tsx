import { Lock } from "lucide-react";
import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import { Button } from "./Button";
import styles from "./MonthHeader.module.css";
import { StatusChip } from "./StatusChip";

interface MonthHeaderProps {
  /** "January 2025" */
  month: string;
  state: "open" | "closed";
  /** The page's buttons: secondary ones, then the one primary at the right.
      Desktop only — on a phone the primary action is the floating button. */
  actions?: ReactNode;
  /** The profile avatar menu, always at the far right. */
  profile: ReactNode;
  /** Shown on a closed month: leaves the read-only view. */
  onBackToOpen?: () => void;
}

/**
 * The top of every tab: the month in `title-page`, whether it is open or
 * closed, the page's actions and the profile menu. A closed month adds a
 * read-only banner with the way back.
 */
export function MonthHeader({ month, state, actions, profile, onBackToOpen }: MonthHeaderProps) {
  return (
    <>
      <header className={styles.header}>
        <div className={styles.titles}>
          <h1 className={styles.title}>{month}</h1>
          <StatusChip kind={state}>{state}</StatusChip>
        </div>
        <div className={styles.side}>
          {actions && <div className={styles.actions}>{actions}</div>}
          {profile}
        </div>
      </header>
      {state === "closed" && (
        <div className={cx("glass", styles.banner)} role="status">
          <Lock size={16} aria-hidden="true" />
          <span className={styles.bannerText}>
            <b>Read-only.</b> {month} is closed; corrections go in the open month.
          </span>
          {onBackToOpen && (
            <Button size="sm" onClick={onBackToOpen}>
              Back to open month
            </Button>
          )}
        </div>
      )}
    </>
  );
}
