import { describe, expect, it } from "vitest";

import type { Field, Section } from "../api/client";
import {
  budgetLabel,
  isPercentage,
  leftAfter,
  percentGap,
  routingLabel,
  shareLabel,
} from "./budget";
import { units } from "./money";

const field = (values: Partial<Field>): Field =>
  ({
    current: "0.0000",
    budget: "0.0000",
    paid: "0.0000",
    left: "0.0000",
    max: null,
    budget_pct: null,
    ...values,
  }) as Field;

const section = (values: Partial<Section>): Section => values as Section;

describe("leftAfter", () => {
  const groceries = field({
    current: "100.0000",
    budget: "300.0000",
    paid: "50.0000",
    max: "400.0000",
    left: "350.0000",
  });

  it("takes a new spend off what is left", () => {
    expect(leftAfter(groceries, units("30"))).toBe(units("320"));
  });

  it("gives the old amount back when a transaction is edited", () => {
    expect(leftAfter(groceries, units("10"), units("30"))).toBe(units("370"));
  });

  it("can go below zero", () => {
    expect(leftAfter(groceries, units("400"))).toBe(units("-50"));
  });

  it("stays at the max while the pot is still above it", () => {
    const capped = field({
      current: "300.0000",
      budget: "300.0000",
      max: "400.0000",
      left: "400.0000",
    });
    expect(leftAfter(capped, units("100"))).toBe(units("400"));
    expect(leftAfter(capped, units("250"))).toBe(units("350"));
  });

  it("keeps what transfers moved in or out", () => {
    const received = field({ budget: "400.0000", left: "450.0000" });
    expect(leftAfter(received, units("100"))).toBe(units("350"));
    const gave = field({ budget: "400.0000", left: "300.0000" });
    expect(leftAfter(gave, units("100"))).toBe(units("200"));
  });
});

describe("percentGap", () => {
  it("is balanced at exactly 100", () => {
    expect(percentGap("100")).toEqual({ state: "balanced", by: "0" });
    expect(percentGap("100.00")).toEqual({ state: "balanced", by: "0" });
  });

  it("says how far under or over", () => {
    expect(percentGap("95")).toEqual({ state: "under", by: "5" });
    expect(percentGap("102")).toEqual({ state: "over", by: "2" });
    expect(percentGap("99.5")).toEqual({ state: "under", by: "0.5" });
    expect(percentGap("100.25")).toEqual({ state: "over", by: "0.25" });
    expect(percentGap("33.33")).toEqual({ state: "under", by: "66.67" });
  });

  it("drops trailing zeros but not the whole number's own", () => {
    expect(percentGap("99.50")).toEqual({ state: "under", by: "0.5" });
    expect(percentGap("90.00")).toEqual({ state: "under", by: "10" });
    expect(percentGap("0")).toEqual({ state: "under", by: "100" });
  });
});

describe("isPercentage", () => {
  it("accepts a bare number from 0 to 100", () => {
    for (const text of ["0", "50", "100", "33.33", " 20 "]) {
      expect(isPercentage(text), text).toBe(true);
    }
  });

  it("refuses everything else", () => {
    for (const text of ["", "100.5", "1000", "-1", "50%", "abc", ".5"]) {
      expect(isPercentage(text), text).toBe(false);
    }
  });
});

describe("labels", () => {
  it("describes a section's kind and share", () => {
    const percent = section({ kind: "post", allocation: { type: "percent", value: "50" } });
    const amount = section({ kind: "pre", allocation: { type: "amount", value: "500.0000" } });
    expect(shareLabel(percent)).toBe("post · 50%");
    expect(shareLabel(amount)).toBe("pre · 500.00");
  });

  it("describes where a section's rest goes", () => {
    expect(routingLabel(section({ rest_routing: { kind: "income", target: null } }))).toBe(
      "→ income",
    );
    expect(routingLabel(section({ rest_routing: { kind: "self", target: null } }))).toBe(
      "→ carries over",
    );
    expect(routingLabel(section({ rest_routing: { kind: "section", target: "Savings" } }))).toBe(
      "→ Savings",
    );
  });

  it("shows a percentage budget with what it comes to", () => {
    expect(budgetLabel(field({ budget: "300.0000" }))).toBe("300.00");
    expect(budgetLabel(field({ budget: "150.0000", budget_pct: "20" }))).toBe("20% → 150.00");
  });
});
