import { Amount } from "./Amount";
import styles from "./PocketCard.module.css";
import { StatusChip } from "./StatusChip";

interface PocketCardProps {
  name: string;
  isDefault: boolean;
  /** What the pocket should hold right now. */
  counter: string;
  /** "Groceries 332.94 · Eating out 90.60 · RESTs 696.86" */
  breakdown: string;
  /** Opens the pocket's edit Sheet. Omit in a closed month. */
  onOpen?: () => void;
}

/**
 * A pocket — where money physically sits — and the amount that should be in
 * it, so it can be checked against the real account.
 */
export function PocketCard({ name, isDefault, counter, breakdown, onOpen }: PocketCardProps) {
  const content = (
    <>
      <span className={styles.top}>
        <span className={styles.name}>
          {name}
          {isDefault && <StatusChip kind="plain">default</StatusChip>}
        </span>
        <Amount value={counter} className={styles.counter} />
      </span>
      <span className="caption">should hold{breakdown && ` · ${breakdown}`}</span>
    </>
  );
  return onOpen ? (
    <button type="button" className={styles.card} onClick={onOpen}>
      {content}
    </button>
  ) : (
    <div className={styles.card}>{content}</div>
  );
}
