import { useCallback, useState } from "react";

const KEY = "monay.expanded";

function read(): string[] {
  try {
    const stored: unknown = JSON.parse(sessionStorage.getItem(KEY) ?? "[]");
    return Array.isArray(stored) ? stored.filter((row) => typeof row === "string") : [];
  } catch {
    return [];
  }
}

/**
 * Which accordion rows are open, by name. Any number may be open at once.
 *
 * Kept for the browser tab's session, so the Budget tab looks the way you left
 * it after a visit to Transactions — or a reload.
 */
export function useExpanded() {
  const [open, setOpen] = useState<ReadonlySet<string>>(() => new Set(read()));

  const set = useCallback((row: string, expanded: boolean) => {
    setOpen((current) => {
      const next = new Set(current);
      if (expanded) next.add(row);
      else next.delete(row);
      try {
        sessionStorage.setItem(KEY, JSON.stringify([...next]));
      } catch {
        // Session storage unavailable: the choice just won't outlive the page.
      }
      return next;
    });
  }, []);

  return { open, set };
}
