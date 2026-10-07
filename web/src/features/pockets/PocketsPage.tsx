import type { Pocket } from "../../api/client";
import { useMonthView } from "../../app/month";
import { Page } from "../../app/Page";
import { useSheet } from "../../app/sheets";
import { Button } from "../../components/Button";
import { PocketCard } from "../../components/PocketCard";
import { Widget } from "../../components/Widget";
import { formatMoney, isZero } from "../../lib/money";
import styles from "./PocketsPage.module.css";

/** "Groceries 332.94 · Eating out 90.60 · RESTs 696.86" */
function breakdown(pocket: Pocket): string {
  const parts = pocket.holdings.map((holding) => `${holding.field} ${formatMoney(holding.left)}`);
  // Only the default pocket carries these two.
  if (!isZero(pocket.rests)) parts.push(`RESTs ${formatMoney(pocket.rests)}`);
  if (!isZero(pocket.unallocated)) parts.push(`unassigned ${formatMoney(pocket.unallocated)}`);
  return parts.join(" · ");
}

/**
 * The Pockets tab: for each place money sits, the amount that should be there
 * right now — so it can be checked against the real account.
 */
export function PocketsPage() {
  const { month, readOnly } = useMonthView();
  const open = useSheet();
  const addPocket = () => open({ kind: "pocket" });

  return (
    <Page
      primary={{ label: "Add pocket", onClick: addPocket }}
      actions={
        <Button variant="primary" onClick={addPocket}>
          Add pocket
        </Button>
      }
    >
      <Widget title="Pockets">
        <ul className={styles.list}>
          {month.pockets.map((pocket) => (
            <li key={pocket.index}>
              <PocketCard
                name={pocket.name}
                isDefault={pocket.is_default}
                counter={pocket.counter}
                breakdown={breakdown(pocket)}
                onOpen={readOnly ? undefined : () => open({ kind: "pocket", edit: pocket })}
              />
            </li>
          ))}
        </ul>
      </Widget>
    </Page>
  );
}
