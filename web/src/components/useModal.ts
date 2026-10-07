import { useEffect, useRef, type MouseEvent, type SyntheticEvent } from "react";

/**
 * Drives a native modal `<dialog>` that is mounted only while it is open.
 *
 * The platform does the hard parts — focus trapping, making the rest of the
 * page inert, the top layer, Escape. This adds what forms need on top:
 * focusing the element marked `data-autofocus`, routing Escape through
 * `onClose` (so the owner decides, e.g. while a save is in flight), and
 * closing on a click on the backdrop.
 */
export function useModal(onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null);
  // A press that starts inside (selecting text in an input) and ends on the
  // backdrop must not close the dialog and lose what was typed.
  const pressedBackdrop = useRef(false);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (!dialog.open) dialog.showModal();
    dialog.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    return () => {
      if (dialog.open) dialog.close();
    };
  }, []);

  return {
    ref,
    onCancel: (event: SyntheticEvent<HTMLDialogElement>) => {
      event.preventDefault(); // Escape: let the owner unmount us instead
      onClose();
    },
    onMouseDown: (event: MouseEvent<HTMLDialogElement>) => {
      pressedBackdrop.current = event.target === event.currentTarget;
    },
    onClick: (event: MouseEvent<HTMLDialogElement>) => {
      // The dialog element itself is only ever hit through its ::backdrop —
      // its content covers the rest of it.
      if (pressedBackdrop.current && event.target === event.currentTarget) onClose();
    },
  };
}
