import { useMonths } from "../../api/queries";
import { useMonthView } from "../../app/month";
import { Amount } from "../../components/Amount";
import { StatusChip } from "../../components/StatusChip";
import { Widget } from "../../components/Widget";
import { cx } from "../../lib/cx";
import styles from "./HistoryWidget.module.css";

/**
 * Every month of the profile, newest first. Opening a closed month shows it
 * read-only; opening the open one returns to it.
 */
export function HistoryWidget() {
  const { profileId, month, view } = useMonthView();
  const months = useMonths(profileId);

  return (
    <Widget title="History">
      {months.isError && <p className="caption">{months.error.message}</p>}
      {months.data && (
        <ul className={styles.list}>
          {months.data.map((summary) => {
            const current = summary.key === month.key;
            return (
              <li key={summary.key}>
                <button
                  type="button"
                  className={cx(styles.row, current && styles.current)}
                  aria-current={current ? "true" : undefined}
                  onClick={() => view(summary.key)}
                >
                  <span className={styles.top}>
                    <span className={styles.key}>{summary.key}</span>
                    <StatusChip kind={summary.state}>{summary.state}</StatusChip>
                  </span>
                  <span className={styles.figures}>
                    <span>
                      income
                      <b>
                        <Amount value={summary.income} />
                      </b>
                    </span>
                    <span>
                      spent
                      <b>
                        <Amount value={summary.spent} />
                      </b>
                    </span>
                    <span>
                      leftovers
                      <b>
                        <Amount value={summary.leftovers} />
                      </b>
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Widget>
  );
}
