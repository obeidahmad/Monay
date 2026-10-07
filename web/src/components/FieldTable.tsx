import { useState, type KeyboardEvent, type ReactNode } from "react";
import { ApiError, type Field, type Schemas } from "../api/client";
import { budgetLabel } from "../lib/budget";
import { formatMoney, plain } from "../lib/money";
import { Amount } from "./Amount";
import styles from "./FieldTable.module.css";
import { Menu, type MenuEntry } from "./Menu";

type FieldUpdate = Schemas["FieldUpdate"];

interface FieldTableProps {
  fields: Field[];
  /** Stacked rows instead of a table — narrow screens. */
  stacked: boolean;
  /** A closed month: values are plain text, nothing opens. */
  readOnly: boolean;
  /** CURRENT can only be typed in a profile's first month. */
  currentEditable: boolean;
  /** Open the field's edit Sheet. */
  onOpen: (field: Field) => void;
  /** Save one value edited in place; rejects with an `ApiError` if refused. */
  onSave: (field: Field, change: FieldUpdate) => Promise<unknown>;
  menu: (field: Field) => MenuEntry[];
}

/**
 * The fields of a section. Column colours are fixed (budget, paid, max and
 * pocket each keep theirs); LEFT is `ok` at zero or more and `error` with a
 * minus sign below.
 *
 * On desktop a budget, max or (first month) current is edited where it stands:
 * click it, type, Enter saves, Escape cancels. On narrow screens each field is
 * a stacked row and tapping it opens the field's Sheet.
 */
export function FieldTable(props: FieldTableProps) {
  return props.stacked ? <StackedFields {...props} /> : <WideTable {...props} />;
}

function WideTable({ fields, readOnly, currentEditable, onSave, menu }: FieldTableProps) {
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          {["field", "budget", "current", "paid", "left", "max", "pocket"].map((heading) => (
            <th key={heading} className="label" scope="col">
              {heading}
            </th>
          ))}
          {!readOnly && (
            <th>
              <span className="sr-only">Actions</span>
            </th>
          )}
        </tr>
      </thead>
      <tbody>
        {fields.map((field) => (
          <tr key={field.index}>
            <th scope="row" className={styles.name}>
              {field.name}
            </th>
            <td className={styles.budget}>
              <Editable
                label={`${field.name} budget`}
                locked={readOnly}
                initial={field.budget_pct === null ? plain(field.budget) : `${field.budget_pct}%`}
                onSave={(text) => onSave(field, { budget: toBudget(text) })}
              >
                {budgetLabel(field)}
              </Editable>
            </td>
            <td>
              <Editable
                label={`${field.name} current`}
                locked={readOnly || !currentEditable}
                initial={plain(field.current)}
                onSave={(text) => onSave(field, { current: text || "0" })}
              >
                <Amount value={field.current} />
              </Editable>
            </td>
            <td className={styles.paid}>{formatMoney(field.paid)}</td>
            <td>
              <Amount value={field.left} tone="balance" />
            </td>
            <td className={styles.dim}>
              <Editable
                label={`${field.name} max`}
                locked={readOnly}
                initial={field.max === null ? "" : plain(field.max)}
                placeholder="∞"
                onSave={(text) => onSave(field, { max: toMax(text) })}
              >
                {field.max === null ? "∞" : formatMoney(field.max)}
              </Editable>
            </td>
            <td className={styles.dim}>{field.pocket}</td>
            {!readOnly && (
              <td className={styles.actions}>
                <Menu label={`Actions for ${field.name}`} items={menu(field)} />
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StackedFields({ fields, readOnly, onOpen, menu }: FieldTableProps) {
  return (
    <ul className={styles.stack}>
      {fields.map((field) => {
        const summary = (
          <>
            <span className={styles.stackTop}>
              <span className={styles.name}>{field.name}</span>
              <Amount value={field.left} tone="balance" />
            </span>
            <span className={styles.trio}>
              <span>
                budget<b className={styles.budget}>{budgetLabel(field)}</b>
              </span>
              <span>
                paid<b className={styles.paid}>{formatMoney(field.paid)}</b>
              </span>
              <span>
                max<b className={styles.dim}>{field.max === null ? "∞" : formatMoney(field.max)}</b>
              </span>
            </span>
            <span className="caption">
              current {formatMoney(field.current)} · {field.pocket}
            </span>
          </>
        );
        return (
          <li key={field.index} className={styles.stackRow}>
            {readOnly ? (
              <div className={styles.stackMain}>{summary}</div>
            ) : (
              <>
                <button type="button" className={styles.stackMain} onClick={() => onOpen(field)}>
                  {summary}
                </button>
                <Menu label={`Actions for ${field.name}`} items={menu(field)} />
              </>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/** `20%` is a percentage budget; anything else is an amount expression. */
function toBudget(text: string): Schemas["AmountOrPercent"] {
  return text.endsWith("%")
    ? { type: "percent", value: text.slice(0, -1).trim() }
    : { type: "amount", value: text || "0" };
}

/** Empty, `∞` or `inf` means no limit. */
function toMax(text: string): string | null {
  return /^(∞|inf|infinite|none)?$/i.test(text) ? null : text;
}

// ---------------------------------------------------------------------------
// A value edited where it stands
// ---------------------------------------------------------------------------
interface EditableProps {
  label: string;
  /** Not editable right now: render the value as plain text. */
  locked: boolean;
  /** What the input starts with — the raw value, not its formatted form. */
  initial: string;
  placeholder?: string;
  onSave: (text: string) => Promise<unknown>;
  children: ReactNode;
}

function Editable({ label, locked, initial, placeholder, onSave, children }: EditableProps) {
  const [draft, setDraft] = useState<string | null>(null); // null = not editing
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (locked) return <>{children}</>;

  if (draft === null) {
    return (
      <button
        type="button"
        className={styles.value}
        title="Click to edit"
        aria-label={`Edit ${label}`}
        onClick={() => {
          setError(null);
          setDraft(initial);
        }}
      >
        {children}
      </button>
    );
  }

  async function save(text: string) {
    if (text === initial) return setDraft(null);
    setSaving(true);
    try {
      await onSave(text);
      setDraft(null);
    } catch (problem) {
      // The month changed elsewhere: this cell may no longer be the field it
      // was opened on, so drop the edit rather than offer a retry.
      if (problem instanceof ApiError && problem.stale) setDraft(null);
      else setError(problem instanceof ApiError ? problem.message : "That couldn't be saved.");
    } finally {
      setSaving(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") void save(event.currentTarget.value.trim());
    else if (event.key === "Escape") setDraft(null);
  }

  return (
    <span className={styles.editing}>
      <input
        className={styles.input}
        value={draft}
        placeholder={placeholder}
        aria-label={label}
        aria-invalid={error ? true : undefined}
        autoFocus
        autoComplete="off"
        // Read-only rather than disabled while saving: a disabled input drops
        // focus, and a refused value should still be right there to fix.
        readOnly={saving}
        onChange={(event) => setDraft(event.target.value)}
        onFocus={(event) => event.target.select()}
        onKeyDown={onKeyDown}
        // Leaving the field without Enter discards the edit.
        onBlur={() => !saving && setDraft(null)}
      />
      {error && (
        <span className={styles.problem} role="alert">
          {error}
        </span>
      )}
    </span>
  );
}
