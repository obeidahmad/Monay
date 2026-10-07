import { Plus, Wallet } from "lucide-react";
import type { Pocket } from "../../api/client";
import { useMonthView } from "../../app/month";
import { Page } from "../../app/Page";
import { useSheet } from "../../app/sheets";
import { Amount } from "../../components/Amount";
import { Button } from "../../components/Button";
import { StatusChip } from "../../components/StatusChip";
import { sectionAccent } from "../../lib/budget";
import { formatMoney, isZero, share, units } from "../../lib/money";
import styles from "./PocketsPage.module.css";

/**
 * The Pockets tab: for each place money sits, the amount that should be there
 * right now and what it is made of — to check against the real account.
 */
export function PocketsPage() {
  const { month, readOnly } = useMonthView();
  const open = useSheet();
  const addPocket = () => open({ kind: "pocket" });
  const total = month.pockets.reduce((sum, p) => sum + units(p.counter), 0n);

  return (
    <Page
      title="Pockets"
      subtitle={`${formatMoney(total)} across ${month.pockets.length === 1 ? "one pocket" : `${month.pockets.length} pockets`}`}
      primary={{ label: "Add pocket", onClick: addPocket }}
      actions={
        <Button variant="primary" icon={<Plus size={18} />} onClick={addPocket}>
          Add pocket
        </Button>
      }
    >
      <div className={styles.grid}>
        {month.pockets.map((pocket, i) => (
          <PocketCard
            key={pocket.index}
            pocket={pocket}
            tint={`var(--chart-${(i % 8) + 1})`}
            onOpen={readOnly ? undefined : () => open({ kind: "pocket", edit: pocket })}
          />
        ))}
      </div>
    </Page>
  );
}

function PocketCard({
  pocket,
  tint,
  onOpen,
}: {
  pocket: Pocket;
  tint: string;
  onOpen?: () => void;
}) {
  const { month } = useMonthView();
  const colorOf = (name: string) =>
    sectionAccent(month.sections.find((s) => s.name === name)?.color ?? 1);
  const parts = [
    ...pocket.holdings.map((h) => ({ name: h.field, amount: h.left, color: colorOf(h.section) })),
    ...(isZero(pocket.rests)
      ? []
      : [{ name: "Section rests", amount: pocket.rests, color: "var(--text-muted)" }]),
    ...(isZero(pocket.unallocated)
      ? []
      : [{ name: "Unassigned income", amount: pocket.unallocated, color: "var(--warn)" }]),
  ];
  const positive = parts.reduce(
    (sum, p) => sum + (units(p.amount) > 0n ? units(p.amount) : 0n),
    0n,
  );

  const body = (
    <>
      <span className={styles.top}>
        <span className={styles.icon}>
          <Wallet size={22} />
        </span>
        <span className={styles.name}>
          <b>{pocket.name}</b>
          {pocket.is_default && <StatusChip kind="plain">default</StatusChip>}
        </span>
      </span>
      <span className={styles.figure}>
        <span className="label">should hold</span>
        <Amount value={pocket.counter} className={styles.counter} />
      </span>
      {positive > 0n && (
        <span className={styles.bar}>
          {parts
            .filter((p) => units(p.amount) > 0n)
            .map((p) => (
              <i
                key={p.name}
                style={{ width: `${share(p.amount, positive) * 100}%`, background: p.color }}
              />
            ))}
        </span>
      )}
      <span className={styles.parts}>
        {parts.length === 0 && <span className={styles.none}>Nothing kept here yet.</span>}
        {parts.map((p) => (
          <span key={p.name}>
            <i style={{ background: p.color }} />
            {p.name}
            <Amount value={p.amount} />
          </span>
        ))}
      </span>
    </>
  );

  const style = { "--accent": tint } as React.CSSProperties;
  return onOpen ? (
    <button type="button" className={`glass ${styles.card}`} style={style} onClick={onOpen}>
      {body}
    </button>
  ) : (
    <div className={`glass ${styles.card}`} style={style}>
      {body}
    </div>
  );
}
