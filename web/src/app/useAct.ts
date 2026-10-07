import { useCallback } from "react";
import { ApiError, type Change } from "../api/client";
import type { ToastKind } from "../components/Toast";
import { useMonthView } from "./month";
import { useToast } from "./toast";

interface Outcome {
  /** What the toast says once it is done. */
  message: string | ((change: Change) => string);
  kind?: ToastKind;
}

/**
 * Runs a one-step change that has no form — Delete from a `⋯` menu, Move up,
 * Make default — and answers with a toast.
 *
 * Deletions come back with an undo token, so the toast offers Undo instead of
 * the app asking "are you sure?" first. A refusal ("this field still holds
 * 332.94 — transfer it away first") is shown as a heads-up toast: there is no
 * field to put it under.
 */
export function useAct() {
  const toast = useToast();
  const { actions } = useMonthView();

  return useCallback(
    async function act(run: () => Promise<Change>, outcome: Outcome): Promise<void> {
      try {
        const change = await run();
        const token = change.undo_token;
        toast({
          kind: outcome.kind ?? "ok",
          message: typeof outcome.message === "string" ? outcome.message : outcome.message(change),
          undo: token
            ? () => void act(() => actions.undo(token), { message: "Put back." })
            : undefined,
        });
      } catch (problem) {
        if (!(problem instanceof ApiError)) throw problem;
        // A stale month has already been announced where it was detected.
        if (!problem.stale) toast({ kind: "warn", message: problem.message });
      }
    },
    [actions, toast],
  );
}
