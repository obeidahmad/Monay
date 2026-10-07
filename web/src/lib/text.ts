/** The letter an avatar shows for a name. */
export function initial(name: string): string {
  return (name.trim()[0] ?? "?").toUpperCase();
}

/** `1 entry`, `3 entries`. */
export function count(n: number, singular: string, plural: string): string {
  return `${n} ${n === 1 ? singular : plural}`;
}
