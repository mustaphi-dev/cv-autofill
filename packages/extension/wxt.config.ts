import { defineConfig } from "wxt";

// See docs/adr/0001-build-tool.md.
export default defineConfig({
  manifestVersion: 3,
  imports: false,
  outDir: "build",
  manifest: {
    name: "CV Autofill",
    minimum_chrome_version: "148",
  },
});
