/**
 * Server state: what is read (queries) and how it is changed (actions).
 *
 * The rule the whole app leans on: **a change returns the month it produced**,
 * and that goes straight into the cache. Nothing is patched up optimistically
 * on the client — every figure on screen was computed by the engine.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import {
  api,
  ApiError,
  unwrap,
  type Change,
  type Month,
  type Profile,
  type Schemas,
} from "./client";

export const keys = {
  health: ["health"] as const,
  profiles: ["profiles"] as const,
  months: (profileId: number) => ["months", profileId] as const,
  month: (profileId: number, key: string) => ["month", profileId, key] as const,
  closePreview: (profileId: number, key: string, revision: string) =>
    ["close-preview", profileId, key, revision] as const,
};

// ---------------------------------------------------------------------------
// Reading
// ---------------------------------------------------------------------------
export function useHealth() {
  return useQuery({
    queryKey: keys.health,
    queryFn: () => unwrap(api.GET("/api/health")),
    staleTime: Infinity,
  });
}

export function useProfiles() {
  return useQuery({
    queryKey: keys.profiles,
    queryFn: () => unwrap(api.GET("/api/profiles")),
  });
}

/** Every month of a profile, newest first — the History list. */
export function useMonths(profileId: number) {
  return useQuery({
    queryKey: keys.months(profileId),
    queryFn: () =>
      unwrap(
        api.GET("/api/profiles/{profile_id}/months", {
          params: { path: { profile_id: profileId } },
        }),
      ),
  });
}

export function useMonth(profileId: number, key: string) {
  return useQuery({
    queryKey: keys.month(profileId, key),
    queryFn: () =>
      unwrap(
        api.GET("/api/profiles/{profile_id}/months/{key}", {
          params: { path: { profile_id: profileId, key } },
        }),
      ),
  });
}

/** What closing would carry forward. Keyed by revision: any change re-asks. */
export function useClosePreview(profileId: number, key: string, revision: string) {
  return useQuery({
    queryKey: keys.closePreview(profileId, key, revision),
    queryFn: () =>
      unwrap(
        api.GET("/api/profiles/{profile_id}/months/{key}/close-preview", {
          params: { path: { profile_id: profileId, key } },
        }),
      ),
    retry: false,
    gcTime: 0,
  });
}

// ---------------------------------------------------------------------------
// Changing a month
// ---------------------------------------------------------------------------
/** The month a change targets, pinned to the revision it was last read at. */
interface Target {
  path: { profile_id: number; key: string };
  header: { "if-match": string };
}
type Call = (target: Target) => Promise<Change>;
type Run = (call: Call) => Promise<Change>;

const at = <Extra extends object>(target: Target, extra: Extra) => ({
  path: { ...target.path, ...extra },
  header: target.header,
});

/** One typed function per use case; `run` supplies the target and the cache. */
function monthActions(run: Run) {
  return {
    addIncome: (body: Schemas["IncomeCreate"]) =>
      run((t) =>
        unwrap(api.POST("/api/profiles/{profile_id}/months/{key}/incomes", { params: t, body })),
      ),
    editIncome: (index: number, body: Schemas["IncomeUpdate"]) =>
      run((t) =>
        unwrap(
          api.PATCH("/api/profiles/{profile_id}/months/{key}/incomes/{index}", {
            params: at(t, { index }),
            body,
          }),
        ),
      ),
    deleteIncome: (index: number) =>
      run((t) =>
        unwrap(
          api.DELETE("/api/profiles/{profile_id}/months/{key}/incomes/{index}", {
            params: at(t, { index }),
          }),
        ),
      ),

    addSection: (body: Schemas["SectionCreate"]) =>
      run((t) =>
        unwrap(api.POST("/api/profiles/{profile_id}/months/{key}/sections", { params: t, body })),
      ),
    editSection: (section: number, body: Schemas["SectionUpdate"]) =>
      run((t) =>
        unwrap(
          api.PATCH("/api/profiles/{profile_id}/months/{key}/sections/{section}", {
            params: at(t, { section }),
            body,
          }),
        ),
      ),
    deleteSection: (section: number) =>
      run((t) =>
        unwrap(
          api.DELETE("/api/profiles/{profile_id}/months/{key}/sections/{section}", {
            params: at(t, { section }),
          }),
        ),
      ),

    addField: (section: number, body: Schemas["FieldCreate"]) =>
      run((t) =>
        unwrap(
          api.POST("/api/profiles/{profile_id}/months/{key}/sections/{section}/fields", {
            params: at(t, { section }),
            body,
          }),
        ),
      ),
    editField: (section: number, field: number, body: Schemas["FieldUpdate"]) =>
      run((t) =>
        unwrap(
          api.PATCH("/api/profiles/{profile_id}/months/{key}/sections/{section}/fields/{field}", {
            params: at(t, { section, field }),
            body,
          }),
        ),
      ),
    deleteField: (section: number, field: number) =>
      run((t) =>
        unwrap(
          api.DELETE("/api/profiles/{profile_id}/months/{key}/sections/{section}/fields/{field}", {
            params: at(t, { section, field }),
          }),
        ),
      ),

    addTransaction: (body: Schemas["TransactionCreate"]) =>
      run((t) =>
        unwrap(
          api.POST("/api/profiles/{profile_id}/months/{key}/transactions", { params: t, body }),
        ),
      ),
    editTransaction: (number: number, body: Schemas["TransactionUpdate"]) =>
      run((t) =>
        unwrap(
          api.PATCH("/api/profiles/{profile_id}/months/{key}/transactions/{number}", {
            params: at(t, { number }),
            body,
          }),
        ),
      ),
    deleteTransaction: (number: number) =>
      run((t) =>
        unwrap(
          api.DELETE("/api/profiles/{profile_id}/months/{key}/transactions/{number}", {
            params: at(t, { number }),
          }),
        ),
      ),

    addTransfer: (body: Schemas["TransferCreate"]) =>
      run((t) =>
        unwrap(api.POST("/api/profiles/{profile_id}/months/{key}/transfers", { params: t, body })),
      ),
    deleteTransfer: (number: number) =>
      run((t) =>
        unwrap(
          api.DELETE("/api/profiles/{profile_id}/months/{key}/transfers/{number}", {
            params: at(t, { number }),
          }),
        ),
      ),

    addPocket: (body: Schemas["PocketCreate"]) =>
      run((t) =>
        unwrap(api.POST("/api/profiles/{profile_id}/months/{key}/pockets", { params: t, body })),
      ),
    editPocket: (index: number, body: Schemas["PocketUpdate"]) =>
      run((t) =>
        unwrap(
          api.PATCH("/api/profiles/{profile_id}/months/{key}/pockets/{index}", {
            params: at(t, { index }),
            body,
          }),
        ),
      ),
    deletePocket: (index: number) =>
      run((t) =>
        unwrap(
          api.DELETE("/api/profiles/{profile_id}/months/{key}/pockets/{index}", {
            params: at(t, { index }),
          }),
        ),
      ),

    /** Take back the change an `undo_token` came from. */
    undo: (token: string) =>
      run((t) =>
        unwrap(
          api.POST("/api/profiles/{profile_id}/months/{key}/undo", {
            params: { path: t.path },
            body: { token },
          }),
        ),
      ),
  };
}

export type MonthActions = ReturnType<typeof monthActions>;

const notLoaded = () =>
  new ApiError(0, "not_loaded", "This month is still loading. Try again in a moment.");

/**
 * Changes to one month.
 *
 * Positions in a month (`index`, `#`) only mean something for the revision
 * they were read at, so each request sends that revision in `If-Match` and the
 * server refuses a stale one (412). Two things keep that honest here:
 * changes run **one at a time** (`scope`), and each reads the revision from
 * the cache *when it runs* — so a quick second edit builds on the first one's
 * result instead of racing it.
 */
export function useMonthActions(profileId: number, key: string): MonthActions {
  const queryClient = useQueryClient();
  const { mutateAsync } = useMutation({
    scope: { id: `month:${profileId}` },
    mutationFn: async (call: Call) => {
      const cached = queryClient.getQueryData<Month>(keys.month(profileId, key));
      if (!cached) throw notLoaded();
      const change = await call({
        path: { profile_id: profileId, key },
        header: { "if-match": cached.revision },
      });
      queryClient.setQueryData(keys.month(profileId, key), change.month);
      return change;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.months(profileId) });
    },
    onError: (error) => {
      // Someone else changed the month: fetch what it looks like now.
      if (error instanceof ApiError && error.stale) {
        void queryClient.invalidateQueries({ queryKey: keys.month(profileId, key) });
      }
    },
  });
  return useMemo(() => monthActions(mutateAsync), [mutateAsync]);
}

/** Close the month; resolves to the next one, now open. */
export function useCloseMonth(profileId: number, key: string) {
  const queryClient = useQueryClient();
  return useMutation({
    scope: { id: `month:${profileId}` },
    mutationFn: async () => {
      const cached = queryClient.getQueryData<Month>(keys.month(profileId, key));
      if (!cached) throw notLoaded();
      return unwrap(
        api.POST("/api/profiles/{profile_id}/months/{key}/close", {
          params: {
            path: { profile_id: profileId, key },
            header: { "if-match": cached.revision },
          },
        }),
      );
    },
    onSuccess: (next) => {
      queryClient.setQueryData(keys.month(profileId, next.key), next);
      // The profile's open month just moved; say so now rather than after a
      // refetch, so the app never shows the closed month as the current one.
      queryClient.setQueryData<Profile[]>(keys.profiles, (profiles) =>
        profiles?.map((p) => (p.id === profileId ? { ...p, open_month: next.key } : p)),
      );
      void queryClient.invalidateQueries({ queryKey: keys.month(profileId, key) });
      void queryClient.invalidateQueries({ queryKey: keys.months(profileId) });
    },
  });
}

// ---------------------------------------------------------------------------
// Profiles
// ---------------------------------------------------------------------------
export function useProfileActions() {
  const queryClient = useQueryClient();
  return useMemo(
    () => ({
      async create(body: Schemas["ProfileCreate"]): Promise<Profile> {
        const created = await unwrap(api.POST("/api/profiles", { body }));
        queryClient.setQueryData<Profile[]>(keys.profiles, (profiles) => [
          ...(profiles ?? []),
          created,
        ]);
        return created;
      },

      async rename(profileId: number, name: string): Promise<Profile> {
        const renamed = await unwrap(
          api.PATCH("/api/profiles/{profile_id}", {
            params: { path: { profile_id: profileId } },
            body: { name },
          }),
        );
        queryClient.setQueryData<Profile[]>(keys.profiles, (profiles) =>
          profiles?.map((p) => (p.id === profileId ? renamed : p)),
        );
        return renamed;
      },

      async remove(profileId: number): Promise<void> {
        await unwrap(
          api.DELETE("/api/profiles/{profile_id}", {
            params: { path: { profile_id: profileId } },
          }),
        );
        queryClient.setQueryData<Profile[]>(keys.profiles, (profiles) =>
          profiles?.filter((p) => p.id !== profileId),
        );
        queryClient.removeQueries({ queryKey: keys.months(profileId) });
        queryClient.removeQueries({ queryKey: ["month", profileId] });
      },
    }),
    [queryClient],
  );
}
