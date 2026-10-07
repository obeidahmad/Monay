import { useState } from "react";
import type { Profile } from "../../api/client";
import { useProfileActions } from "../../api/queries";
import { useProfile } from "../../app/profile";
import { useToast } from "../../app/toast";
import { useSubmit } from "../../app/useSubmit";
import { Sheet } from "../../components/Sheet";
import { TextField } from "../../components/TextField";
import { currentKey } from "../../lib/dates";
import { SheetActions } from "../forms";

interface ProfileSheetProps {
  /** The profile to rename; absent to add one. */
  edit?: Profile;
  onClose: () => void;
}

/** Add a profile — a fully independent budget — or rename one. */
export function ProfileSheet({ edit, onClose }: ProfileSheetProps) {
  const profiles = useProfileActions();
  const { select } = useProfile();
  const toast = useToast();
  const { busy, errors, submit } = useSubmit(["name", "first_month"], onClose);

  const [name, setName] = useState(edit?.name ?? "");
  const [firstMonth, setFirstMonth] = useState(currentKey);

  const canSave = name.trim() !== "" && (edit !== undefined || /^\d{4}-\d{2}$/.test(firstMonth));

  function save() {
    void submit(async () => {
      if (!edit) {
        const created = await profiles.create({ name: name.trim(), first_month: firstMonth });
        select(created.id);
        toast({ message: `Profile ${created.name} created.` });
      } else if (name.trim() !== edit.name) {
        const renamed = await profiles.rename(edit.id, name.trim());
        toast({ message: `Profile renamed to ${renamed.name}.` });
      }
      onClose();
    });
  }

  return (
    <Sheet
      title={edit ? "Rename profile" : "Add profile"}
      onClose={onClose}
      onSubmit={save}
      error={errors.form}
      missing={canSave ? null : "Give the profile a name."}
      footer={<SheetActions onCancel={onClose} canSave={canSave} busy={busy} />}
    >
      <TextField
        label="name"
        value={name}
        onChange={setName}
        error={errors.fields.name}
        placeholder="alex"
        maxLength={60}
        hint={
          edit ? undefined : "A profile is its own budget: its own months, sections and pockets."
        }
        autoFocus
      />
      {!edit && (
        <TextField
          label="first month"
          type="month"
          value={firstMonth}
          onChange={setFirstMonth}
          error={errors.fields.first_month}
          hint="The month the budget starts in. Months follow one another from here as you close them."
        />
      )}
    </Sheet>
  );
}
