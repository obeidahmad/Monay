import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

interface EmptyStateProps {
  title: string;
  /** One sentence of help. */
  children?: ReactNode;
  /** The single obvious next step (a primary button), if there is one. */
  action?: ReactNode;
}

/** What a widget shows when it has nothing yet: a line, a sentence, one button. */
export function EmptyState({ title, children, action }: EmptyStateProps) {
  return (
    <div className={styles.empty}>
      <p className={styles.title}>{title}</p>
      {children && <p className={styles.text}>{children}</p>}
      {action}
    </div>
  );
}
