import { cx } from "../lib/cx";
import { formatMoney, isNegative, type Units } from "../lib/money";

interface AmountProps {
  value: string | Units;
  /**
   * How the sign shows. `signed` (default) turns a negative amount `error`;
   * `balance` also turns zero-or-more `ok` (a field's LEFT); `plain` never
   * colours — for the hero, or amounts that take a column colour.
   */
  tone?: "signed" | "balance" | "plain";
  className?: string;
}

/**
 * A money amount: two decimals, thousands separators, tabular figures. Negative
 * values always carry their minus sign, so colour is never the only signal.
 */
export function Amount({ value, tone = "signed", className }: AmountProps) {
  const negative = isNegative(value);
  const colour = tone === "plain" ? null : negative ? "neg" : tone === "balance" ? "pos" : null;
  return <span className={cx(colour, className)}>{formatMoney(value)}</span>;
}
