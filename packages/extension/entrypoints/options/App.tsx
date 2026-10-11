import { Profile } from "@cv-autofill/schema";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { send } from "../../lib/send";
import { Editor } from "./Editor";
import { SECTION_LABELS } from "./fields";
import { describeIssue } from "./issues";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

function summarise(profile: Profile): string {
  const name = [profile.personal?.firstName, profile.personal?.lastName]
    .filter(Boolean)
    .join(" ");
  const counts = Object.entries(profile).flatMap(([k, v]) =>
    Array.isArray(v) && v.length > 0
      ? [`${SECTION_LABELS[k] ?? k}: ${String(v.length)}`]
      : [],
  );
  return [name || "No name yet", ...counts].join(" · ");
}

export function App() {
  // undefined: not loaded (still loading, or the load failed).
  const [profile, setProfile] = useState<Profile | null | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [alert, setAlert] = useState<{ title: string; items: string[] } | null>(
    null,
  );
  const [pending, setPending] = useState<Profile | null>(null);
  // Bumped whenever the saved profile is replaced, so the editor starts over.
  const [version, setVersion] = useState(0);
  const [editorDirty, setEditorDirty] = useState(false);
  const replaceDialog = useRef<HTMLDialogElement>(null);
  const deleteDialog = useRef<HTMLDialogElement>(null);

  const fail = (title: string, items: string[] = []) => {
    setStatus("");
    setAlert({ title, items });
  };

  // Runs an event handler's async work and reports anything unexpected.
  const run = (task: () => Promise<void>) => {
    task().catch(() => {
      fail("Something went wrong. Please try again.");
    });
  };

  async function load() {
    try {
      const reply = await send({ type: "profile.get" });
      if (!reply.ok) {
        fail("Your saved profile could not be read.");
        return;
      }
      setProfile(Profile.nullable().parse(reply.data));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    run(load);
  }, []);

  async function save(next: Profile, done: string): Promise<boolean> {
    const reply = await send({ type: "profile.save", profile: next });
    if (!reply.ok) {
      fail("Saving failed. Your previous profile is unchanged.");
      return false;
    }
    setProfile(next);
    setVersion((v) => v + 1);
    setAlert(null);
    setStatus(done);
    return true;
  }

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setStatus("");
    if (file.size > MAX_FILE_BYTES) {
      fail("This file is too large to be a profile (max 5 MB).");
      return;
    }

    let raw: unknown;
    try {
      raw = JSON.parse(await file.text());
    } catch {
      fail("This file isn't valid JSON.");
      return;
    }
    const version = (raw as { schemaVersion?: unknown } | null)?.schemaVersion;
    if (typeof version === "number" && version > 1) {
      fail(
        "This profile was made by a newer version of CV Autofill. Update the extension, then try again.",
      );
      return;
    }
    const parsed = Profile.safeParse(raw);
    if (!parsed.success) {
      fail(
        "Nothing was imported. Fix these in the file:",
        parsed.error.issues.map(describeIssue),
      );
      return;
    }
    // Ask unless we know nothing is stored: undefined means the load is
    // pending or failed, and a stored profile may still exist. Also ask when
    // the import would throw away unsaved edits in the form.
    if (profile !== null || editorDirty) {
      setPending(parsed.data);
      replaceDialog.current?.showModal();
      return;
    }
    await save(parsed.data, "Profile imported.");
  }

  async function confirmReplace() {
    replaceDialog.current?.close();
    if (pending) await save(pending, "Profile imported.");
    setPending(null);
  }

  function exportProfile() {
    if (!profile) return;
    const blob = new Blob([JSON.stringify(profile, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "cv-autofill-profile.json";
    link.click();
    URL.revokeObjectURL(url);
    setStatus("Profile exported.");
  }

  async function confirmDelete() {
    deleteDialog.current?.close();
    const reply = await send({ type: "data.deleteAll" });
    if (!reply.ok) {
      fail("Deleting failed. Nothing was removed.");
      return;
    }
    setProfile(null);
    setVersion((v) => v + 1);
    setAlert(null);
    setStatus("All your data was deleted.");
  }

  return (
    <main>
      <h1>CV Autofill settings</h1>

      <section aria-labelledby="profile-heading">
        <h2 id="profile-heading">Your profile</h2>
        <p className="muted">
          {profile === undefined
            ? loading
              ? "Loading…"
              : "Your saved profile could not be loaded."
            : profile === null
              ? "No profile yet. Import a JSON file, or fill in the form below."
              : summarise(profile)}
        </p>
        <label>
          Import profile (JSON){" "}
          <input
            type="file"
            accept="application/json,.json"
            onChange={(e) => {
              run(() => onFile(e));
            }}
          />
        </label>{" "}
        <button type="button" onClick={exportProfile} disabled={!profile}>
          Export profile (JSON)
        </button>
      </section>

      <p role="status">{status}</p>
      {alert && (
        <div role="alert">
          <p>{alert.title}</p>
          {alert.items.length > 0 && (
            <ul>
              {alert.items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {profile !== undefined && (
        <Editor
          key={version}
          saved={profile}
          onDirtyChange={setEditorDirty}
          onSave={(next) =>
            save(next, "Changes saved.").catch(() => {
              fail("Saving failed. Your previous profile is unchanged.");
              return false;
            })
          }
        />
      )}

      <section aria-labelledby="danger-heading">
        <h2 id="danger-heading">Delete all data</h2>
        <p className="muted">
          Removes your profile and settings from this browser.
        </p>
        <button
          type="button"
          className="danger"
          onClick={() => deleteDialog.current?.showModal()}
        >
          Delete all my data
        </button>
      </section>

      <dialog ref={replaceDialog} aria-labelledby="replace-title">
        <h2 id="replace-title">Replace your profile?</h2>
        <p>
          {profile !== null &&
            "The imported file will replace your current profile. Export it first if you want a copy. "}
          {editorDirty && "Your unsaved changes in the form will be lost."}
        </p>
        <button
          type="button"
          onClick={() => {
            run(confirmReplace);
          }}
        >
          Replace
        </button>{" "}
        <button type="button" onClick={() => replaceDialog.current?.close()}>
          Cancel
        </button>
      </dialog>

      <dialog ref={deleteDialog} aria-labelledby="delete-title">
        <h2 id="delete-title">Delete all your data?</h2>
        <p>
          This removes your profile and settings from this browser. It cannot be
          undone.
        </p>
        <button
          type="button"
          className="danger"
          onClick={() => {
            run(confirmDelete);
          }}
        >
          Delete everything
        </button>{" "}
        <button type="button" onClick={() => deleteDialog.current?.close()}>
          Cancel
        </button>
      </dialog>
    </main>
  );
}
