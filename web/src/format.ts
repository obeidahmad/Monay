// Display helpers: amounts with two decimals and thousands separators.

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function fmt(amount: string | null | undefined): string {
  if (amount === null || amount === undefined) return "∞";
  const negative = amount.startsWith("-");
  const [whole, cents = "00"] = amount.replace("-", "").split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "-" : ""}${grouped}.${cents.padEnd(2, "0")}`;
}

export const isNeg = (amount: string) => amount.startsWith("-") && Number(amount) !== 0;

export function dayLabel(day: number, monthKey: string): string {
  const month = Number(monthKey.split("-")[1]);
  return `${day} ${MONTHS[month - 1]}`;
}

export function daysIn(monthKey: string): number {
  const [y, m] = monthKey.split("-").map(Number);
  return new Date(y, m, 0).getDate();
}

/** Today's day if the viewed month is the current calendar month, else 1. */
export function defaultDay(monthKey: string): number {
  const now = new Date();
  const key = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  return key === monthKey ? now.getDate() : 1;
}

export const accentVar = (index: number) => `var(--section-${(index % 8) + 1})`;
