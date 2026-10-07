import type { ReactNode } from "react";
import { Sidebar, TabBar } from "../components/NavTabs";
import styles from "./AppShell.module.css";

/**
 * The app's frame: a 72px icon sidebar and the page beside it on desktop; on a
 * phone a single column with the tab bar floating at the bottom.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <main className={styles.main}>{children}</main>
      <TabBar />
    </div>
  );
}
