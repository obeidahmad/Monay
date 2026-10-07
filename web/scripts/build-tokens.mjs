// Turns design/tokens.json (vendored from the Monay design system) into CSS
// custom properties: src/styles/tokens.gen.css. Components only ever reference
// the variables, so re-syncing the design system is "replace tokens.json".
//
//   colour / shadow …  → --<name>, once per theme
//   spacing / radius … → --<name>
//   type styles        → --type-<name> (a `font` shorthand), and
//                        --type-<name>-tracking where the style sets one
//   font families      → --font-<family>

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = resolve(root, "design/tokens.json");
const target = resolve(root, "src/styles/tokens.gen.css");

const tokens = JSON.parse(readFileSync(source, "utf8"));
const themes = tokens.color.themes.map((theme) => theme.id);
const [primary] = themes;

/** `{ok}` is an alias of another token; everything else is a literal value. */
const css = (value) => String(value).replace(/^\{(.+)\}$/, "var(--$1)");

const shared = []; // the same in every theme
const themed = Object.fromEntries(themes.map((id) => [id, []]));

for (const [family, group] of Object.entries(tokens)) {
  if (family === "type" || !Array.isArray(group?.tokens)) continue;
  for (const { name, value } of group.tokens) {
    if (typeof value === "object" && value !== null) {
      // A token missing a theme's value inherits the primary theme's.
      for (const id of themes) themed[id].push(`--${name}: ${css(value[id] ?? value[primary])};`);
    } else {
      shared.push(`--${name}: ${css(value)};`);
    }
  }
}

for (const [family, stack] of Object.entries(tokens.type.families)) {
  shared.push(`--font-${family}: ${stack};`);
}
for (const group of tokens.type.groups) {
  for (const style of group.styles) {
    const font = `${style.fontWeight} ${style.fontSize}/${style.lineHeight} var(--font-${group.family})`;
    shared.push(`--type-${style.name}: ${font};`);
    if (style.letterSpacing) shared.push(`--type-${style.name}-tracking: ${style.letterSpacing};`);
  }
}

const block = (selector, lines, indent = "") =>
  `${indent}${selector} {\n${lines.map((line) => `${indent}  ${line}`).join("\n")}\n${indent}}`;

const scheme = (id) => [`color-scheme: ${id};`, ...themed[id]];
const others = themes.filter((id) => id !== primary);

const output = [
  `/* Generated from design/tokens.json (${tokens.name} v${tokens.version}) by scripts/build-tokens.mjs. Do not edit. */`,
  block(":root", shared),
  // The primary theme is the default; data-theme pins one explicitly (on the
  // root from the Appearance setting, or on any element to theme a subtree).
  block(`:root,\n[data-theme="${primary}"]`, scheme(primary)),
  // With no explicit choice, follow the operating system.
  ...others.map(
    (id) =>
      `@media (prefers-color-scheme: ${id}) {\n${block(":root:not([data-theme])", scheme(id), "  ")}\n}`,
  ),
  ...others.map((id) => block(`[data-theme="${id}"]`, scheme(id))),
  "",
].join("\n\n");

mkdirSync(dirname(target), { recursive: true });
writeFileSync(target, output);
console.log(
  `tokens: ${shared.length} shared + ${themed[primary].length} per theme (${themes.join(", ")}) -> src/styles/tokens.gen.css`,
);
