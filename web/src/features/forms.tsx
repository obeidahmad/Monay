/** Pieces the app's Sheets have in common. */

import { Trash2 } from "lucide-react";
import type { Month } from "../api/client";
import { Button } from "../components/Button";
import { SheetSpacer } from "../components/Sheet";

interface SheetActionsProps {
  /** Present on edit Sheets only: Remove sits at the bottom-left, away from Save. */
  onRemove?: () => void;
  onCancel: () => void;
  /** Save stays disabled until the form is valid. */
  canSave: boolean;
  busy: boolean;
  saveLabel?: string;
}

/** A Sheet's footer: [Remove] … [Cancel] [Save]. */
export function SheetActions({
  onRemove,
  onCancel,
  canSave,
  busy,
  saveLabel = "Save",
}: SheetActionsProps) {
  return (
    <>
      {onRemove && (
        <Button variant="danger" icon={<Trash2 size={16} />} onClick={onRemove} disabled={busy}>
          Remove
        </Button>
      )}
      <SheetSpacer />
      <Button onClick={onCancel}>Cancel</Button>
      <Button type="submit" variant="primary" disabled={!canSave || busy}>
        {saveLabel}
      </Button>
    </>
  );
}

/** Every field of the month as `<option>`s, grouped by section. */
export function FieldOptions({ month }: { month: Month }) {
  return (
    <>
      {month.sections
        .filter((section) => section.fields.length > 0)
        .map((section) => (
          <optgroup key={section.index} label={section.name}>
            {section.fields.map((field) => (
              <option key={field.index} value={`${section.index}:${field.index}`}>
                {field.name}
              </option>
            ))}
          </optgroup>
        ))}
    </>
  );
}
