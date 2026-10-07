import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Toast } from "../components/Toast";
import { ToastContext, type ToastMessage } from "./toast";

const SHOWN_MS = 5_000;
const SHOWN_WITH_UNDO_MS = 8_000;

interface Showing extends ToastMessage {
  id: number;
}

/** Shows one toast at a time: five seconds, eight when it offers Undo. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [showing, setShowing] = useState<Showing | null>(null);
  const nextId = useRef(0);

  const show = useCallback((toast: ToastMessage) => {
    nextId.current += 1;
    setShowing({ ...toast, id: nextId.current });
  }, []);

  const dismiss = useCallback(() => setShowing(null), []);

  useEffect(() => {
    if (!showing) return;
    const timer = window.setTimeout(dismiss, showing.undo ? SHOWN_WITH_UNDO_MS : SHOWN_MS);
    return () => window.clearTimeout(timer);
  }, [showing, dismiss]);

  return (
    <ToastContext value={show}>
      {children}
      {showing && (
        <Toast
          key={showing.id}
          kind={showing.kind ?? "ok"}
          message={showing.message}
          onDismiss={dismiss}
          onUndo={
            showing.undo &&
            (() => {
              dismiss();
              showing.undo?.();
            })
          }
        />
      )}
    </ToastContext>
  );
}
