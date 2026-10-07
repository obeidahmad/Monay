/**
 * Per-browser conveniences (which profile was open, the chosen appearance).
 * Storage can be unavailable — private windows, blocked site data — and the app
 * must behave the same without it, so every access is guarded.
 */

export function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStored(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    // Nothing to do: the setting simply won't be remembered.
  }
}
