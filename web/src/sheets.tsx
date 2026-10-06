// Every form in Monay, one Sheet each — they replace the old command bar.
import { useState } from "react";
import { ApiError } from "./api";
import { daysIn, defaultDay, fmt } from "./format";
import type { AppState, Field, Income, MonthView, Pocket, Section, SectionKind, Transaction, Viewing } from "./types";
import { AmountField, DayStepper, Segmented, SelectField, Sheet, TextField } from "./ui";

/** Runs a mutation; resolves on success (the app closes the sheet + toasts). */
export type Act = (path: string, body: unknown, ok: string | ((s: AppState) => string)) => Promise<void>;

export type DeleteRequest = { title: string; body: string; path: string; payload: unknown; ok: string };

export type SheetSpec =
  | { kind: "profile-add" }
  | { kind: "profile-rename"; name: string }
  | { kind: "income"; income?: Income }
  | { kind: "section"; section?: Section }
  | { kind: "field"; section?: string; field?: Field }
  | { kind: "tx"; tx?: Transaction; preset?: { section: string; field: string } }
  | { kind: "transfer"; from?: { section: string; field: string } }
  | { kind: "pocket"; pocket?: Pocket };

interface Ctx {
  month: MonthView | null;
  viewing: Viewing | null;
  act: Act;
  onClose: () => void;
  onDelete: (req: DeleteRequest) => void;
}

/** Wraps a submit: errors land in the sheet, success is handled by `act`. */
function useSubmit() {
  const [error, setError] = useState<string | null>(null);
  async function run(fn: () => Promise<void>) {
    setError(null);
    try {
      await fn();
    } catch (e) {
      if (e instanceof ApiError && e.allowed) setError(`${e.message}`);
      else setError(e instanceof Error ? e.message : String(e));
    }
  }
  return { error, run };
}

const changed = (a: string, b: string) => (a.trim() !== b.trim() ? a.trim() : undefined);

export function SheetHost({ spec, ...ctx }: Ctx & { spec: SheetSpec }) {
  switch (spec.kind) {
    case "profile-add": return <ProfileAddSheet {...ctx} />;
    case "profile-rename": return <ProfileRenameSheet {...ctx} name={spec.name} />;
    case "income": return <IncomeSheet {...ctx} income={spec.income} />;
    case "section": return <SectionSheet {...ctx} section={spec.section} />;
    case "field": return <FieldSheet {...ctx} sectionName={spec.section} field={spec.field} />;
    case "tx": return <TransactionSheet {...ctx} tx={spec.tx} preset={spec.preset} />;
    case "transfer": return <TransferSheet {...ctx} from={spec.from} />;
    case "pocket": return <PocketSheet {...ctx} pocket={spec.pocket} />;
  }
}

// --- profiles ----------------------------------------------------------------
function ProfileAddSheet({ act, onClose }: Ctx) {
  const [name, setName] = useState("");
  const { error, run } = useSubmit();
  return (
    <Sheet title="Add profile" onClose={onClose} canSubmit={!!name.trim()} error={error}
      submitLabel="Create profile"
      onSubmit={() => run(() => act("/api/profiles", { name }, `Profile ${name.trim()} created`))}>
      <TextField label="Name" value={name} onChange={setName} autoFocus placeholder="alex"
        hint="A profile is a fully independent budget, starting this month." />
    </Sheet>
  );
}

function ProfileRenameSheet({ act, onClose, name: current }: Ctx & { name: string }) {
  const [name, setName] = useState(current);
  const { error, run } = useSubmit();
  return (
    <Sheet title="Rename profile" onClose={onClose} canSubmit={!!changed(name, current)} error={error}
      onSubmit={() => run(() => act("/api/profiles/rename", { name }, `Profile renamed to ${name.trim()}`))}>
      <TextField label="Name" value={name} onChange={setName} autoFocus />
    </Sheet>
  );
}

// --- income ------------------------------------------------------------------
function IncomeSheet({ act, onClose, onDelete, income }: Ctx & { income?: Income }) {
  const [name, setName] = useState(income?.name ?? "");
  const [amount, setAmount] = useState(income?.amount ?? "");
  const { error, run } = useSubmit();
  const editing = !!income;
  return (
    <Sheet title={editing ? "Edit income" : "Add income"} onClose={onClose} error={error}
      canSubmit={!!name.trim() && !!amount.trim()}
      onRemove={editing ? () => onDelete({
        title: "Remove income?", body: `Remove ${income.name} (${fmt(income.amount)}) from this month.`,
        path: "/api/incomes/delete", payload: { income: income.name }, ok: `Income ${income.name} removed`,
      }) : undefined}
      onSubmit={() => run(() => editing
        ? act("/api/incomes/edit", { income: income.name, name: changed(name, income.name), amount: changed(amount, income.amount) },
            `Income ${name.trim()} updated`)
        : act("/api/incomes", { name, amount }, (s) => `Income ${name.trim()} ${fmt(s.month?.incomes.at(-1)?.amount)}. Total ${fmt(s.month?.total_income)}.`))}>
      <TextField label="Source" value={name} onChange={setName} autoFocus={!editing} placeholder="Salary" />
      <AmountField label="Amount" value={amount} onChange={setAmount} autoFocus={editing} />
    </Sheet>
  );
}

// --- sections ----------------------------------------------------------------
const KIND_HINT: Record<SectionKind, string> = {
  tax: "Takes a % of fresh income (not leftovers) off the top, before anything else.",
  pre: "Takes a fixed amount or a % of what's left, off the top, in order.",
  post: "Splits what remains by %. Post sections must add up to 100%.",
};

function SectionSheet({ act, onClose, onDelete, month, section }: Ctx & { section?: Section }) {
  const editing = !!section;
  const [kind, setKind] = useState<SectionKind>(section?.kind ?? "post");
  const [name, setName] = useState(section?.name ?? "");
  const [mode, setMode] = useState<"pct" | "amount">(section?.alloc_kind ?? "pct");
  const [value, setValue] = useState(section ? (section.percentage ?? section.amount ?? "") : "");
  const routingInit = section ? (section.routing.kind === "section" ? section.routing.target! : section.routing.kind) : "income";
  const [rest, setRest] = useState(routingInit);
  const [position, setPosition] = useState(String(section?.position ?? ""));
  const { error, run } = useSubmit();

  const effMode = kind === "pre" ? mode : "pct";
  const alloc = value.trim() ? (effMode === "pct" ? `${value.trim().replace(/%$/, "")}%` : value.trim()) : "";
  const initialAlloc = section ? (section.alloc_kind === "pct" ? `${section.percentage}%` : section.amount!) : "";
  const others = (month?.sections ?? []).filter((s) => s.name !== section?.name);

  async function submit() {
    if (!editing) {
      await act("/api/sections", { kind, name, alloc }, `Section ${name.trim()} added (${kind})`);
      return;
    }
    const pos = position.trim() === "" ? undefined : Number(position);
    await act("/api/sections/edit", {
      section: section.name,
      name: changed(name, section.name),
      alloc: alloc !== initialAlloc ? alloc : undefined,
      rest: rest !== routingInit ? rest : undefined,
      position: pos !== undefined && pos !== section.position ? pos : undefined,
    }, `Section ${name.trim()} updated`);
  }

  return (
    <Sheet title={editing ? "Edit section" : "Add section"} onClose={onClose} error={error}
      canSubmit={!!name.trim() && !!alloc && (position.trim() === "" || /^\d+$/.test(position.trim()))}
      onRemove={editing ? () => onDelete({
        title: "Delete section?", body: `Delete ${section.name}. Only an empty section (no fields) can be deleted.`,
        path: "/api/sections/delete", payload: { section: section.name }, ok: `Section ${section.name} deleted`,
      }) : undefined}
      onSubmit={() => run(submit)}>
      {!editing && (
        <Segmented label="Kind" value={kind} onChange={setKind}
          options={[{ value: "tax", label: "Tax" }, { value: "pre", label: "Pre" }, { value: "post", label: "Post" }]} />
      )}
      <div className="caption" style={{ marginTop: editing ? 0 : -8 }}>{KIND_HINT[kind]}</div>
      <TextField label="Name" value={name} onChange={setName} autoFocus={!editing} placeholder="Needs" />
      {kind === "pre" && (
        <Segmented label="Allocate" value={mode} onChange={setMode}
          options={[{ value: "pct", label: "Percent" }, { value: "amount", label: "Amount" }]} />
      )}
      {effMode === "pct" ? (
        <TextField label="Share (%)" value={value.replace(/%$/, "")} onChange={setValue} placeholder="50"
          hint={kind === "post" && month ? `Post sections now add up to ${month.summary.pct_total}%.` : undefined} />
      ) : (
        <AmountField label="Amount" value={value} onChange={setValue} />
      )}
      {editing && (
        <div className="form-row">
          <SelectField label="Rest at close" value={rest} onChange={setRest}
            options={[
              { value: "income", label: "→ next month's income" },
              { value: "self", label: "→ carries over (itself)" },
              ...others.map((s) => ({ value: s.name, label: `→ ${s.name}` })),
              ...(rest !== "income" && rest !== "self" && !others.some((s) => s.name === rest)
                ? [{ value: rest, label: `→ ${rest}` }] : []),
            ]} />
          <TextField label="Position" value={position} onChange={setPosition}
            hint="Order matters for pre sections." />
        </div>
      )}
    </Sheet>
  );
}

// --- fields ------------------------------------------------------------------
function FieldSheet({ act, onClose, onDelete, month, viewing, sectionName, field }: Ctx & { sectionName?: string; field?: Field }) {
  const editing = !!field;
  const sections = month?.sections ?? [];
  const [section, setSection] = useState(sectionName ?? sections[0]?.name ?? "");
  const [name, setName] = useState(field?.name ?? "");
  const [mode, setMode] = useState<"amount" | "pct">(field?.budget_pct ? "pct" : "amount");
  const [budget, setBudget] = useState(field ? (field.budget_pct ?? field.budget) : "");
  const [hasMax, setHasMax] = useState(field ? field.cap !== null : false);
  const [max, setMax] = useState(field?.cap ?? "");
  const [pocket, setPocket] = useState(field?.pocket ?? "");
  const [current, setCurrent] = useState(field?.current ?? "");
  const { error, run } = useSubmit();

  const budgetText = budget.trim() ? (mode === "pct" ? `${budget.trim().replace(/%$/, "")}%` : budget.trim()) : "";
  const maxText = hasMax ? max.trim() : "inf";

  async function submit() {
    if (!editing) {
      await act("/api/fields", { section, name, budget: budgetText || "0", max: maxText },
        `Field ${name.trim()} added to ${section}`);
      return;
    }
    const initialBudget = field.budget_pct ? `${field.budget_pct}%` : field.budget;
    const initialMax = field.cap ?? "inf";
    await act("/api/fields/edit", {
      section: sectionName,
      field: field.name,
      name: changed(name, field.name),
      budget: budgetText && budgetText !== initialBudget ? budgetText : undefined,
      max: maxText !== initialMax ? maxText : undefined,
      pocket: pocket !== field.pocket ? pocket : undefined,
      current: viewing?.first_month ? changed(current, field.current) : undefined,
    }, (s) => {
      const sec = s.month?.sections.find((x) => x.name === sectionName);
      const f = sec?.fields.find((x) => x.name === name.trim());
      return f && sec ? `${f.name} updated. ${fmt(f.left)} left (${sec.name} rest ${fmt(sec.rest)}).` : "Field updated";
    });
  }

  return (
    <Sheet title={editing ? "Edit field" : "Add field"} onClose={onClose} error={error}
      canSubmit={!!name.trim() && !!section && (!hasMax || !!max.trim())}
      onRemove={editing ? () => onDelete({
        title: "Delete field?",
        body: `Delete ${field.name}. A field can only go once its pot is empty (left 0.00) and it has no transactions or transfers this month.`,
        path: "/api/fields/delete", payload: { section: sectionName, field: field.name }, ok: `Field ${field.name} deleted`,
      }) : undefined}
      onSubmit={() => run(submit)}>
      {!editing && (
        <SelectField label="Section" value={section} onChange={setSection}
          options={sections.map((s) => ({ value: s.name, label: s.name }))} />
      )}
      <TextField label="Name" value={name} onChange={setName} autoFocus={!editing} placeholder="Groceries" />
      <Segmented label="Budget" value={mode} onChange={setMode}
        options={[{ value: "amount", label: "Amount" }, { value: "pct", label: "% of section" }]} />
      {mode === "amount" ? (
        <AmountField label="Monthly budget" value={budget} onChange={setBudget} />
      ) : (
        <TextField label="Share (%)" value={budget.replace(/%$/, "")} onChange={setBudget} placeholder="50"
          hint="Of the section's available after its fixed budgets, rounded down to the cent." />
      )}
      <div className="tf">
        <span className="label">Max (rollover cap)</span>
        <div className="segmented" role="group" aria-label="Max">
          <button type="button" aria-pressed={!hasMax} onClick={() => setHasMax(false)}>No max (∞)</button>
          <button type="button" aria-pressed={hasMax} onClick={() => setHasMax(true)}>Cap at…</button>
        </div>
      </div>
      {hasMax && <AmountField label="Max amount" value={max} onChange={setMax} hint="The pot never grows past this." />}
      {editing && month && (
        <SelectField label="Pocket" value={pocket} onChange={setPocket}
          options={month.pockets.map((p) => ({ value: p.name, label: p.name + (p.is_default ? " (default)" : "") }))} />
      )}
      {editing && viewing?.first_month && (
        <AmountField label="Current" value={current} onChange={setCurrent}
          hint="What the pot already holds. Editable in your first month only; afterwards it carries over." />
      )}
    </Sheet>
  );
}

// --- transactions ------------------------------------------------------------
function allFields(month: MonthView | null) {
  return (month?.sections ?? []).flatMap((s) => s.fields.map((f) => ({ section: s.name, field: f.name, accent: s.accent })));
}
const fkey = (x: { section: string; field: string }) => `${x.section}\u0000${x.field}`;
const fparse = (k: string) => { const [section, field] = k.split("\u0000"); return { section, field }; };

function FieldPicker({ month, value, onChange, label = "Field" }: {
  month: MonthView | null; value: string; onChange: (k: string) => void; label?: string;
}) {
  const fields = allFields(month);
  const recent: string[] = [];
  for (const t of [...(month?.transactions ?? [])].reverse()) {
    const k = fkey(t);
    if (!recent.includes(k) && fields.some((f) => fkey(f) === k)) recent.push(k);
    if (recent.length >= 5) break;
  }
  const dupes = new Set(fields.map((f) => f.field).filter((n, i, a) => a.indexOf(n) !== i));
  const show = (k: string) => { const p = fparse(k); return dupes.has(p.field) ? `${p.field} · ${p.section}` : p.field; };
  return (
    <>
      {recent.length > 0 && (
        <div className="tf">
          <span className="label">Recent</span>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {recent.map((k) => (
              <button key={k} type="button" className="chip-btn" aria-pressed={k === value} onClick={() => onChange(k)}>{show(k)}</button>
            ))}
          </div>
        </div>
      )}
      <SelectField label={label} value={value} onChange={onChange}
        options={[{ value: "", label: "Choose a field…" },
          ...fields.map((f) => ({ value: fkey(f), label: `${f.field} — ${f.section}` }))]} />
    </>
  );
}

function TransactionSheet({ act, onClose, onDelete, month, tx, preset }: Ctx & { tx?: Transaction; preset?: { section: string; field: string } }) {
  const editing = !!tx;
  const key = month?.key ?? "";
  const [target, setTarget] = useState(tx ? fkey(tx) : preset ? fkey(preset) : "");
  const [amount, setAmount] = useState(tx?.amount ?? "");
  const [day, setDay] = useState(tx?.day ?? defaultDay(key));
  const [description, setDescription] = useState(tx?.description ?? "");
  const { error, run } = useSubmit();

  async function submit() {
    if (editing) {
      await act("/api/transactions/edit", {
        index: tx.index,
        amount: changed(amount, tx.amount),
        day: day !== tx.day ? day : undefined,
        description: description !== tx.description ? description : undefined,
      }, `Transaction #${tx.index} updated`);
      return;
    }
    const { section, field } = fparse(target);
    await act("/api/transactions", { section, field, amount, day, description }, (s) => {
      const sec = s.month?.sections.find((x) => x.name === section);
      const f = sec?.fields.find((x) => x.name === field);
      const spent = s.month?.transactions.at(-1)?.amount;
      return f && sec ? `${field} -${fmt(spent)}. ${fmt(f.left)} left (${section} rest ${fmt(sec.rest)}).` : "Transaction added";
    });
  }

  return (
    <Sheet title={editing ? `Edit transaction #${tx.index}` : "Add transaction"} onClose={onClose} error={error}
      canSubmit={!!target && !!amount.trim()}
      onRemove={editing ? () => onDelete({
        title: "Delete transaction?", body: `Delete #${tx.index}: ${tx.field} ${fmt(tx.amount)}${tx.description ? ` (${tx.description})` : ""}.`,
        path: "/api/transactions/delete", payload: { index: tx.index }, ok: `Transaction #${tx.index} deleted`,
      }) : undefined}
      onSubmit={() => run(submit)}>
      {editing ? (
        <div className="caption">{tx.field} · {tx.section}</div>
      ) : (
        <FieldPicker month={month} value={target} onChange={setTarget} />
      )}
      <AmountField label="Amount" value={amount} onChange={setAmount} autoFocus={editing || !!preset}
        hint="Arithmetic works: 15.71+1.35" />
      <DayStepper value={day} max={key ? daysIn(key) : 31} onChange={setDay} />
      <TextField label="Description" value={description} onChange={setDescription} placeholder="Optional" />
    </Sheet>
  );
}

function TransferSheet({ act, onClose, month, from }: Ctx & { from?: { section: string; field: string } }) {
  const key = month?.key ?? "";
  const [src, setSrc] = useState(from ? fkey(from) : "");
  const [dst, setDst] = useState("");
  const [amount, setAmount] = useState("");
  const [day, setDay] = useState(defaultDay(key));
  const [note, setNote] = useState("");
  const { error, run } = useSubmit();
  const options = [{ value: "", label: "Choose a field…" },
    ...allFields(month).map((f) => ({ value: fkey(f), label: `${f.field} — ${f.section}` }))];
  return (
    <Sheet title="Transfer" onClose={onClose} error={error} submitLabel="Move money"
      canSubmit={!!src && !!dst && src !== dst && !!amount.trim()}
      onSubmit={() => run(async () => {
        const a = fparse(src), b = fparse(dst);
        await act("/api/transfers", {
          from_section: a.section, from_field: a.field, to_section: b.section, to_field: b.field, amount, day, note,
        }, (s) => `Moved ${fmt(s.month?.transfers.at(-1)?.amount)} ${a.field} → ${b.field}`);
      })}>
      <div className="caption" style={{ marginTop: -8 }}>Moves pot money (left) between fields. Refused if it would push the target past its max.</div>
      <SelectField label="From" value={src} onChange={setSrc} options={options} />
      <SelectField label="To" value={dst} onChange={setDst} options={options} />
      <AmountField label="Amount" value={amount} onChange={setAmount} />
      <DayStepper value={day} max={key ? daysIn(key) : 31} onChange={setDay} />
      <TextField label="Note" value={note} onChange={setNote} placeholder="Optional" />
    </Sheet>
  );
}

// --- pockets -----------------------------------------------------------------
function PocketSheet({ act, onClose, onDelete, pocket }: Ctx & { pocket?: Pocket }) {
  const editing = !!pocket;
  const [name, setName] = useState(pocket?.name ?? "");
  const [main, setMain] = useState(false);
  const { error, run } = useSubmit();
  return (
    <Sheet title={editing ? "Edit pocket" : "Add pocket"} onClose={onClose} error={error}
      canSubmit={!!name.trim() && (!editing || !!changed(name, pocket.name) || main)}
      onRemove={editing && !pocket.is_default ? () => onDelete({
        title: "Delete pocket?", body: `Delete ${pocket.name}. Only a pocket no field uses can be deleted.`,
        path: "/api/pockets/delete", payload: { pocket: pocket.name }, ok: `Pocket ${pocket.name} deleted`,
      }) : undefined}
      onSubmit={() => run(() => editing
        ? act("/api/pockets/edit", { pocket: pocket.name, name: changed(name, pocket.name), main }, `Pocket ${name.trim()} updated`)
        : act("/api/pockets", { name }, `Pocket ${name.trim()} added`))}>
      <TextField label="Name" value={name} onChange={setName} autoFocus placeholder="Revolut"
        hint={editing ? undefined : "A place your money physically sits: a bank account, cash, a broker."} />
      {editing && !pocket.is_default && (
        <label className="caption" style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
          <input type="checkbox" checked={main} onChange={(e) => setMain(e.target.checked)} />
          Make this the default pocket (it also holds section rests and new fields)
        </label>
      )}
    </Sheet>
  );
}
