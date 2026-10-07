import { useState } from "react";
import { ApiError } from "../api/client";

interface FormErrors {
  /** A refusal that belongs to no single input; shown above the buttons. */
  form: string | null;
  /** Refusals by input name, shown under that input. */
  fields: Record<string, string | undefined>;
}

const NONE: FormErrors = { form: null, fields: {} };

/**
 * Runs a form's save and sorts out what comes back.
 *
 * The API names the input at fault when it can (`ErrorOut.field`). If that is
 * one of this form's `inputs`, the message goes under it; otherwise it goes
 * above the buttons. Errors never go to a toast.
 *
 * `onStale` runs when the month changed elsewhere (412). A form holds
 * positions from the month it was opened on, so the only safe move is to close
 * it — the caller has already been told why (see MonthGate).
 */
export function useSubmit(inputs: readonly string[], onStale: () => void) {
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<FormErrors>(NONE);

  async function submit(save: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setErrors(NONE);
    try {
      await save();
    } catch (problem) {
      if (!(problem instanceof ApiError)) throw problem;
      if (problem.stale) return onStale();
      // "field.section" (a nested input) → "field"
      const input = problem.field?.split(".")[0];
      setErrors(
        input && inputs.includes(input)
          ? { form: null, fields: { [input]: problem.message } }
          : { form: problem.message, fields: {} },
      );
    } finally {
      setBusy(false);
    }
  }

  return { busy, errors, submit };
}
