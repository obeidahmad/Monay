import { useCallback, useRef, useState, type ReactNode } from "react";
import { CloseMonthDialog } from "../features/budget/CloseMonthDialog";
import { FieldSheet } from "../features/budget/FieldSheet";
import { IncomeSheet } from "../features/budget/IncomeSheet";
import { SectionSheet } from "../features/budget/SectionSheet";
import { PocketSheet } from "../features/pockets/PocketSheet";
import { DeleteProfileDialog } from "../features/settings/DeleteProfileDialog";
import { ProfileSheet } from "../features/settings/ProfileSheet";
import { TransactionSheet } from "../features/transactions/TransactionSheet";
import { TransferSheet } from "../features/transactions/TransferSheet";
import { SheetContext, type SheetRequest } from "./sheets";

/**
 * Renders whichever Sheet or dialog was asked for (`useSheet()`), one at a
 * time. Each request mounts a fresh component — the `key` — so a form always
 * starts from the data it was opened with, never from a previous opening.
 */
export function SheetHost({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<{ id: number; request: SheetRequest } | null>(null);
  const opened = useRef(0);

  const open = useCallback((request: SheetRequest) => {
    opened.current += 1;
    setActive({ id: opened.current, request });
  }, []);
  const close = useCallback(() => setActive(null), []);

  return (
    <SheetContext value={open}>
      {children}
      {active && <ActiveSheet key={active.id} request={active.request} onClose={close} />}
    </SheetContext>
  );
}

function ActiveSheet({ request, onClose }: { request: SheetRequest; onClose: () => void }) {
  switch (request.kind) {
    case "transaction":
      return <TransactionSheet edit={request.edit} field={request.field} onClose={onClose} />;
    case "transfer":
      return <TransferSheet from={request.from} onClose={onClose} />;
    case "section":
      return <SectionSheet edit={request.edit} onClose={onClose} />;
    case "field":
      return <FieldSheet section={request.section} edit={request.edit} onClose={onClose} />;
    case "income":
      return <IncomeSheet edit={request.edit} onClose={onClose} />;
    case "pocket":
      return <PocketSheet edit={request.edit} onClose={onClose} />;
    case "profile":
      return <ProfileSheet edit={request.edit} onClose={onClose} />;
    case "close-month":
      return <CloseMonthDialog onClose={onClose} />;
    case "delete-profile":
      return <DeleteProfileDialog profile={request.profile} onClose={onClose} />;
  }
}
