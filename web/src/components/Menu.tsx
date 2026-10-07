import { Ellipsis } from "lucide-react";
import { useId, useRef, type KeyboardEvent, type ReactNode, type ToggleEvent } from "react";
import { cx } from "../lib/cx";
import styles from "./Menu.module.css";

export interface MenuAction {
  label: string;
  onSelect: () => void;
  icon?: ReactNode;
  /** Error-coloured text: removes something. */
  danger?: boolean;
  disabled?: boolean;
  /** Marks the current choice in a list of alternatives (the open profile). */
  checked?: boolean;
}

export type MenuEntry = MenuAction | "divider";

interface MenuProps {
  /** Accessible name of the trigger, e.g. "Actions for Groceries". */
  label: string;
  items: MenuEntry[];
  /** The trigger's content; defaults to the `⋯` icon. */
  children?: ReactNode;
  /** Classes for the trigger button (it is unstyled by default). */
  className?: string;
  /** Which edge of the trigger the menu lines up with. */
  align?: "start" | "end";
}

/**
 * A button that opens a menu of actions.
 *
 * Built on the Popover API: the menu renders in the browser's top layer, so it
 * is never clipped or painted over by the glass panels around its trigger
 * (each of which is its own stacking context), and it comes with light-dismiss
 * and Escape handling. All this component adds is placement and arrow keys.
 */
export function Menu({ label, items, children, className, align = "end" }: MenuProps) {
  const id = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const actions = () =>
    Array.from(
      menuRef.current?.querySelectorAll<HTMLButtonElement>("[role^='menuitem']:not(:disabled)") ??
        [],
    );

  function onToggle(event: ToggleEvent<HTMLDivElement>) {
    const menu = menuRef.current;
    const trigger = triggerRef.current;
    if (!menu || !trigger) return;
    if (event.newState !== "open") {
      delete menu.dataset.placed;
      return;
    }
    // Below the trigger, or above it when there is no room; kept on screen.
    const anchor = trigger.getBoundingClientRect();
    const { offsetWidth: width, offsetHeight: height } = menu;
    const gap = 6;
    const edge = 8;
    const below = anchor.bottom + gap;
    const top =
      below + height > window.innerHeight - edge
        ? Math.max(edge, anchor.top - gap - height)
        : below;
    const wanted = align === "end" ? anchor.right - width : anchor.left;
    const left = Math.min(Math.max(edge, wanted), window.innerWidth - width - edge);
    menu.style.top = `${top}px`;
    menu.style.left = `${left}px`;
    menu.dataset.placed = ""; // revealed only once it is where it belongs
    actions()[0]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const list = actions();
    const current = list.indexOf(document.activeElement as HTMLButtonElement);
    const move = (to: number) => {
      event.preventDefault();
      list[(to + list.length) % list.length]?.focus();
    };
    if (event.key === "ArrowDown") move(current + 1);
    else if (event.key === "ArrowUp") move(current - 1);
    else if (event.key === "Home") move(0);
    else if (event.key === "End") move(list.length - 1);
    else if (event.key === "Tab") menuRef.current?.hidePopover();
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={cx(styles.trigger, className)}
        popoverTarget={id}
        aria-haspopup="menu"
        aria-label={label}
      >
        {children ?? <Ellipsis size={18} aria-hidden="true" />}
      </button>
      <div
        ref={menuRef}
        id={id}
        popover="auto"
        role="menu"
        aria-label={label}
        className={cx("glass-strong", styles.menu)}
        onToggle={onToggle}
        onKeyDown={onKeyDown}
      >
        {items.map((item, index) =>
          item === "divider" ? (
            <hr key={index} className={styles.divider} />
          ) : (
            <button
              key={index}
              type="button"
              role={item.checked === undefined ? "menuitem" : "menuitemradio"}
              aria-checked={item.checked}
              disabled={item.disabled}
              className={cx(styles.item, item.danger && styles.danger)}
              onClick={() => {
                menuRef.current?.hidePopover();
                item.onSelect();
              }}
            >
              {item.icon && <span className={styles.icon}>{item.icon}</span>}
              <span className={styles.text}>{item.label}</span>
              {item.checked && (
                <span className={styles.check} aria-hidden="true">
                  ✓
                </span>
              )}
            </button>
          ),
        )}
      </div>
    </>
  );
}
