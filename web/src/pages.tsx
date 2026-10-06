// The app's tabs: Budget, Transactions, Pockets, Settings, plus History and Help.
import { useState } from "react";
import { accentVar, dayLabel, fmt, isNeg } from "./format";
import type { DeleteRequest, SheetSpec } from "./sheets";
import type { AppState, HistoryRow, MonthView, Section } from "./types";
import { Amount, EmptyState, Menu, Segmented, StatusChip } from "./ui";

export type Theme = "system" | "light" | "dark";

interface PageProps {
  state: AppState;
  month: MonthView;
  readOnly: boolean;
  open: (s: SheetSpec) => void;
  onDelete: (r: DeleteRequest) => void;
}

// --- Budget ------------------------------------------------------------------
export function BudgetPage({ month, readOnly, open, onDelete, expanded, toggle, setExpanded }: PageProps & {
  expanded: Set<string>;
  toggle: (name: string) => void;
  setExpanded: (s: Set<string>) => void;
}) {
  const s = month.summary;
  const income = Number(month.total_income);
  const allNames = ["income", ...month.sections.map((x) => x.name)];
  const allOpen = allNames.every((n) => expanded.has(n));
  return (
    <div className="stack">
      <section className="widget glass" aria-label="Month headline">
        <div className="headline">
          <div>
            <div className="label">income</div>
            <Hero value={month.total_income} />
          </div>
          <div>
            <div className="label">post pool</div>
            <div className={`amount-lg ${isNeg(s.post_pool) ? "neg" : ""}`}>{fmt(s.post_pool)}</div>
          </div>
          {s.has_post && (
            <div>
              <div className="label">allocation</div>
              <div className={`amount-lg ${s.balanced ? "pos" : "warn"}`}>
                Σ {s.pct_total}% {s.balanced ? "✓" : "⚠"}
              </div>
            </div>
          )}
        </div>
        {month.sections.length > 0 && income > 0 && (
          <>
            <div className="alloc-bar" role="img" aria-label="How income is allocated across sections">
              {month.sections.map((sec) => {
                const share = Math.max(0, Number(sec.available) - Number(sec.carried_rest));
                return <span key={sec.name} title={`${sec.name} ${fmt(sec.available)}`}
                  style={{ width: `${Math.min(100, (share / income) * 100)}%`, background: accentVar(sec.accent) }} />;
              })}
            </div>
            <div className="alloc-legend caption">
              {month.sections.map((sec) => (
                <span key={sec.name}><i className="dot" style={{ background: accentVar(sec.accent) }} />{sec.name} {fmt(sec.available)}</span>
              ))}
            </div>
          </>
        )}
        {!s.balanced && (
          <div className="caption warn" style={{ marginTop: 12 }}>
            ⚠ Post sections add up to {s.pct_total}%, not 100%. Fix it before closing the month.
          </div>
        )}
      </section>

      <section className="widget glass" aria-label="Sections">
        <div className="widget-head">
          <h2 className="title-widget">Sections</h2>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {(month.sections.length > 0 || month.incomes.length > 0) && (
              <button className="btn ghost small" onClick={() => setExpanded(allOpen ? new Set() : new Set(allNames))}>
                {allOpen ? "Collapse all" : "Expand all"}
              </button>
            )}
            {!readOnly && <button className="btn small" onClick={() => open({ kind: "income" })}>Add income</button>}
            {!readOnly && <button className="btn small" onClick={() => open({ kind: "section" })}>Add section</button>}
          </div>
        </div>

        <div className="sec-grid sec-headrow">
          <span className="label">sections</span>
          <span className="label num">avail</span>
          <span className="label num">rest</span>
          <span className="label col-routing">at close</span>
          <span />
        </div>

        {month.incomes.length > 0 && (
          <IncomeRow month={month} isOpen={expanded.has("income")} toggle={() => toggle("income")} readOnly={readOnly} open={open} />
        )}

        {month.sections.length === 0 ? (
          <div style={{ paddingTop: 12 }}>
            <EmptyState text="No sections yet. Sections split your income: tax and pre come off the top, post sections share the rest."
              action={!readOnly && <button className="btn" onClick={() => open({ kind: "section" })}>Add section</button>} />
          </div>
        ) : (
          month.sections.map((sec) => (
            <SectionRow key={sec.name} section={sec} isOpen={expanded.has(sec.name)} toggle={() => toggle(sec.name)}
              readOnly={readOnly} open={open} onDelete={onDelete} />
          ))
        )}

        <div className="caption summary-line">
          income {fmt(s.total_income)} · post pool {fmt(s.post_pool)}
          {s.has_post && <> · Σ% = {s.pct_total} <span className={s.balanced ? "pos" : "warn"}>{s.balanced ? "✓" : "⚠"}</span></>}
        </div>
      </section>
    </div>
  );
}

function Hero({ value }: { value: string }) {
  const [whole, cents] = fmt(value).split(".");
  return <div className={`hero ${isNeg(value) ? "neg" : ""}`}>{whole}<small>.{cents}</small></div>;
}

function IncomeRow({ month, isOpen, toggle, readOnly, open }: {
  month: MonthView; isOpen: boolean; toggle: () => void; readOnly: boolean; open: (s: SheetSpec) => void;
}) {
  return (
    <div className="sec-row">
      <div className="sec-grid">
        <button className="sec-toggle" onClick={toggle} aria-expanded={isOpen}>
          <i className="bar" style={{ background: "var(--income-accent)" }} />
          <span>
            <span className="name" style={{ color: "var(--income-accent)" }}>
              <span className="marker">{isOpen ? "▼" : "▶"}</span>Income
            </span>
            <span className="caption">{month.incomes.length} {month.incomes.length === 1 ? "entry" : "entries"}</span>
          </span>
        </button>
        <Amount value={month.total_income} />
        <span />
        <span className="col-routing" />
        <span />
      </div>
      {isOpen && (
        <div className="sec-body table-wrap">
          <table className="table">
            <thead><tr><th>Source</th><th className="num">Amount</th><th>Kind</th></tr></thead>
            <tbody>
              {month.incomes.map((inc) => (
                <tr key={inc.name} className={readOnly ? "" : "clickable"}
                  onClick={readOnly ? undefined : () => open({ kind: "income", income: inc })}>
                  <td className="fname">{inc.name}</td>
                  <td className="num"><Amount value={inc.amount} /></td>
                  <td className="muted">{inc.kind}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SectionRow({ section: s, isOpen, toggle, readOnly, open, onDelete }: {
  section: Section; isOpen: boolean; toggle: () => void; readOnly: boolean;
  open: (s: SheetSpec) => void; onDelete: (r: DeleteRequest) => void;
}) {
  const accent = accentVar(s.accent);
  const negRest = isNeg(s.rest);
  return (
    <div className="sec-row">
      <div className="sec-grid">
        <button className="sec-toggle" onClick={toggle} aria-expanded={isOpen}>
          <i className="bar" style={{ background: accent }} />
          <span style={{ minWidth: 0 }}>
            <span className="name" style={{ color: accent }}>
              <span className="marker">{isOpen ? "▼" : "▶"}</span>{s.name}
            </span>
            <span className="caption">{s.share_label}{Number(s.carried_rest) !== 0 && ` · +${fmt(s.carried_rest)} carried`}</span>
          </span>
        </button>
        <Amount value={s.available} />
        <span className="num">
          {negRest && <span className="warn" title="Negative rest: this section is overspent" aria-label="warning">⚠ </span>}
          <Amount value={s.rest} />
        </span>
        <span className="routing col-routing" title="Where this section's rest goes when the month closes">{s.routing_label}</span>
        {readOnly ? <span /> : (
          <Menu label={`${s.name} actions`} items={[
            { label: "Add field", onClick: () => open({ kind: "field", section: s.name }) },
            { label: "Edit section", onClick: () => open({ kind: "section", section: s }) },
            { label: "Delete section", danger: true, onClick: () => onDelete({
              title: "Delete section?", body: `Delete ${s.name}. Only an empty section (no fields) can be deleted.`,
              path: "/api/sections/delete", payload: { section: s.name }, ok: `Section ${s.name} deleted`,
            }) },
          ]} />
        )}
      </div>
      {isOpen && (
        <div className="sec-body">
          {s.fields.length === 0 ? (
            <EmptyState text="No fields in this section yet."
              action={!readOnly && <button className="btn small" onClick={() => open({ kind: "field", section: s.name })}>Add field</button>} />
          ) : (
            <div className="table-wrap">
              <table className="table field-table">
                <thead>
                  <tr>
                    <th>Field</th><th className="num">Budget</th><th className="num">Current</th><th className="num">Paid</th>
                    <th className="num">Left</th><th className="num">Max</th><th>Pocket</th>{!readOnly && <th />}
                  </tr>
                </thead>
                <tbody>
                  {s.fields.map((f) => (
                    <tr key={f.name} className={readOnly ? "" : "clickable"}
                      onClick={readOnly ? undefined : () => open({ kind: "field", section: s.name, field: f })}>
                      <td className="fname">{f.name}</td>
                      <td className="num c-budget" data-label="budget">{f.budget_pct ? `${f.budget_pct}% → ${fmt(f.budget)}` : fmt(f.budget)}</td>
                      <td className="num" data-label="current"><Amount value={f.current} /></td>
                      <td className="num c-paid" data-label="paid">{fmt(f.paid)}</td>
                      <td className="num" data-label="left"><Amount value={f.left} className={isNeg(f.left) ? "" : "pos"} /></td>
                      <td className="num c-dim" data-label="max">{fmt(f.cap)}</td>
                      <td className="c-dim" data-label="pocket">{f.pocket}</td>
                      {!readOnly && (
                        <td onClick={(e) => e.stopPropagation()} style={{ width: 40 }}>
                          <Menu label={`${f.name} actions`} items={[
                            { label: "Add transaction", onClick: () => open({ kind: "tx", preset: { section: s.name, field: f.name } }) },
                            { label: "Edit", onClick: () => open({ kind: "field", section: s.name, field: f }) },
                            { label: "Transfer from here", onClick: () => open({ kind: "transfer", from: { section: s.name, field: f.name } }) },
                            { label: "Delete", danger: true, onClick: () => onDelete({
                              title: "Delete field?",
                              body: `Delete ${f.name}. A field can only go once its pot is empty (left 0.00) and it has no transactions or transfers this month.`,
                              path: "/api/fields/delete", payload: { section: s.name, field: f.name }, ok: `Field ${f.name} deleted`,
                            }) },
                          ]} />
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="caption" style={{ marginTop: 8 }}>
            consumed {fmt(s.consumed)} · budget left <span className={isNeg(s.budget_left) ? "neg" : ""}>{fmt(s.budget_left)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Transactions ------------------------------------------------------------
export function TransactionsPage({ month, readOnly, open }: PageProps) {
  const [filter, setFilter] = useState("");
  const accentOf = new Map(month.sections.map((s) => [s.name, s.accent]));
  const q = filter.trim().toLowerCase();
  const rows = [...month.transactions].reverse().filter(
    (t) => !q || t.field.toLowerCase().includes(q) || t.description.toLowerCase().includes(q),
  );
  return (
    <div className="stack">
      <section className="widget glass" aria-label="Transactions">
        <div className="widget-head">
          <h2 className="title-widget">Transactions</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <div className="tf" style={{ minWidth: 200 }}>
              <input aria-label="Filter by field or description" placeholder="Filter by field or text"
                value={filter} onChange={(e) => setFilter(e.target.value)} style={{ minHeight: 40 }} />
            </div>
            {!readOnly && <button className="btn small" onClick={() => open({ kind: "transfer" })}>Transfer</button>}
          </div>
        </div>
        {month.transactions.length === 0 ? (
          <EmptyState text="No transactions yet."
            action={!readOnly && month.sections.some((s) => s.fields.length) &&
              <button className="btn" onClick={() => open({ kind: "tx" })}>Add transaction</button>} />
        ) : rows.length === 0 ? (
          <EmptyState text={`Nothing matches “${filter}”.`} action={<button className="btn small" onClick={() => setFilter("")}>Clear filter</button>} />
        ) : (
          <div className="row-list">
            {rows.map((t) => (
              <div key={t.index} className="list-row">
                <span className="day-badge">{dayLabel(t.day, month.key)}</span>
                <span style={{ display: "flex", gap: 12, alignItems: "center", minWidth: 0 }}>
                  <span className="avatar" style={{ background: accentVar(accentOf.get(t.section) ?? 0) }}>{t.field.slice(0, 1).toUpperCase()}</span>
                  <span style={{ minWidth: 0 }}>
                    <span className="title" style={{ display: "block" }}>{t.description || t.field}</span>
                    <span className="caption">#{t.index} · {t.field} · {t.section}</span>
                  </span>
                </span>
                <span className="num c-paid">-{fmt(t.amount)}</span>
                {readOnly ? <span /> : (
                  <Menu label={`Transaction ${t.index} actions`} items={[
                    { label: "Edit", onClick: () => open({ kind: "tx", tx: t }) },
                  ]} />
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {month.transfers.length > 0 && !q && (
        <section className="widget glass" aria-label="Transfers">
          <div className="widget-head"><h2 className="title-widget">Transfers</h2></div>
          <div className="row-list">
            {month.transfers.map((t, i) => (
              <div key={i} className="list-row">
                <span className="day-badge">{dayLabel(t.day, month.key)}</span>
                <span style={{ minWidth: 0 }}>
                  <span className="title" style={{ display: "block" }}>
                    <span style={{ color: "var(--section-3)" }}>⇄</span> {t.from_field} → {t.to_field}
                  </span>
                  {t.note && <span className="caption">{t.note}</span>}
                </span>
                <span className="num strong">{fmt(t.amount)}</span>
                <span />
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// --- Pockets -----------------------------------------------------------------
export function PocketsPage({ month, readOnly, open }: PageProps) {
  return (
    <div className="stack">
      <div className="caption">How much each place should hold right now: the sum of its fields' left. The default pocket also holds the live section rests.</div>
      {month.pockets.length === 0 ? (
        <EmptyState text="No pockets yet." action={!readOnly && <button className="btn" onClick={() => open({ kind: "pocket" })}>Add pocket</button>} />
      ) : (
        <div className="pocket-grid">
          {month.pockets.map((p) => (
            <section key={p.name} className="pocket-card glass" aria-label={`Pocket ${p.name}`}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                <h3 className="title-widget">{p.name} {p.is_default && <span className="chip" style={{ marginLeft: 6 }}>default</span>}</h3>
                {!readOnly && <Menu label={`${p.name} actions`} items={[{ label: "Edit", onClick: () => open({ kind: "pocket", pocket: p }) }]} />}
              </div>
              <div>
                <div className="label">should hold</div>
                <div className={`amount-lg ${isNeg(p.counter) ? "neg" : ""}`}>{fmt(p.counter)}</div>
              </div>
              {(p.fields.length > 0 || (p.rests && Number(p.rests) !== 0)) && (
                <div className="pocket-lines caption">
                  {p.fields.map((f) => (
                    <div key={`${f.section}/${f.field}`}><span>{f.field}</span><Amount value={f.left} /></div>
                  ))}
                  {p.rests && Number(p.rests) !== 0 && <div><span>Section rests</span><Amount value={p.rests} /></div>}
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

// --- History -----------------------------------------------------------------
export function HistoryWidget({ history, viewingKey, onView }: {
  history: HistoryRow[]; viewingKey: string | null; onView: (key: string, isOpen: boolean) => void;
}) {
  return (
    <section className="widget glass" aria-label="History">
      <div className="widget-head" style={{ marginBottom: 8 }}><h2 className="title-widget">History</h2></div>
      {history.length === 0 ? <EmptyState text="No months yet." /> : (
        <div>
          {history.map((h) => (
            <button key={h.key} className="history-row" aria-current={h.key === viewingKey}
              onClick={() => onView(h.key, h.state === "open")}>
              <span>
                <span className="strong" style={{ fontWeight: 700 }}>{h.label}</span>{" "}
                <span className="caption">{h.key}</span>
              </span>
              <StatusChip closed={h.state === "closed"} />
              <span className="stats caption">
                <span>income {fmt(h.income)}</span>
                <span>spent <span className="c-paid">{fmt(h.spent)}</span></span>
                <span>leftovers <span className={isNeg(h.leftovers) ? "neg" : ""}>{fmt(h.leftovers)}</span></span>
              </span>
            </button>
          ))}
        </div>
      )}
      <div className="caption" style={{ marginTop: 8 }}>Open a past month to view it read-only.</div>
    </section>
  );
}

// --- Settings ----------------------------------------------------------------
export function SettingsPage({ state, open, onDelete, onSwitch, theme, setTheme }: {
  state: AppState;
  open: (s: SheetSpec) => void;
  onDelete: (r: DeleteRequest) => void;
  onSwitch: (name: string) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
}) {
  return (
    <div className="stack" style={{ maxWidth: 720 }}>
      <section className="widget glass" aria-label="Profiles">
        <div className="widget-head">
          <h2 className="title-widget">Profiles</h2>
          <button className="btn small" onClick={() => open({ kind: "profile-add" })}>Add profile</button>
        </div>
        <div className="caption" style={{ marginBottom: 8 }}>Each profile is a fully independent budget with its own months, sections and pockets.</div>
        <div className="row-list">
          {state.profiles.map((p) => {
            const current = p.id === state.profile?.id;
            return (
              <div key={p.id} className="list-row" style={{ gridTemplateColumns: "40px minmax(0,1fr) auto 40px" }}>
                <span className="avatar" style={{ background: "var(--income-accent)" }}>{p.name.slice(0, 1).toUpperCase()}</span>
                <span className="title">{p.name}</span>
                {current ? <span className="chip"><span className="pos">●</span> current</span>
                  : <button className="btn small" onClick={() => onSwitch(p.name)}>Switch</button>}
                <Menu label={`${p.name} actions`} items={[
                  ...(current ? [{ label: "Rename", onClick: () => open({ kind: "profile-rename", name: p.name }) }] : []),
                  { label: "Delete", danger: true, onClick: () => onDelete({
                    title: `Delete profile ${p.name}?`,
                    body: `This deletes ${p.name} and every one of its months for good. It can't be undone.`,
                    path: "/api/profiles/delete", payload: { name: p.name }, ok: `Profile ${p.name} deleted`,
                  }) },
                ]} />
              </div>
            );
          })}
        </div>
      </section>
      <section className="widget glass" aria-label="Appearance">
        <div className="widget-head"><h2 className="title-widget">Appearance</h2></div>
        <Segmented value={theme} onChange={setTheme}
          options={[{ value: "system", label: "System" }, { value: "light", label: "Light" }, { value: "dark", label: "Dark" }]} />
      </section>
    </div>
  );
}

// --- Help (the old Docs tab) ---------------------------------------------------
export function HelpPage() {
  const items: [string, string][] = [
    ["Zero-based budgeting", "Every unit of income gets a job. Sections take slices of the month's income; fields inside a section are the budget lines you spend from."],
    ["Section kinds", "Tax sections skim a % off fresh income first (leftovers aren't taxed twice). Pre sections then take a fixed amount or a % off the top, in order. Post sections split what remains by % and must add up to 100% before you can close the month."],
    ["Avail and rest", "Avail is a section's slice (plus any rest routed in last month). Rest = avail − what its fields consumed; it can go negative (⚠). At close, rest goes to next month's income, carries over in the section, or moves to another section — pick this in Edit section."],
    ["Fields", "Each field has a monthly budget (an amount, or a % of the section's avail after its fixed budgets), a current pot carried from last month, what you paid, and what's left: left = current + budget − paid, capped at max (∞ for none)."],
    ["Transactions and transfers", "Add transaction records money leaving a field's pot. Transfer moves accumulated pot money between fields without touching budget math, and is refused if it would push the target past its max."],
    ["Pockets", "Pockets are where money physically sits. Each shows how much it should hold right now, so you can reconcile against your real accounts."],
    ["Closing a month", "Close month locks the month forever and creates the next one: the structure is copied, every field's current becomes its final left, and rests routed to income arrive as a single Leftovers entry. Past months stay viewable in History."],
    ["Amounts", "Any amount field accepts arithmetic, like 15.71+1.35 or (7.81)/2+6.5. Values are stored at 4 decimals with banker's rounding and shown with 2."],
  ];
  return (
    <div className="stack" style={{ maxWidth: 760 }}>
      {items.map(([title, body]) => (
        <section key={title} className="widget glass">
          <h2 className="title-widget" style={{ marginBottom: 8 }}>{title}</h2>
          <div>{body}</div>
        </section>
      ))}
    </div>
  );
}
