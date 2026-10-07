import { useState, type FormEvent } from "react";
import { useProfileActions } from "../../api/queries";
import { PROFILE_KEY } from "../../app/profile";
import { useSubmit } from "../../app/useSubmit";
import { Button } from "../../components/Button";
import { Logo } from "../../components/Logo";
import { TextField } from "../../components/TextField";
import { Widget } from "../../components/Widget";
import { currentKey } from "../../lib/dates";
import { writeStored } from "../../lib/storage";
import styles from "./Welcome.module.css";

/**
 * What the app shows before any profile exists: one question, one button.
 * Creating the profile also creates its first month and a default pocket, so
 * the Budget tab is ready the moment this is done.
 */
export function Welcome() {
  const profiles = useProfileActions();
  const { busy, errors, submit } = useSubmit(["name", "first_month"], () => {});
  const [name, setName] = useState("");
  const [firstMonth, setFirstMonth] = useState(currentKey);

  const canSave = name.trim() !== "" && /^\d{4}-\d{2}$/.test(firstMonth);

  function create(event: FormEvent) {
    event.preventDefault();
    if (!canSave) return;
    void submit(async () => {
      const created = await profiles.create({ name: name.trim(), first_month: firstMonth });
      writeStored(PROFILE_KEY, String(created.id));
    });
  }

  return (
    <main className={styles.welcome}>
      <Logo size={52} />
      <Widget className={styles.card}>
        <form className={styles.form} onSubmit={create} noValidate>
          <div>
            <h1 className={styles.title}>Start your budget</h1>
            <p className={styles.text}>
              Give every unit of income a job, and watch what you don't spend roll forward. A
              profile is one budget — you can add more later.
            </p>
          </div>
          <TextField
            label="profile name"
            value={name}
            onChange={setName}
            error={errors.fields.name}
            placeholder="alex"
            maxLength={60}
            autoFocus
          />
          <TextField
            label="first month"
            type="month"
            value={firstMonth}
            onChange={setFirstMonth}
            error={errors.fields.first_month}
            hint="The month your budget starts in."
          />
          {errors.form && (
            <p className={styles.error} role="alert">
              {errors.form}
            </p>
          )}
          <Button type="submit" variant="primary" block disabled={!canSave || busy}>
            Create profile
          </Button>
        </form>
      </Widget>
    </main>
  );
}
