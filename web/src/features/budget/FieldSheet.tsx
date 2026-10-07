import { useState } from "react";
import type { Field, Schemas, Section } from "../../api/client";
import { useMonthView } from "../../app/month";
import { useToast } from "../../app/toast";
import { useAct } from "../../app/useAct";
import { useSubmit } from "../../app/useSubmit";
import { Sheet } from "../../components/Sheet";
import {
  AmountField,
  Labelled,
  SegmentedControl,
  SelectField,
  TextField,
} from "../../components/TextField";
import { findField, isPercentage } from "../../lib/budget";
import { evaluate } from "../../lib/expression";
import { formatMoney, plain } from "../../lib/money";
import { SheetActions } from "../forms";

interface FieldSheetProps {
  /** The section the field belongs to. */
  section: Section;
  edit?: Field;
  onClose: () => void;
}

/**
 * Add or edit a field — a budget line: what it is fed each month (budget), how
 * far its pot may grow (max), and where that money physically sits (pocket).
 */
export function FieldSheet({ section, edit, onClose }: FieldSheetProps) {
  const { month, actions } = useMonthView();
  const toast = useToast();
  const act = useAct();
  const { busy, errors, submit } = useSubmit(
    ["name", "budget", "max", "pocket", "current"],
    onClose,
  );

  const defaultPocket = month.pockets.find((pocket) => pocket.is_default) ?? month.pockets[0];
  const original = {
    name: edit?.name ?? "",
    type: edit?.budget_pct != null ? ("percent" as const) : ("amount" as const),
    budget: edit ? (edit.budget_pct ?? plain(edit.budget)) : "",
    max: edit?.max != null ? plain(edit.max) : null, // null = no limit
    pocket: String(edit?.pocket_index ?? defaultPocket?.index ?? 0),
    current: edit ? plain(edit.current) : "",
  };
  const [name, setName] = useState(original.name);
  const [type, setType] = useState<"amount" | "percent">(original.type);
  const [budget, setBudget] = useState(original.budget);
  const [limited, setLimited] = useState(original.max !== null);
  const [max, setMax] = useState(original.max ?? "");
  const [pocket, setPocket] = useState(original.pocket);
  const [current, setCurrent] = useState(original.current);

  const nonNegative = (text: string) => {
    const value = evaluate(text);
    return value !== null && value >= 0n;
  };
  // An empty budget is a budget of zero.
  const budgetOk =
    budget.trim() === "" || (type === "percent" ? isPercentage(budget) : nonNegative(budget));
  const maxOk = !limited || nonNegative(max);
  const currentOk = current.trim() === "" || evaluate(current) !== null;
  const missing =
    name.trim() === ""
      ? "Give the field a name."
      : !budgetOk
        ? type === "percent"
          ? "Enter a budget percentage between 0 and 100."
          : "Enter a budget of zero or more."
        : !maxOk
          ? "Enter the max, or choose No limit."
          : !currentOk
            ? "Enter the current amount, or leave it empty."
            : null;
  const canSave = missing === null;

  const budgetChoice = (
    <SegmentedControl
      label="Budget as"
      compact
      value={type}
      options={[
        { value: "amount", label: "Amount" },
        { value: "percent", label: "Percent" },
      ]}
      onChange={setType}
    />
  );
  const maxChoice = (
    <SegmentedControl
      label="Max"
      compact
      value={limited ? "limit" : "none"}
      options={[
        { value: "none", label: "No limit" },
        { value: "limit", label: "Limit" },
      ]}
      onChange={(choice) => setLimited(choice === "limit")}
    />
  );

  const budgetBody = (): Schemas["AmountOrPercent"] => ({ type, value: budget.trim() || "0" });
  const nextMax = limited ? max.trim() : null;

  function save() {
    void submit(async () => {
      if (!edit) {
        await actions.addField(section.index, {
          name: name.trim(),
          budget: budgetBody(),
          max: nextMax,
          pocket: Number(pocket),
          // CURRENT is only ever typed in a profile's first month.
          ...(month.is_first && current.trim() !== "" ? { current: current.trim() } : {}),
        });
        toast({ message: `Field ${name.trim()} added to ${section.name}.` });
      } else {
        const body: Schemas["FieldUpdate"] = {};
        if (name.trim() !== original.name) body.name = name.trim();
        if (type !== original.type || budget.trim() !== original.budget) body.budget = budgetBody();
        // `max: null` means "no limit", so it is only sent when it changed.
        if (nextMax !== original.max) body.max = nextMax;
        if (pocket !== original.pocket) body.pocket = Number(pocket);
        if (month.is_first && current.trim() !== original.current) {
          body.current = current.trim() || "0";
        }
        if (Object.keys(body).length > 0) {
          const change = await actions.editField(section.index, edit.index, body);
          const saved = findField(change.month, section.index, edit.index);
          const left = saved ? ` ${formatMoney(saved.field.left)} left.` : "";
          toast({ message: `Field ${name.trim()} updated.${left}` });
        }
      }
      onClose();
    });
  }

  function remove() {
    if (!edit) return;
    onClose();
    void act(() => actions.deleteField(section.index, edit.index), {
      kind: "info",
      message: `Field ${edit.name} deleted`,
    });
  }

  return (
    <Sheet
      title={edit ? "Edit field" : `Add field to ${section.name}`}
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
        placeholder="Groceries"
        maxLength={60}
        autoFocus
      />

      {type === "percent" ? (
        <TextField
          label="budget %"
          aside={budgetChoice}
          value={budget}
          onChange={setBudget}
          error={
            errors.fields.budget ?? (budgetOk ? null : "Enter a percentage between 0 and 100.")
          }
          hint={`% of what ${section.name} has left after its fixed budgets.`}
          placeholder="20"
          inputMode="decimal"
          numeric
        />
      ) : (
        <AmountField
          label="budget"
          aside={budgetChoice}
          value={budget}
          onChange={setBudget}
          error={errors.fields.budget}
          hint="What this field is fed each month."
        />
      )}

      {limited ? (
        <AmountField
          label="max"
          aside={maxChoice}
          value={max}
          onChange={setMax}
          error={errors.fields.max}
          hint="The pot never grows past this; budget it can't hold stays in the section."
        />
      ) : (
        <Labelled
          label="max"
          aside={maxChoice}
          hint="∞ — the pot can grow without limit as unspent budget rolls over."
        />
      )}

      <SelectField
        label="pocket"
        value={pocket}
        onChange={setPocket}
        error={errors.fields.pocket}
        hint="Where this money physically sits."
      >
        {month.pockets.map((option) => (
          <option key={option.index} value={option.index}>
            {option.name}
            {option.is_default ? " (default)" : ""}
          </option>
        ))}
      </SelectField>

      {month.is_first && (
        <AmountField
          label="current"
          value={current}
          onChange={setCurrent}
          error={errors.fields.current}
          hint="What this pot already holds. Only set by hand in your first month — after that it carries over."
        />
      )}
    </Sheet>
  );
}
