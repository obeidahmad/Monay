import { useState } from "react";
import type { FieldRef, Schemas, Transaction } from "../../api/client";
import { useMonthView } from "../../app/month";
import { useToast } from "../../app/toast";
import { useAct } from "../../app/useAct";
import { useSubmit } from "../../app/useSubmit";
import { Button } from "../../components/Button";
import { Chip, ChipRow } from "../../components/Chip";
import { EmptyState } from "../../components/EmptyState";
import { Sheet, SheetSpacer } from "../../components/Sheet";
import { AmountField, DayStepper, SelectField, TextField } from "../../components/TextField";
import { findField, leftAfter, sectionAccent } from "../../lib/budget";
import { daysIn, defaultDay, weekdayLabel } from "../../lib/dates";
import { evaluate } from "../../lib/expression";
import { formatMoney, plain, units } from "../../lib/money";
import { fieldKey, parseFieldKey, recentFieldKeys, resolveFieldKey } from "../fieldKey";
import { FieldOptions, SheetActions } from "../forms";
import styles from "../sheets.module.css";

interface TransactionSheetProps {
  /** The transaction to correct; absent to record a new one. */
  edit?: Transaction;
  /** Start on this field (opened from a field's menu). */
  field?: FieldRef;
  onClose: () => void;
}

/**
 * Record or correct a transaction. Built to be quick: a chip for each recently
 * used field, one number, a day that already says today, Save.
 */
export function TransactionSheet({ edit, field: preset, onClose }: TransactionSheetProps) {
  const { month, actions } = useMonthView();
  const toast = useToast();
  const act = useAct();
  const { busy, errors, submit } = useSubmit(["field", "amount", "day", "description"], onClose);

  const recent = recentFieldKeys(month);
  const original = {
    target: edit
      ? fieldKey(edit.field.section_index, edit.field.field_index)
      : preset
        ? fieldKey(preset.section, preset.field)
        : (recent[0] ?? ""),
    amount: edit ? edit.expression || plain(edit.amount) : "",
  };
  const [target, setTarget] = useState(original.target);
  const [amount, setAmount] = useState(original.amount);
  const [day, setDay] = useState(() => edit?.day ?? defaultDay(month.key));
  const [description, setDescription] = useState(edit?.description ?? "");

  const chosen = resolveFieldKey(month, target);
  const value = evaluate(amount);
  const missing = !chosen
    ? "Choose a field."
    : value === null || value <= 0n
      ? "Enter an amount greater than zero."
      : null;
  const canSave = missing === null;
  // Editing on the same field: the old amount comes back before the new one goes.
  const refund = edit && target === original.target ? units(edit.amount) : 0n;

  if (month.sections.every((section) => section.fields.length === 0)) {
    return (
      <Sheet
        title="Add transaction"
        onClose={onClose}
        onSubmit={onClose}
        footer={
          <>
            <SheetSpacer />
            <Button onClick={onClose}>Close</Button>
          </>
        }
      >
        <EmptyState title="No fields yet">
          A transaction is money leaving a field. Add a section and a field on the Budget tab first.
        </EmptyState>
      </Sheet>
    );
  }

  /** "332.94 left." for the field the change landed on. */
  function leftOf(change: Schemas["ChangeOut"], ref: FieldRef): string {
    const landed = findField(change.month, ref.section, ref.field);
    return landed ? ` ${formatMoney(landed.field.left)} left.` : "";
  }

  function save() {
    const ref = parseFieldKey(target);
    if (!ref || !chosen || value === null) return;
    void submit(async () => {
      if (!edit) {
        const change = await actions.addTransaction({
          field: ref,
          amount: amount.trim(),
          day,
          description: description.trim(),
        });
        toast({ message: `${chosen.field.name} -${formatMoney(value)}.${leftOf(change, ref)}` });
      } else {
        // Send only what changed: an untouched value is left exactly as stored.
        const body: Schemas["TransactionUpdate"] = {};
        if (target !== original.target) body.field = ref;
        if (amount.trim() !== original.amount) body.amount = amount.trim();
        if (day !== edit.day) body.day = day;
        if (description.trim() !== edit.description) body.description = description.trim();
        if (Object.keys(body).length > 0) {
          const change = await actions.editTransaction(edit.number, body);
          toast({ message: `Transaction #${edit.number} updated.${leftOf(change, ref)}` });
        }
      }
      onClose();
    });
  }

  function remove() {
    if (!edit) return;
    onClose();
    void act(() => actions.deleteTransaction(edit.number), {
      kind: "info",
      message: "Transaction deleted",
    });
  }

  return (
    <Sheet
      title={edit ? "Edit transaction" : "Add transaction"}
      onClose={onClose}
      onSubmit={save}
      error={errors.form}
      missing={missing}
      footer={
        <SheetActions
          onRemove={edit ? remove : undefined}
          onCancel={onClose}
          canSave={canSave}
          busy={busy}
        />
      }
    >
      <SelectField
        label="field"
        value={target}
        onChange={setTarget}
        error={errors.fields.field}
        accent={chosen ? sectionAccent(chosen.section.index) : null}
      >
        <option value="" disabled>
          Choose a field
        </option>
        <FieldOptions month={month} />
      </SelectField>

      {recent.length > 1 && (
        <ChipRow label="Recent fields">
          {recent.map((key) => {
            const option = resolveFieldKey(month, key);
            return (
              option && (
                <Chip
                  key={key}
                  selected={key === target}
                  accent={sectionAccent(option.section.index)}
                  onClick={() => setTarget(key)}
                >
                  {option.field.name}
                </Chip>
              )
            );
          })}
        </ChipRow>
      )}

      <AmountField
        label="amount"
        value={amount}
        onChange={setAmount}
        error={errors.fields.amount}
        autoFocus
        describe={(spend) =>
          chosen && ` · ${formatMoney(leftAfter(chosen.field, spend, refund))} left after`
        }
      />

      <div className={styles.pair}>
        <DayStepper
          value={day}
          max={Math.max(daysIn(month.key), day)}
          onChange={setDay}
          caption={weekdayLabel(month.key, day)}
          error={errors.fields.day}
        />
        <TextField
          label="description"
          value={description}
          onChange={setDescription}
          error={errors.fields.description}
          placeholder="Optional"
          maxLength={200}
        />
      </div>
    </Sheet>
  );
}
