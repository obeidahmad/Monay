import { cx } from "../lib/cx";
import { DEFAULT_ICON, SECTION_ICONS } from "../lib/sectionIcons";
import styles from "./SectionIcon.module.css";

interface SectionIconProps {
  /** Palette slot 1–8. */
  color: number;
  icon: string | null | undefined;
  kind?: "tax" | "pre" | "post";
  size?: "sm" | "md" | "lg";
  className?: string;
}

/** A section's badge: its icon on a tile of its own colour. */
export function SectionIcon({
  color,
  icon,
  kind = "post",
  size = "md",
  className,
}: SectionIconProps) {
  const entry = SECTION_ICONS[icon ?? ""] ?? SECTION_ICONS[DEFAULT_ICON[kind]];
  const Icon = entry?.Icon;
  const px = size === "lg" ? 28 : size === "sm" ? 16 : 22;
  return (
    <span
      className={cx(styles.tile, styles[size], className)}
      style={{ "--accent": `var(--section-${color})` } as React.CSSProperties}
      aria-hidden="true"
    >
      {Icon && <Icon size={px} strokeWidth={2.2} />}
    </span>
  );
}
