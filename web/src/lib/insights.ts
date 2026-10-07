/**
 * Figures the charts and cards are drawn from, derived from a month the engine
 * already computed. Plain numbers: these feed geometry and percentages.
 */

import type { Month, Section } from "../api/client";
import { currentKey, daysIn } from "./dates";
import { units, type Units } from "./money";

const sum = (values: Units[]): Units => values.reduce((total, value) => total + value, 0n);

/** What has been paid out of a section this month. */
export function sectionSpent(section: Section): Units {
  return sum(section.fields.map((field) => units(field.paid)));
}

/** Σ of the fields' budgets in a section. */
export function sectionBudget(section: Section): Units {
  return sum(section.fields.map((field) => units(field.budget)));
}

/** Spend per day; index 0 is day 1. Optionally for one section only. */
export function dailySpend(month: Month, section?: number): number[] {
  const days = Array.from({ length: daysIn(month.key) }, () => 0);
  for (const tx of month.transactions) {
    if (section !== undefined && tx.field.section_index !== section) continue;
    const slot = Math.min(days.length, Math.max(1, tx.day)) - 1;
    days[slot] = (days[slot] ?? 0) + Number(tx.amount);
  }
  return days;
}

export const cumulative = (values: number[]): number[] => {
  let total = 0;
  return values.map((value) => (total += value));
};

/** Today's day when `key` is the current month; the last day when it is past. */
export function throughDay(key: string, now: Date = new Date()): number {
  const today = currentKey(now);
  if (key === today) return now.getDate();
  return key < today ? daysIn(key) : 0;
}

/** A straight line from 0 to `total` across the month: the pace of a budget. */
export function pace(key: string, total: number): number[] {
  const days = daysIn(key);
  return Array.from({ length: days }, (_, i) => (total * (i + 1)) / days);
}

/** "↓ 12.4%" against a previous value; null when there is nothing to compare. */
export function change(current: number, previous: number | undefined): string | null {
  if (previous === undefined || previous === 0) return null;
  const pct = ((current - previous) / Math.abs(previous)) * 100;
  if (Math.abs(pct) < 0.05) return "→ 0%";
  return `${pct > 0 ? "↑" : "↓"} ${Math.abs(pct).toFixed(1)}%`;
}
