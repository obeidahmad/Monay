import { Avatar } from "../components/Avatar";
import { Menu, type MenuEntry } from "../components/Menu";
import { initial } from "../lib/text";
import { useProfile } from "./profile";
import styles from "./ProfileMenu.module.css";
import { useSheet } from "./sheets";

/** The avatar at the right of the header: switch, add or rename a profile. */
export function ProfileMenu() {
  const { profiles, profile, select } = useProfile();
  const open = useSheet();

  const items: MenuEntry[] = [
    ...profiles.map((option) => ({
      label: option.name,
      checked: option.id === profile.id,
      onSelect: () => select(option.id),
    })),
    "divider",
    { label: "Add profile", onSelect: () => open({ kind: "profile" }) },
    { label: `Rename ${profile.name}`, onSelect: () => open({ kind: "profile", edit: profile }) },
  ];

  return (
    <Menu label={`Profile: ${profile.name}`} items={items} className={styles.trigger}>
      <Avatar size="sm">{initial(profile.name)}</Avatar>
    </Menu>
  );
}
