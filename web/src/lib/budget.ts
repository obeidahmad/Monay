/** Small pieces of budget presentation shared by several screens. */

import type { Field, Month, Section } from "../api/client";
import { formatMoney, units, type Units } from "./money";

/**
 * A section's accent from its palette slot (1–8): the colour chosen for it, or
 * the one its position gives it. A section keeps that colour everywhere.
 */
export function sectionAccent(color: number): string {
  return `var(--section-${color})`;
}

/** A plain number for a chart's geometry (never for an amount that is printed). */
export function num(value: string): number {
  return Number(value);
}

export const INCOME_ACCENT = "var(--income-accent)";

/** "post · 50%" / "pre · 500.00" — a section's kind and share. */
export function shareLabel(section: Section): string {
  const { type, value } = section.allocation;
  return `${section.kind} · ${type === "percent" ? `${value}%` : formatMoney(value)}`;
}

/** Where a section's REST goes at close, in the app's words. */
export function routingLabel(section: Section): string {
  const { kind, target } = section.rest_routing;
  if (kind === "income") return "→ income";
  if (kind === "self") return "→ carries over";
  return `→ ${target ?? "income"}`;
}

/** A field's budget as shown in the table: `300.00`, or `20% → 150.00`. */
export function budgetLabel(field: Field): string {
  const amount = formatMoney(field.budget);
  return field.budget_pct === null ? amount : `${field.budget_pct}% → ${amount}`;
}

/**
 * What a field's LEFT would be after spending `spend` more (and getting
 * `refund` back — the old amount, when a transaction is being edited).
 *
 * The engine's rule: LEFT = min(CURRENT + BUDGET − PAID, MAX), then transfers
 * move LEFT on top of that. This only previews it; the server recomputes.
 */
export function leftAfter(field: Field, spend: Units, refund: Units = 0n): Units {
  const cap = field.max === null ? null : units(field.max);
  const clamp = (value: Units): Units => (cap !== null && value > cap ? cap : value);
  const pot = units(field.current) + units(field.budget) - units(field.paid);
  const moved = units(field.left) - clamp(pot); // net effect of transfers
  return clamp(pot - spend + refund) + moved;
}

/**
 * How far the post-sections' percentages are from 100, worked out on the
 * decimal digits themselves — `33.33 + 33.33 + 33.34` is exactly 100 here,
 * which it is not in floating point.
 */
export function percentGap(total: string): {
  state: "balanced" | "under" | "over";
  /** The distance from 100 as a bare number, e.g. `"2"` or `"0.5"`. */
  by: string;
} {
  const [whole = "0", fraction = ""] = total.split(".");
  const scale = 10n ** BigInt(fraction.length);
  const difference = 100n * scale - BigInt(whole + fraction);
  if (difference === 0n) return { state: "balanced", by: "0" };
  const magnitude = difference < 0n ? -difference : difference;
  const decimals = (magnitude % scale).toString().padStart(fraction.length, "0");
  const by = fraction ? `${magnitude / scale}.${decimals}`.replace(/\.?0+$/, "") : `${magnitude}`;
  return { state: difference > 0n ? "under" : "over", by };
}

/** A bare percentage a person typed: a number from 0 to 100. */
export function isPercentage(text: string): boolean {
  const value = text.trim();
  return /^\d{1,3}(\.\d+)?$/.test(value) && Number(value) <= 100;
}

/** Every field of a month with the section it sits in, in display order. */
export function allFields(month: Month): { section: Section; field: Field }[] {
  return month.sections.flatMap((section) => section.fields.map((field) => ({ section, field })));
}

export function findField(month: Month, section: number, field: number) {
  const owner = month.sections[section];
  const found = owner?.fields[field];
  return owner && found ? { section: owner, field: found } : null;
}
