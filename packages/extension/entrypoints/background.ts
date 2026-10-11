import { browser } from "wxt/browser";
import { defineBackground } from "wxt/utils/define-background";
import { handleMessage } from "../lib/handle-message";

export default defineBackground(() => {
  // Reply through sendResponse and return true: this works in every browser,
  // so we do not depend on Promise-returning listeners (spec section 3).
  browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    void handleMessage(message, sender).then(sendResponse);
    return true;
  });
});
