# 0001. Extension build tool: WXT, MV3 everywhere, Chromium 148 minimum

Date: 2026-10-11. Status: accepted.

## Context

We ship one codebase to Chromium (Release 1), Firefox and Safari, all on Manifest V3 (spec section 3). We need per-browser manifests, per-browser options such as content script `world`, dev reload and packaging.

Facts checked on 2026-10-11:

- WXT 0.21.4 targets MV2 for Firefox and Safari by default and MV3 elsewhere. Its `manifestVersion` config option overrides that for every command.
- WXT's `browser` export only picks `globalThis.browser` or `globalThis.chrome`. It is not a polyfill.
- Chrome 148 added the `browser.*` namespace and Promise-returning `runtime.onMessage` listeners ([Chrome docs](https://developer.chrome.com/docs/extensions/develop/concepts/browser-namespace)). Firefox and Safari have both natively.

## Decision

- Use WXT, pinned to an exact version, with `manifestVersion: 3` in `wxt.config.ts`.
- Set `minimum_chrome_version` to 148 (spec section 3 updated). Call `browser.*` directly. No polyfill, no wrapper.
- Turn off WXT auto-imports (`imports: false`), so every import is explicit.

Alternatives considered:

- Plain Vite with a hand-written manifest. Fewer dependencies, but we would build per-browser manifests, reload and packaging ourselves.
- CRXJS. Chrome first, weaker Firefox and Safari support.
- Plasmo. Less active, heavier.
- Keep Chromium 116 with `@wxt-dev/webextension-polyfill`. Supports older Chromium, but adds a dependency and two message-handling behaviours.

## Consequences

- Users on Chromium older than 148 cannot install. Chromium browsers auto-update, so this is a small group. Reversible: lower the minimum and add the polyfill.
- WXT is pre-1.0, so expect breaking changes on upgrade. Our entry points are plain TypeScript, so leaving WXT for plain Vite is a contained change.
- Firefox and Safari builds must be checked to come out as MV3 when those releases start.
