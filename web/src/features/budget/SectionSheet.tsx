import { useState } from "react";
import type { RestRouting, Schemas, Section, SectionKind } from "../../api/client";
import { useMonthView } from "../../app/month";
import { useToast } from "../../app/toast";
import { useAct } from "../../app/useAct";
import { useSubmit } from "../../app/useSubmit";
import { Sheet } from "../../components/Sheet";
import {
  AmountField,
  Segmented,
  SegmentedControl,
  SelectField,
  TextField,
} from "../../components/TextField";
import { isPercentage } from "../../lib/budget";
import { evaluate } from "../../lib/expression";
import { plain } from "../../lib/money";
import { SheetActions } from "../forms";
import styles from "../sheets.module.css";

interface SectionSheetProps {
  edit?: Section;
  onClose: () => void;
}

const KINDS: { value: SectionKind; label: string }[] = [
  { value: "tax", label: "Tax" },
  { value: "pre", label: "Pre" },
  { value: "post", label: "Post" },
];

const KIND_HELP: Record<SectionKind, string> = {
  tax: "Taken first: a percentage of fresh income only — leftovers from last month were already taxed.",
  pre: "Taken off the top next, in order: a fixed amount, or a percentage of the income that remains.",
  post: "Splits whatever is left. The post-sections must add up to 100%.",
};

/** A section's rest routing as a `<select>` value. */
function routingValue(routing: RestRouting): string {
  return routing.kind === "section" ? `section:${routing.target ?? ""}` : routing.kind;
}

function toRouting(value: string): RestRouting {
  if (value === "income" || value === "self") return { kind: value };
  return { kind: "section", target: value.slice("section:".length) };
}

/** Add or edit a section: its name, how it takes its share, where its rest goes. */
export function SectionSheet({ edit, onClose }: SectionSheetProps) {
  const { month, actions } = useMonthView();
  const toast = useToast();
  const act = useAct();
  const { busy, errors, submit } = useSubmit(["name", "allocation", "rest_routing"], onClose);

  const original = {
    name: edit?.name ?? "",
    type: edit?.allocation.type ?? "percent",
    // An amount is shown as typed (`500`), a percentage as it is (`50`).
    value: edit
      ? edit.allocation.type === "amount"
        ? plain(edit.allocation.value)
        : edit.allocation.value
      : "",
    routing: edit ? routingValue(edit.rest_routing) : "income",
  };
  const [name, setName] = useState(original.name);
  const [kind, setKind] = useState<SectionKind>(edit?.kind ?? "post");
  const [type, setType] = useState<"amount" | "percent">(original.type);
  const [value, setValue] = useState(original.value);
  const [routing, setRouting] = useState(original.routing);

  // Only a pre-section may take a fixed amount.
  const effectiveType = kind === "pre" ? type : "percent";
  const amount = evaluate(value);
  const valueOk =
    effectiveType === "percent" ? isPercentage(value) : amount !== null && amount >= 0n;
  const missing =
    name.trim() === ""
      ? "Give the section a name."
      : !valueOk
        ? effectiveType === "percent"
          ? "Enter a percentage between 0 and 100."
          : "Enter an amount."
        : null;
  const canSave = missing === null;

  // A pre-section chooses between a fixed amount and a percentage.
  const typeChoice = kind === "pre" && (
    <SegmentedControl
      label="Takes"
      compact
      value={type}
      options={[
        { value: "amount", label: "Amount" },
        { value: "percent", label: "Percent" },
      ]}
      onChange={setType}
    />
  );

  const others = month.sections.filter((section) => section.index !== edit?.index);
  // A target that no longer exists still has to be selectable to be shown.
  const missingTarget =
    routing.startsWith("section:") &&
    !others.some((section) => `section:${section.name}` === routing);

  function save() {
    const allocation = { type: effectiveType, value: value.trim() };
    void submit(async () => {
      if (!edit) {
        await actions.addSection({
          name: name.trim(),
          kind,
          allocation,
          rest_routing: toRouting(routing),
        });
        toast({ message: `Section ${name.trim()} added.` });
      } else {
        const body: Schemas["SectionUpdate"] = {};
        if (name.trim() !== original.name) body.name = name.trim();
        if (effectiveType !== original.type || value.trim() !== original.value) {
          body.allocation = allocation;
        }
        if (routing !== original.routing) body.rest_routing = toRouting(routing);
        if (Object.keys(body).length > 0) {
          await actions.editSection(edit.index, body);
          toast({ message: `Section ${name.trim()} updated.` });
        }
      }
      onClose();
    });
  }

  function remove() {
    if (!edit) return;
    onClose();
    void act(() => actions.deleteSection(edit.index), {
      kind: "info",
      message: `Section ${edit.name} deleted`,
    });
  }

  return (
    <Sheet
      title={edit ? "Edit section" : "Add section"}
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
        placeholder="Needs"
        maxLength={60}
        autoFocus
      />

      {edit ? (
        <p className={styles.note}>
          A <b>{edit.kind}</b>-section. {KIND_HELP[edit.kind]}
        </p>
      ) : (
        <Segmented
          label="kind"
          value={kind}
          options={KINDS}
          onChange={setKind}
          hint={KIND_HELP[kind]}
        />
      )}

      {effectiveType === "percent" ? (
        <TextField
          label="percentage"
          aside={typeChoice}
          value={value}
          onChange={setValue}
          error={
            errors.fields.allocation ??
            (value.trim() !== "" && !isPercentage(value)
              ? "Enter a percentage between 0 and 100."
              : null)
          }
          hint="% of the income this kind of section draws from."
          placeholder="50"
          inputMode="decimal"
          numeric
        />
      ) : (
        <AmountField
          label="amount"
          aside={typeChoice}
          value={value}
          onChange={setValue}
          error={errors.fields.allocation}
          hint="A fixed amount, taken every month."
        />
      )}

      <SelectField
        label="rest goes to"
        value={routing}
        onChange={setRouting}
        error={errors.fields.rest_routing}
        hint="Where this section's unused money goes when the month is closed."
      >
        <option value="income">Next month's income</option>
        <option value="self">Stays in this section</option>
        {others.map((section) => (
          <option key={section.index} value={`section:${section.name}`}>
            Section: {section.name}
          </option>
        ))}
        {missingTarget && (
          <option value={routing}>Section: {routing.slice("section:".length)} (missing)</option>
        )}
      </SelectField>
    </Sheet>
  );
}
