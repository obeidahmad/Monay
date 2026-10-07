import { createContext, useContext } from "react";
import type { Month } from "../api/client";
import type { MonthActions } from "../api/queries";

export interface MonthState {
  profileId: number;
  /** The month on screen — the open one, or a closed one opened from History. */
  month: Month;
  /** A closed month: every edit control is hidden. */
  readOnly: boolean;
  /** The key of the profile's open month. */
  openKey: string;
  /** Typed changes to the month on screen; each resolves to the new month. */
  actions: MonthActions;
  /** Look at another month (read-only if closed); `null` returns to the open one. */
  view: (key: string | null) => void;
}

export const MonthContext = createContext<MonthState | null>(null);

export function useMonthView(): MonthState {
  const state = useContext(MonthContext);
  if (!state) throw new Error("useMonthView must be used inside the app shell");
  return state;
}
