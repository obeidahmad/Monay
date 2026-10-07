import { useState } from "react";
import { ApiError } from "../../api/client";
import { useCloseMonth, useClosePreview } from "../../api/queries";
import { useMonthView } from "../../app/month";
import { useToast } from "../../app/toast";
import { Amount } from "../../components/Amount";
import { ConfirmDialog, type SummaryRow } from "../../components/ConfirmDialog";

/**
 * Closing a month rolls everything forward and locks it for good, so it is one
 * of the two actions that ask first. The figures come from the server actually
 * rehearsing the close — what you read here is what will happen.
 */
export function CloseMonthDialog({ onClose }: { onClose: () => void }) {
  const { profileId, month, view } = useMonthView();
  const preview = useClosePreview(profileId, month.key, month.revision);
  const close = useCloseMonth(profileId, month.key);
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);

  const rows: SummaryRow[] = preview.data
    ? [
        { label: "Income", value: <Amount value={preview.data.income} /> },
        { label: "Spent", value: <Amount value={preview.data.spent} /> },
        {
          label: `Leftovers to ${preview.data.next_label}`,
          value: <Amount value={preview.data.leftovers} />,
        },
        ...preview.data.carries.map((carry) => ({
          label: `Carried into ${carry.section}`,
          value: <Amount value={carry.amount} />,
        })),
      ]
    : [];

  // The server refuses to rehearse a month that can't be closed, and says why.
  const blocker = preview.isError
    ? preview.error.message
    : preview.isPending
      ? "Working out what carries forward…"
      : null;

  async function confirm() {
    setError(null);
    try {
      const next = await close.mutateAsync();
      toast({ message: `${month.label} closed. Now in ${next.label}.` });
      view(null);
      onClose();
    } catch (problem) {
      if (!(problem instanceof ApiError)) throw problem;
      setError(problem.message);
    }
  }

  return (
    <ConfirmDialog
      title={`Close ${month.label}?`}
      rows={rows}
      consequence="This locks the month. It becomes read-only in History."
      confirmLabel="Close month"
      onConfirm={() => void confirm()}
      onCancel={onClose}
      busy={close.isPending}
      blocker={blocker}
      error={error}
    />
  );
}
