// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { afterEach, beforeAll, beforeEach, expect, test, vi } from "vitest";
import { App } from "../entrypoints/options/App";
import { send } from "../lib/send";
import v1 from "../../schema/fixtures/profile.v1.json";

vi.mock("../lib/send", () => ({ send: vi.fn() }));
const sendMock = vi.mocked(send);
const createObjectURL = vi.fn<(blob: Blob) => string>(() => "blob:profile");

// jsdom has no <dialog> methods or object URLs.
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
  URL.createObjectURL = createObjectURL;
  URL.revokeObjectURL = vi.fn();
});

let stored: unknown = null;
beforeEach(() => {
  stored = null;
  sendMock.mockImplementation((request) => {
    if (request.type === "profile.get")
      return Promise.resolve({ ok: true, data: stored });
    if (request.type === "profile.save") stored = request.profile;
    if (request.type === "data.deleteAll") stored = null;
    return Promise.resolve({ ok: true, data: null });
  });
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const jsonFile = (content: unknown, name = "profile.json") =>
  new File(
    [typeof content === "string" ? content : JSON.stringify(content)],
    name,
    {
      type: "application/json",
    },
  );

async function setup() {
  const user = userEvent.setup();
  const view = render(<App />);
  await screen.findByText(/No profile yet|Ada Lovelace/);
  return { user, view };
}

const importFile = (user: ReturnType<typeof userEvent.setup>, file: File) =>
  user.upload(screen.getByLabelText("Import profile (JSON)"), file);

// axe cannot measure colour contrast in jsdom; that is checked by hand.
async function expectAccessible(container: HTMLElement) {
  const { violations } = await axe.run(container, {
    rules: { "color-contrast": { enabled: false } },
  });
  expect(violations.map((v) => v.id)).toEqual([]);
}

test("shows the empty state and passes an accessibility scan", async () => {
  const { view } = await setup();
  expect(
    screen.getByRole<HTMLButtonElement>("button", {
      name: "Export profile (JSON)",
    }).disabled,
  ).toBe(true);
  await expectAccessible(view.container);
});

test("imports a valid profile", async () => {
  const { user } = await setup();
  await importFile(user, jsonFile(v1));
  await screen.findByText("Profile imported.");
  expect(sendMock).toHaveBeenCalledWith(
    expect.objectContaining({ type: "profile.save" }),
  );
  screen.getByText(/Ada Lovelace · Links: 1 · Work experience: 1/);
});

test("rejects a file that is not JSON", async () => {
  const { user } = await setup();
  await importFile(user, jsonFile("{not json"));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "This file isn't valid JSON.",
  );
  expect(sendMock).not.toHaveBeenCalledWith(
    expect.objectContaining({ type: "profile.save" }),
  );
});

test("rejects a profile from a newer version", async () => {
  const { user } = await setup();
  await importFile(user, jsonFile({ schemaVersion: 2 }));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "made by a newer version",
  );
});

test("rejects an oversized file", async () => {
  const { user } = await setup();
  await importFile(user, jsonFile(" ".repeat(5 * 1024 * 1024 + 1)));
  expect((await screen.findByRole("alert")).textContent).toContain("too large");
});

test("lists invalid fields without showing their values", async () => {
  const secret = "SECRET-COMPANY-NAME";
  const bad = {
    ...v1,
    work: [{ ...v1.work[0], company: secret.repeat(20) }],
    links: [{ ...v1.links[0], url: "javascript:alert(1)" }],
  };
  const { user, view } = await setup();
  await importFile(user, jsonFile(bad));
  const alert = await screen.findByRole("alert");
  expect(alert.textContent).toContain(
    "Work experience, entry 1, company: too long (max 300)",
  );
  expect(alert.textContent).toContain("Links, entry 1, url:");
  expect(alert.textContent).not.toContain(secret);
  expect(alert.textContent).not.toContain("javascript");
  await expectAccessible(view.container);
});

test("asks before replacing an existing profile", async () => {
  stored = v1;
  const { user, view } = await setup();
  const next = { ...v1, personal: { firstName: "Grace" } };

  await importFile(user, jsonFile(next));
  expect(
    screen
      .getByRole("dialog", { name: "Replace your profile?" })
      .hasAttribute("open"),
  ).toBe(true);
  await expectAccessible(view.container);
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(stored).toBe(v1);

  await importFile(user, jsonFile(next));
  await user.click(screen.getByRole("button", { name: "Replace" }));
  await waitFor(() => {
    expect(stored).toMatchObject({ personal: { firstName: "Grace" } });
  });
});

test("exports the profile as a JSON download", async () => {
  stored = v1;
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(() => undefined);
  const { user } = await setup();
  await user.click(
    screen.getByRole("button", { name: "Export profile (JSON)" }),
  );

  const [blob] = createObjectURL.mock.lastCall ?? [];
  if (!blob) throw new Error("no download was created");
  expect(JSON.parse(await blob.text())).toMatchObject({
    personal: { firstName: "Ada" },
  });
  expect(click).toHaveBeenCalledOnce();
  screen.getByText("Profile exported.");
});

test("deletes everything only after confirmation", async () => {
  stored = v1;
  const { user } = await setup();
  await user.click(screen.getByRole("button", { name: "Delete all my data" }));
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(sendMock).not.toHaveBeenCalledWith({ type: "data.deleteAll" });

  await user.click(screen.getByRole("button", { name: "Delete all my data" }));
  await user.click(screen.getByRole("button", { name: "Delete everything" }));
  await screen.findByText("All your data was deleted.");
  expect(sendMock).toHaveBeenCalledWith({ type: "data.deleteAll" });
  screen.getByText(/No profile yet/);
});

test("reports a failed save and keeps the old profile", async () => {
  const { user } = await setup();
  sendMock.mockResolvedValueOnce({ ok: false, error: "storage_failed" });
  await importFile(user, jsonFile(v1));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Saving failed",
  );
  screen.getByText(/No profile yet/);
});

test("names profile-wide problems without printing undefined", async () => {
  const { user } = await setup();
  const dup = { ...v1, work: [v1.work[0], { ...v1.work[0] }], extra: 1 };
  await importFile(user, jsonFile(dup));
  const text = (await screen.findByRole("alert")).textContent;
  expect(text).toContain("Profile: Two entries share the same id");
  expect(text).toContain('Profile: unknown field "extra"');
  expect(text).not.toContain("undefined");
});

test("still asks before replacing when the saved profile failed to load", async () => {
  stored = v1;
  sendMock.mockResolvedValueOnce({ ok: false, error: "storage_failed" });
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("Your saved profile could not be read.");
  expect(screen.queryByText("Loading…")).toBeNull();
  screen.getByText("Your saved profile could not be loaded.");

  await importFile(user, jsonFile(v1));
  expect(
    screen
      .getByRole("dialog", { name: "Replace your profile?" })
      .hasAttribute("open"),
  ).toBe(true);
  expect(sendMock).not.toHaveBeenCalledWith(
    expect.objectContaining({ type: "profile.save" }),
  );
});

test("leaves the loading state when the load throws", async () => {
  sendMock.mockRejectedValueOnce(new Error("background gone"));
  render(<App />);
  await screen.findByText("Something went wrong. Please try again.");
  expect(screen.queryByText("Loading…")).toBeNull();
  screen.getByText("Your saved profile could not be loaded.");
});
