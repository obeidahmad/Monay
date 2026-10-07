import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "../lib/cx";
import styles from "./Button.module.css";

type Variant = "secondary" | "primary" | "danger" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * `primary` is the one filled action of a view; everything else is a glass
   * pill. `danger` is a glass pill with error-coloured text — it never gets a
   * red fill. `ghost` is a bare text button (Undo in a toast).
   */
  variant?: Variant;
  size?: "md" | "sm";
  icon?: ReactNode;
  /** Fill the width of the container. */
  block?: boolean;
}

export function Button({
  variant = "secondary",
  size = "md",
  icon,
  block = false,
  type = "button",
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        styles.button,
        styles[variant],
        size === "sm" && styles.sm,
        block && styles.block,
        className,
      )}
      {...rest}
    >
      {icon}
      {children}
    </button>
  );
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** What the button does — it has no visible text, so this is its name. */
  "aria-label": string;
}

/** A round glass button holding just an icon or glyph. */
export function IconButton({ type = "button", className, children, ...rest }: IconButtonProps) {
  return (
    <button type={type} className={cx(styles.button, styles.icon, className)} {...rest}>
      {children}
    </button>
  );
}
