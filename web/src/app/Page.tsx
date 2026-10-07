import { Lock, Plus } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "../components/Button";
import { cx } from "../lib/cx";
import { MonthSwitcher } from "./AppShell";
import { useMonthView } from "./month";
import styles from "./Page.module.css";

interface PageProps {
  title: string;
  /** A line under the title. */
  subtitle?: ReactNode;
  /** Something before the title: a back link, a section's icon. */
  lead?: ReactNode;
  /** Header buttons: secondary ones, then the single primary at the right. */
  actions?: ReactNode;
  /** The page's primary action as the floating button on a phone. */
  primary?: { label: string; onClick: () => void };
  children: ReactNode;
}

/** A page: a big title, its actions, and — in a closed month — the way back. */
export function Page({ title, subtitle, lead, actions, primary, children }: PageProps) {
  const { month, readOnly, view } = useMonthView();
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        {lead}
        <div className={styles.titles}>
          <h1 className={styles.title}>{title}</h1>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
        {!readOnly && actions && <div className={styles.actions}>{actions}</div>}
        <div className={styles.month}>
          <MonthSwitcher />
        </div>
      </header>

      {readOnly && (
        <div className={cx("glass", styles.banner)} role="status">
          <Lock size={16} aria-hidden="true" />
          <span className={styles.bannerText}>
            <b>Read-only.</b> {month.label} is closed; corrections go in the open month.
          </span>
          <Button size="sm" onClick={() => view(null)}>
            Back to open month
          </Button>
        </div>
      )}

      {children}

      {primary && !readOnly && (
        <button
          type="button"
          className={styles.fab}
          aria-label={primary.label}
          onClick={primary.onClick}
        >
          <Plus size={28} strokeWidth={2.4} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
