import { ChevronDown, Minus, Plus } from "lucide-react";
import {
  useId,
  useState,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";
import { cx } from "../lib/cx";
import { evaluate } from "../lib/expression";
import { formatMoney, type Units } from "../lib/money";
import styles from "./TextField.module.css";

// ---------------------------------------------------------------------------
// The frame every input shares: a label above, a hint or an error below.
// ---------------------------------------------------------------------------
interface FrameProps {
  /** The id of the control the label names; omit when there is no control. */
  id?: string;
  label: string;
  /** A small control on the label's line: the choice that qualifies the input. */
  aside?: ReactNode;
  hint?: ReactNode;
  /** Says what to do, never just "Invalid". Shown instead of the hint. */
  error?: string | null;
  children?: ReactNode;
  className?: string;
}

function Frame({ id, label, aside, hint, error, children, className }: FrameProps) {
  return (
    <div className={cx(styles.field, className)}>
      <div className={styles.labelRow}>
        {id ? (
          <label htmlFor={id} className="label">
            {label}
          </label>
        ) : (
          <span className="label">{label}</span>
        )}
        {aside}
      </div>
      {children}
      {error ? (
        <p id={id && `${id}-note`} className={styles.error}>
          {error}
        </p>
      ) : (
        hint && (
          <p id={id && `${id}-note`} className="caption">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

/** A label with a choice beside it and a sentence beneath — and no input. */
export function Labelled({ label, aside, hint }: Pick<FrameProps, "label" | "aside" | "hint">) {
  return <Frame label={label} aside={aside} hint={hint} />;
}

// ---------------------------------------------------------------------------
// Text
// ---------------------------------------------------------------------------
interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
  aside?: ReactNode;
  hint?: ReactNode;
  error?: string | null;
  /** Take focus when the page or Sheet opens. */
  autoFocus?: boolean;
  /** Right-align (numbers). */
  numeric?: boolean;
}

export function TextField({
  label,
  value,
  onChange,
  aside,
  hint,
  error,
  autoFocus,
  numeric,
  className,
  ...rest
}: TextFieldProps) {
  const id = useId();
  return (
    <Frame id={id} label={label} aside={aside} hint={hint} error={error} className={className}>
      <input
        id={id}
        className={cx(styles.control, numeric && styles.numeric)}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? `${id}-note` : undefined}
        // On a page this focuses on mount. Inside a Sheet the input isn't
        // focusable yet (the dialog opens a moment later), so the Sheet looks
        // for the marker and focuses it once it is (useModal).
        autoFocus={autoFocus}
        data-autofocus={autoFocus ? "" : undefined}
        autoComplete="off"
        {...rest}
      />
    </Frame>
  );
}

// ---------------------------------------------------------------------------
// Amount — accepts arithmetic and shows the result as you type
// ---------------------------------------------------------------------------
export const AMOUNT_HELP = "Use numbers with + - * / and parentheses, like 15.71+1.35.";

interface AmountFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** Extra words after the result: `= 17.06 · 332.94 left after`. */
  describe?: (amount: Units) => ReactNode;
  aside?: ReactNode;
  /** Shown while the field is empty. */
  hint?: ReactNode;
  /** An error from the server for this field. */
  error?: string | null;
  autoFocus?: boolean;
  placeholder?: string;
  className?: string;
}

export function AmountField({
  label,
  value,
  onChange,
  describe,
  aside,
  hint,
  error,
  autoFocus,
  placeholder = "0.00",
  className,
}: AmountFieldProps) {
  // Half-typed input ("15.71+") is not a mistake yet: only complain once the
  // person has left the field.
  const [touched, setTouched] = useState(false);
  const amount = evaluate(value);
  const empty = value.trim() === "";

  const note = empty ? (
    hint
  ) : amount !== null ? (
    <>
      = {formatMoney(amount)}
      {describe?.(amount)}
    </>
  ) : (
    "…"
  );
  const problem = error ?? (!empty && amount === null && touched ? AMOUNT_HELP : null);

  return (
    <TextField
      label={label}
      value={value}
      onChange={onChange}
      onBlur={() => setTouched(true)}
      aside={aside}
      hint={note}
      error={problem}
      autoFocus={autoFocus}
      placeholder={placeholder}
      inputMode="decimal"
      numeric
      className={className}
    />
  );
}

// ---------------------------------------------------------------------------
// Select
// ---------------------------------------------------------------------------
interface SelectFieldProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "onChange"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: ReactNode;
  error?: string | null;
  /** A swatch shown inside the control (the chosen field's section accent). */
  accent?: string | null;
  children: ReactNode;
}

export function SelectField({
  label,
  value,
  onChange,
  hint,
  error,
  accent,
  children,
  className,
  ...rest
}: SelectFieldProps) {
  const id = useId();
  return (
    <Frame id={id} label={label} hint={hint} error={error} className={className}>
      <div className={styles.selectWrap}>
        {accent && <i className={styles.swatch} style={{ background: accent }} />}
        <select
          id={id}
          className={cx(styles.control, styles.select, accent && styles.withSwatch)}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || hint ? `${id}-note` : undefined}
          {...rest}
        >
          {children}
        </select>
        <ChevronDown className={styles.chevron} size={18} aria-hidden="true" />
      </div>
    </Frame>
  );
}

// ---------------------------------------------------------------------------
// Segmented choice: a pill track with the chosen option lifted
// ---------------------------------------------------------------------------
interface SegmentedControlProps<Value extends string> {
  /** The group's accessible name. */
  label: string;
  value: Value;
  options: { value: Value; label: string }[];
  onChange: (value: Value) => void;
  /** A smaller track, for sitting on a label's line. */
  compact?: boolean;
}

/** The track on its own — for a label row, or wherever a label already exists. */
export function SegmentedControl<Value extends string>({
  label,
  value,
  options,
  onChange,
  compact = false,
}: SegmentedControlProps<Value>) {
  return (
    <div
      className={cx(styles.segmented, compact && styles.compact)}
      role="radiogroup"
      aria-label={label}
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={option.value === value}
          className={cx(styles.segment, option.value === value && styles.chosen)}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

interface SegmentedProps<Value extends string> extends SegmentedControlProps<Value> {
  hint?: ReactNode;
}

/** A segmented choice as a form field: label above, optional hint below. */
export function Segmented<Value extends string>({ hint, ...control }: SegmentedProps<Value>) {
  return (
    <div className={styles.field}>
      <span className="label" aria-hidden="true">
        {control.label}
      </span>
      <SegmentedControl {...control} />
      {hint && <p className="caption">{hint}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Day stepper
// ---------------------------------------------------------------------------
interface DayStepperProps {
  label?: string;
  value: number;
  min?: number;
  max: number;
  onChange: (day: number) => void;
  /** "Sun 5 Jan" under the control. */
  caption?: ReactNode;
  error?: string | null;
}

export function DayStepper({
  label = "day",
  value,
  min = 1,
  max,
  onChange,
  caption,
  error,
}: DayStepperProps) {
  const id = useId();
  const clamp = (day: number) => Math.min(max, Math.max(min, day));
  return (
    <Frame id={id} label={label} hint={caption} error={error}>
      <div className={styles.stepper}>
        <button
          type="button"
          className={styles.step}
          aria-label="Previous day"
          disabled={value <= min}
          onClick={() => onChange(clamp(value - 1))}
        >
          <Minus size={16} />
        </button>
        <input
          id={id}
          className={styles.stepValue}
          value={value}
          inputMode="numeric"
          autoComplete="off"
          aria-describedby={caption || error ? `${id}-note` : undefined}
          onChange={(event) => {
            const typed = Number(event.target.value.replace(/\D/g, "").slice(-2));
            if (typed >= min) onChange(clamp(typed));
          }}
          onFocus={(event) => event.target.select()}
        />
        <button
          type="button"
          className={styles.step}
          aria-label="Next day"
          disabled={value >= max}
          onClick={() => onChange(clamp(value + 1))}
        >
          <Plus size={16} />
        </button>
      </div>
    </Frame>
  );
}
