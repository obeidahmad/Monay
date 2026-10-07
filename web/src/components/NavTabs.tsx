import { ChartPie, Ellipsis, ReceiptText, Settings, Wallet, type LucideIcon } from "lucide-react";
import { Link, NavLink, useLocation, useNavigate } from "react-router";
import { cx } from "../lib/cx";
import { Monogram } from "./Logo";
import { Menu } from "./Menu";
import styles from "./NavTabs.module.css";

interface Tab {
  to: string;
  label: string;
  Icon: LucideIcon;
}

const BUDGET: Tab = { to: "/budget", label: "Budget", Icon: ChartPie };
const TRANSACTIONS: Tab = { to: "/transactions", label: "Transactions", Icon: ReceiptText };
const POCKETS: Tab = { to: "/pockets", label: "Pockets", Icon: Wallet };
const SETTINGS: Tab = { to: "/settings", label: "Settings", Icon: Settings };

/** Outlined 24px-grid icons, 2px strokes; the selected tab's icon is filled. */
function TabIcon({ Icon, active }: { Icon: LucideIcon; active: boolean }) {
  return (
    <Icon
      size={22}
      strokeWidth={2}
      fill={active ? "currentColor" : "none"}
      fillOpacity={active ? 0.25 : 0}
      aria-hidden="true"
    />
  );
}

function TabLink({ tab }: { tab: Tab }) {
  // Keep the query string: the month being viewed (?month=) survives a tab change.
  const { search } = useLocation();
  return (
    <NavLink
      to={{ pathname: tab.to, search }}
      className={({ isActive }) => cx(styles.item, isActive && styles.selected)}
    >
      {({ isActive }) => (
        <>
          <TabIcon Icon={tab.Icon} active={isActive} />
          {tab.label}
        </>
      )}
    </NavLink>
  );
}

/** Desktop: a 72px sidebar of icon-over-label items, on the bare ground. */
export function Sidebar() {
  const { search } = useLocation();
  return (
    <nav className={styles.sidebar} aria-label="Main">
      <Link to={{ pathname: "/budget", search }} className={styles.brand} aria-label="Monay">
        <Monogram size={40} />
      </Link>
      {[BUDGET, TRANSACTIONS, POCKETS, SETTINGS].map((tab) => (
        <TabLink key={tab.to} tab={tab} />
      ))}
    </nav>
  );
}

/** Phones: a floating glass bar of four items; More holds Settings and History. */
export function TabBar() {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const inMore = pathname === "/settings" || pathname === "/history";
  return (
    <nav className={cx("glass-strong", styles.tabbar)} aria-label="Main">
      {[BUDGET, TRANSACTIONS, POCKETS].map((tab) => (
        <TabLink key={tab.to} tab={tab} />
      ))}
      <Menu
        label="More"
        className={cx(styles.item, inMore && styles.selected)}
        items={[
          { label: "Settings", onSelect: () => navigate({ pathname: "/settings", search }) },
          { label: "History", onSelect: () => navigate({ pathname: "/history", search }) },
        ]}
      >
        <TabIcon Icon={Ellipsis} active={inMore} />
        More
      </Menu>
    </nav>
  );
}
