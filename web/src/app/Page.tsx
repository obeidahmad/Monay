import { Plus } from "lucide-react";
import type { ReactNode } from "react";
import { MonthHeader } from "../components/MonthHeader";
import { HistoryWidget } from "../features/history/HistoryWidget";
import { useMonthView } from "./month";
import styles from "./Page.module.css";
import { ProfileMenu } from "./ProfileMenu";

interface PageProps {
  /** Header buttons: secondary ones, then the single primary at the right. */
  actions?: ReactNode;
  /**
   * The page's primary action, for phones: there it is a floating round button
   * above the tab bar instead of a header button.
   */
  primary?: { label: string; onClick: () => void };
  /** Hide the History column (the History page itself). */
  bare?: boolean;
  children: ReactNode;
}

/**
 * The frame of every tab: the month header, then two columns — the working
 * content wide on the left, a narrow History widget on the right. One column
 * on smaller screens.
 */
export function Page({ actions, primary, bare = false, children }: PageProps) {
  const { month, readOnly, view } = useMonthView();
  return (
    <div className={styles.page}>
      <MonthHeader
        month={month.label}
        state={month.state}
        actions={readOnly ? undefined : actions}
        profile={<ProfileMenu />}
        onBackToOpen={() => view(null)}
      />
      <div className={bare ? styles.single : styles.columns}>
        <div className={styles.content}>{children}</div>
        {!bare && (
          <aside className={styles.aside}>
            <HistoryWidget />
          </aside>
        )}
      </div>
      {primary && !readOnly && (
        <button
          type="button"
          className={styles.fab}
          aria-label={primary.label}
          onClick={primary.onClick}
        >
          <Plus size={28} strokeWidth={2.25} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
