import { Lock } from "lucide-react";
import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import styles from "./StatusChip.module.css";

type Kind = "open" | "closed" | "ok" | "warn" | "plain";

interface StatusChipProps {
  kind: Kind;
  children: ReactNode;
  className?: string;
}

/**
 * A small pill for state. The fill never changes; only the glyph and word take
 * a colour — and state is always a glyph *plus* a word, never colour alone.
 */
export function StatusChip({ kind, children, className }: StatusChipProps) {
  return (
    <span className={cx(styles.chip, styles[kind], className)}>
      {kind !== "plain" && (
        <span className={styles.glyph} aria-hidden="true">
          {GLYPH[kind]}
        </span>
      )}
      {children}
    </span>
  );
}

const GLYPH: Record<Exclude<Kind, "plain">, ReactNode> = {
  open: "●",
  closed: <Lock size={12} strokeWidth={2.5} />,
  ok: "✓",
  warn: "⚠",
};
