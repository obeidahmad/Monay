import { useCallback, useSyncExternalStore } from "react";

/** Whether a media query matches, kept in sync as the viewport changes. */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (notify: () => void) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", notify);
      return () => list.removeEventListener("change", notify);
    },
    [query],
  );
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches);
}

/** The design system's phone breakpoint: one column, bottom tab bar, FAB. */
export const PHONE = "(max-width: 640px)";

/** Below this the field table has no room for seven columns and stacks. */
export const NARROW = "(max-width: 960px)";
