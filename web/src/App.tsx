import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, closePreview, getState, mutate } from "./api";
import { fmt } from "./format";
import {
  IconBudget, IconHelp, IconMore, IconPlus, IconPockets, IconSettings, IconTransactions,
} from "./icons";
import {
  BudgetPage, HelpPage, HistoryWidget, PocketsPage, SettingsPage, TransactionsPage, type Theme,
} from "./pages";
import { SheetHost, type Act, type DeleteRequest, type SheetSpec } from "./sheets";
import type { AppState, ClosePreview } from "./types";
import { ConfirmDialog, StatusChip, TextField, Toasts, type ToastMsg } from "./ui";

type Tab = "budget" | "transactions" | "pockets" | "settings" | "help" | "more";

const NAV: { tab: Tab; label: string; icon: () => React.JSX.Element }[] = [
  { tab: "budget", label: "Budget", icon: IconBudget },
  { tab: "transactions", label: "Transactions", icon: IconTransactions },
  { tab: "pockets", label: "Pockets", icon: IconPockets },
  { tab: "settings", label: "Settings", icon: IconSettings },
];

// Per-viewer conveniences only (tab, expanded rows, theme); never budget data.
function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(`monay.${key}`);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}
function save(key: string, value: unknown) {
  try { localStorage.setItem(`monay.${key}`, JSON.stringify(value)); } catch { /* storage unavailable */ }
}

function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(() => load<Theme>("theme", "system"));
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const apply = () => {
      const resolved = theme === "system" ? (mq.matches ? "light" : "dark") : theme;
      document.documentElement.dataset.theme = resolved;
    };
    apply();
    mq.addEventListener("change", apply);
    save("theme", theme);
    return () => mq.removeEventListener("change", apply);
  }, [theme]);
  return [theme, setTheme];
}

export default function App() {
  const [state, setState] = useState<AppState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tab, setTabRaw] = useState<Tab>(() => load<Tab>("tab", "budget"));
  const [expanded, setExpandedRaw] = useState<Set<string>>(() => new Set(load<string[]>("expanded", [])));
  const [sheet, setSheet] = useState<SheetSpec | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<DeleteRequest | null>(null);
  const [closing, setClosing] = useState<ClosePreview | null>(null);
  const [toasts, setToasts] = useState<ToastMsg[]>([]);
  const [theme, setTheme] = useTheme();
  const toastId = useRef(0);

  const setTab = (t: Tab) => { setTabRaw(t); save("tab", t); };
  const setExpanded = (s: Set<string>) => { setExpandedRaw(s); save("expanded", [...s]); };
  const toggle = (name: string) => {
    const next = new Set(expanded);
    if (next.has(name)) next.delete(name); else next.add(name);
    setExpanded(next);
  };

  const toast = useCallback((text: string, tone: ToastMsg["tone"] = "ok") => {
    const id = ++toastId.current;
    setToasts((t) => [...t.slice(-2), { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  const refresh = useCallback(() => {
    getState().then((s) => { setState(s); setLoadError(null); }).catch((e: Error) => setLoadError(e.message));
  }, []);
  useEffect(refresh, [refresh]);

  /** Run a mutation, adopt the fresh state, toast, and close any open form. */
  const act: Act = async (path, body, ok) => {
    const next = await mutate(path, body);
    setState(next);
    setSheet(null);
    setConfirmDelete(null);
    toast(typeof ok === "string" ? ok : ok(next));
  };

  /** For buttons outside a form: errors become toasts. */
  const quick = async (path: string, body: unknown, ok: string) => {
    try { await act(path, body, ok); } catch (e) { toast(e instanceof Error ? e.message : String(e), "error"); }
  };

  async function startClose() {
    try { setClosing(await closePreview()); } catch (e) { toast(e instanceof ApiError ? e.message : String(e), "error"); }
  }

  if (!state) {
    return (
      <div style={{ padding: 48 }}>
        {loadError ? <div className="form-error">{loadError} <button className="btn small" onClick={refresh}>Retry</button></div>
          : <span className="muted">Loading Monay…</span>}
      </div>
    );
  }

  if (!state.profile) {
    return (
      <>
        <Welcome act={act} />
        <Toasts toasts={toasts} />
      </>
    );
  }

  const month = state.month;
  const viewing = state.viewing;
  const readOnly = !!viewing?.closed;
  const hasFields = !!month?.sections.some((s) => s.fields.length > 0);
  const viewMonth = (key: string, isOpen: boolean) =>
    quick("/api/month/view", { key: isOpen ? null : key }, isOpen ? "Back to the open month" : `Viewing ${key} (read-only)`);

  const primary: { label: string; onClick: () => void; disabled?: boolean } | null = readOnly ? null
    : tab === "pockets" ? { label: "Add pocket", onClick: () => setSheet({ kind: "pocket" }) }
    : tab === "budget" || tab === "transactions"
      ? { label: "Add transaction", onClick: () => setSheet({ kind: "tx" }), disabled: !hasFields }
      : null;

  const page = (() => {
    if (tab === "settings") {
      return <SettingsPage state={state} open={setSheet} onDelete={setConfirmDelete} theme={theme} setTheme={setTheme}
        onSwitch={(name) => quick("/api/profiles/switch", { name }, `Switched to ${name}`)} />;
    }
    if (tab === "help") return <HelpPage />;
    if (tab === "more") {
      return (
        <div className="stack">
          <HistoryWidget history={state.history} viewingKey={viewing?.key ?? null} onView={viewMonth} />
          <SettingsPage state={state} open={setSheet} onDelete={setConfirmDelete} theme={theme} setTheme={setTheme}
            onSwitch={(name) => quick("/api/profiles/switch", { name }, `Switched to ${name}`)} />
          <HelpPage />
        </div>
      );
    }
    if (!month) return <div className="muted">No month.</div>;
    const props = { state, month, readOnly, open: setSheet, onDelete: setConfirmDelete };
    if (tab === "transactions") return <TransactionsPage {...props} />;
    if (tab === "pockets") return <PocketsPage {...props} />;
    return <BudgetPage {...props} expanded={expanded} toggle={toggle} setExpanded={setExpanded} />;
  })();

  const showHistoryColumn = tab === "budget" || tab === "transactions" || tab === "pockets";
  const pageTitle = tab === "settings" ? "Settings" : tab === "help" ? "How Monay works" : tab === "more" ? "More" : viewing?.label ?? "Monay";

  return (
    <div className="shell">
      <nav className="sidebar glass" aria-label="Main">
        <div className="brand" aria-hidden="true">M</div>
        {NAV.map(({ tab: t, label, icon: Icon }) => (
          <button key={t} className="nav-item" aria-current={tab === t ? "page" : undefined} onClick={() => setTab(t)}>
            <Icon />{label}
          </button>
        ))}
        <div className="nav-spacer" />
        <button className="nav-item" aria-current={tab === "help" ? "page" : undefined} onClick={() => setTab("help")}>
          <IconHelp />Help
        </button>
      </nav>

      <main className="main">
        <div className="topbar">
          <span className="title-widget">{viewing?.label}</span>
          <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {viewing && <StatusChip closed={viewing.closed} />}
            <button className="avatar" style={{ background: "var(--income-accent)", border: 0, cursor: "pointer" }}
              aria-label={`Profile ${state.profile.name}`} onClick={() => setTab("more")}>
              {state.profile.name.slice(0, 1).toUpperCase()}
            </button>
          </span>
        </div>

        <header className="page-head">
          <div className="left">
            <h1 className="title-page">{pageTitle}</h1>
            {showHistoryColumn && viewing && <StatusChip closed={viewing.closed} />}
            <span className="caption">Profile: <b className="strong">{state.profile.name}</b></span>
          </div>
          <div className="right">
            {showHistoryColumn && !readOnly && month && (
              <button className="btn hide-mobile" onClick={startClose}>Close month</button>
            )}
            {primary && (
              <button className="btn primary hide-mobile" onClick={primary.onClick} disabled={primary.disabled}
                title={primary.disabled ? "Add a section and a field first" : undefined}>
                <IconPlus size={18} />{primary.label}
              </button>
            )}
          </div>
        </header>

        {readOnly && viewing && (
          <div className="banner glass">
            <span>🔒&#xFE0E; <b className="strong">{viewing.label}</b> is closed. You're viewing it read-only.</span>
            <button className="btn small" onClick={() => viewMonth("", true)}>Back to open month</button>
          </div>
        )}

        {month && month.warnings.length > 0 && showHistoryColumn && !readOnly && (
          <div className="caption warn" style={{ marginBottom: 12 }}>⚠ {month.warnings.join(" · ")}</div>
        )}

        {showHistoryColumn ? (
          <div className="columns">
            {page}
            <aside className="stack hide-mobile">
              <HistoryWidget history={state.history} viewingKey={viewing?.key ?? null} onView={viewMonth} />
              {!readOnly && month && (
                <button className="btn" onClick={startClose} style={{ alignSelf: "flex-start" }}>Close {viewing?.label}</button>
              )}
            </aside>
          </div>
        ) : page}
      </main>

      {/* mobile chrome */}
      {primary && !primary.disabled && (
        <button className="fab" aria-label={primary.label} onClick={primary.onClick}><IconPlus size={26} /></button>
      )}
      <nav className="tabbar glass-strong" aria-label="Main">
        {NAV.slice(0, 3).map(({ tab: t, label, icon: Icon }) => (
          <button key={t} className="nav-item" aria-current={tab === t ? "page" : undefined} onClick={() => setTab(t)}>
            <Icon />{label}
          </button>
        ))}
        <button className="nav-item" aria-current={["more", "settings", "help"].includes(tab) ? "page" : undefined}
          onClick={() => setTab("more")}>
          <IconMore />More
        </button>
      </nav>

      {sheet && (
        <SheetHost spec={sheet} month={month} viewing={viewing} act={act} onClose={() => setSheet(null)}
          onDelete={(r) => setConfirmDelete(r)} />
      )}

      {confirmDelete && (
        <DeleteDialog req={confirmDelete} act={act} onClose={() => setConfirmDelete(null)} />
      )}

      {closing && (
        <ConfirmDialog title={`Close ${closing.label}?`} confirmLabel="Close month" onClose={() => setClosing(null)}
          onConfirm={async () => {
            try {
              await act("/api/month/close", {}, (s) => `Closed. Now in ${s.viewing?.label}.`);
            } catch (e) {
              toast(e instanceof Error ? e.message : String(e), "error");
            }
            setClosing(null);
          }}>
          <div className="warn">⚠ Closing locks {closing.label} forever.</div>
          <div>
            Leftovers <b className="strong">{fmt(closing.leftovers)}</b> go to {closing.next_label}'s income.
          </div>
          {closing.carries.length > 0 && (
            <div className="caption">
              {closing.carries.map((c) => `${c.section} rest ${fmt(c.rest)} carries`).join(" · ")}
            </div>
          )}
          <div className="caption">Every field's left becomes its current in {closing.next_label}; the structure is copied forward.</div>
        </ConfirmDialog>
      )}

      <Toasts toasts={toasts} />
    </div>
  );
}

function DeleteDialog({ req, act, onClose }: { req: DeleteRequest; act: Act; onClose: () => void }) {
  const [error, setError] = useState<string | null>(null);
  return (
    <ConfirmDialog title={req.title} confirmLabel="Delete" danger onClose={onClose}
      onConfirm={async () => {
        try { await act(req.path, req.payload, req.ok); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
      }}>
      <div>{req.body}</div>
      {error && <div className="form-error" role="alert">{error}</div>}
    </ConfirmDialog>
  );
}

function Welcome({ act }: { act: Act }) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 16 }}>
      <form className="widget glass-strong" style={{ maxWidth: 440, width: "100%" }}
        onSubmit={async (e) => {
          e.preventDefault();
          if (!name.trim()) return;
          try { await act("/api/profiles", { name }, `Welcome, ${name.trim()}`); } catch (err) { setError((err as Error).message); }
        }}>
        <div className="brand" aria-hidden="true">M</div>
        <h1 className="title-page" style={{ marginBottom: 8 }}>Welcome to Monay</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          Zero-based budgeting: give every unit of income a job, and let what you don't spend roll forward. Start by naming your profile.
        </p>
        <div className="form">
          <TextField label="Profile name" value={name} onChange={setName} autoFocus placeholder="alex" error={error} />
          <button type="submit" className="btn primary" disabled={!name.trim()}>Create profile</button>
        </div>
      </form>
    </div>
  );
}
