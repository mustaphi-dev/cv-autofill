import { beforeEach, expect, test, vi } from "vitest";
import { browser } from "wxt/browser";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { handleMessage } from "../lib/handle-message";

const page = { url: `${browser.runtime.getURL("/")}options.html` };
const ask = (message: unknown, sender = page) => handleMessage(message, sender);
const profile = {
  schemaVersion: 1,
  work: [{ id: crypto.randomUUID(), company: "Acme" }],
};

beforeEach(() => {
  fakeBrowser.reset();
});

test("refuses messages from job sites and unknown senders", async () => {
  const reply = { ok: false, error: "forbidden" };
  expect(
    await ask({ type: "profile.get" }, { url: "https://jobs.example/apply" }),
  ).toEqual(reply);
  expect(await handleMessage({ type: "profile.get" }, {})).toEqual(reply);
});

test("rejects malformed requests", async () => {
  const reply = { ok: false, error: "invalid_request" };
  expect(await ask("profile.get")).toEqual(reply);
  expect(await ask({ type: "profile.steal" })).toEqual(reply);
  expect(
    await ask({ type: "profile.save", profile: { schemaVersion: 9 } }),
  ).toEqual(reply);
});

test("returns null before a profile exists", async () => {
  expect(await ask({ type: "profile.get" })).toEqual({ ok: true, data: null });
});

test("saves and returns the profile", async () => {
  expect(await ask({ type: "profile.save", profile })).toEqual({
    ok: true,
    data: null,
  });
  const reply = await ask({ type: "profile.get" });
  expect(reply.ok && reply.data).toMatchObject(profile);
});

test("reports a corrupted stored profile instead of returning it", async () => {
  await browser.storage.local.set({
    profile: { schemaVersion: 1, work: "broken" },
  });
  expect(await ask({ type: "profile.get" })).toEqual({
    ok: false,
    error: "stored_profile_invalid",
  });
});

test("delete-all clears local and session storage", async () => {
  await ask({ type: "profile.save", profile });
  await browser.storage.local.set({ settings: { telemetry: true } });
  await browser.storage.session.set({ session: { step: 2 } });

  expect(await ask({ type: "data.deleteAll" })).toEqual({
    ok: true,
    data: null,
  });
  expect(await browser.storage.local.get()).toEqual({});
  expect(await browser.storage.session.get()).toEqual({});
});

test("error replies never contain the submitted values", async () => {
  const secret = "SECRET-VALUE-1234";
  const bad = {
    schemaVersion: 1,
    work: [{ id: "not-a-uuid", company: secret }],
  };
  const reply = await ask({ type: "profile.save", profile: bad });
  expect(reply.ok).toBe(false);
  expect(JSON.stringify(reply)).not.toContain(secret);
});

test("reports storage failures and logs them", async () => {
  vi.spyOn(browser.storage.local, "set").mockRejectedValueOnce(
    new Error("QUOTA_BYTES"),
  );
  const log = vi.spyOn(console, "error").mockImplementation(() => undefined);
  expect(await ask({ type: "profile.save", profile })).toEqual({
    ok: false,
    error: "storage_failed",
  });
  expect(log).toHaveBeenCalledOnce();
});
