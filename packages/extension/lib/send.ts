import { Reply, type Request } from "@cv-autofill/schema";
import { browser } from "wxt/browser";

// Sends a request to the background and validates the reply (spec section 5).
export async function send(request: Request): Promise<Reply> {
  return Reply.parse(await browser.runtime.sendMessage(request));
}
