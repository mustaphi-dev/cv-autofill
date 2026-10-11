import { Profile, Request, type Reply } from "@cv-autofill/schema";
import { browser, type Browser } from "wxt/browser";

const PROFILE_KEY = "profile";

// The background owns all storage (spec section 5). Nothing is kept in
// memory: every request reads storage, so a restarted background loses nothing.
export async function handleMessage(
  message: unknown,
  sender: Browser.runtime.MessageSender,
): Promise<Reply> {
  // The browser sets sender.url, so a web page cannot fake it.
  if (!sender.url?.startsWith(browser.runtime.getURL("/"))) {
    return { ok: false, error: "forbidden" };
  }
  const request = Request.safeParse(message);
  if (!request.success) return { ok: false, error: "invalid_request" };

  try {
    switch (request.data.type) {
      case "profile.get": {
        const stored = await browser.storage.local.get(PROFILE_KEY);
        if (stored[PROFILE_KEY] === undefined) return { ok: true, data: null };
        const profile = Profile.safeParse(stored[PROFILE_KEY]);
        return profile.success
          ? { ok: true, data: profile.data }
          : { ok: false, error: "stored_profile_invalid" };
      }
      case "profile.save":
        await browser.storage.local.set({
          [PROFILE_KEY]: request.data.profile,
        });
        return { ok: true, data: null };
      case "data.deleteAll":
        await Promise.all([
          browser.storage.local.clear(),
          browser.storage.session.clear(),
        ]);
        return { ok: true, data: null };
    }
  } catch (error) {
    console.error(`background: ${request.data.type} failed`, error);
    return { ok: false, error: "storage_failed" };
  }
}
