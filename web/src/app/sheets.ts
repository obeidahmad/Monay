import { createContext, useContext } from "react";
import type { Field, FieldRef, Income, Pocket, Profile, Section, Transaction } from "../api/client";

/**
 * Every form and confirmation the app can open. Absent `edit` means "add".
 * One host (SheetHost) renders them, so any screen can ask for any of them —
 * Add transaction, for one, is reachable from four places.
 */
export type SheetRequest =
  | { kind: "transaction"; edit?: Transaction; field?: FieldRef }
  | { kind: "transfer"; from?: FieldRef }
  | { kind: "section"; edit?: Section }
  | { kind: "field"; section: Section; edit?: Field }
  | { kind: "income"; edit?: Income }
  | { kind: "pocket"; edit?: Pocket }
  | { kind: "profile"; edit?: Profile }
  | { kind: "close-month" }
  | { kind: "delete-profile"; profile: Profile };

export type OpenSheet = (request: SheetRequest) => void;

export const SheetContext = createContext<OpenSheet | null>(null);

export function useSheet(): OpenSheet {
  const open = useContext(SheetContext);
  if (!open) throw new Error("useSheet must be used inside <SheetHost>");
  return open;
}
