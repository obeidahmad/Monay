import { SectionIcon } from "../../components/SectionIcon";
import { cx } from "../../lib/cx";
import { DEFAULT_ICON, SECTION_ICONS } from "../../lib/sectionIcons";
import styles from "./AppearancePicker.module.css";

interface AppearancePickerProps {
  color: number;
  /** Icon name, or "" for the default of the section's kind. */
  icon: string;
  kind: "tax" | "pre" | "post";
  onColor: (color: number) => void;
  onIcon: (icon: string) => void;
}

const COLORS = ["Gold", "Blue", "Magenta", "Green", "Cyan", "Amber", "Azure", "Red"];

/** Pick a section's colour and icon, with a live preview of its badge. */
export function AppearancePicker({ color, icon, kind, onColor, onIcon }: AppearancePickerProps) {
  const shown = icon || DEFAULT_ICON[kind];
  return (
    <div className={styles.picker}>
      <div className={styles.preview}>
        <SectionIcon color={color} icon={shown} kind={kind} size="lg" />
        <div className={styles.colors} role="radiogroup" aria-label="Colour">
          {COLORS.map((name, i) => (
            <button
              key={name}
              type="button"
              role="radio"
              aria-checked={color === i + 1}
              aria-label={name}
              title={name}
              className={cx(styles.color, color === i + 1 && styles.chosen)}
              style={{ background: `var(--section-${i + 1})` }}
              onClick={() => onColor(i + 1)}
            />
          ))}
        </div>
      </div>
      <div className={styles.icons} role="radiogroup" aria-label="Icon">
        {Object.entries(SECTION_ICONS).map(([name, { Icon, label }]) => (
          <button
            key={name}
            type="button"
            role="radio"
            aria-checked={shown === name}
            aria-label={label}
            title={label}
            className={cx(styles.icon, shown === name && styles.chosenIcon)}
            onClick={() => onIcon(name)}
          >
            <Icon size={18} />
          </button>
        ))}
      </div>
    </div>
  );
}
