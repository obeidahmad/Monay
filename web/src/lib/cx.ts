/** Join class names, skipping the falsy ones: `cx("row", open && "open")`. */
export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}
