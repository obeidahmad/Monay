import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import styles from "./Avatar.module.css";

interface AvatarProps {
  /** A single letter (a section's or profile's initial) or a glyph (`⇄`). */
  children: ReactNode;
  /** A section accent to fill with; without one the avatar is neutral. */
  accent?: string;
  size?: "md" | "sm";
  className?: string;
}

/** A round badge: a letter on a section's accent, or a neutral glyph. */
export function Avatar({ children, accent, size = "md", className }: AvatarProps) {
  return (
    <span
      className={cx(styles.avatar, size === "sm" && styles.sm, accent && styles.filled, className)}
      style={accent ? { background: accent } : undefined}
      aria-hidden="true"
    >
      {children}
    </span>
  );
}
