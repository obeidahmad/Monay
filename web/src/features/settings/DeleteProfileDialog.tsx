import { useState } from "react";
import { ApiError, type Profile } from "../../api/client";
import { useMonths, useProfileActions } from "../../api/queries";
import { useToast } from "../../app/toast";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { count } from "../../lib/text";

interface DeleteProfileDialogProps {
  profile: Profile;
  onClose: () => void;
}

/** Deleting a profile takes every month with it, so this one asks first. */
export function DeleteProfileDialog({ profile, onClose }: DeleteProfileDialogProps) {
  const profiles = useProfileActions();
  const months = useMonths(profile.id);
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setBusy(true);
    try {
      await profiles.remove(profile.id);
      toast({ kind: "info", message: `Profile ${profile.name} deleted.` });
      onClose();
    } catch (problem) {
      if (!(problem instanceof ApiError)) throw problem;
      setError(problem.message);
      setBusy(false);
    }
  }

  return (
    <ConfirmDialog
      title={`Delete profile ${profile.name}?`}
      rows={
        months.data
          ? [{ label: "Budget", value: count(months.data.length, "month", "months") }]
          : []
      }
      consequence="This deletes the profile and every month in it. It can't be undone."
      confirmLabel="Delete profile"
      onConfirm={() => void confirm()}
      onCancel={onClose}
      busy={busy}
      error={error}
    />
  );
}
