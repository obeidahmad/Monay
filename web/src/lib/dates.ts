/** Month keys (`yyyy-mm`) and days of the month, as the app shows them. */

export function parseKey(key: string): { year: number; month: number } {
  const [year = "0", month = "1"] = key.split("-");
  return { year: Number(year), month: Number(month) };
}

/** Today's month, in the user's own time zone. */
export function currentKey(now: Date = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function daysIn(key: string): number {
  const { year, month } = parseKey(key);
  return new Date(year, month, 0).getDate(); // day 0 of the next month
}

/**
 * The day a new entry most likely belongs to: today when the month is the
 * current one, otherwise the nearest day that month has.
 */
export function defaultDay(key: string, now: Date = new Date()): number {
  const today = currentKey(now);
  if (key === today) return now.getDate();
  return key < today ? daysIn(key) : 1;
}

const DAY = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });
const WEEKDAY = new Intl.DateTimeFormat("en-GB", {
  weekday: "short",
  day: "numeric",
  month: "short",
});

function dateOf(key: string, day: number): Date {
  const { year, month } = parseKey(key);
  // The engine accepts any day 1–31; keep a stray "31 Feb" inside its month.
  return new Date(year, month - 1, Math.min(Math.max(day, 1), daysIn(key)));
}

/** "5 Jan" — how a day reads in a list. */
export function dayLabel(key: string, day: number): string {
  return DAY.format(dateOf(key, day));
}

/** "Sun 5 Jan" — the day stepper's caption. */
export function weekdayLabel(key: string, day: number): string {
  return WEEKDAY.format(dateOf(key, day)).replace(",", "");
}
