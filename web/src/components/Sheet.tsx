import { X } from "lucide-react";
import { useId, type FormEvent, type ReactNode } from "react";
import { cx } from "../lib/cx";
import { IconButton } from "./Button";
import styles from "./Sheet.module.css";
import { useModal } from "./useModal";

interface SheetProps {
  title: string;
  onClose: () => void;
  /** Called on Save — the button, or Enter in any field. */
  onSubmit: () => void;
  /**
   * The actions row. By convention: Remove (edit sheets only) at the left,
   * then Cancel and the primary Save at the right.
   */
  footer: ReactNode;
  /** An error that belongs to no single field. */
  error?: string | null;
  /** Why Save is disabled — a disabled button always says what it is waiting for. */
  missing?: string | null;
  children: ReactNode;
}

/**
 * Holds every form. A centred dialog on desktop; on a phone it slides up from
 * the bottom edge, full width, with a drag handle. Enter saves, Escape closes.
 *
 * Mount it to open it and unmount it to close it — each opening starts from a
 * clean form that way.
 */
export function Sheet({ title, onClose, onSubmit, footer, error, missing, children }: SheetProps) {
  const modal = useModal(onClose);
  const titleId = useId();

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <dialog {...modal} className={cx("glass-strong", styles.sheet)} aria-labelledby={titleId}>
      <form className={styles.form} onSubmit={submit} noValidate>
        <span className={styles.handle} aria-hidden="true" />
        <header className={styles.header}>
          <h2 id={titleId} className={styles.title}>
            {title}
          </h2>
          <IconButton aria-label="Close" onClick={onClose}>
            <X size={18} />
          </IconButton>
        </header>
        <div className={styles.body}>{children}</div>
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : (
          missing && <p className={styles.missing}>{missing}</p>
        )}
        <footer className={styles.footer}>{footer}</footer>
      </form>
    </dialog>
  );
}

/** Pushes what follows it in a Sheet footer to the right-hand side. */
export function SheetSpacer() {
  return <span className={styles.spacer} />;
}
