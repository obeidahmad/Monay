import { Search } from "lucide-react";
import { useState } from "react";
import type { Month, Section, Transaction, Transfer } from "../../api/client";
import { useMonthView } from "../../app/month";
import { Page } from "../../app/Page";
import { useSheet } from "../../app/sheets";
import { useAct } from "../../app/useAct";
import { Avatar } from "../../components/Avatar";
import { Button } from "../../components/Button";
import { Chip, ChipRow } from "../../components/Chip";
import { EmptyState } from "../../components/EmptyState";
import { Menu } from "../../components/Menu";
import { SectionIcon } from "../../components/SectionIcon";
import { TransactionRow } from "../../components/TransactionRow";
import { Widget } from "../../components/Widget";
import { sectionAccent } from "../../lib/budget";
import { dayLabel } from "../../lib/dates";
import styles from "./TransactionsPage.module.css";

type Entry =
  | { kind: "transaction"; day: number; item: Transaction }
  | { kind: "transfer"; day: number; item: Transfer };

/** Transactions and transfers as one list, most recent day first. */
function entriesOf(month: Month): Entry[] {
  const entries: Entry[] = [
    ...month.transactions.map((item) => ({ kind: "transaction" as const, day: item.day, item })),
    ...month.transfers.map((item) => ({ kind: "transfer" as const, day: item.day, item })),
  ];
  // Newest day first; within a day, the latest entry first.
  return entries.sort((a, b) => b.day - a.day || b.item.number - a.item.number);
}

function matches(entry: Entry, text: string, section: number | null): boolean {
  const fields =
    entry.kind === "transaction"
      ? [entry.item.field]
      : [entry.item.from_field, entry.item.to_field];
  if (section !== null && !fields.some((field) => field.section_index === section)) return false;
  if (text === "") return true;
  const words = [
    ...fields.flatMap((field) => [field.field, field.section]),
    entry.kind === "transaction" ? entry.item.description : entry.item.note,
  ];
  return words.some((word) => word.toLowerCase().includes(text));
}

function IconOf({ section }: { section: Section | undefined }) {
  return <SectionIcon color={section?.color ?? 1} icon={section?.icon} kind={section?.kind} />;
}

/** The Transactions tab: everything that happened this month, searchable. */
export function TransactionsPage() {
  const { month, readOnly, actions } = useMonthView();
  const open = useSheet();
  const act = useAct();
  const [search, setSearch] = useState("");
  const [section, setSection] = useState<number | null>(null);

  const all = entriesOf(month);
  const shown = all.filter((entry) => matches(entry, search.trim().toLowerCase(), section));
  const addTransaction = () => open({ kind: "transaction" });

  return (
    <Page
      title="Transactions"
      subtitle={`${month.label} · ${all.length === 1 ? "1 entry" : `${all.length} entries`}`}
      primary={{ label: "Add transaction", onClick: addTransaction }}
      actions={
        <>
          <Button onClick={() => open({ kind: "transfer" })}>Transfer</Button>
          <Button variant="primary" onClick={addTransaction}>
            Add transaction
          </Button>
        </>
      }
    >
      <Widget>
        {all.length === 0 ? (
          <EmptyState
            title="No transactions yet"
            action={
              !readOnly && (
                <Button variant="primary" onClick={addTransaction}>
                  Add transaction
                </Button>
              )
            }
          >
            Record money as it leaves a field. Each one lowers what that field has left.
          </EmptyState>
        ) : (
          <>
            <div className={styles.toolbar}>
              <label className={styles.search}>
                <Search size={16} aria-hidden="true" />
                <span className="sr-only">Search transactions</span>
                <input
                  type="search"
                  value={search}
                  placeholder="Search field or description"
                  onChange={(event) => setSearch(event.target.value)}
                />
              </label>
              {!readOnly && (
                <Button className={styles.phoneOnly} onClick={() => open({ kind: "transfer" })}>
                  Transfer
                </Button>
              )}
            </div>
            <ChipRow label="Filter by section">
              {month.sections
                .filter((option) => option.fields.length > 0)
                .map((option) => (
                  <Chip
                    key={option.index}
                    accent={sectionAccent(option.color)}
                    selected={section === option.index}
                    removable
                    onClick={() => setSection(section === option.index ? null : option.index)}
                  >
                    {option.name}
                  </Chip>
                ))}
            </ChipRow>

            {shown.length === 0 ? (
              <p className={styles.nothing}>Nothing matches. Clear the search or the filter.</p>
            ) : (
              <ul className={styles.list}>
                {shown.map((entry) =>
                  entry.kind === "transaction" ? (
                    <TransactionRow
                      key={`t${entry.item.number}`}
                      kind="spend"
                      avatar={<IconOf section={month.sections[entry.item.field.section_index]} />}
                      title={entry.item.field.field}
                      detail={[
                        `#${entry.item.number}`,
                        dayLabel(month.key, entry.item.day),
                        entry.item.field.section,
                        entry.item.description,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                      amount={entry.item.amount}
                      onOpen={
                        readOnly ? undefined : () => open({ kind: "transaction", edit: entry.item })
                      }
                      menu={
                        !readOnly && (
                          <Menu
                            label={`Actions for transaction #${entry.item.number}`}
                            items={[
                              {
                                label: "Edit",
                                onSelect: () => open({ kind: "transaction", edit: entry.item }),
                              },
                              {
                                label: "Delete",
                                danger: true,
                                onSelect: () =>
                                  void act(() => actions.deleteTransaction(entry.item.number), {
                                    kind: "info",
                                    message: "Transaction deleted",
                                  }),
                              },
                            ]}
                          />
                        )
                      }
                    />
                  ) : (
                    <TransactionRow
                      key={`x${entry.item.number}`}
                      kind="transfer"
                      avatar={<Avatar>⇄</Avatar>}
                      title={`${entry.item.from_field.field} → ${entry.item.to_field.field}`}
                      detail={["transfer", dayLabel(month.key, entry.item.day), entry.item.note]
                        .filter(Boolean)
                        .join(" · ")}
                      amount={entry.item.amount}
                      menu={
                        !readOnly && (
                          <Menu
                            label={`Actions for transfer ${entry.item.from_field.field} to ${entry.item.to_field.field}`}
                            items={[
                              {
                                label: "Delete",
                                danger: true,
                                onSelect: () =>
                                  void act(() => actions.deleteTransfer(entry.item.number), {
                                    kind: "info",
                                    message: "Transfer deleted",
                                  }),
                              },
                            ]}
                          />
                        )
                      }
                    />
                  ),
                )}
              </ul>
            )}
          </>
        )}
      </Widget>
    </Page>
  );
}
