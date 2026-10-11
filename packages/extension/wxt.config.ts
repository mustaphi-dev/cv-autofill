import { defineConfig } from "wxt";

// See docs/adr/0001-build-tool.md.
export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifestVersion: 3,
  imports: false,
  outDir: "build",
  manifest: {
    name: "CV Autofill",
    minimum_chrome_version: "148",
    // The background stores the profile (spec section 5). No install warning.
    permissions: ["storage"],
  },
});
