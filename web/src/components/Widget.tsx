import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import styles from "./Widget.module.css";

interface WidgetProps {
  title?: string;
  /** Controls at the right of the header (an Add pill, a filter). */
  actions?: ReactNode;
  /** Drop the padding — for content that draws its own edges (a row list). */
  flush?: boolean;
  className?: string;
  children: ReactNode;
}

/**
 * The glass panel every screen is made of. One idea per widget — a headline
 * figure, an accordion, a list — and widgets are never nested: inside one, use
 * `surface-raised` tiles.
 */
export function Widget({ title, actions, flush = false, className, children }: WidgetProps) {
  return (
    <section className={cx("glass", styles.widget, flush && styles.flush, className)}>
      {(title || actions) && (
        <header className={styles.header}>
          {title && <h2 className={styles.title}>{title}</h2>}
          {actions && <div className={styles.actions}>{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
