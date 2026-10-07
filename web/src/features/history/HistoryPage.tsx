import { Page } from "../../app/Page";
import { HistoryWidget } from "./HistoryWidget";

/** History as its own page — where a phone finds it, under More. */
export function HistoryPage() {
  return (
    <Page bare>
      <HistoryWidget />
    </Page>
  );
}
