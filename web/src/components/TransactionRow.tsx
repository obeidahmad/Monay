import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import { formatMoney } from "../lib/money";
import styles from "./TransactionRow.module.css";

interface TransactionRowProps {
  /** The section's letter on its accent — or `⇄` for a transfer. */
  avatar: ReactNode;
  /** The field's name; for a transfer, "From → To". */
  title: string;
  /** The muted second line: `#2 · 5 Jan · Needs · weekly shop`. */
  detail: string;
  amount: string;
  /** Spending takes the paid column's colour; a transfer is plain text. */
  kind: "spend" | "transfer";
  /** Opens the row's edit Sheet. Omit when there is nothing to open. */
  onOpen?: () => void;
  /** The trailing `⋯` menu. */
  menu?: ReactNode;
}

/** One transaction or transfer, 64px tall, inside a glass widget. */
export function TransactionRow({
  avatar,
  title,
  detail,
  amount,
  kind,
  onOpen,
  menu,
}: TransactionRowProps) {
  const content = (
    <>
      {avatar}
      <span className={styles.text}>
        <span className={styles.title}>{title}</span>
        <span className={styles.detail}>{detail}</span>
      </span>
      <span className={cx(styles.amount, kind === "spend" && styles.spend)}>
        {formatMoney(amount)}
      </span>
    </>
  );
  return (
    <li className={styles.row}>
      {onOpen ? (
        <button type="button" className={styles.main} onClick={onOpen}>
          {content}
        </button>
      ) : (
        <div className={styles.main}>{content}</div>
      )}
      {menu}
    </li>
  );
}
