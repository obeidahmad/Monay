import { createContext, useContext } from "react";

/** System follows the OS setting; Light and Dark pin one. */
export type Appearance = "system" | "light" | "dark";

/** Also read by the inline script in index.html, before React starts. */
export const APPEARANCE_KEY = "monay.theme";

export interface ThemeState {
  appearance: Appearance;
  setAppearance: (next: Appearance) => void;
}

export const ThemeContext = createContext<ThemeState | null>(null);

export function useTheme(): ThemeState {
  const state = useContext(ThemeContext);
  if (!state) throw new Error("useTheme must be used inside <ThemeProvider>");
  return state;
}
