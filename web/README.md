# Monay — web app

The browser front end: React + TypeScript on Vite, built from the Monay design system. It talks to the engine only through the HTTP API (`monay/api/`); every figure on screen was computed by the engine, never here.

How it fits into the whole project is in [docs/DEVELOPING.md](../docs/DEVELOPING.md) (§8 the API, §9 this app).

## Run it

You need Node.js 24+ and the Python environment from the repo root (`uv sync`).

```bash
uv run python -m monay.api      # in the repo root: the API on http://127.0.0.1:8000
npm install                     # in web/
npm run dev                     # http://localhost:5173
```

The dev server forwards `/api` to the API (`vite.config.ts`). Point it elsewhere with `MONAY_API_URL=http://127.0.0.1:9000 npm run dev`.

| Script              | What it does                                                               |
| ------------------- | -------------------------------------------------------------------------- |
| `npm run dev`       | regenerate (below), then start the dev server                              |
| `npm run build`     | regenerate types + tokens, type-check, bundle into `dist/`                 |
| `npm run gen`       | export the OpenAPI document, then generate the API types and the token CSS |
| `npm run typecheck` | `tsc`, strict                                                              |
| `npm run lint`      | ESLint                                                                     |
| `npm test`          | Vitest: the `*.test.ts` files beside the code in `src/lib`                 |
| `npm run format`    | Prettier, in place (`format:check` only verifies, as CI does)              |

## Generated files

Three files are produced by `npm run gen` and are **not** in git. Edit their sources instead.

| File                        | Source                              | Made by                                                   |
| --------------------------- | ----------------------------------- | --------------------------------------------------------- |
| `openapi.json`              | `monay/api/schemas.py` + the routes | `gen:openapi` (`python -m monay.api.openapi`, needs `uv`) |
| `src/api/schema.gen.ts`     | `openapi.json`                      | `gen:types` (`openapi-typescript`)                        |
| `src/styles/tokens.gen.css` | `design/tokens.json`                | `gen:tokens` (`scripts/build-tokens.mjs`)                 |

So after changing the API, `npm run gen` (or just restart `npm run dev`) and TypeScript tells you everything that no longer matches. `npm run build` deliberately skips `gen:openapi`: in the Docker build the document comes from the Python stage, and Node has no `uv` there.

## Layout

```
design/tokens.json   the design tokens, vendored from the Monay design system
scripts/             build-tokens.mjs
src/
  api/               client.ts — the typed client and ApiError
                     queries.ts — every read and change, and the cache rules
  app/               Root (profile → month → pages), AppShell, Page,
                     SheetHost, and the theme / toast / profile / month contexts
  components/        the design system's components, one file each
  features/          budget (overview + a page per section) · transactions · pockets ·
                     analytics · settings · onboarding
  lib/               money (bigint, half-even) · expression · dates · budget helpers
  styles/global.css  the ground and its orbs, glass, type helpers
```

## Working with the design system

`src/components/` holds the building blocks: `Widget`, `Button`, `Sheet`, `ConfirmDialog`, `Toast`, `Menu`, `TextField`, `StatusChip`, `SectionIcon`, `Logo`, and the charts (`charts.tsx`: trend, donut, columns, waterfall, heatmap, meter, gauge, stat tile).

- **Tokens only.** Stylesheets reference `var(--…)` from `tokens.gen.css`: colours, type styles (`--type-title-widget`), spacing, radii, shadows, blur. Never a literal colour.
- **Themes are token values.** `data-theme="light" | "dark"` on the root element pins one; without it the stylesheet follows the operating system.
- **To re-sync** after the design system changes: replace `design/tokens.json` with its `tokens.json` and run `npm run gen:tokens`. Component markup follows the design system's component guidelines; update the matching file here when one changes.
- **Where this app departs from the design system's written layout**, on purpose: navigation is a left rail with the items centred vertically; the primary action is the brand mint; a section is a card that opens its own page (not an accordion row) and carries a chosen colour and icon; History is the month button, not a side column; income is its own card, not a row among the sections. The design system's README still describes the earlier layout and should be brought in line.

## Conventions

- **Money is never a `number`.** Use `lib/money.ts`. Amounts a person types are sent as text and evaluated by the server.
- **`api/queries.ts` is the only door to the server.** A change returns the month it produced, which goes into the cache; nothing is patched optimistically.
- **Forms are `Sheet`s**, opened with `useSheet()`. Use `useSubmit` so a refusal lands under the input it names; errors never go to a toast.
- **Deleting offers Undo** (`useAct`) rather than asking first. Only closing a month and deleting a profile confirm.
- Files that export a React component export nothing else (fast refresh); contexts and hooks live in a `.ts` file beside their provider.
