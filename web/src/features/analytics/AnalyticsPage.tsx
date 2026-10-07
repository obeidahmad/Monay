import { useMonth, useMonths } from "../../api/queries";
import { useMonthView } from "../../app/month";
import { Page } from "../../app/Page";
import {
  ColumnChart,
  DonutChart,
  HeatmapCalendar,
  StatTile,
  TrendChart,
  WaterfallChart,
  type TrendSeries,
} from "../../components/charts";
import { Widget } from "../../components/Widget";
import { num, sectionAccent } from "../../lib/budget";
import { currentKey, dayLabel, daysIn } from "../../lib/dates";
import {
  change,
  cumulative,
  dailySpend,
  pace,
  sectionBudget,
  sectionSpent,
  throughDay,
} from "../../lib/insights";
import { formatMoney } from "../../lib/money";
import styles from "./AnalyticsPage.module.css";

/** The Analytics tab: one question per chart, all about the month on screen. */
export function AnalyticsPage() {
  const { profileId, month } = useMonthView();
  const months = useMonths(profileId);

  // History, oldest first, up to and including the month on screen.
  const history = [...(months.data ?? [])].reverse().filter((m) => m.key <= month.key);
  const previous = history.length > 1 ? history[history.length - 2] : undefined;
  const lastMonth = useMonth(profileId, previous?.key ?? month.key);

  const income = num(month.total_income);
  const spent = num(month.spent);
  const net = income - spent;
  const rate = income > 0 ? (net / income) * 100 : 0;
  const prevIncome = previous && num(previous.income);
  const prevSpent = previous && num(previous.spent);
  const versus = previous ? `vs ${previous.label.split(" ")[0]}` : "";
  const delta = (text: string | null, good: boolean) => (text ? { text, good, versus } : undefined);

  const days = daysIn(month.key);
  const through = throughDay(month.key);
  const spentByDay = dailySpend(month);
  const budget = month.sections.reduce((total, s) => total + Number(sectionBudget(s)) / 10_000, 0);
  const trend: TrendSeries[] = [
    {
      name: "Spent",
      color: "var(--chart-spent)",
      values: cumulative(spentByDay).map((v, i) => (i < through ? v : null)),
      area: true,
    },
    {
      name: "Budget pace",
      color: "var(--chart-budget)",
      values: pace(month.key, budget),
      line: "dashed",
    },
  ];
  if (previous && lastMonth.data && lastMonth.data.key === previous.key) {
    trend.push({
      name: previous.label,
      color: "var(--chart-last)",
      values: cumulative(dailySpend(lastMonth.data)).slice(0, days),
      thin: true,
    });
  }

  const slices = month.sections.map((s) => ({
    name: s.name,
    color: sectionAccent(s.color),
    value: Number(sectionSpent(s)) / 10_000,
  }));

  // Spending by section across months: a section keeps its name and colour.
  const recent = history.slice(-6);
  const names = [...new Set(recent.flatMap((m) => m.sections.map((s) => s.name)))];
  const stacks = names.map((name) => ({
    name,
    color: sectionAccent(
      [...recent]
        .reverse()
        .flatMap((m) => m.sections)
        .find((s) => s.name === name)?.color ?? 1,
    ),
    values: recent.map((m) => num(m.sections.find((s) => s.name === name)?.spent ?? "0")),
  }));

  return (
    <Page title="Analytics" subtitle={`${month.label} · ${month.state}`}>
      <Widget>
        <div className={styles.tiles}>
          <StatTile
            label="Spent"
            value={formatMoney(month.spent)}
            delta={delta(change(spent, prevSpent), spent <= (prevSpent ?? spent))}
            spark={history.map((m) => num(m.spent))}
            sparkColor="var(--chart-spent)"
          />
          <StatTile
            label="Income"
            value={formatMoney(month.total_income)}
            delta={delta(change(income, prevIncome), income >= (prevIncome ?? income))}
            spark={history.map((m) => num(m.income))}
            sparkColor="var(--chart-income)"
          />
          <StatTile
            label="Net"
            value={`${net >= 0 ? "+" : ""}${formatMoney(net.toFixed(4))}`}
            tone={net < 0 ? "neg" : "plain"}
            spark={history.map((m) => num(m.income) - num(m.spent))}
          />
          <StatTile label="Kept" value={`${Math.round(rate)}%`} />
        </div>
      </Widget>

      <div className={styles.pair}>
        <Widget title="Where is my spending heading?">
          <TrendChart
            title="Cumulative spending against the budget pace"
            labelAt={(i) => dayLabel(month.key, i + 1)}
            xTicks={[0, 6, 13, 20, days - 1].map((i) => [i, dayLabel(month.key, i + 1)])}
            marker={through > 0 && through < days ? through - 1 : undefined}
            series={trend}
          />
        </Widget>
        <Widget title="What share went where?">
          {spent === 0 ? (
            <p className={styles.muted}>Nothing spent yet this month.</p>
          ) : (
            <DonutChart
              title="Spending by section"
              slices={slices}
              centerValue={formatMoney(month.spent)}
              centerLabel="spent"
            />
          )}
        </Widget>
      </div>

      <div className={styles.pair}>
        <Widget title="Where does my income go?">
          <WaterfallChart
            title="Income stepping down through the sections"
            income={income}
            steps={month.sections.map((s) => ({
              name: s.name,
              color: sectionAccent(s.color),
              value: num(s.available) - num(s.carried_rest),
            }))}
          />
        </Widget>
        <Widget title="Which days did I spend on?">
          <HeatmapCalendar
            monthKey={month.key}
            byDay={spentByDay}
            today={month.key === currentKey() ? through : undefined}
          />
        </Widget>
      </div>

      <Widget title="How did each month compare?">
        {recent.length === 0 ? (
          <p className={styles.muted}>No months yet.</p>
        ) : (
          <ColumnChart
            wide
            title="Spending by section, month by month"
            categories={recent.map((m) => m.key)}
            stacks={stacks}
            reference={{ name: "Income", values: recent.map((m) => num(m.income)) }}
          />
        )}
      </Widget>
    </Page>
  );
}
