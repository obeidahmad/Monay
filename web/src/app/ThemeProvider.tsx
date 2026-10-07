import { useCallback, useMemo, useState, type ReactNode } from "react";
import { readStored, writeStored } from "../lib/storage";
import { APPEARANCE_KEY, ThemeContext, type Appearance } from "./theme";

function stored(): Appearance {
  const value = readStored(APPEARANCE_KEY);
  return value === "light" || value === "dark" ? value : "system";
}

/**
 * Dark and white mode share every rule; only token values differ. Choosing one
 * sets `data-theme` on the root element — or removes it, and the tokens
 * stylesheet then follows the operating system.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [appearance, setState] = useState<Appearance>(stored);

  const setAppearance = useCallback((next: Appearance) => {
    const root = document.documentElement;
    // Fade colours only, for the length of the switch.
    root.classList.add("theme-fade");
    window.setTimeout(() => root.classList.remove("theme-fade"), 250);

    if (next === "system") delete root.dataset.theme;
    else root.dataset.theme = next;
    writeStored(APPEARANCE_KEY, next === "system" ? null : next);
    setState(next);
  }, []);

  const value = useMemo(() => ({ appearance, setAppearance }), [appearance, setAppearance]);
  return <ThemeContext value={value}>{children}</ThemeContext>;
}
