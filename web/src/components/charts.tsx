/**
 * The charts, drawn as plain SVG to the design system's chart rules: thin quiet
 * marks (2px lines, columns up to 24px with a rounded data end, 2px gaps),
 * hairline grid, a legend whenever colour carries identity, and a glass tooltip
 * on hover and keyboard focus.
 *
 * Geometry runs on plain numbers; that is fine for the position of a mark. The
 * amounts printed in the app itself still come from lib/money.
 */

import { useState, type CSSProperties, type ReactNode } from "react";
import { cx } from "../lib/cx";
import { daysIn, parseKey } from "../lib/dates";
import styles from "./charts.module.css";

const fmt = (value: number) =>
  value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const compact = (value: number) =>
  Math.abs(value) >= 1000 ? `${+(value / 1000).toFixed(1)}k` : `${Math.round(value)}`;
const round = (value: number) => Math.round(value * 10) / 10;

/** Round tick values covering 0…max. */
function ticksFor(max: number, count = 4): number[] {
  if (max <= 0) return [0, 1];
  const rough = max / count;
  const power = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? rough;
  const out: number[] = [];
  for (let v = 0; v < max + step * 0.999; v += step) out.push(+v.toFixed(6));
  return out;
}

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------
interface Tip {
  x: number;
  y: number;
  title?: string;
  rows: { color: string; value: string; name: string; dashed?: boolean }[];
}

function TipBox({ tip }: { tip: Tip | null }) {
  if (!tip) return null;
  const flip = tip.x > window.innerWidth - 220;
  return (
    <div
      className={cx("glass-strong", styles.tip)}
      style={{
        left: flip ? undefined : tip.x + 14,
        right: flip ? window.innerWidth - tip.x + 14 : undefined,
        top: Math.max(8, tip.y - 12),
      }}
      role="status"
    >
      {tip.title && <div className={styles.tipTitle}>{tip.title}</div>}
      {tip.rows.map((row) => (
        <div key={row.name} className={styles.tipRow}>
          <i
            style={
              row.dashed
                ? { borderTop: `2px dashed ${row.color}`, height: 0 }
                : { background: row.color }
            }
          />
          <b>{row.value}</b>
          <span>{row.name}</span>
        </div>
      ))}
    </div>
  );
}

export interface LegendItem {
  name: string;
  color: string;
  line?: "solid" | "dashed" | "dotted";
  detail?: string;
}

export function Legend({ items }: { items: LegendItem[] }) {
  return (
    <ul className={styles.legend}>
      {items.map((item) => (
        <li key={item.name}>
          {item.line ? (
            <i className={styles.lineKey} style={{ borderTop: `2px ${item.line} ${item.color}` }} />
          ) : (
            <i className={styles.swatch} style={{ background: item.color }} />
          )}
          {item.name}
          {item.detail && <b>{item.detail}</b>}
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Meter + gauge: how much of this is used?
// ---------------------------------------------------------------------------
function severity(ratio: number): { tone: "info" | "warn" | "error"; word: string } {
  if (ratio > 1) return { tone: "error", word: "Over budget" };
  if (ratio >= 0.8) return { tone: "warn", word: "Close to limit" };
  return { tone: "info", word: "On track" };
}

interface MeterProps {
  used: number;
  of: number;
  /** A section colour for the fill while things are on track. */
  color?: string;
  /** Thicker bar for a headline meter. */
  size?: "md" | "lg";
  label?: string;
}

/** A pill bar: the fill carries severity, and always with a word beside it. */
export function Meter({ used, of, color, size = "md", label }: MeterProps) {
  const ratio = of > 0 ? used / of : used > 0 ? 2 : 0;
  const { tone } = severity(ratio);
  const fill = tone === "info" ? (color ?? "var(--info)") : `var(--${tone})`;
  return (
    <div
      className={cx(styles.track, size === "lg" && styles.trackLg)}
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={Math.max(of, 0)}
      aria-valuenow={Math.max(used, 0)}
    >
      <i style={{ width: `${Math.min(100, Math.max(0, ratio * 100))}%`, background: fill }} />
    </div>
  );
}

/** "On track" / "Close to limit" / "Over budget", in the matching colour. */
export function MeterWord({ used, of }: { used: number; of: number }) {
  const ratio = of > 0 ? used / of : used > 0 ? 2 : 0;
  const { tone, word } = severity(ratio);
  if (of <= 0 && used <= 0) return <span className={styles.wordMuted}>Nothing budgeted</span>;
  return <span className={styles[`word-${tone}`]}>{word}</span>;
}

export function Gauge({ used, of, color, caption }: MeterProps & { caption?: ReactNode }) {
  const ratio = of > 0 ? used / of : used > 0 ? 2 : 0;
  const { tone, word } = severity(ratio);
  const fill = tone === "info" ? (color ?? "var(--info)") : `var(--${tone})`;
  const r = 70;
  const arc = Math.PI * r;
  const shown = Math.min(1, Math.max(0, ratio));
  return (
    <div className={styles.gauge}>
      <svg
        viewBox="0 0 180 104"
        width="100%"
        role="img"
        aria-label={`${Math.round(ratio * 100)}% used`}
      >
        <path
          d="M20 94a70 70 0 0 1 140 0"
          fill="none"
          stroke="var(--chart-track)"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d="M20 94a70 70 0 0 1 140 0"
          fill="none"
          stroke={fill}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${arc * shown} ${arc}`}
        />
        <text x="90" y="80" textAnchor="middle" className={styles.gaugeValue}>
          {Math.round(ratio * 100)}%
        </text>
      </svg>
      <div className={styles[`word-${tone}`]}>{word}</div>
      {caption && <div className={styles.gaugeCaption}>{caption}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sparkline + stat tile
// ---------------------------------------------------------------------------
function smooth(points: [number, number][]): string {
  const n = points.length;
  if (n < 2) return "";
  const dx: number[] = [];
  const m: number[] = [];
  for (let i = 0; i < n - 1; i++) {
    dx[i] = points[i + 1]![0] - points[i]![0];
    m[i] = (points[i + 1]![1] - points[i]![1]) / dx[i]!;
  }
  const t: number[] = [m[0]!];
  for (let i = 1; i < n - 1; i++) t[i] = m[i - 1]! * m[i]! <= 0 ? 0 : (m[i - 1]! + m[i]!) / 2;
  t[n - 1] = m[n - 2]!;
  let d = `M${round(points[0]![0])},${round(points[0]![1])}`;
  for (let i = 0; i < n - 1; i++) {
    const h = dx[i]! / 3;
    const [x0, y0] = points[i]!;
    const [x1, y1] = points[i + 1]!;
    d += ` C${round(x0 + h)},${round(y0 + t[i]! * h)} ${round(x1 - h)},${round(y1 - t[i + 1]! * h)} ${round(x1)},${round(y1)}`;
  }
  return d;
}

export function Sparkline({
  values,
  color = "var(--chart-1)",
}: {
  values: number[];
  color?: string;
}) {
  if (values.length < 2) return null;
  const w = 96;
  const h = 28;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const pts = values.map(
    (v, i) =>
      [
        4 + ((w - 12) * i) / (values.length - 1),
        4 + (h - 8) * (1 - (v - min) / (max - min || 1)),
      ] as [number, number],
  );
  const last = pts[pts.length - 1]!;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} aria-hidden="true">
      <path d={smooth(pts)} className={styles.line} style={{ stroke: "var(--chart-budget)" }} />
      <circle cx={last[0]} cy={last[1]} r="4" fill={color} className={styles.ring} />
    </svg>
  );
}

interface StatTileProps {
  label: string;
  value: ReactNode;
  /** "↓ 12.4%" with the period it compares against. */
  delta?: { text: string; good: boolean; versus: string };
  spark?: number[];
  sparkColor?: string;
  tone?: "plain" | "neg" | "pos" | "warn";
}

/** One headline number, its change against a named period, and a sparkline. */
export function StatTile({
  label,
  value,
  delta,
  spark,
  sparkColor,
  tone = "plain",
}: StatTileProps) {
  return (
    <div className={styles.stat}>
      <div className="label">{label}</div>
      <div className={cx(styles.statValue, tone !== "plain" && styles[`tone-${tone}`])}>
        {value}
      </div>
      {delta && (
        <div className={styles.delta}>
          <span className={delta.good ? "pos" : "neg"}>{delta.text}</span> {delta.versus}
        </div>
      )}
      {spark && spark.length > 1 && <Sparkline values={spark} color={sparkColor} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trend: lines over time
// ---------------------------------------------------------------------------
export interface TrendSeries {
  name: string;
  color: string;
  values: (number | null)[];
  line?: "solid" | "dashed" | "dotted";
  thin?: boolean;
  area?: boolean;
}

interface TrendChartProps {
  title: string;
  series: TrendSeries[];
  /** Label for position `i` (tooltip title). */
  labelAt: (index: number) => string;
  /** `[index, text]` pairs for the x axis. */
  xTicks: [number, string][];
  /** A vertical marker, e.g. today. */
  marker?: number;
  /** The chart spans the page: draw on a wider canvas so type stays small. */
  wide?: boolean;
}

const DASH = { solid: undefined, dashed: "6 5", dotted: "1.5 5" } as const;

export function TrendChart({ title, series, labelAt, xTicks, marker, wide }: TrendChartProps) {
  const [tip, setTip] = useState<(Tip & { index: number }) | null>(null);
  const W = wide ? 1120 : 640;
  const H = wide ? 280 : 240;
  const m = { l: 40, r: 16, t: 14, b: 28 };
  const n = Math.max(2, ...series.map((s) => s.values.length));
  const max = Math.max(1, ...series.flatMap((s) => s.values.map((v) => v ?? 0)));
  const ticks = ticksFor(max);
  const top = ticks[ticks.length - 1]!;
  const x = (i: number) => m.l + ((W - m.l - m.r) * i) / (n - 1);
  const y = (v: number) => m.t + (H - m.t - m.b) * (1 - v / top);

  function show(index: number, clientX: number, clientY: number) {
    const i = Math.max(0, Math.min(n - 1, index));
    setTip({
      index: i,
      x: clientX,
      y: clientY,
      title: labelAt(i),
      rows: series
        .filter((s) => s.values[i] != null)
        .map((s) => ({
          color: s.color,
          value: fmt(s.values[i]!),
          name: s.name,
          dashed: s.line !== undefined && s.line !== "solid",
        })),
    });
  }

  return (
    <div className={styles.chart}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label={title}
        tabIndex={0}
        onPointerMove={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          const px = ((e.clientX - box.left) * W) / box.width;
          show(Math.round((px - m.l) / ((W - m.l - m.r) / (n - 1))), e.clientX, e.clientY);
        }}
        onPointerLeave={() => setTip(null)}
        onBlur={() => setTip(null)}
        onKeyDown={(e) => {
          if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
          e.preventDefault();
          const box = e.currentTarget.getBoundingClientRect();
          const next = (tip?.index ?? n - 1) + (e.key === "ArrowLeft" ? -1 : 1);
          const i = Math.max(0, Math.min(n - 1, next));
          show(i, box.left + (x(i) * box.width) / W, box.top + box.height / 3);
        }}
      >
        {ticks.map((v) => (
          <g key={v}>
            <line
              x1={m.l}
              x2={W - m.r}
              y1={y(v)}
              y2={y(v)}
              className={v === 0 ? styles.axis : styles.grid}
            />
            <text x={m.l - 8} y={y(v) + 4} textAnchor="end" className={styles.tick}>
              {compact(v)}
            </text>
          </g>
        ))}
        {xTicks.map(([i, text]) => (
          <text key={i} x={x(i)} y={H - 8} textAnchor="middle" className={styles.tick}>
            {text}
          </text>
        ))}
        {marker !== undefined && (
          <line x1={x(marker)} x2={x(marker)} y1={m.t} y2={H - m.b} className={styles.grid} />
        )}
        {series.map((s) => {
          const pts = s.values.flatMap((v, i) =>
            v == null ? [] : [[x(i), y(v)] as [number, number]],
          );
          if (pts.length < 2) return null;
          const d = smooth(pts);
          const last = pts[pts.length - 1]!;
          return (
            <g key={s.name}>
              {s.area && (
                <path
                  d={`${d} L${round(last[0])},${y(0)} L${round(pts[0]![0])},${y(0)} Z`}
                  fill={s.color}
                  fillOpacity="0.12"
                />
              )}
              <path
                d={d}
                className={styles.line}
                style={{
                  stroke: s.color,
                  strokeWidth: s.thin ? 1.5 : 2.5,
                  strokeDasharray: DASH[s.line ?? "solid"],
                }}
              />
              {(s.line ?? "solid") === "solid" && !s.thin && (
                <circle cx={last[0]} cy={last[1]} r="4" fill={s.color} className={styles.ring} />
              )}
            </g>
          );
        })}
        {tip && (
          <line
            x1={x(tip.index)}
            x2={x(tip.index)}
            y1={m.t}
            y2={H - m.b}
            className={styles.cross}
          />
        )}
      </svg>
      <Legend
        items={series.map((s) => ({ name: s.name, color: s.color, line: s.line ?? "solid" }))}
      />
      <TipBox tip={tip} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Donut: what share went where?
// ---------------------------------------------------------------------------
export interface Slice {
  name: string;
  color: string;
  value: number;
}

export function DonutChart({
  title,
  slices,
  centerValue,
  centerLabel,
}: {
  title: string;
  slices: Slice[];
  centerValue: string;
  centerLabel: string;
}) {
  const [tip, setTip] = useState<Tip | null>(null);
  const shown = slices.filter((s) => s.value > 0);
  const total = shown.reduce((sum, s) => sum + s.value, 0);
  const r = 62;
  const c = 2 * Math.PI * r;
  const gap = shown.length > 1 ? 3 : 0;
  // Each slice starts where the previous ones end.
  const arcs = shown.map((slice, i) => ({
    slice,
    length: (slice.value / total) * c,
    offset: shown.slice(0, i).reduce((sum, s) => sum + (s.value / total) * c, 0),
  }));

  return (
    <div className={styles.donutWrap}>
      <svg viewBox="0 0 160 160" className={styles.donut} role="img" aria-label={title}>
        <circle cx="80" cy="80" r={r} fill="none" stroke="var(--chart-track)" strokeWidth="18" />
        {arcs.map(({ slice, length, offset }) => {
          const dash = `${Math.max(0, length - gap)} ${c}`;
          return (
            <circle
              key={slice.name}
              cx="80"
              cy="80"
              r={r}
              fill="none"
              stroke={slice.color}
              strokeWidth="18"
              strokeDasharray={dash}
              strokeDashoffset={-offset}
              transform="rotate(-90 80 80)"
              className={styles.mark}
              tabIndex={0}
              onPointerMove={(e) =>
                setTip({
                  x: e.clientX,
                  y: e.clientY,
                  rows: [
                    {
                      color: slice.color,
                      value: fmt(slice.value),
                      name: `${slice.name} · ${Math.round((slice.value / total) * 100)}%`,
                    },
                  ],
                })
              }
              onPointerLeave={() => setTip(null)}
            />
          );
        })}
        <text x="80" y="78" textAnchor="middle" className={styles.donutValue}>
          {centerValue}
        </text>
        <text x="80" y="96" textAnchor="middle" className={styles.tick}>
          {centerLabel}
        </text>
      </svg>
      <Legend
        items={slices.map((s) => ({
          name: s.name,
          color: s.color,
          detail: total > 0 ? `${fmt(s.value)} · ${Math.round((s.value / total) * 100)}%` : fmt(0),
        }))}
      />
      <TipBox tip={tip} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Columns: one stack per period
// ---------------------------------------------------------------------------
export function ColumnChart({
  title,
  categories,
  stacks,
  reference,
  wide,
}: {
  title: string;
  categories: string[];
  stacks: { name: string; color: string; values: number[] }[];
  /** A marker per category (e.g. that month's income). */
  reference?: { name: string; values: number[] };
  wide?: boolean;
}) {
  const [tip, setTip] = useState<Tip | null>(null);
  const W = wide ? 1120 : 640;
  const H = wide ? 280 : 240;
  const m = { l: 40, r: 12, t: 14, b: 28 };
  const totals = categories.map((_, i) => stacks.reduce((sum, s) => sum + (s.values[i] ?? 0), 0));
  const max = Math.max(1, ...totals, ...(reference?.values ?? []));
  const ticks = ticksFor(max);
  const top = ticks[ticks.length - 1]!;
  const y = (v: number) => m.t + (H - m.t - m.b) * (1 - v / top);
  const band = (W - m.l - m.r) / Math.max(1, categories.length);
  const bw = Math.min(24, band * 0.5);

  return (
    <div className={styles.chart}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={title}>
        {ticks.map((v) => (
          <g key={v}>
            <line
              x1={m.l}
              x2={W - m.r}
              y1={y(v)}
              y2={y(v)}
              className={v === 0 ? styles.axis : styles.grid}
            />
            <text x={m.l - 8} y={y(v) + 4} textAnchor="end" className={styles.tick}>
              {compact(v)}
            </text>
          </g>
        ))}
        {categories.map((category, ci) => {
          const cx0 = m.l + band * ci + band / 2;
          let base = 0;
          const present = stacks.filter((s) => (s.values[ci] ?? 0) > 0);
          return (
            <g
              key={category}
              className={styles.mark}
              tabIndex={0}
              onPointerMove={(e) =>
                setTip({
                  x: e.clientX,
                  y: e.clientY,
                  title: category,
                  rows: [
                    ...present.map((s) => ({
                      color: s.color,
                      value: fmt(s.values[ci]!),
                      name: s.name,
                    })),
                    ...(reference
                      ? [
                          {
                            color: "var(--text-strong)",
                            value: fmt(reference.values[ci] ?? 0),
                            name: reference.name,
                          },
                        ]
                      : []),
                  ],
                })
              }
              onPointerLeave={() => setTip(null)}
            >
              <rect
                x={cx0 - band / 2}
                y={m.t}
                width={band}
                height={H - m.t - m.b}
                fill="transparent"
              />
              {present.map((s, si) => {
                const v = s.values[ci]!;
                const y0 = y(base + v);
                const h = Math.max(0, y(base) - y0 - (si < present.length - 1 ? 2 : 0));
                base += v;
                const isTop = si === present.length - 1;
                return (
                  <rect
                    key={s.name}
                    x={cx0 - bw / 2}
                    y={y0 + (isTop ? 0 : 2)}
                    width={bw}
                    height={h}
                    rx={isTop ? 4 : 0}
                    fill={s.color}
                  />
                );
              })}
              {reference && (
                <line
                  x1={cx0 - bw / 2 - 5}
                  x2={cx0 + bw / 2 + 5}
                  y1={y(reference.values[ci] ?? 0)}
                  y2={y(reference.values[ci] ?? 0)}
                  stroke="var(--text-strong)"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              )}
              <text x={cx0} y={H - 8} textAnchor="middle" className={styles.tick}>
                {category}
              </text>
            </g>
          );
        })}
      </svg>
      <Legend
        items={[
          ...stacks.map((s) => ({ name: s.name, color: s.color })),
          ...(reference
            ? [{ name: reference.name, color: "var(--text-strong)", line: "solid" as const }]
            : []),
        ]}
      />
      <TipBox tip={tip} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Waterfall: income stepping down through the sections
// ---------------------------------------------------------------------------
export function WaterfallChart({
  title,
  income,
  steps,
}: {
  title: string;
  income: number;
  steps: Slice[];
}) {
  const [tip, setTip] = useState<Tip | null>(null);
  const W = 640;
  const H = 240;
  const m = { l: 40, r: 12, t: 22, b: 28 };
  const ticks = ticksFor(Math.max(1, income));
  const top = ticks[ticks.length - 1]!;
  const y = (v: number) => m.t + (H - m.t - m.b) * (1 - v / top);
  const cols = steps.length + 1;
  const band = (W - m.l - m.r) / cols;
  const bw = Math.min(40, band * 0.56);
  const bars: { name: string; color: string; from: number; to: number; value: number }[] = [
    { name: "Income", color: "var(--income-accent)", from: 0, to: income, value: income },
  ];
  let remaining = income;
  for (const step of steps) {
    bars.push({
      name: step.name,
      color: step.color,
      from: remaining - step.value,
      to: remaining,
      value: -step.value,
    });
    remaining -= step.value;
  }

  return (
    <div className={styles.chart}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={title}>
        {ticks.map((v) => (
          <g key={v}>
            <line
              x1={m.l}
              x2={W - m.r}
              y1={y(v)}
              y2={y(v)}
              className={v === 0 ? styles.axis : styles.grid}
            />
            <text x={m.l - 8} y={y(v) + 4} textAnchor="end" className={styles.tick}>
              {compact(v)}
            </text>
          </g>
        ))}
        {bars.map((bar, i) => {
          const cx0 = m.l + band * i + band / 2;
          const yTop = y(Math.max(bar.from, bar.to));
          const h = Math.max(2, Math.abs(y(bar.from) - y(bar.to)));
          return (
            <g
              key={bar.name}
              className={styles.mark}
              tabIndex={0}
              onPointerMove={(e) =>
                setTip({
                  x: e.clientX,
                  y: e.clientY,
                  title: bar.name,
                  rows: [
                    {
                      color: bar.color,
                      value: fmt(Math.abs(bar.value)),
                      name: i === 0 ? "comes in" : "set aside",
                    },
                    {
                      color: "var(--chart-track)",
                      value: fmt(i === 0 ? income : bar.from),
                      name: "still unassigned",
                    },
                  ],
                })
              }
              onPointerLeave={() => setTip(null)}
            >
              <rect x={cx0 - bw / 2} y={yTop} width={bw} height={h} rx="4" fill={bar.color} />
              {i < bars.length - 1 && (
                <line
                  x1={cx0 + bw / 2}
                  x2={cx0 + band - bw / 2}
                  y1={y(i === 0 ? bar.to : bar.from)}
                  y2={y(i === 0 ? bar.to : bar.from)}
                  className={styles.axis}
                />
              )}
              <text x={cx0} y={yTop - 6} textAnchor="middle" className={styles.dataLabel}>
                {i === 0 ? compact(bar.value) : `-${compact(-bar.value)}`}
              </text>
              <text x={cx0} y={H - 8} textAnchor="middle" className={styles.tick}>
                {bar.name.length > 10 ? `${bar.name.slice(0, 9)}…` : bar.name}
              </text>
            </g>
          );
        })}
      </svg>
      <p className={styles.status}>
        {Math.abs(remaining) < 0.005 ? (
          <span className="pos">✓ Fully allocated</span>
        ) : remaining > 0 ? (
          <span className={styles["word-warn"]}>⚠ {fmt(remaining)} unassigned</span>
        ) : (
          <span className="neg">⚠ {fmt(-remaining)} more than income</span>
        )}
      </p>
      <TipBox tip={tip} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Heatmap calendar: which days did I spend on?
// ---------------------------------------------------------------------------
export function HeatmapCalendar({
  monthKey,
  byDay,
  today,
}: {
  monthKey: string;
  /** Spend per day; index 0 is day 1. */
  byDay: number[];
  /** Today's day number when this is the current month. */
  today?: number;
}) {
  const [tip, setTip] = useState<Tip | null>(null);
  const { year, month } = parseKey(monthKey);
  const days = daysIn(monthKey);
  const lead = (new Date(year, month - 1, 1).getDay() + 6) % 7; // Monday first
  const max = Math.max(0, ...byDay);
  const level = (v: number) => (v <= 0 || max <= 0 ? 0 : Math.min(5, Math.ceil((v / max) * 5)));
  const name = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });

  return (
    <div>
      <div className={styles.heat}>
        {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
          <span key={i} className={styles.heatHead}>
            {d}
          </span>
        ))}
        {Array.from({ length: lead }, (_, i) => (
          <span key={`lead-${i}`} />
        ))}
        {Array.from({ length: days }, (_, i) => {
          const day = i + 1;
          const value = byDay[i] ?? 0;
          const lv = level(value);
          const future = today !== undefined && day > today;
          return (
            <span
              key={day}
              className={cx(styles.cell, future && styles.future, day === today && styles.today)}
              style={
                future
                  ? undefined
                  : ({
                      background: `var(--heat-${lv})`,
                      color: lv > 0 ? `var(--heat-ink-${lv})` : undefined,
                    } as CSSProperties)
              }
              tabIndex={0}
              onPointerMove={(e) =>
                setTip({
                  x: e.clientX,
                  y: e.clientY,
                  title: name.format(new Date(year, month - 1, day)),
                  rows: [
                    { color: `var(--heat-${Math.max(lv, 1)})`, value: fmt(value), name: "spent" },
                  ],
                })
              }
              onPointerLeave={() => setTip(null)}
            >
              {day}
            </span>
          );
        })}
      </div>
      <div className={styles.heatKey}>
        Less
        {[0, 1, 2, 3, 4, 5].map((lv) => (
          <i key={lv} style={{ background: `var(--heat-${lv})` }} />
        ))}
        More
      </div>
      <TipBox tip={tip} />
    </div>
  );
}
