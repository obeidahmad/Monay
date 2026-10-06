// Shared UI primitives from the Monay design system: Sheet, ConfirmDialog,
// Toasts, TextField, AmountField, DayStepper, Menu, Segmented, StatusChip.
import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { evaluate } from "./api";
import { fmt } from "./format";
import { IconClose, IconLock, IconMinus, IconMore, IconPlusSmall } from "./icons";

// --- Sheet -------------------------------------------------------------------
export function Sheet(props: {
  title: string;
  onClose: () => void;
  onSubmit: () => void | Promise<void>;
  submitLabel?: string;
  canSubmit?: boolean;
  error?: string | null;
  onRemove?: () => void;
  removeLabel?: string;
  children: ReactNode;
}) {
  const { title, onClose, onSubmit, submitLabel = "Save", canSubmit = true, error, onRemove } = props;
  const [busy, setBusy] = useState(false);
  useEscape(onClose);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit || busy) return;
    setBusy(true);
    try {
      await onSubmit();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="sheet glass-strong" role="dialog" aria-modal="true" aria-label={title} onSubmit={submit}>
        <div className="handle" />
        <div className="sheet-head">
          <h2>{title}</h2>
          <button type="button" className="icon-btn" aria-label="Close" onClick={onClose}>
            <IconClose />
          </button>
        </div>
        <div className="form">
          {props.children}
          {error && <div className="form-error" role="alert">{error}</div>}
        </div>
        <div className="sheet-foot">
          {onRemove && (
            <button type="button" className="btn danger" onClick={onRemove}>
              {props.removeLabel ?? "Remove"}
            </button>
          )}
          <div className="actions">
            <button type="button" className="btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn primary" disabled={!canSubmit || busy}>{submitLabel}</button>
          </div>
        </div>
      </form>
    </div>
  );
}

// --- ConfirmDialog -----------------------------------------------------------
export function ConfirmDialog(props: {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  onConfirm: () => void | Promise<void>;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  useEscape(props.onClose);
  return (
    <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && props.onClose()}>
      <div className="sheet glass-strong" role="alertdialog" aria-modal="true" aria-label={props.title}>
        <div className="handle" />
        <div className="sheet-head"><h2>{props.title}</h2></div>
        <div className="form">{props.children}</div>
        <div className="sheet-foot">
          <div className="actions">
            <button type="button" className="btn" onClick={props.onClose}>Cancel</button>
            <button
              type="button"
              className={`btn primary`}
              disabled={busy}
              autoFocus
              onClick={async () => {
                setBusy(true);
                try { await props.onConfirm(); } finally { setBusy(false); }
              }}
            >
              {props.confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function useEscape(onClose: () => void) {
  const ref = useRef(onClose);
  ref.current = onClose;
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && ref.current();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);
}

// --- Toasts ------------------------------------------------------------------
export interface ToastMsg { id: number; text: string; tone: "ok" | "error" | "info" }

export function Toasts({ toasts }: { toasts: ToastMsg[] }) {
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className="toast" role={t.tone === "error" ? "alert" : "status"}>
          <span className={t.tone === "ok" ? "pos" : t.tone === "error" ? "neg" : "muted"}>
            {t.tone === "ok" ? "✓" : t.tone === "error" ? "⚠" : "●"}
          </span>
          {t.text}
        </div>
      ))}
    </div>
  );
}

// --- inputs ------------------------------------------------------------------
export function TextField(props: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hint?: ReactNode;
  autoFocus?: boolean;
  aside?: ReactNode;
  error?: string | null;
}) {
  const id = useId();
  return (
    <div className="tf">
      <label className="label" htmlFor={id}>{props.label}{props.aside}</label>
      <input id={id} value={props.value} placeholder={props.placeholder} autoFocus={props.autoFocus}
        autoComplete="off" onChange={(e) => props.onChange(e.target.value)} />
      {props.error ? <div className="field-error">{props.error}</div> : props.hint && <div className="hint">{props.hint}</div>}
    </div>
  );
}

/** An amount input that accepts arithmetic and previews the result (= 17.06). */
export function AmountField(props: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  hint?: ReactNode;
  allowPercent?: boolean;
  aside?: ReactNode;
}) {
  const id = useId();
  const [preview, setPreview] = useState<{ ok: boolean; text: string } | null>(null);
  const raw = props.value.trim();
  const isPct = props.allowPercent && raw.endsWith("%");

  useEffect(() => {
    if (!raw || isPct || /^-?\d+(\.\d+)?$/.test(raw) || /^inf|∞$/i.test(raw)) {
      setPreview(null);
      return;
    }
    let live = true;
    const t = setTimeout(() => {
      evaluate(raw)
        .then((v) => live && setPreview({ ok: true, text: `= ${fmt(v)}` }))
        .catch((e: Error) => live && setPreview({ ok: false, text: e.message }));
    }, 250);
    return () => { live = false; clearTimeout(t); };
  }, [raw, isPct]);

  return (
    <div className="tf">
      <label className="label" htmlFor={id}>{props.label}{props.aside}</label>
      <input id={id} className="num-input" inputMode="decimal" value={props.value}
        placeholder={props.placeholder ?? "0.00"} autoFocus={props.autoFocus} autoComplete="off"
        onChange={(e) => props.onChange(e.target.value)} />
      {preview ? (
        <div className={preview.ok ? "caption" : "field-error"} style={{ textAlign: preview.ok ? "right" : "left" }}>
          {preview.text}
        </div>
      ) : (
        props.hint && <div className="hint">{props.hint}</div>
      )}
    </div>
  );
}

export function SelectField(props: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  hint?: ReactNode;
}) {
  const id = useId();
  return (
    <div className="tf">
      <label className="label" htmlFor={id}>{props.label}</label>
      <select id={id} value={props.value} onChange={(e) => props.onChange(e.target.value)}>
        {props.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      {props.hint && <div className="hint">{props.hint}</div>}
    </div>
  );
}

export function DayStepper(props: { value: number; max: number; onChange: (v: number) => void; label?: string }) {
  const id = useId();
  const clamp = (v: number) => Math.min(props.max, Math.max(1, v || 1));
  return (
    <div className="tf">
      <label className="label" htmlFor={id}>{props.label ?? "Day"}</label>
      <div className="stepper">
        <button type="button" className="icon-btn" aria-label="Previous day" onClick={() => props.onChange(clamp(props.value - 1))}><IconMinus /></button>
        <input id={id} inputMode="numeric" value={props.value}
          onChange={(e) => props.onChange(clamp(Number(e.target.value.replace(/\D/g, ""))))} />
        <button type="button" className="icon-btn" aria-label="Next day" onClick={() => props.onChange(clamp(props.value + 1))}><IconPlusSmall /></button>
      </div>
    </div>
  );
}

export function Segmented<T extends string>(props: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string; disabled?: boolean }[];
  label?: string;
}) {
  return (
    <div className="tf">
      {props.label && <span className="label">{props.label}</span>}
      <div className="segmented" role="group" aria-label={props.label}>
        {props.options.map((o) => (
          <button key={o.value} type="button" aria-pressed={o.value === props.value} disabled={o.disabled}
            onClick={() => props.onChange(o.value)}>{o.label}</button>
        ))}
      </div>
    </div>
  );
}

// --- menu ----------------------------------------------------------------------
export function Menu({ items, label }: { items: { label: string; onClick: () => void; danger?: boolean }[]; label: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    const k = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", h);
    document.addEventListener("keydown", k);
    return () => { document.removeEventListener("mousedown", h); document.removeEventListener("keydown", k); };
  }, [open]);
  return (
    <div className="menu-anchor" ref={ref}>
      <button type="button" className="icon-btn" aria-label={label} aria-haspopup="menu" aria-expanded={open}
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}>
        <IconMore />
      </button>
      {open && (
        <div className="menu glass-strong" role="menu">
          {items.map((it) => (
            <button key={it.label} type="button" role="menuitem" className={it.danger ? "danger" : ""}
              onClick={(e) => { e.stopPropagation(); setOpen(false); it.onClick(); }}>
              {it.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// --- small bits --------------------------------------------------------------
export function StatusChip({ closed }: { closed: boolean }) {
  return closed ? (
    <span className="chip"><IconLock /> closed</span>
  ) : (
    <span className="chip"><span className="pos">●</span> open</span>
  );
}

export function Amount({ value, className = "" }: { value: string | null; className?: string }) {
  const neg = value !== null && value.startsWith("-") && Number(value) !== 0;
  return <span className={`num ${neg ? "neg" : ""} ${className}`}>{fmt(value)}</span>;
}

export function EmptyState({ text, action }: { text: string; action?: ReactNode }) {
  return (
    <div className="empty">
      <span className="muted">{text}</span>
      {action}
    </div>
  );
}
