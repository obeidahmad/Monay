import { createContext, useContext } from "react";
import type { Profile } from "../api/client";

/** Which profile this browser had open last (a convenience, not app state). */
export const PROFILE_KEY = "monay.profile";

export interface ProfileState {
  profiles: Profile[];
  /** The profile on screen. */
  profile: Profile;
  select: (profileId: number) => void;
}

export const ProfileContext = createContext<ProfileState | null>(null);

export function useProfile(): ProfileState {
  const state = useContext(ProfileContext);
  if (!state) throw new Error("useProfile must be used inside the app shell");
  return state;
}
