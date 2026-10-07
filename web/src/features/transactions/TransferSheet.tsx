import { useState } from "react";
import type { FieldRef } from "../../api/client";
import { useMonthView } from "../../app/month";
import { useToast } from "../../app/toast";
import { useSubmit } from "../../app/useSubmit";
import { Sheet } from "../../components/Sheet";
import { AmountField, DayStepper, SelectField, TextField } from "../../components/TextField";
import { sectionAccent } from "../../lib/budget";
import { daysIn, defaultDay, weekdayLabel } from "../../lib/dates";
import { evaluate } from "../../lib/expression";
import { formatMoney, units } from "../../lib/money";
import { fieldKey, parseFieldKey, resolveFieldKey } from "../fieldKey";
import { FieldOptions, SheetActions } from "../forms";
import styles from "../sheets.module.css";

interface TransferSheetProps {
  /** Start with this field as the source (opened from a field's menu). */
  from?: FieldRef;
  onClose: () => void;
}

/**
 * Move money that has built up in one field's pot into another's. It relocates
 * LEFT only — nothing is "spent" — and is refused if it would push the
 * receiving field above its max.
 */
export function TransferSheet({ from: preset, onClose }: TransferSheetProps) {
  const { month, actions } = useMonthView();
  const toast = useToast();
  const { busy, errors, submit } = useSubmit(
    ["from_field", "to_field", "amount", "day", "note"],
    onClose,
  );

  const [from, setFrom] = useState(preset ? fieldKey(preset.section, preset.field) : "");
  const [to, setTo] = useState("");
  const [amount, setAmount] = useState("");
  const [day, setDay] = useState(() => defaultDay(month.key));
  const [note, setNote] = useState("");

  const source = resolveFieldKey(month, from);
  const target = resolveFieldKey(month, to);
  const value = evaluate(amount);
  const sameField = from !== "" && from === to;
  const missing =
    !source || !target
      ? "Choose the field to move from and the field to move to."
      : sameField
        ? "Choose two different fields."
        : value === null || value <= 0n
          ? "Enter an amount greater than zero."
          : null;
  const canSave = missing === null;

  // How much the receiving field can still take before its max.
  const room =
    target && target.field.max !== null ? units(target.field.max) - units(target.field.left) : null;

  function save() {
    const fromRef = parseFieldKey(from);
    const toRef = parseFieldKey(to);
    if (!fromRef || !toRef || !source || !target || value === null) return;
    void submit(async () => {
      await actions.addTransfer({
        from_field: fromRef,
        to_field: toRef,
        amount: amount.trim(),
        day,
        note: note.trim(),
      });
      toast({
        message: `Moved ${formatMoney(value)} ${source.field.name} → ${target.field.name}.`,
      });
      onClose();
    });
  }

  return (
    <Sheet
      title="Transfer"
      onClose={onClose}
      onSubmit={save}
      error={errors.form}
      missing={missing}
      footer={
        <SheetActions onCancel={onClose} canSave={canSave} busy={busy} saveLabel="Transfer" />
      }
    >
      <SelectField
        label="from"
        value={from}
        onChange={setFrom}
        error={errors.fields.from_field}
        accent={source ? sectionAccent(source.section.index) : null}
        hint={source && `Holds ${formatMoney(source.field.left)}.`}
      >
        <option value="" disabled>
          Choose a field
        </option>
        <FieldOptions month={month} />
      </SelectField>

      <SelectField
        label="to"
        value={to}
        onChange={setTo}
        error={
          errors.fields.to_field ?? (sameField ? "Choose a different field to move it to." : null)
        }
        accent={target ? sectionAccent(target.section.index) : null}
        hint={
          target &&
          (room === null
            ? `Holds ${formatMoney(target.field.left)}; no max.`
            : `Holds ${formatMoney(target.field.left)}; room for ${formatMoney(room)} before its max.`)
        }
      >
        <option value="" disabled>
          Choose a field
        </option>
        <FieldOptions month={month} />
      </SelectField>

      <AmountField
        label="amount"
        value={amount}
        onChange={setAmount}
        error={errors.fields.amount}
        autoFocus={Boolean(preset)}
        describe={(moved) =>
          source && ` · ${source.field.name} keeps ${formatMoney(units(source.field.left) - moved)}`
        }
      />

      <div className={styles.pair}>
        <DayStepper
          value={day}
          max={daysIn(month.key)}
          onChange={setDay}
          caption={weekdayLabel(month.key, day)}
          error={errors.fields.day}
        />
        <TextField
          label="note"
          value={note}
          onChange={setNote}
          error={errors.fields.note}
          placeholder="Optional"
          maxLength={200}
        />
      </div>
    </Sheet>
  );
}
