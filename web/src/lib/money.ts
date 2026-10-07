/**
 * Money on the client.
 *
 * The API sends money as a decimal string at 4 places ("332.9400"). It is never
 * turned into a JS number for anything a person reads or that is sent back: the
 * arithmetic here is on bigint ten-thousandths, and the 2-place view rounds
 * half-to-even exactly like the engine's `Money.display()`
 * (monay/domain/money.py). A float would get there too — until the day it
 * shows 0.13 where the engine says 0.12.
 */

/** Ten-thousandths: the engine's 4dp storage unit, as an integer. */
export type Units = bigint;

const DECIMAL = /^(-?)(\d+)(?:\.(\d+))?$/;

/** "332.9400" → 3329400n. Throws on anything that is not a plain decimal. */
export function units(text: string): Units {
  const match = DECIMAL.exec(text.trim());
  if (!match) throw new Error(`not a money value: ${JSON.stringify(text)}`);
  const [, sign, whole = "0", fraction = ""] = match;
  const magnitude = BigInt(whole) * 10_000n + BigInt(fraction.padEnd(4, "0").slice(0, 4));
  return sign === "-" ? -magnitude : magnitude;
}

/** Whole cents, rounding half to even (banker's rounding). */
export function cents(value: Units): bigint {
  const negative = value < 0n;
  const magnitude = negative ? -value : value;
  let quotient = magnitude / 100n;
  const remainder = magnitude % 100n;
  if (remainder > 50n || (remainder === 50n && quotient % 2n === 1n)) quotient += 1n;
  return negative ? -quotient : quotient;
}

const toUnits = (value: string | Units): Units =>
  typeof value === "string" ? units(value) : value;

/** The display form: two decimals, thousands separators — `1,500.00`, `-17.06`. */
export function formatMoney(value: string | Units): string {
  const rounded = cents(toUnits(value));
  const magnitude = rounded < 0n ? -rounded : rounded;
  const whole = (magnitude / 100n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const fraction = (magnitude % 100n).toString().padStart(2, "0");
  return `${rounded < 0n ? "-" : ""}${whole}.${fraction}`;
}

/** Whole part and decimals separately, for the hero figure (`2,000` + `.00`). */
export function splitMoney(value: string | Units): { whole: string; fraction: string } {
  const text = formatMoney(value);
  const dot = text.lastIndexOf(".");
  return { whole: text.slice(0, dot), fraction: text.slice(dot) };
}

/** Negative *as displayed*: a value that rounds to 0.00 is not shown as a loss. */
export function isNegative(value: string | Units): boolean {
  return cents(toUnits(value)) < 0n;
}

export function isZero(value: string | Units): boolean {
  return toUnits(value) === 0n;
}

/** The value as a person would type it: `300`, `33.33`, `-17.5` — for inputs. */
export function plain(value: string | Units): string {
  const amount = toUnits(value);
  const magnitude = amount < 0n ? -amount : amount;
  const fraction = (magnitude % 10_000n).toString().padStart(4, "0").replace(/0+$/, "");
  return `${amount < 0n ? "-" : ""}${magnitude / 10_000n}${fraction ? `.${fraction}` : ""}`;
}

/** Back to the wire format (`"332.9400"`). */
export function toWire(value: Units): string {
  const magnitude = value < 0n ? -value : value;
  const fraction = (magnitude % 10_000n).toString().padStart(4, "0");
  return `${value < 0n ? "-" : ""}${magnitude / 10_000n}.${fraction}`;
}

/**
 * `part / whole` as a plain number in [0, 1] — for the *width of a bar* only.
 * Geometry is the one place a float is fine: nobody reads a pixel as an amount.
 */
export function share(part: string | Units, whole: string | Units): number {
  const total = toUnits(whole);
  if (total <= 0n) return 0;
  const ratio = Number((toUnits(part) * 10_000n) / total) / 10_000;
  return Math.min(1, Math.max(0, ratio));
}
