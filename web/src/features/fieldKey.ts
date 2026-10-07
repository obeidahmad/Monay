import type { FieldRef, Month } from "../api/client";
import { findField } from "../lib/budget";

/**
 * A field as a `<select>` value: `"section:field"` positions, e.g. `"1:0"`.
 * Empty string means nothing chosen yet.
 */
export function fieldKey(section: number, field: number): string {
  return `${section}:${field}`;
}

export function parseFieldKey(key: string): FieldRef | null {
  const match = /^(\d+):(\d+)$/.exec(key);
  return match ? { section: Number(match[1]), field: Number(match[2]) } : null;
}

/** The section and field a key points at, if it still does. */
export function resolveFieldKey(month: Month, key: string) {
  const ref = parseFieldKey(key);
  return ref ? findField(month, ref.section, ref.field) : null;
}

/** The fields most recently spent from, newest first — the quick-pick chips. */
export function recentFieldKeys(month: Month, limit = 4): string[] {
  const keys: string[] = [];
  for (const transaction of [...month.transactions].reverse()) {
    const key = fieldKey(transaction.field.section_index, transaction.field.field_index);
    if (!keys.includes(key)) keys.push(key);
    if (keys.length === limit) break;
  }
  return keys;
}
