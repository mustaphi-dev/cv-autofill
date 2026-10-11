import { Profile, type Issue } from "@cv-autofill/schema";
import { useEffect, useState, type DragEvent } from "react";
import { LISTS, PERSONAL, type Field } from "./fields";
import { describeIssue, reason } from "./issues";

type Obj = Record<string, unknown>;
type Path = readonly PropertyKey[];

const isObj = (v: unknown): v is Obj =>
  typeof v === "object" && v !== null && !Array.isArray(v);

function getAt(root: unknown, path: Path): unknown {
  let node = root;
  for (const key of path) {
    if (Array.isArray(node) && typeof key === "number") node = node[key];
    else if (isObj(node)) node = node[String(key)];
    else return undefined;
  }
  return node;
}

// Returns a copy of root with the value at path replaced. Undefined values are
// removed later by clean().
function setAt(root: Obj, path: Path, value: unknown): Obj {
  const next = structuredClone(root);
  let node = next as Record<PropertyKey, unknown>;
  path.forEach((key, i) => {
    if (i === path.length - 1) node[key] = value;
    else node = (node[key] ??= {}) as Record<PropertyKey, unknown>;
  });
  return next;
}

// Drops blank text, blank lines, empty lists and empty objects, so optional
// fields left empty in the form are simply absent.
function clean(value: unknown): unknown {
  if (typeof value === "string") return value.trim() === "" ? undefined : value;
  if (Array.isArray(value)) {
    const items = value.map(clean).filter((v) => v !== undefined);
    return items.length > 0 ? items : undefined;
  }
  if (isObj(value)) {
    const entries = Object.entries(value).flatMap(([k, v]) => {
      const c = clean(v);
      return c === undefined ? [] : [[k, c] as const];
    });
    return entries.length > 0 ? Object.fromEntries(entries) : undefined;
  }
  return value;
}

const startsWith = (path: Path, prefix: Path) =>
  prefix.every((k, i) => path[i] === k);
const fieldId = (path: Path) => `f-${path.map(String).join("-")}`;
const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

type InputProps = {
  field: Field;
  path: Path;
  value: unknown;
  errors: Issue[];
  update: (path: Path, value: unknown) => void;
};

function FieldInput({ field, path, value, errors, update }: InputProps) {
  const id = fieldId(path);
  const errorId = `${id}-error`;
  const invalid = errors.length > 0;
  const aria = {
    "aria-invalid": invalid,
    "aria-describedby": invalid ? errorId : undefined,
  };
  const str =
    typeof value === "string" || typeof value === "number" ? String(value) : "";
  const error = invalid && (
    <p id={errorId} className="field-error">
      {errors.map(reason).join("; ")}
    </p>
  );

  if (field.kind === "date") {
    const year = getAt(value, ["year"]);
    const month = getAt(value, ["month"]);
    return (
      <fieldset className="field">
        <legend>{field.label}</legend>
        <label>
          Year{" "}
          <input
            id={id}
            type="number"
            value={typeof year === "number" ? year : ""}
            onChange={(e) => {
              update(
                path,
                e.target.value === ""
                  ? undefined
                  : {
                      ...(isObj(value) ? value : {}),
                      year: Number(e.target.value),
                    },
              );
            }}
            {...aria}
          />
        </label>{" "}
        <label>
          Month{" "}
          <select
            value={typeof month === "number" ? month : ""}
            disabled={typeof year !== "number"}
            onChange={(e) => {
              update(
                [...path, "month"],
                e.target.value === "" ? undefined : Number(e.target.value),
              );
            }}
          >
            <option value="">—</option>
            {MONTHS.map((m, i) => (
              <option key={m} value={i + 1}>
                {m}
              </option>
            ))}
          </select>
        </label>
        {error}
      </fieldset>
    );
  }

  if (field.kind === "check") {
    return (
      <div className="field">
        <label>
          <input
            id={id}
            type="checkbox"
            checked={value === true}
            onChange={(e) => {
              update(path, e.target.checked || undefined);
            }}
            {...aria}
          />{" "}
          {field.label}
        </label>
        {error}
      </div>
    );
  }

  let control;
  if (field.kind === "long" || field.kind === "lines") {
    const text =
      field.kind === "lines" && Array.isArray(value) ? value.join("\n") : str;
    control = (
      <textarea
        id={id}
        rows={field.kind === "long" ? 6 : 3}
        value={text}
        onChange={(e) => {
          update(
            path,
            field.kind === "lines"
              ? e.target.value.split("\n")
              : e.target.value,
          );
        }}
        {...aria}
      />
    );
  } else if (field.kind === "choice") {
    control = (
      <select
        id={id}
        value={str}
        onChange={(e) => {
          update(path, e.target.value === "" ? undefined : e.target.value);
        }}
        {...aria}
      >
        <option value="">—</option>
        {field.options?.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    );
  } else {
    control = (
      <input
        id={id}
        type={
          field.kind === "number"
            ? "number"
            : field.kind === "url"
              ? "url"
              : field.kind === "email"
                ? "email"
                : "text"
        }
        value={str}
        onChange={(e) => {
          const v = e.target.value;
          update(
            path,
            field.kind === "number" ? (v === "" ? undefined : Number(v)) : v,
          );
        }}
        {...aria}
      />
    );
  }
  return (
    <div className="field">
      <label htmlFor={id}>{field.label}</label>
      {control}
      {error}
    </div>
  );
}

type EditorProps = {
  saved: Profile | null;
  onSave: (next: Profile) => Promise<boolean>;
  onDirtyChange?: (dirty: boolean) => void;
};

export function Editor({ saved, onSave, onDirtyChange }: EditorProps) {
  const initial: Obj = saved ?? { schemaVersion: 1 };
  const [draft, setDraft] = useState<Obj>(initial);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [announcement, setAnnouncement] = useState("");
  const [saving, setSaving] = useState(false);
  const dirty = JSON.stringify(clean(draft)) !== JSON.stringify(clean(initial));

  // Warn before leaving the page with unsaved changes.
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => {
      window.removeEventListener("beforeunload", warn);
    };
  }, [dirty]);

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  const update = (path: Path, value: unknown) => {
    setDraft((d) => setAt(d, path, value));
  };
  const list = (key: string) => {
    const v = draft[key];
    return Array.isArray(v) ? (v as unknown[]) : [];
  };
  // Issues are located by entry index, so they go stale once entries move.
  const setList = (key: string, items: unknown[]) => {
    setDraft((d) => ({ ...d, [key]: items }));
    setIssues([]);
  };
  const move = (key: string, from: number, to: number, singular: string) => {
    const items = [...list(key)];
    const [item] = items.splice(from, 1);
    items.splice(to, 0, item);
    setList(key, items);
    setAnnouncement(`${singular} moved to position ${String(to + 1)}.`);
  };
  const errorsAt = (path: Path) =>
    issues.filter((i) => startsWith(i.path, path));

  async function save() {
    const parsed = Profile.safeParse(clean(draft) ?? {});
    if (!parsed.success) {
      setIssues(parsed.error.issues);
      const first = parsed.error.issues[0];
      if (first) {
        // Focus the first invalid field once React has rendered the errors.
        requestAnimationFrame(() => {
          for (let p = first.path.length; p > 0; p--) {
            const el = document.getElementById(fieldId(first.path.slice(0, p)));
            if (el) {
              el.focus();
              return;
            }
          }
        });
      }
      return;
    }
    setIssues([]);
    // The form is locked while saving: on success the editor restarts from
    // the saved profile, which would drop anything typed in the meantime.
    setSaving(true);
    try {
      await onSave(parsed.data);
    } finally {
      setSaving(false);
    }
  }

  const renderFields = (fields: Field[], base: Path, entry: unknown) =>
    fields
      // A current entry has no end date.
      .filter(
        (f) => !(f.path[0] === "end" && getAt(entry, ["current"]) === true),
      )
      .map((f) => {
        const path = [...base, ...f.path];
        return (
          <FieldInput
            key={path.map(String).join(".")}
            field={f}
            path={path}
            value={getAt(draft, path)}
            errors={errorsAt(path)}
            update={(p, v) => {
              update(p, v);
              if (f.path[0] === "current" && v === true)
                update([...base, "end"], undefined);
            }}
          />
        );
      });

  return (
    <section aria-labelledby="editor-heading">
      <h2 id="editor-heading">Edit your profile</h2>
      <fieldset className="form-lock" disabled={saving}>
        <details open>
          <summary>Personal details</summary>
          {renderFields(PERSONAL, ["personal"], getAt(draft, ["personal"]))}
        </details>

        <details open={typeof draft.summary === "string"}>
          <summary>Summary</summary>
          <FieldInput
            field={{
              path: ["summary"],
              label: "Professional summary",
              kind: "long",
            }}
            path={["summary"]}
            value={draft.summary}
            errors={errorsAt(["summary"])}
            update={update}
          />
        </details>

        {LISTS.map(({ key, label, singular, fields }) => {
          const entries = list(key);
          return (
            <details key={key} open={entries.length > 0}>
              <summary>
                {label} ({entries.length})
              </summary>
              <ol className="entries">
                {entries.map((entry, i) => (
                  <li
                    key={String(getAt(entry, ["id"]))}
                    onDragOver={(e) => {
                      e.preventDefault();
                    }}
                    onDrop={(e: DragEvent) => {
                      e.preventDefault();
                      // Only accept entries dragged from this same section.
                      const [fromKey, from] = e.dataTransfer
                        .getData("text/plain")
                        .split(":");
                      if (fromKey === key && Number(from) !== i)
                        move(key, Number(from), i, singular);
                    }}
                  >
                    <fieldset>
                      <legend>
                        <span
                          className="handle"
                          draggable
                          aria-hidden="true"
                          title="Drag to reorder"
                          onDragStart={(e) => {
                            e.dataTransfer.setData(
                              "text/plain",
                              `${key}:${String(i)}`,
                            );
                          }}
                        >
                          ⠿
                        </span>{" "}
                        {singular} {i + 1}
                      </legend>
                      {renderFields(fields, [key, i], entry)}
                      <div className="entry-actions">
                        <button
                          type="button"
                          disabled={i === 0}
                          onClick={() => {
                            move(key, i, i - 1, singular);
                          }}
                        >
                          Move up
                        </button>{" "}
                        <button
                          type="button"
                          disabled={i === entries.length - 1}
                          onClick={() => {
                            move(key, i, i + 1, singular);
                          }}
                        >
                          Move down
                        </button>{" "}
                        <button
                          type="button"
                          className="danger"
                          onClick={() => {
                            setList(
                              key,
                              entries.filter((_, j) => j !== i),
                            );
                            setAnnouncement(
                              `${singular} ${String(i + 1)} removed. Discard changes to undo.`,
                            );
                          }}
                        >
                          Delete {singular.toLowerCase()} {i + 1}
                        </button>
                      </div>
                    </fieldset>
                  </li>
                ))}
              </ol>
              <button
                type="button"
                onClick={() => {
                  setList(key, [...entries, { id: crypto.randomUUID() }]);
                }}
              >
                Add {singular.toLowerCase()}
              </button>
            </details>
          );
        })}

        <p role="status">{announcement}</p>
        {issues.length > 0 && (
          <div role="alert">
            <p>Not saved. Fix these first:</p>
            <ul>
              {issues.map((issue, i) => (
                <li key={i}>{describeIssue(issue)}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="save-bar">
          {dirty && <span>Unsaved changes </span>}
          <button
            type="button"
            disabled={!dirty}
            onClick={() => {
              void save();
            }}
          >
            Save changes
          </button>{" "}
          <button
            type="button"
            disabled={!dirty}
            onClick={() => {
              setDraft(initial);
              setIssues([]);
              setAnnouncement("Changes discarded.");
            }}
          >
            Discard changes
          </button>
        </div>
      </fieldset>
    </section>
  );
}
