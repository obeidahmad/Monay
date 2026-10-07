import { useState } from "react";
import type { Income, Schemas } from "../../api/client";
import { useMonthView } from "../../app/month";
import { useToast } from "../../app/toast";
import { useAct } from "../../app/useAct";
import { useSubmit } from "../../app/useSubmit";
import { Sheet } from "../../components/Sheet";
import { AmountField, TextField } from "../../components/TextField";
import { evaluate } from "../../lib/expression";
import { formatMoney, plain } from "../../lib/money";
import { SheetActions } from "../forms";

interface IncomeSheetProps {
  edit?: Income;
  onClose: () => void;
}

/** Add or edit an income entry — a named amount entering the month. */
export function IncomeSheet({ edit, onClose }: IncomeSheetProps) {
  const { actions } = useMonthView();
  const toast = useToast();
  const act = useAct();
  const { busy, errors, submit } = useSubmit(["name", "amount"], onClose);

  const original = { name: edit?.name ?? "", amount: edit ? plain(edit.amount) : "" };
  const [name, setName] = useState(original.name);
  const [amount, setAmount] = useState(original.amount);

  const missing =
    name.trim() === ""
      ? "Give the income a name."
      : evaluate(amount) === null
        ? "Enter an amount."
        : null;
  const canSave = missing === null;

  function save() {
    void submit(async () => {
      if (!edit) {
        const change = await actions.addIncome({ name: name.trim(), amount: amount.trim() });
        toast({
          message: `Income ${name.trim()} added. Total ${formatMoney(change.month.total_income)}.`,
        });
      } else {
        const body: Schemas["IncomeUpdate"] = {};
        if (name.trim() !== original.name) body.name = name.trim();
        if (amount.trim() !== original.amount) body.amount = amount.trim();
        if (Object.keys(body).length > 0) {
          const change = await actions.editIncome(edit.index, body);
          toast({
            message: `Income ${name.trim()} updated. Total ${formatMoney(change.month.total_income)}.`,
          });
        }
      }
      onClose();
    });
  }

  function remove() {
    if (!edit) return;
    onClose();
    void act(() => actions.deleteIncome(edit.index), {
      kind: "info",
      message: `Income ${edit.name} deleted`,
    });
  }

  return (
    <Sheet
      title={edit ? "Edit income" : "Add income"}
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
      <TextField
        label="name"
        value={name}
        onChange={setName}
        error={errors.fields.name}
        placeholder="Salary"
        maxLength={60}
        autoFocus
      />
      <AmountField
        label="amount"
        value={amount}
        onChange={setAmount}
        error={errors.fields.amount}
        hint={
          edit?.kind === "leftover"
            ? "Carried over when last month was closed."
            : "What comes in this month."
        }
      />
    </Sheet>
  );
}
