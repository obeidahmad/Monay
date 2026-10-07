import { ArrowLeft, Pencil, Plus } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router";
import type { Field, Section } from "../../api/client";
import { useMonthView } from "../../app/month";
import { Page } from "../../app/Page";
import { useSheet } from "../../app/sheets";
import { useAct } from "../../app/useAct";
import { Amount } from "../../components/Amount";
import { Button } from "../../components/Button";
import { DonutChart, Gauge, Meter, MeterWord, StatTile, TrendChart } from "../../components/charts";
import { EmptyState } from "../../components/EmptyState";
import { Menu, type MenuEntry } from "../../components/Menu";
import { SectionIcon } from "../../components/SectionIcon";
import { TransactionRow } from "../../components/TransactionRow";
import { Widget } from "../../components/Widget";
import { budgetLabel, num, routingLabel, sectionAccent, shareLabel } from "../../lib/budget";
import { dayLabel, daysIn } from "../../lib/dates";
import { cumulative, dailySpend, pace, sectionSpent, throughDay } from "../../lib/insights";
import { formatMoney, isZero } from "../../lib/money";
import styles from "./SectionPage.module.css";

// Shades for the fields of one section in its donut: the section's colour,
// stepping towards the surface so neighbours differ in lightness, not hue.
const shade = (accent: string, index: number) =>
  `color-mix(in srgb, ${accent} ${Math.max(28, 100 - index * 18)}%, var(--surface-raised))`;

/** Everything about one section: its fields, its spending, its transactions. */
export function SectionPage() {
  const { index } = useParams();
  const { month, readOnly, actions } = useMonthView();
  const { search } = useLocation();
  const navigate = useNavigate();
  const open = useSheet();
  const act = useAct();

  const section = month.sections[Number(index)];
  if (!section) return <Navigate to={{ pathname: "/budget", search }} replace />;

  const accent = sectionAccent(section.color);
  const spent = sectionSpent(section);
  const used = Number(spent) / 10_000;
  const available = num(section.available);
  const last = month.sections.length - 1;
  const transactions = month.transactions
    .filter((tx) => tx.field.section_index === section.index)
    .sort((a, b) => b.day - a.day || b.number - a.number);

  const through = throughDay(month.key);
  const spentByDay = cumulative(dailySpend(month, section.index));
  const days = daysIn(month.key);

  const move = (to: number) =>
    void act(() => actions.editSection(section.index, { position: to }), {
      message: `${section.name} moved.`,
    }).then((moved) => moved && navigate({ pathname: `/budget/${to}`, search }, { replace: true }));

  const more: MenuEntry[] = [
    { label: "Transfer between fields", onSelect: () => open({ kind: "transfer" }) },
    {
      label: "Move earlier",
      disabled: section.index === 0,
      onSelect: () => move(section.index - 1),
    },
    {
      label: "Move later",
      disabled: section.index === last,
      onSelect: () => move(section.index + 1),
    },
    "divider",
    {
      label: "Delete section",
      danger: true,
      onSelect: () =>
        void act(() => actions.deleteSection(section.index), {
          kind: "info",
          message: `Section ${section.name} deleted`,
        }).then((deleted) => deleted && navigate({ pathname: "/budget", search })),
    },
  ];

  return (
    <Page
      title={section.name}
      subtitle={`${shareLabel(section)} · rest ${routingLabel(section)}`}
      lead={
        <>
          <Link
            to={{ pathname: "/budget", search }}
            className={styles.back}
            aria-label="Back to Budget"
          >
            <ArrowLeft size={20} />
          </Link>
          <SectionIcon color={section.color} icon={section.icon} kind={section.kind} size="lg" />
        </>
      }
      primary={{ label: "Add transaction", onClick: () => open({ kind: "transaction" }) }}
      actions={
        <>
          <Menu label={`More actions for ${section.name}`} items={more} />
          <Button
            icon={<Pencil size={16} />}
            onClick={() => open({ kind: "section", edit: section })}
          >
            Edit
          </Button>
          <Button
            variant="primary"
            icon={<Plus size={18} />}
            onClick={() => open({ kind: "field", section })}
          >
            Add field
          </Button>
        </>
      }
    >
      <section
        className={`glass ${styles.summary}`}
        style={{ "--accent": accent } as React.CSSProperties}
      >
        <div className={styles.tiles}>
          <StatTile label="Available" value={formatMoney(section.available)} />
          <StatTile label="Spent" value={formatMoney(spent)} />
          <StatTile
            label="Rest"
            value={formatMoney(section.rest)}
            tone={section.rest.startsWith("-") ? "neg" : "plain"}
          />
          <StatTile label="Budget left" value={formatMoney(section.budget_left)} />
        </div>
        <div className={styles.summaryMeter}>
          <Meter used={used} of={available} size="lg" color={accent} label="Spent of available" />
          <p>
            <span>
              <b>{formatMoney(spent)}</b> spent of {formatMoney(section.available)} available
              {!isZero(section.carried_rest) &&
                ` (includes ${formatMoney(section.carried_rest)} carried in)`}
            </span>
            <MeterWord used={used} of={available} />
          </p>
        </div>
      </section>

      <div className={styles.columns}>
        <Widget
          title="Fields"
          actions={
            !readOnly && (
              <Button
                size="sm"
                icon={<Plus size={16} />}
                onClick={() => open({ kind: "field", section })}
              >
                Add field
              </Button>
            )
          }
        >
          {section.fields.length === 0 ? (
            <EmptyState
              title="No fields yet"
              action={
                !readOnly && (
                  <Button variant="primary" onClick={() => open({ kind: "field", section })}>
                    Add field
                  </Button>
                )
              }
            >
              A field is a budget line inside this section: Groceries, Rent, Emergency fund.
            </EmptyState>
          ) : (
            <ul className={styles.fields}>
              {section.fields.map((field) => (
                <FieldCard key={field.index} section={section} field={field} />
              ))}
            </ul>
          )}
        </Widget>

        <div className={styles.side}>
          <Widget title="Used so far">
            <Gauge
              used={used}
              of={available}
              color={accent}
              caption={`${formatMoney(spent)} paid · ${formatMoney(section.rest)} rest`}
            />
          </Widget>
          <Widget title="By field">
            {used === 0 ? (
              <p className={styles.muted}>Nothing spent in this section yet.</p>
            ) : (
              <DonutChart
                title={`${section.name} spending by field`}
                slices={section.fields.map((field, i) => ({
                  name: field.name,
                  color: shade(accent, i),
                  value: num(field.paid),
                }))}
                centerValue={formatMoney(spent)}
                centerLabel="spent"
              />
            )}
          </Widget>
        </div>
      </div>

      <Widget title="Spending this month">
        <TrendChart
          wide
          title={`${section.name}: spending through the month`}
          labelAt={(i) => dayLabel(month.key, i + 1)}
          xTicks={[0, 6, 13, 20, days - 1].map((i) => [i, dayLabel(month.key, i + 1)])}
          marker={through > 0 && through < days ? through - 1 : undefined}
          series={[
            {
              name: "Spent",
              color: accent,
              values: spentByDay.map((v, i) => (i < through ? v : null)),
              area: true,
            },
            {
              name: "Available, spread evenly",
              color: "var(--chart-budget)",
              values: pace(month.key, Math.max(0, available)),
              line: "dashed",
              thin: true,
            },
          ]}
        />
      </Widget>

      <Widget title="Transactions">
        {transactions.length === 0 ? (
          <p className={styles.muted}>No transactions in {section.name} this month.</p>
        ) : (
          <ul className={styles.list}>
            {transactions.map((tx) => (
              <TransactionRow
                key={tx.number}
                kind="spend"
                avatar={
                  <SectionIcon
                    color={section.color}
                    icon={section.icon}
                    kind={section.kind}
                    size="sm"
                  />
                }
                title={tx.field.field}
                detail={[`#${tx.number}`, dayLabel(month.key, tx.day), tx.description]
                  .filter(Boolean)
                  .join(" · ")}
                amount={tx.amount}
                onOpen={readOnly ? undefined : () => open({ kind: "transaction", edit: tx })}
              />
            ))}
          </ul>
        )}
      </Widget>
    </Page>
  );
}

function FieldCard({ section, field }: { section: Section; field: Field }) {
  const { readOnly, actions } = useMonthView();
  const open = useSheet();
  const act = useAct();
  const ref = { section: section.index, field: field.index };
  const paid = num(field.paid);
  const budget = num(field.budget);

  const menu: MenuEntry[] = [
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

  const body = (
    <>
      <span className={styles.fieldTop}>
        <span className={styles.fieldName}>
          <b>{field.name}</b>
          <small>
            {field.pocket} · max {field.max === null ? "∞" : formatMoney(field.max)}
          </small>
        </span>
        <span className={styles.fieldLeft}>
          <Amount value={field.left} tone="balance" />
          <small>left</small>
        </span>
      </span>
      <Meter
        used={paid}
        of={budget}
        color={sectionAccent(section.color)}
        label={`${field.name} paid of budget`}
      />
      <span className={styles.fieldFoot}>
        <span>
          <b>{formatMoney(field.paid)}</b> paid of {budgetLabel(field)} · started with{" "}
          {formatMoney(field.current)}
        </span>
        <MeterWord used={paid} of={budget} />
      </span>
    </>
  );

  return (
    <li className={styles.field}>
      {readOnly ? (
        <div className={styles.fieldMain}>{body}</div>
      ) : (
        <>
          <button
            type="button"
            className={styles.fieldMain}
            onClick={() => open({ kind: "field", section, edit: field })}
          >
            {body}
          </button>
          <Menu label={`Actions for ${field.name}`} items={menu} />
        </>
      )}
    </li>
  );
}
