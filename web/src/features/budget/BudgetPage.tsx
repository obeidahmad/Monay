import { ChevronRight, Plus } from "lucide-react";
import { Link, useLocation } from "react-router";
import type { Income, Section } from "../../api/client";
import { useMonthView } from "../../app/month";
import { Page } from "../../app/Page";
import { useSheet } from "../../app/sheets";
import { useAct } from "../../app/useAct";
import { Amount } from "../../components/Amount";
import { Button } from "../../components/Button";
import { DonutChart, Meter, MeterWord, StatTile } from "../../components/charts";
import { Menu, type MenuEntry } from "../../components/Menu";
import { SectionIcon } from "../../components/SectionIcon";
import { Widget } from "../../components/Widget";
import { num, percentGap, routingLabel, sectionAccent, shareLabel } from "../../lib/budget";
import { sectionSpent } from "../../lib/insights";
import { formatMoney, isNegative, splitMoney, units } from "../../lib/money";
import { count } from "../../lib/text";
import styles from "./BudgetPage.module.css";

/**
 * The Budget tab: the month at a glance, where the income comes from, and one
 * card per section. A section opens into its own page.
 */
export function BudgetPage() {
  const { month, readOnly } = useMonthView();
  const open = useSheet();
  const addTransaction = () => open({ kind: "transaction" });

  return (
    <Page
      title="Budget"
      subtitle={`${month.label} · ${month.state}`}
      primary={{ label: "Add transaction", onClick: addTransaction }}
      actions={
        <>
          <Button onClick={() => open({ kind: "close-month" })}>Close month</Button>
          <Button variant="primary" icon={<Plus size={18} />} onClick={addTransaction}>
            Add transaction
          </Button>
        </>
      }
    >
      <Overview />

      <div className={styles.pair}>
        <IncomeCard />
        <SpendingCard />
      </div>

      <section className={styles.sections}>
        <header className={styles.sectionsHead}>
          <h2 className={styles.heading}>Sections</h2>
          <PostCheck />
        </header>
        <div className={styles.grid}>
          {month.sections.map((section) => (
            <SectionCard key={section.name} section={section} />
          ))}
          {!readOnly && (
            <button
              type="button"
              className={styles.addCard}
              onClick={() => open({ kind: "section" })}
            >
              <Plus size={22} aria-hidden="true" />
              <b>Add section</b>
              <span>
                {month.sections.length === 0
                  ? "Sections split your income. Start with Needs, Wants and Savings."
                  : "Tax, pre or post — with its own colour and icon."}
              </span>
            </button>
          )}
        </div>
      </section>

      {!readOnly && (
        <div className={styles.phoneActions}>
          <Button onClick={() => open({ kind: "close-month" })}>Close month</Button>
        </div>
      )}
    </Page>
  );
}

// ---------------------------------------------------------------------------
// The month at a glance
// ---------------------------------------------------------------------------
function Overview() {
  const { month } = useMonthView();
  const income = splitMoney(month.total_income);
  const spent = units(month.spent);
  const rest = month.sections.reduce((total, s) => total + units(s.rest), 0n);
  const unassigned = units(month.unallocated);
  const incomeN = num(month.total_income);
  const spentN = num(month.spent);

  return (
    <section className={`glass ${styles.overview}`}>
      <div className={styles.heroBlock}>
        <p className="label">income this month</p>
        <p className={styles.hero}>
          {income.whole}
          <span>{income.fraction}</span>
        </p>
        <div className={styles.heroMeter}>
          <Meter
            used={spentN}
            of={incomeN}
            size="lg"
            color="var(--brand-mint)"
            label="Spent of income"
          />
          <p className={styles.meterLine}>
            <span>
              <b>{formatMoney(spent)}</b> spent
            </span>
            <span>
              {incomeN > 0 ? `${Math.round((spentN / incomeN) * 100)}% of income` : "no income yet"}
            </span>
          </p>
        </div>
      </div>
      <div className={styles.tiles}>
        <StatTile label="Spent" value={formatMoney(spent)} />
        <StatTile label="Rest" value={formatMoney(rest)} tone={rest < 0n ? "neg" : "plain"} />
        <StatTile label="Post pool" value={formatMoney(month.post_pool)} />
        <StatTile
          label="Unassigned"
          value={formatMoney(unassigned)}
          tone={unassigned === 0n ? "plain" : "warn"}
        />
      </div>
    </section>
  );
}

/** Whether the post-sections add up to 100%. */
function PostCheck() {
  const { month } = useMonthView();
  if (month.post_pct_total === null) return null;
  const gap = percentGap(month.post_pct_total);
  return gap.state === "balanced" ? (
    <span className={`${styles.check} pos`}>✓ post-sections add up to 100%</span>
  ) : (
    <span className={`${styles.check} ${styles.warn}`}>
      ⚠ post-sections add up to {month.post_pct_total}% — {gap.by}%{" "}
      {gap.state === "under" ? "unassigned" : "over"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Income — where the money comes from. Not a section.
// ---------------------------------------------------------------------------
function IncomeCard() {
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
    <Widget
      title="Income"
      actions={
        !readOnly && (
          <Button size="sm" icon={<Plus size={16} />} onClick={() => open({ kind: "income" })}>
            Add income
          </Button>
        )
      }
    >
      {month.incomes.length === 0 ? (
        <p className={styles.empty}>
          Nothing has come in yet. Add your salary or any other income.
        </p>
      ) : (
        <ul className={styles.incomes}>
          {month.incomes.map((income) => (
            <li key={income.index}>
              <span className={styles.incomeDot} />
              <span className={styles.incomeText}>
                <b>{income.name}</b>
                <small>
                  {income.kind === "leftover" ? "carried over from last month" : "added this month"}
                </small>
              </span>
              <Amount value={income.amount} className={styles.incomeAmount} />
              {!readOnly && <Menu label={`Actions for ${income.name}`} items={menuFor(income)} />}
            </li>
          ))}
        </ul>
      )}
    </Widget>
  );
}

function SpendingCard() {
  const { month } = useMonthView();
  const slices = month.sections.map((section) => ({
    name: section.name,
    color: sectionAccent(section.color),
    value: Number(sectionSpent(section)) / 10_000,
  }));
  return (
    <Widget title="Where it went">
      {slices.every((slice) => slice.value === 0) ? (
        <p className={styles.empty}>
          Once you record transactions, this shows how your spending splits across sections.
        </p>
      ) : (
        <DonutChart
          title="Spending by section"
          slices={slices}
          centerValue={formatMoney(month.spent)}
          centerLabel="spent"
        />
      )}
    </Widget>
  );
}

// ---------------------------------------------------------------------------
// One section: a card that opens its page
// ---------------------------------------------------------------------------
function SectionCard({ section }: { section: Section }) {
  const { search } = useLocation();
  const spent = sectionSpent(section);
  const available = units(section.available);
  const used = Number(spent) / 10_000;
  const of = num(section.available);

  return (
    <Link
      to={{ pathname: `/budget/${section.index}`, search }}
      className={`glass ${styles.card}`}
      style={{ "--accent": sectionAccent(section.color) } as React.CSSProperties}
    >
      <div className={styles.cardTop}>
        <SectionIcon color={section.color} icon={section.icon} kind={section.kind} />
        <div className={styles.cardName}>
          <b>{section.name}</b>
          <small>
            {shareLabel(section)} · {count(section.fields.length, "field", "fields")}
          </small>
        </div>
        <ChevronRight size={20} className={styles.chevron} aria-hidden="true" />
      </div>

      <div className={styles.cardFigure}>
        <span className="label">rest</span>
        <Amount value={section.rest} className={styles.cardRest} />
      </div>

      <div className={styles.cardMeter}>
        <Meter
          used={used}
          of={of}
          color={sectionAccent(section.color)}
          label={`${section.name} spent of available`}
        />
        <p>
          <span>
            <b>{formatMoney(spent)}</b> spent of {formatMoney(available)}
          </span>
          <MeterWord used={used} of={of} />
        </p>
      </div>

      <p className={styles.cardFoot}>
        {isNegative(section.rest) && <span className={styles.warn}>⚠ negative rest · </span>}
        rest {routingLabel(section)}
      </p>
    </Link>
  );
}
