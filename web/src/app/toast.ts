import { createContext, useContext } from "react";
import type { ToastKind } from "../components/Toast";

export interface ToastMessage {
  message: string;
  /** `ok` (done) by default; `warn` for a heads-up; `info` for a note. */
  kind?: ToastKind;
  /** Adds an Undo button and keeps the toast up a little longer. */
  undo?: () => void;
}

/** Show a toast. A new one replaces whatever is showing. */
export type ShowToast = (toast: ToastMessage) => void;

export const ToastContext = createContext<ShowToast | null>(null);

export function useToast(): ShowToast {
  const show = useContext(ToastContext);
  if (!show) throw new Error("useToast must be used inside <ToastProvider>");
  return show;
}
