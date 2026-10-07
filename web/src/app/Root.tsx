import { useCallback, useMemo, useState, type ReactNode } from "react";
import { Outlet, useSearchParams } from "react-router";
import { ApiError, type Change, type Profile } from "../api/client";
import { useMonth, useMonthActions, useProfiles, type MonthActions } from "../api/queries";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { Logo } from "../components/Logo";
import { Widget } from "../components/Widget";
import { Welcome } from "../features/onboarding/Welcome";
import { readStored, writeStored } from "../lib/storage";
import { AppShell } from "./AppShell";
import { MonthContext, type MonthState } from "./month";
import { PROFILE_KEY, ProfileContext } from "./profile";
import styles from "./Root.module.css";
import { SheetHost } from "./SheetHost";
import { useToast } from "./toast";

const MONTH_KEY = /^\d{4}-(0[1-9]|1[0-2])$/;

/**
 * The app's entry: decides between "can't reach the server", "no profile yet"
 * (onboarding) and the workspace.
 */
export function Root() {
  const profiles = useProfiles();

  if (profiles.isPending) return <Splash />;
  if (profiles.isError) {
    return (
      <Splash>
        <EmptyState
          title="Can't load Monay"
          action={
            <Button variant="primary" onClick={() => void profiles.refetch()}>
              Try again
            </Button>
          }
        >
          {profiles.error.message}
        </EmptyState>
      </Splash>
    );
  }
  if (profiles.data.length === 0) return <Welcome />;
  return <Workspace profiles={profiles.data} />;
}

/** The ground with the wordmark, while there is nothing else to show. */
function Splash({ children }: { children?: ReactNode }) {
  return (
    <div className={styles.splash}>
      <Logo size={44} />
      {children && <Widget className={styles.card}>{children}</Widget>}
    </div>
  );
}

function Workspace({ profiles }: { profiles: Profile[] }) {
  const [selectedId, setSelectedId] = useState(() => Number(readStored(PROFILE_KEY)) || null);
  const [, setParams] = useSearchParams();

  // The remembered profile may be gone (deleted elsewhere): fall back to the first.
  const profile = profiles.find((p) => p.id === selectedId) ?? profiles[0];

  const select = useCallback(
    (profileId: number) => {
      writeStored(PROFILE_KEY, String(profileId));
      setSelectedId(profileId);
      // A month being viewed belongs to the profile we are leaving.
      setParams(
        (params) => {
          const next = new URLSearchParams(params);
          next.delete("month");
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const state = useMemo(
    () => (profile ? { profiles, profile, select } : null),
    [profiles, profile, select],
  );
  if (!state) return null; // unreachable: Root only renders this with profiles

  return (
    <ProfileContext value={state}>
      {/* Keyed by profile: switching profiles starts from a clean slate. */}
      <MonthGate key={state.profile.id} profile={state.profile} />
    </ProfileContext>
  );
}

/** Loads the month on screen and provides it (and its actions) to the pages. */
function MonthGate({ profile }: { profile: Profile }) {
  const toast = useToast();
  const [params, setParams] = useSearchParams();

  const openKey = profile.open_month ?? "";
  const requested = params.get("month");
  // ?month=… looks at another month; without it, the profile's open month.
  const key = requested && MONTH_KEY.test(requested) ? requested : openKey;

  const query = useMonth(profile.id, key);
  const actions = useMonthActions(profile.id, key);

  const view = useCallback(
    (next: string | null) => {
      setParams((current) => {
        const updated = new URLSearchParams(current);
        if (next === null || next === openKey) updated.delete("month");
        else updated.set("month", next);
        return updated;
      });
    },
    [openKey, setParams],
  );

  // When the month changed somewhere else, say so once, here — whoever started
  // the change (a form, a menu) then just steps back. The fresh month is
  // already being fetched (useMonthActions).
  const guarded = useMemo(
    () =>
      announcing(actions, () =>
        toast({
          kind: "warn",
          message: "This month was changed somewhere else. It's been refreshed — try again.",
        }),
      ),
    [actions, toast],
  );

  const month = query.data;
  const state = useMemo<MonthState | null>(
    () =>
      month
        ? {
            profileId: profile.id,
            month,
            readOnly: month.state === "closed",
            openKey,
            actions: guarded,
            view,
          }
        : null,
    [profile.id, month, openKey, guarded, view],
  );

  if (!state) {
    return (
      <AppShell bare>
        {query.isError && (
          <Widget>
            <EmptyState
              title={key === openKey ? "Can't load this month" : `No month ${key}`}
              action={
                key === openKey ? (
                  <Button variant="primary" onClick={() => void query.refetch()}>
                    Try again
                  </Button>
                ) : (
                  <Button variant="primary" onClick={() => view(null)}>
                    Back to open month
                  </Button>
                )
              }
            >
              {query.error.message}
            </EmptyState>
          </Widget>
        )}
      </AppShell>
    );
  }

  return (
    <MonthContext value={state}>
      <SheetHost>
        <AppShell>
          <Outlet />
        </AppShell>
      </SheetHost>
    </MonthContext>
  );
}

/** Wrap every action so a stale-month refusal (412) is announced on its way out. */
function announcing(actions: MonthActions, announce: () => void): MonthActions {
  const wrapped: Record<string, unknown> = {};
  for (const [name, action] of Object.entries(actions)) {
    const run = action as (...args: unknown[]) => Promise<Change>;
    wrapped[name] = (...args: unknown[]) =>
      run(...args).catch((problem: unknown) => {
        if (problem instanceof ApiError && problem.stale) announce();
        throw problem;
      });
  }
  return wrapped as MonthActions;
}
