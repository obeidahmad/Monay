import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, Navigate } from "react-router";
import { RouterProvider } from "react-router/dom";
import { ApiError } from "./api/client";
import { Root } from "./app/Root";
import { ThemeProvider } from "./app/ThemeProvider";
import { ToastProvider } from "./app/ToastProvider";
import { BudgetPage } from "./features/budget/BudgetPage";
import { SectionPage } from "./features/budget/SectionPage";
import { AnalyticsPage } from "./features/analytics/AnalyticsPage";
import { PocketsPage } from "./features/pockets/PocketsPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { TransactionsPage } from "./features/transactions/TransactionsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // A refusal (4xx) won't change by asking again; a dropped connection might.
      retry: (failures, error) =>
        failures < 2 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
    },
  },
});

/** One URL per tab; `?month=yyyy-mm` looks at another month (see MonthGate). */
const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      { index: true, element: <Navigate to="/budget" replace /> },
      { path: "budget", element: <BudgetPage /> },
      { path: "budget/:index", element: <SectionPage /> },
      { path: "analytics", element: <AnalyticsPage /> },
      { path: "transactions", element: <TransactionsPage /> },
      { path: "pockets", element: <PocketsPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <Navigate to="/budget" replace /> },
    ],
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
