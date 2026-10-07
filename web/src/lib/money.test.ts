import { describe, expect, it } from "vitest";

import {
  cents,
  formatMoney,
  isNegative,
  isZero,
  plain,
  share,
  splitMoney,
  toWire,
  units,
} from "./money";

describe("units", () => {
  it("reads the wire format into ten-thousandths", () => {
    expect(units("332.9400")).toBe(3_329_400n);
    expect(units("12")).toBe(120_000n);
    expect(units("-0.5")).toBe(-5_000n);
    expect(units(" 0.0001 ")).toBe(1n);
  });

  it("refuses anything that is not a plain decimal", () => {
    for (const text of ["", "1e3", "1,5", "abc", "1.2.3", "--1"]) {
      expect(() => units(text)).toThrow();
    }
  });
});

describe("cents", () => {
  it("rounds half to even, like the engine", () => {
    expect(cents(units("0.125"))).toBe(12n);
    expect(cents(units("0.135"))).toBe(14n);
    expect(cents(units("0.1251"))).toBe(13n);
    expect(cents(units("-0.125"))).toBe(-12n);
    expect(cents(units("-0.135"))).toBe(-14n);
  });
});

describe("formatMoney", () => {
  it("shows two decimals and thousands separators", () => {
    expect(formatMoney("1500")).toBe("1,500.00");
    expect(formatMoney("-17.0600")).toBe("-17.06");
    expect(formatMoney("1234567.8950")).toBe("1,234,567.90");
    expect(formatMoney("999.9950")).toBe("1,000.00");
    expect(formatMoney(3_329_400n)).toBe("332.94");
  });

  it("never prints a negative zero", () => {
    expect(formatMoney("-0.0040")).toBe("0.00");
  });

  it("splits the whole part from the decimals", () => {
    expect(splitMoney("2000.0000")).toEqual({ whole: "2,000", fraction: ".00" });
    expect(splitMoney("-17.06")).toEqual({ whole: "-17", fraction: ".06" });
  });
});

describe("sign checks", () => {
  it("calls a value negative only if it displays as one", () => {
    expect(isNegative("-0.0100")).toBe(true);
    expect(isNegative("-0.0040")).toBe(false);
    expect(isNegative("0.0000")).toBe(false);
  });

  it("calls a value zero only if it is exactly zero", () => {
    expect(isZero("0.0000")).toBe(true);
    expect(isZero("-0.0040")).toBe(false);
  });
});

describe("plain and toWire", () => {
  it("writes a value the way a person would type it", () => {
    expect(plain("300.0000")).toBe("300");
    expect(plain("33.3300")).toBe("33.33");
    expect(plain("-17.5000")).toBe("-17.5");
    expect(plain("0.0000")).toBe("0");
  });

  it("writes the wire format back, unchanged", () => {
    expect(toWire(-5_000n)).toBe("-0.5000");
    for (const text of ["332.9400", "0.0000", "-150.0000", "1234567.8901"]) {
      expect(toWire(units(text))).toBe(text);
    }
  });
});

describe("share", () => {
  it("is a ratio kept inside 0..1", () => {
    expect(share("750", "2000")).toBe(0.375);
    expect(share("3000", "2000")).toBe(1);
    expect(share("-5", "100")).toBe(0);
  });

  it("is zero when there is nothing to take a share of", () => {
    expect(share("5", "0")).toBe(0);
    expect(share("5", "-10")).toBe(0);
  });
});
