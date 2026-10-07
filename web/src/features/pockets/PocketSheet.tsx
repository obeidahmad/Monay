import { useState } from "react";
import type { Pocket } from "../../api/client";
import { useMonthView } from "../../app/month";
import { useToast } from "../../app/toast";
import { useAct } from "../../app/useAct";
import { useSubmit } from "../../app/useSubmit";
import { Button } from "../../components/Button";
import { Sheet } from "../../components/Sheet";
import { TextField } from "../../components/TextField";
import { SheetActions } from "../forms";
import styles from "../sheets.module.css";

interface PocketSheetProps {
  edit?: Pocket;
  onClose: () => void;
}

/** Add a pocket, or rename one, make it the default, or delete it if unused. */
export function PocketSheet({ edit, onClose }: PocketSheetProps) {
  const { actions } = useMonthView();
  const toast = useToast();
  const act = useAct();
  const { busy, errors, submit } = useSubmit(["name"], onClose);
  const [name, setName] = useState(edit?.name ?? "");

  const canSave = name.trim() !== "";

  function save() {
    void submit(async () => {
      if (!edit) {
        await actions.addPocket({ name: name.trim() });
        toast({ message: `Pocket ${name.trim()} added.` });
      } else if (name.trim() !== edit.name) {
        await actions.editPocket(edit.index, { name: name.trim() });
        toast({ message: `Pocket renamed to ${name.trim()}.` });
      }
      onClose();
    });
  }

  function makeDefault() {
    if (!edit) return;
    onClose();
    void act(() => actions.editPocket(edit.index, { is_default: true }), {
      message: `${edit.name} is now the default pocket.`,
    });
  }

  function remove() {
    if (!edit) return;
    onClose();
    void act(() => actions.deletePocket(edit.index), {
      kind: "info",
      message: `Pocket ${edit.name} deleted`,
    });
  }

  return (
    <Sheet
      title={edit ? "Edit pocket" : "Add pocket"}
      onClose={onClose}
      onSubmit={save}
      error={errors.form}
      missing={canSave ? null : "Give the pocket a name."}
      footer={
        <SheetActions
          // The default pocket holds the RESTs; it can be replaced, not removed.
          onRemove={edit && !edit.is_default ? remove : undefined}
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
        placeholder="Bank"
        maxLength={60}
        hint={edit ? undefined : "A place money physically sits: an account, a wallet, a broker."}
        autoFocus
      />
      {edit &&
        (edit.is_default ? (
          <p className={styles.note}>
            This is the default pocket: it also holds every section's rest and any income not yet
            given to a section. To delete it, make another pocket the default first.
          </p>
        ) : (
          <div className={styles.group}>
            <Button onClick={makeDefault} disabled={busy}>
              Make default
            </Button>
            <p className={styles.note}>
              The default pocket holds every section's rest and any unassigned income.
            </p>
          </div>
        ))}
    </Sheet>
  );
}
