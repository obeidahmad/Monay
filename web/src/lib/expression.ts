/**
 * Amount expressions (`15.71+1.35`, `(7.81)/2+6.5`), evaluated exactly.
 *
 * This exists for the live "= 17.06" under an amount input. The server is the
 * authority — it evaluates the same text again with the engine's own evaluator
 * (monay/domain/expressions.py) and that result is what gets stored — so this
 * has to agree with it, which rules out floats. Values are kept as exact
 * fractions of bigints and rounded once, half-to-even at 4 places, the way the
 * engine quantizes into `Money`.
 *
 * Grammar (the engine's whitelist): numbers, `+ - * /`, parentheses, unary ±.
 */

import type { Units } from "./money";

const MAX_LENGTH = 200; // same limit as the engine

interface Fraction {
  n: bigint;
  d: bigint; // always > 0
}

class Unreadable extends Error {}

/** The value in ten-thousandths, or `null` if the text is not a valid amount. */
export function evaluate(text: string): Units | null {
  const source = text.trim();
  if (!source || source.length > MAX_LENGTH) return null;
  try {
    const parser = new Parser(source);
    const value = parser.expression();
    parser.expectEnd();
    return round(value);
  } catch (error) {
    if (error instanceof Unreadable) return null;
    throw error;
  }
}

class Parser {
  private position = 0;
  private readonly source: string;

  constructor(source: string) {
    this.source = source;
  }

  expression(): Fraction {
    let left = this.term();
    for (;;) {
      if (this.take("+")) left = add(left, this.term());
      else if (this.take("-")) left = add(left, negate(this.term()));
      else return left;
    }
  }

  expectEnd(): void {
    this.skipSpace();
    if (this.position < this.source.length) throw new Unreadable();
  }

  private term(): Fraction {
    let left = this.unary();
    for (;;) {
      if (this.take("*")) left = multiply(left, this.unary());
      else if (this.take("/")) left = divide(left, this.unary());
      else return left;
    }
  }

  private unary(): Fraction {
    if (this.take("+")) return this.unary();
    if (this.take("-")) return negate(this.unary());
    return this.primary();
  }

  private primary(): Fraction {
    if (this.take("(")) {
      const inner = this.expression();
      if (!this.take(")")) throw new Unreadable();
      return inner;
    }
    return this.number();
  }

  private number(): Fraction {
    this.skipSpace();
    // 12 · 12.5 · .5 · 12. · 1_000 — a digit somewhere is required.
    const match = /^(\d[\d_]*)?(?:\.(\d*))?/.exec(this.source.slice(this.position));
    const whole = (match?.[1] ?? "").replaceAll("_", "");
    const fraction = match?.[2] ?? "";
    if (!match || (whole === "" && fraction === "")) throw new Unreadable();
    this.position += match[0].length;
    return { n: BigInt(whole + fraction || "0"), d: 10n ** BigInt(fraction.length) };
  }

  private take(symbol: string): boolean {
    this.skipSpace();
    if (this.source[this.position] !== symbol) return false;
    this.position += 1;
    return true;
  }

  private skipSpace(): void {
    while (this.source[this.position] === " ") this.position += 1;
  }
}

const add = (a: Fraction, b: Fraction): Fraction => ({ n: a.n * b.d + b.n * a.d, d: a.d * b.d });
const negate = (a: Fraction): Fraction => ({ n: -a.n, d: a.d });
const multiply = (a: Fraction, b: Fraction): Fraction => ({ n: a.n * b.n, d: a.d * b.d });

function divide(a: Fraction, b: Fraction): Fraction {
  if (b.n === 0n) throw new Unreadable(); // division by zero
  const sign = b.n < 0n ? -1n : 1n;
  return { n: a.n * b.d * sign, d: a.d * b.n * sign };
}

/** To ten-thousandths, half to even. */
function round({ n, d }: Fraction): Units {
  const scaled = n * 10_000n;
  const negative = scaled < 0n;
  const magnitude = negative ? -scaled : scaled;
  let quotient = magnitude / d;
  const twice = (magnitude % d) * 2n;
  if (twice > d || (twice === d && quotient % 2n === 1n)) quotient += 1n;
  return negative ? -quotient : quotient;
}
