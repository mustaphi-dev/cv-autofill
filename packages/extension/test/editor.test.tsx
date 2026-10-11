// @vitest-environment jsdom
import { Profile } from "@cv-autofill/schema";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { afterEach, expect, test, vi } from "vitest";
import { Editor } from "../entrypoints/options/Editor";
import { LISTS, PERSONAL } from "../entrypoints/options/fields";
import jsonSchema from "../../schema/profile.v1.schema.json";
import v1 from "../../schema/fixtures/profile.v1.json";

afterEach(cleanup);

const jobB = {
  id: "0b8e6c64-0d3a-4c1e-9a55-1d1f6b3a00b2",
  company: "Babbage & Co",
};
const saved = Profile.parse({ ...v1, work: [...v1.work, jobB] });

function setup(profile: Profile | null = saved) {
  const onSave = vi.fn<(next: Profile) => Promise<boolean>>(() =>
    Promise.resolve(true),
  );
  const user = userEvent.setup();
  const view = render(<Editor saved={profile} onSave={onSave} />);
  const savedProfile = () => {
    const [arg] = onSave.mock.lastCall ?? [];
    if (!arg) throw new Error("onSave was not called");
    return arg;
  };
  return { user, view, onSave, savedProfile };
}

const job = (n: number) =>
  screen.getByRole("group", { name: new RegExp(`Job ${String(n)}$`) });

// Leaf fields in the JSON Schema: dates and arrays are single form fields.
type Node = { properties?: Record<string, Node>; items?: Node };
function leaves(node: Node, prefix: string[] = []): string[] {
  const props = node.properties;
  if (!props || "year" in props) return [prefix.join(".")];
  return Object.entries(props).flatMap(([k, v]) => leaves(v, [...prefix, k]));
}

test("the field table covers every field in the schema", () => {
  const schema = jsonSchema as unknown as Node;
  const props = schema.properties ?? {};
  const paths = (fields: { path: readonly string[] }[]) =>
    fields.map((f) => f.path.join(".")).sort();

  expect(paths(PERSONAL)).toEqual(leaves(props.personal ?? {}).sort());
  for (const section of LISTS) {
    const entry = props[section.key]?.items ?? {};
    const expected = leaves(entry).filter((p) => p !== "id");
    expect([section.key, ...paths(section.fields)]).toEqual([
      section.key,
      ...expected.sort(),
    ]);
  }
  const listKeys = Object.keys(props).filter((k) => props[k]?.items);
  expect(LISTS.map((s) => s.key).sort()).toEqual(listKeys.sort());
});

test("edits a field and saves the trimmed profile", async () => {
  const { user, savedProfile } = setup();
  const company = within(job(1)).getByLabelText("Company");
  await user.clear(company);
  await user.type(company, "  Engines Ltd ");
  expect(screen.getByText(/Unsaved changes/)).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(savedProfile().work[0]?.company).toBe("Engines Ltd");
});

test("clearing an optional field removes it", async () => {
  const { user, savedProfile } = setup();
  await user.clear(within(job(1)).getByLabelText("Company"));
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(savedProfile().work[0]).not.toHaveProperty("company");
});

test("shows errors at the field, focuses it, and does not save", async () => {
  const { user, view, onSave } = setup();
  const company = within(job(1)).getByLabelText("Company");
  await user.clear(company);
  await user.click(company);
  await user.paste("x".repeat(301));
  await user.click(screen.getByRole("button", { name: "Save changes" }));

  expect(onSave).not.toHaveBeenCalled();
  expect(company.getAttribute("aria-invalid")).toBe("true");
  const errorId = company.getAttribute("aria-describedby") ?? "";
  expect(document.getElementById(errorId)?.textContent).toBe(
    "too long (max 300)",
  );
  expect(screen.getByRole("alert").textContent).toContain(
    "Work experience, entry 1, company: too long (max 300)",
  );
  await waitFor(() => {
    expect(document.activeElement).toBe(company);
  });
  const { violations } = await axe.run(view.container, {
    rules: { "color-contrast": { enabled: false } },
  });
  expect(violations.map((v) => v.id)).toEqual([]);
});

test("each bullet is one line, and blank lines are dropped", async () => {
  const { user, savedProfile } = setup();
  const bullets = within(job(2)).getByLabelText(
    "Description bullets (one per line)",
  );
  await user.type(bullets, "Built it{Enter}{Enter}Shipped it");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(savedProfile().work[1]?.bullets).toEqual(["Built it", "Shipped it"]);
});

test("adds and deletes entries", async () => {
  const { user, savedProfile } = setup();
  await user.click(screen.getByRole("button", { name: "Add job" }));
  await user.type(within(job(3)).getByLabelText("Company"), "New Co");
  await user.click(screen.getByRole("button", { name: "Delete job 1" }));
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(savedProfile().work.map((w) => w.company)).toEqual([
    "Babbage & Co",
    "New Co",
  ]);
});

test("moves entries with buttons and announces it", async () => {
  const { user, savedProfile } = setup();
  await user.click(within(job(1)).getByRole("button", { name: "Move down" }));
  expect(screen.getByRole("status").textContent).toBe(
    "Job moved to position 2.",
  );
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(savedProfile().work.map((w) => w.company)).toEqual([
    "Babbage & Co",
    "Analytical Engines Ltd",
  ]);
});

test("moves entries by drag and drop, only within a section", async () => {
  const { user, savedProfile } = setup();
  const data = new Map<string, string>();
  const dataTransfer = {
    setData: (k: string, v: string) => data.set(k, v),
    getData: (k: string) => data.get(k) ?? "",
  };
  const handle = (n: number) => job(n).querySelector(".handle") ?? job(n);

  fireEvent.dragStart(handle(2), { dataTransfer });
  fireEvent.drop(job(1).closest("li") ?? job(1), { dataTransfer });

  // A link dropped on a job is ignored.
  const link = screen.getByRole("group", { name: /Link 1$/ });
  fireEvent.dragStart(link.querySelector(".handle") ?? link, { dataTransfer });
  fireEvent.drop(job(2).closest("li") ?? job(2), { dataTransfer });

  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(savedProfile().work.map((w) => w.company)).toEqual([
    "Babbage & Co",
    "Analytical Engines Ltd",
  ]);
});

test("marking an entry current hides and clears its end date", async () => {
  const { user, savedProfile } = setup();
  const year = within(
    within(job(2)).getByRole("group", { name: "End" }),
  ).getByLabelText("Year");
  await user.type(year, "2020");
  await user.click(within(job(2)).getByLabelText("Current"));
  expect(within(job(2)).queryByRole("group", { name: "End" })).toBeNull();
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(savedProfile().work[1]).toMatchObject({ current: true });
  expect(savedProfile().work[1]).not.toHaveProperty("end");
});

test("discard restores the saved profile", async () => {
  const { user } = setup();
  await user.click(screen.getByRole("button", { name: "Delete job 1" }));
  await user.click(screen.getByRole("button", { name: "Discard changes" }));
  expect(within(job(1)).getByLabelText<HTMLInputElement>("Company").value).toBe(
    "Analytical Engines Ltd",
  );
  expect(
    screen.getByRole<HTMLButtonElement>("button", { name: "Save changes" })
      .disabled,
  ).toBe(true);
});

test("warns before leaving only when there are unsaved changes", async () => {
  const { user } = setup();
  const leave = () => {
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    return event.defaultPrevented;
  };
  expect(leave()).toBe(false);
  await user.type(within(job(1)).getByLabelText("Location"), "London");
  expect(leave()).toBe(true);
});

test("starts empty when there is no profile and builds one", async () => {
  const { user, savedProfile } = setup(null);
  await user.type(screen.getByLabelText("First name"), "Grace");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(savedProfile()).toMatchObject({
    schemaVersion: 1,
    personal: { firstName: "Grace" },
    work: [],
  });
});

test("locks the form while a save is in progress", async () => {
  const { user, onSave } = setup();
  const save = Promise.withResolvers<boolean>();
  onSave.mockReturnValue(save.promise);
  const company = within(job(1)).getByLabelText<HTMLInputElement>("Company");
  await user.type(company, "!");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(company.matches(":disabled")).toBe(true);
  save.resolve(false);
  await waitFor(() => {
    expect(company.matches(":disabled")).toBe(false);
  });
});

test("clears errors once entries are reordered", async () => {
  const { user } = setup();
  const company = within(job(1)).getByLabelText("Company");
  await user.clear(company);
  await user.click(company);
  await user.paste("x".repeat(301));
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(screen.getByRole("alert")).toBeTruthy();

  await user.click(within(job(1)).getByRole("button", { name: "Move down" }));
  expect(screen.queryByRole("alert")).toBeNull();
  expect(
    within(job(1)).getByLabelText("Company").getAttribute("aria-invalid"),
  ).toBe("false");
});
