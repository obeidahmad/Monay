import {
  ArrowLeftRight,
  ChartNoAxesCombined,
  ChevronDown,
  LayoutGrid,
  Settings,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router";
import { useMonths } from "../api/queries";
import { Mark } from "../components/Logo";
import { Menu, type MenuEntry } from "../components/Menu";
import { cx } from "../lib/cx";
import styles from "./AppShell.module.css";
import { useMonthView } from "./month";
import { ProfileMenu } from "./ProfileMenu";

const TABS: { to: string; label: string; Icon: LucideIcon }[] = [
  { to: "/budget", label: "Budget", Icon: LayoutGrid },
  { to: "/transactions", label: "Transactions", Icon: ArrowLeftRight },
  { to: "/pockets", label: "Pockets", Icon: Wallet },
  { to: "/analytics", label: "Analytics", Icon: ChartNoAxesCombined },
];

function Tabs({ className }: { className?: string }) {
  // Keep the query string: the month being viewed (?month=) survives a tab change.
  const { search } = useLocation();
  return (
    <nav className={cx("glass-strong", styles.tabs, className)} aria-label="Main">
      {TABS.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={{ pathname: to, search }}
          className={({ isActive }) => cx(styles.tab, isActive && styles.active)}
        >
          <Icon size={20} strokeWidth={2.2} aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

/**
 * Which month is on screen, and the way to another one. Past months are a
 * place you visit now and then — so they live behind this one button instead
 * of taking a column of the page.
 */
export function MonthSwitcher() {
  const { profileId, month, openKey, view } = useMonthView();
  const months = useMonths(profileId);
  const items: MenuEntry[] = (months.data ?? []).map((summary) => ({
    label: `${summary.label}${summary.key === openKey ? " · open" : ""}`,
    checked: summary.key === month.key,
    onSelect: () => view(summary.key),
  }));
  return (
    <Menu label="Choose a month" items={items} className={styles.month}>
      <i className={cx(styles.dot, month.state === "closed" && styles.closed)} />
      <span>{month.label}</span>
      <ChevronDown size={16} aria-hidden="true" />
    </Menu>
  );
}

/**
 * The app's frame. Desktop: a rail down the left edge — the logo at its top,
 * the navigation centred vertically, settings and the profile at its foot.
 * Phone: a top bar, and the navigation as a floating pill centred at the bottom.
 */
export function AppShell({ children, bare = false }: { children: ReactNode; bare?: boolean }) {
  const { search } = useLocation();
  return (
    <div className={styles.shell}>
      <aside className={styles.rail}>
        <Link to={{ pathname: "/budget", search }} className={styles.brand} aria-label="Monay">
          <Mark size={44} />
        </Link>
        <Tabs className={styles.railTabs} />
        <div className={styles.foot}>
          {!bare && (
            <NavLink
              to={{ pathname: "/settings", search }}
              className={({ isActive }) => cx(styles.round, isActive && styles.roundActive)}
              aria-label="Settings"
            >
              <Settings size={20} />
            </NavLink>
          )}
          {!bare && <ProfileMenu />}
        </div>
      </aside>

      <div className={styles.body}>
        <header className={styles.top}>
          <Link to={{ pathname: "/budget", search }} className={styles.topBrand} aria-label="Monay">
            <Mark size={36} />
          </Link>
          <span className={styles.grow} />
          {!bare && <MonthSwitcher />}
          {!bare && (
            <span className={styles.topProfile}>
              <ProfileMenu />
            </span>
          )}
        </header>
        <main className={styles.main}>{children}</main>
      </div>

      <Tabs className={styles.bottom} />
    </div>
  );
}
