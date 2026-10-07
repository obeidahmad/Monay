import { describe, expect, it } from "vitest";

import { evaluate } from "./expression";

describe("evaluate", () => {
  it("evaluates the engine's grammar", () => {
    expect(evaluate("15.71+1.35")).toBe(170_600n);
    expect(evaluate("(7.81)/2+6.5")).toBe(104_050n);
    expect(evaluate("2*3-1")).toBe(50_000n);
    expect(evaluate("2+3*4")).toBe(140_000n);
    expect(evaluate("(2+3)*4")).toBe(200_000n);
    expect(evaluate("-5+2")).toBe(-30_000n);
    expect(evaluate("1/-2")).toBe(-5_000n);
    expect(evaluate(" 1 + 2 ")).toBe(30_000n);
  });

  it("reads the number forms the engine reads", () => {
    expect(evaluate("1_000")).toBe(10_000_000n);
    expect(evaluate(".5")).toBe(5_000n);
    expect(evaluate("12.")).toBe(120_000n);
  });

  it("is exact where floating point is not", () => {
    expect(evaluate("0.1+0.2")).toBe(3_000n);
    expect(evaluate("1/3*3")).toBe(10_000n);
    expect(evaluate("33.33+33.33+33.34")).toBe(1_000_000n);
  });

  it("rounds once, half to even at four places", () => {
    expect(evaluate("1/3")).toBe(3_333n);
    expect(evaluate("2/3")).toBe(6_667n);
    expect(evaluate("0.00005")).toBe(0n);
    expect(evaluate("0.00015")).toBe(2n);
    expect(evaluate("-0.00015")).toBe(-2n);
  });

  it("returns null for anything that is not an amount", () => {
    const unreadable = [
      "",
      "   ",
      "12,50",
      "1+",
      "(1",
      "1)",
      "abc",
      "1 2",
      "2**3",
      "9e9",
      ".",
      "_1",
    ];
    for (const text of unreadable) expect(evaluate(text), text).toBeNull();
  });

  it("returns null for a division by zero", () => {
    expect(evaluate("1/0")).toBeNull();
    expect(evaluate("1/(2-2)")).toBeNull();
  });

  it("refuses text longer than the engine accepts", () => {
    expect(evaluate("1+".repeat(100) + "1")).toBeNull(); // 201 characters
    expect(evaluate("1+".repeat(99) + "1")).toBe(1_000_000n);
  });
});
