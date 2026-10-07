import { useHealth, useMonths } from "../../api/queries";
import { useMonthView } from "../../app/month";
import { Page } from "../../app/Page";
import { useProfile } from "../../app/profile";
import { useSheet } from "../../app/sheets";
import { useTheme, type Appearance } from "../../app/theme";
import { Avatar } from "../../components/Avatar";
import { Button } from "../../components/Button";
import { Logo } from "../../components/Logo";
import { Menu } from "../../components/Menu";
import { StatusChip } from "../../components/StatusChip";
import { SegmentedControl } from "../../components/TextField";
import { Widget } from "../../components/Widget";
import { formatMoney } from "../../lib/money";
import { initial } from "../../lib/text";
import styles from "./SettingsPage.module.css";

const APPEARANCES: { value: Appearance; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

/** The Settings tab: profiles, appearance, and what you are running. */
export function SettingsPage() {
  const { profiles, profile, select } = useProfile();
  const { appearance, setAppearance } = useTheme();
  const open = useSheet();
  const health = useHealth();
  const { profileId, month, view } = useMonthView();
  const months = useMonths(profileId);
  const addProfile = () => open({ kind: "profile" });

  return (
    <Page
      title="Settings"
      primary={{ label: "Add profile", onClick: addProfile }}
      actions={
        <Button variant="primary" onClick={addProfile}>
          Add profile
        </Button>
      }
    >
      <Widget title="Profiles">
        <ul className={styles.profiles}>
          {profiles.map((option) => {
            const current = option.id === profile.id;
            return (
              <li key={option.id} className={styles.profile}>
                <button
                  type="button"
                  className={styles.profileMain}
                  aria-current={current ? "true" : undefined}
                  onClick={() => select(option.id)}
                >
                  <Avatar>{initial(option.name)}</Avatar>
                  <span className={styles.profileText}>
                    <span className={styles.profileName}>{option.name}</span>
                    <span className="caption">
                      {option.open_month ? `open month ${option.open_month}` : "no months"}
                    </span>
                  </span>
                  {current && <StatusChip kind="ok">current</StatusChip>}
                </button>
                <Menu
                  label={`Actions for profile ${option.name}`}
                  items={[
                    { label: "Switch to", disabled: current, onSelect: () => select(option.id) },
                    { label: "Rename", onSelect: () => open({ kind: "profile", edit: option }) },
                    "divider",
                    {
                      label: "Delete",
                      danger: true,
                      onSelect: () => open({ kind: "delete-profile", profile: option }),
                    },
                  ]}
                />
              </li>
            );
          })}
        </ul>
      </Widget>

      <Widget title="Appearance">
        <div className={styles.appearance}>
          <SegmentedControl
            label="Appearance"
            value={appearance}
            options={APPEARANCES}
            onChange={setAppearance}
          />
          <p className="caption">System follows your device's light or dark setting.</p>
        </div>
      </Widget>

      <Widget title="History">
        <ul className={styles.months}>
          {(months.data ?? []).map((summary) => (
            <li key={summary.key}>
              <button
                type="button"
                className={styles.month}
                aria-current={summary.key === month.key ? "true" : undefined}
                onClick={() => view(summary.key)}
              >
                <span className={styles.monthName}>
                  <b>{summary.label}</b>
                  <StatusChip kind={summary.state}>{summary.state}</StatusChip>
                </span>
                <span className="caption">
                  income {formatMoney(summary.income)} · spent {formatMoney(summary.spent)} ·
                  leftovers {formatMoney(summary.leftovers)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </Widget>

      <Widget title="About">
        <div className={styles.about}>
          <Logo size={36} />
          <p className="caption">
            {health.data ? `Version ${health.data.version}` : "Zero-based budgeting"} ·{" "}
            <a href="/api/docs" target="_blank" rel="noreferrer">
              API reference
            </a>
          </p>
        </div>
      </Widget>
    </Page>
  );
}
