import type { Field, Income, Schemas, Section } from "../../api/client";
import { useMonthView } from "../../app/month";
import { Page } from "../../app/Page";
import { useSheet } from "../../app/sheets";
import { useToast } from "../../app/toast";
import { useAct } from "../../app/useAct";
import { NARROW, useMediaQuery } from "../../app/useMediaQuery";
import { AllocationBar } from "../../components/AllocationBar";
import { Amount } from "../../components/Amount";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { FieldTable } from "../../components/FieldTable";
import { Menu, type MenuEntry } from "../../components/Menu";
import { SectionList, SectionRow } from "../../components/SectionRow";
import { Widget } from "../../components/Widget";
import {
  findField,
  INCOME_ACCENT,
  percentGap,
  routingLabel,
  sectionAccent,
  shareLabel,
} from "../../lib/budget";
import { cx } from "../../lib/cx";
import { formatMoney, isNegative, isZero, splitMoney, units } from "../../lib/money";
import { count } from "../../lib/text";
import styles from "./BudgetPage.module.css";
import { useExpanded } from "./useExpanded";

const INCOME_ROW = "income"; // no section can take this name — the engine reserves it

/**
 * The Budget tab: the month's headline, how the post pool splits, and the
 * accordion of sections with their fields.
 */
export function BudgetPage() {
  const { month, readOnly } = useMonthView();
  const open = useSheet();
  const expanded = useExpanded();

  const addTransaction = () => open({ kind: "transaction" });

  return (
    <Page
      primary={{ label: "Add transaction", onClick: addTransaction }}
      actions={
        <>
          <Button onClick={() => open({ kind: "close-month" })}>Close month</Button>
          <Button variant="primary" onClick={addTransaction}>
            Add transaction
          </Button>
        </>
      }
    >
      <div className={styles.summary}>
        <Headline />
        <PostSplit />
      </div>

      <SectionList>
        <IncomeRow
          open={expanded.open.has(INCOME_ROW)}
          onToggle={() => expanded.set(INCOME_ROW, !expanded.open.has(INCOME_ROW))}
        />
        {month.sections.map((section) => (
          <BudgetSection
            key={section.name}
            section={section}
            open={expanded.open.has(section.name)}
            onToggle={() => expanded.set(section.name, !expanded.open.has(section.name))}
          />
        ))}
        {month.sections.length === 0 && (
          <EmptyState
            title="No sections yet"
            action={
              !readOnly && (
                <Button variant="primary" onClick={() => open({ kind: "section" })}>
                  Add section
                </Button>
              )
            }
          >
            Sections split your income. Start with Needs, Wants and Savings.
          </EmptyState>
        )}
        {!readOnly && (
          <div className={styles.footer}>
            {month.sections.length > 0 && (
              <Button onClick={() => open({ kind: "section" })}>Add section</Button>
            )}
            <Button onClick={() => open({ kind: "income" })}>Add income</Button>
            <Button className={styles.phoneOnly} onClick={() => open({ kind: "close-month" })}>
              Close month
            </Button>
          </div>
        )}
      </SectionList>
    </Page>
  );
}

// ---------------------------------------------------------------------------
// Headline: income (the page's one hero), post pool, the Σ% check
// ---------------------------------------------------------------------------
function Headline() {
  const { month } = useMonthView();
  const income = splitMoney(month.total_income);
  const gap = month.post_pct_total === null ? null : percentGap(month.post_pct_total);
  const unassigned = units(month.unallocated);
  const overdrawn = month.sections.filter((section) => isNegative(section.rest));

  return (
    <Widget className={styles.headline}>
      <div className={styles.figures}>
        <div>
          <p className="label">income</p>
          {/* Never coloured: the hero is always text-strong. */}
          <p className={styles.hero}>
            {income.whole}
            <span className={styles.cents}>{income.fraction}</span>
          </p>
        </div>
        <div className={styles.secondary}>
          <div>
            <p className="label">post pool</p>
            <p className={styles.figure}>{formatMoney(month.post_pool)}</p>
          </div>
          {gap && (
            <div>
              <p className="label">allocation</p>
              {gap.state === "balanced" ? (
                <p className={cx(styles.figure, "pos")}>100 ✓</p>
              ) : (
                <p className={cx(styles.figure, styles.warn)}>
                  {month.post_pct_total}, {gap.by} {gap.state === "under" ? "unassigned" : "over"}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {(unassigned !== 0n || overdrawn.length > 0) && (
        <ul className={styles.notes}>
          {unassigned > 0n && (
            <li>⚠ {formatMoney(unassigned)} of income isn't assigned to a section.</li>
          )}
          {unassigned < 0n && (
            <li>⚠ Sections take {formatMoney(-unassigned)} more than this month's income.</li>
          )}
          {overdrawn.map((section) => (
            <li key={section.name}>
              ⚠ {section.name} has a negative rest ({formatMoney(section.rest)}).
            </li>
          ))}
        </ul>
      )}
    </Widget>
  );
}

function PostSplit() {
  const { month } = useMonthView();
  const post = month.sections.filter((section) => section.kind === "post");
  if (post.length === 0 || month.post_pct_total === null) return null;
  return (
    <Widget>
      <AllocationBar
        pool={month.post_pool}
        total={month.post_pct_total}
        segments={post.map((section) => ({
          name: section.name,
          percent: section.allocation.value,
          accent: sectionAccent(section.index),
        }))}
      />
    </Widget>
  );
}

// ---------------------------------------------------------------------------
// The income row — not a section, but it reads like one
// ---------------------------------------------------------------------------
function IncomeRow({ open: isOpen, onToggle }: { open: boolean; onToggle: () => void }) {
  const { month, readOnly, actions } = useMonthView();
  const open = useSheet();
  const act = useAct();

  const menuFor = (income: Income): MenuEntry[] => [
    { label: "Edit", onSelect: () => open({ kind: "income", edit: income }) },
    {
      label: "Delete",
      danger: true,
      onSelect: () =>
        void act(() => actions.deleteIncome(income.index), {
          kind: "info",
          message: `Income ${income.name} deleted`,
        }),
    },
  ];

  return (
    <SectionRow
      accent={INCOME_ACCENT}
      name="Income"
      share={count(month.incomes.length, "entry", "entries")}
      avail={month.total_income}
      open={isOpen}
      onToggle={onToggle}
      menu={
        !readOnly && (
          <Menu
            label="Actions for income"
            items={[{ label: "Add income", onSelect: () => open({ kind: "income" }) }]}
          />
        )
      }
    >
      {month.incomes.length === 0 ? (
        <p className="caption">No income yet. Add what comes in this month.</p>
      ) : (
        <ul className={styles.incomes}>
          {month.incomes.map((income) => (
            <li key={income.index} className={styles.income}>
              <span className={styles.incomeText}>
                <span className={styles.incomeName}>{income.name}</span>
                <span className="caption">{income.kind}</span>
              </span>
              <Amount value={income.amount} className={styles.incomeAmount} />
              {!readOnly && <Menu label={`Actions for ${income.name}`} items={menuFor(income)} />}
            </li>
          ))}
        </ul>
      )}
      {!readOnly && (
        <div>
          <Button size="sm" onClick={() => open({ kind: "income" })}>
            Add income
          </Button>
        </div>
      )}
    </SectionRow>
  );
}

// ---------------------------------------------------------------------------
// One section and, when open, its fields
// ---------------------------------------------------------------------------
interface BudgetSectionProps {
  section: Section;
  open: boolean;
  onToggle: () => void;
}

function BudgetSection({ section, open: isOpen, onToggle }: BudgetSectionProps) {
  const { month, readOnly, actions } = useMonthView();
  const open = useSheet();
  const act = useAct();
  const toast = useToast();
  const stacked = useMediaQuery(NARROW);

  const last = month.sections.length - 1;
  const move = (to: number) =>
    void act(() => actions.editSection(section.index, { position: to }), {
      message: `${section.name} moved.`,
    });

  const sectionMenu: MenuEntry[] = [
    { label: "Add field", onSelect: () => open({ kind: "field", section }) },
    { label: "Edit section", onSelect: () => open({ kind: "section", edit: section }) },
    { label: "Move up", disabled: section.index === 0, onSelect: () => move(section.index - 1) },
    {
      label: "Move down",
      disabled: section.index === last,
      onSelect: () => move(section.index + 1),
    },
    "divider",
    {
      label: "Delete",
      danger: true,
      onSelect: () =>
        void act(() => actions.deleteSection(section.index), {
          kind: "info",
          message: `Section ${section.name} deleted`,
        }),
    },
  ];

  const fieldMenu = (field: Field): MenuEntry[] => {
    const ref = { section: section.index, field: field.index };
    return [
      { label: "Add transaction", onSelect: () => open({ kind: "transaction", field: ref }) },
      { label: "Transfer from here", onSelect: () => open({ kind: "transfer", from: ref }) },
      { label: "Edit", onSelect: () => open({ kind: "field", section, edit: field }) },
      "divider",
      {
        label: "Delete",
        danger: true,
        onSelect: () =>
          void act(() => actions.deleteField(section.index, field.index), {
            kind: "info",
            message: `Field ${field.name} deleted`,
          }),
      },
    ];
  };

  /** A value edited in place in the table. */
  async function saveInline(field: Field, change: Schemas["FieldUpdate"]) {
    const result = await actions.editField(section.index, field.index, change);
    const saved = findField(result.month, section.index, field.index);
    toast({
      message: `${field.name} updated.${saved ? ` ${formatMoney(saved.field.left)} left.` : ""}`,
    });
  }

  return (
    <SectionRow
      accent={sectionAccent(section.index)}
      name={section.name}
      share={shareLabel(section)}
      avail={section.available}
      rest={section.rest}
      routing={routingLabel(section)}
      open={isOpen}
      onToggle={onToggle}
      menu={!readOnly && <Menu label={`Actions for ${section.name}`} items={sectionMenu} />}
    >
      {section.fields.length === 0 ? (
        <p className="caption">
          No fields yet. A field is a budget line: Groceries, Rent, Emergency fund.
        </p>
      ) : (
        <FieldTable
          fields={section.fields}
          stacked={stacked}
          readOnly={readOnly}
          currentEditable={month.is_first}
          onOpen={(field) => open({ kind: "field", section, edit: field })}
          onSave={saveInline}
          menu={fieldMenu}
        />
      )}
      <div className={styles.sectionFooter}>
        {!readOnly && (
          <Button size="sm" onClick={() => open({ kind: "field", section })}>
            Add field
          </Button>
        )}
        <span className="caption">
          {!isZero(section.carried_rest) && <>carried in {formatMoney(section.carried_rest)} · </>}
          budget left <Amount value={section.budget_left} />
        </span>
      </div>
    </SectionRow>
  );
}
