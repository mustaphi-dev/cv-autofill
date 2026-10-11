# Release 1 plan: usable on Chromium

Status: draft for review. Follows the build order in spec section 15 and the per-feature loop in spec section 17 (design note, devil's advocate, your approval, implement, demo, summary, your approval, commit). Diagrams and component details are in [architecture.md](architecture.md); security is in [threat-model.md](threat-model.md).

## Questions and concerns

Items I could not settle from the spec, found contradictory, or could not verify. Each has a recommendation so you can just say yes or no.

**Permissions and browsers**

- **Q1. Does a click inside the side panel grant `activeTab`?** Chrome's docs list the gestures that grant it as: toolbar action click, context menu item, keyboard shortcut, omnibox suggestion. Side panel buttons are not listed, so the spec's "the Fill click grants `activeTab`" may not hold. *Recommendation:* the toolbar click that opens the panel grants `activeTab` for the current page. If that access has lapsed (for example, after navigating to another site), the Fill button calls `permissions.request` for that one origin, which is allowed from a click in the panel. I will prove this with a small spike at the start of M4 before building on it.
- **Q2. Unknown iframe origins need a broad optional permission.** To request a cross-origin iframe origin at runtime, it must be covered by `optional_host_permissions` in the manifest. For the generic engine we cannot list every company's careers domain ahead of time, so we would declare `https://*/*` as *optional* and request one origin at a time. Nothing is granted at install, but a store reviewer may read this as "requests all sites". *Recommendation:* declare it as optional, explain it in the store listing, and request only the exact origin when needed. If you would rather not, the generic engine skips cross-origin iframes and marks them "Needs you".
- **Q3. Chromium browsers differ.** Third-party reports say Opera's `sidePanel` support is incomplete and Arc has limited extension API support. I could not confirm either from vendor docs. *Recommendation:* Release 1 officially supports Chrome, Edge and Brave. Opera and Arc are best effort, with a popup fallback when `sidePanel` is missing (the platform layer already needs this for Safari).
- **Q4. Greenhouse API host permission.** Fetching `boards-api.greenhouse.io` from the background needs either CORS headers on that API or a host permission for it. I will check in M7. If a permission is needed, I recommend making it optional and requesting it on the first Greenhouse fill.

**Privacy and UK GDPR** (not legal advice. I recommend a short review by someone qualified before publishing.)

- **Q5. No UK region on Render.** Render's EU region is Frankfurt. I found no UK region. UK GDPR treats EEA countries as adequate, so Frankfurt is fine. I will confirm that PostgreSQL and Key Value are also offered in Frankfurt during M3 setup.
- **Q6. The LLM provider is likely in the US.** Fireworks says zero data retention is the default for open models. Together offers it as an organisation setting you must switch on. Both appear to be US companies, which makes CV parsing a restricted transfer under UK GDPR. That needs the provider to be covered by the UK extension to the EU-US Data Privacy Framework, or a signed UK transfer agreement (IDTA or addendum). I will check each shortlisted provider's terms in M3. Because parsing sends full CVs to a third party, a short data protection impact assessment (DPIA) is probably expected. *Recommendation:* I draft the DPIA and privacy policy in M3, and you have them reviewed.
- **Q7. Telemetry can be re-linked despite ID rotation.** Events are sent with a stable per-install API key. If the backend stored the key (or the IP address) next to events, the 30-day install ID rotation would be pointless. *Recommendation:* the backend never stores key ID, IP address or request ID with events or reports. The privacy policy says so, and a test checks the stored columns. This is a promise rather than a technical guarantee. The stronger alternative is a separate, unauthenticated, rate-limited events endpoint, at the cost of abuse resistance. Which do you prefer?
- **Q8. The CV eval set needs real-looking CVs.** Real CVs are personal data. *Recommendation:* use synthetic CVs in many layouts (one column, two columns, tables, academic), plus your own CV if you agree, kept out of the repository.

**Scope that the spec leaves unclear**

- **Q9. Profile encryption at rest has no milestone.** *Recommendation:* defer it to Release 4 (hardening). Design the storage layer in M2 so it can be added without a migration of the calling code.
- **Q10. M10 says "report queue". Does that mean the offline event queue, the problem-report queue in the admin dashboard, or both?** The dashboard and stats are Release 3. *Recommendation:* M10 builds the "Report a problem" button, the `POST /v1/problem-reports` endpoint, the offline event queue, and one admin-only endpoint that lists problem reports. The dashboard waits for Release 3. Until then, LLM spend and quota hits are watched through logs and an alert.
- **Q11. Commit cadence.** Section 15 says commit at the end of each milestone. Section 17 says commit after each approved feature. *Recommendation:* commit after each approved feature (this meets both rules), and tag the end of each milestone.
- **Q12. Multi-step session in Release 1.** The Workday multi-step work is Release 2, but section 5 says the background must resume after being killed mid-fill, and the fixture list includes a multi-step wizard. Both need the session store. *Recommendation:* build the session store in M5 and test it with the wizard fixture. Workday-specific step handling stays in Release 2.
- **Q13. One source of truth for types.** The spec says backend Pydantic models are generated from shared JSON Schema, and also that extension client types are generated from or checked against the backend's OpenAPI. *Recommendation:* schemas are written once in `packages/schema` (Zod) and exported to JSON Schema, which generates the Pydantic models. The backend's OpenAPI is then checked against the Zod schemas in CI, without generating code from it.

**Facts checked**

- Chrome exposes the `browser` namespace from Chrome 148, and `webextension-polyfill` becomes a no-op there ([Chrome docs](https://developer.chrome.com/docs/extensions/develop/concepts/browser-namespace)). With a minimum of Chromium 116, the polyfill or an equivalent wrapper is still needed. This is consistent with the spec.
- The minimum versions table in spec section 3 will be checked against current MDN compat data in M1, as the spec asks.

## LLM budget proposal

Release 1 uses the LLM only for CV parsing. AI mapping is Release 3.

**Per-parse cost estimate.** About 6,000 input tokens (instructions, schema and CV text) and 3,000 output tokens (structured profile). Open-weight model prices at hosted providers in mid-2026 are roughly $0.15–$0.30 per million input tokens and $0.60–$1.20 per million output tokens. These figures are from aggregator sites. I will confirm them on each provider's own pricing page. That puts one parse at $0.003–$0.006. I round up to **$0.01 per parse** to cover retries and validation re-asks.

| Scenario | Parses per month | Estimated cost per month |
|---|---|---|
| You plus a private beta (50 users) | ~100 | ~$1 |
| 1,000 new installs a month | ~1,500 | ~$15 |
| 10,000 new installs a month | ~15,000 | ~$150 |

Parsing happens once per user, plus re-uploads, so cost grows with new installs, not with use.

**Proposed defaults**

- Global hard cap: **$3 per day** (at most about $90 per month). When it is reached, parsing pauses until midnight UTC and users are told to import JSON or enter the profile by hand. Filling is unaffected.
- Alerts at 50% and 80% of the daily cap.
- Provider-side monthly spend limit of **$100** as a second safety net.
- Per-install quota: **3 parses per day**.
- One-off model evaluation in M3: 2–3 models × ~30 CVs × a few runs, under $5.

Expected Release 1 spend: under $5 a month until there are real users. Hosting (Render web service, PostgreSQL, Key Value) is separate. I will get current Render prices in M3 rather than guess.

**Provider shortlist:** Fireworks (zero retention by default for open models) and Together (zero retention when switched on), with DeepInfra as a third candidate if its retention terms check out. The model is picked by eval in M3, as spec section 11 requires.

## How each milestone runs

Each milestone is split into the features listed. Every feature goes through the section 17 loop on its own. A milestone is done when all its acceptance criteria pass in CI (or in a recorded demo where CI cannot cover it), and you have approved it. I do not start the next milestone before that.

Cross-cutting criteria for every milestone: lint, type-check and tests pass in CI; no `any`, no swallowed errors, no bare `setTimeout` waits; every new dependency has its licence checked; ADRs are written for the choices made; README is updated.

## M1. Monorepo, tooling, CI skeleton

**Features:** pnpm workspace and `uv` backend project; TypeScript strict, ESLint, Prettier, Ruff, mypy strict; GitHub Actions running lint, type-check and unit tests; pre-commit secret scanning; conventional commits and changelog tooling; compat-data check.

**ADRs:** build tool (WXT evaluated first, MV3 forced for every target); schema library (Zod expected).

**Acceptance criteria**
- `pnpm install && pnpm -r test` and `uv run pytest` pass on a clean clone.
- CI runs lint, type-check and unit tests on every push, and fails on a deliberate lint error.
- The secret scanner blocks a commit containing a fake API key.
- An empty extension builds for Chromium as MV3 and loads unpacked in Chrome without errors.
- A note confirms or corrects the minimum versions in spec section 3 against current MDN compat data.

## M2. Shared schemas, profile model, options page

**Features:** profile schema (JSON Resume based, every section in spec section 2, `id`, `order`, `{year, month}` dates, bullet descriptions, aliases, `schemaVersion`); migrations framework; JSON Schema export and generated Pydantic models; storage layer in the background; options page with JSON import and export, manual editing, drag to reorder, and delete-all.

**Acceptance criteria**
- Every profile section in spec section 2 exists as its own typed array. A test fails if a project can be validated as a work entry.
- Importing an invalid JSON file shows a clear error and changes nothing.
- Exporting and then re-importing a profile gives an identical profile.
- A migration from a test v0 profile to v1 has a test.
- Generated Pydantic models match the Zod schemas (CI check fails on drift).
- Options page works by keyboard alone, has labelled controls and visible focus, and works in light and dark mode. Checked with an automated accessibility scan plus a manual screen reader pass.
- Delete-all removes the profile, files and settings, verified by test.

## M3. Backend skeleton and CV parsing

**Features:** FastAPI app, Docker, Compose for local Postgres and Redis; Alembic; `/healthz`, `/readyz`; `POST /v1/installs` with hashed keys, rotation, revocation and issuance abuse protection; rate limiting and quotas in Key Value with `429` + `Retry-After`; `GET /v1/status`; `POST /v1/parse` with column-aware `pdfplumber` extraction, `python-docx`, scanned-PDF detection, LLM provider interface with failover, schema-constrained output; consent notice and review screen in the options page; CV eval set and model selection; Render deployment in Frankfurt; uptime monitor; Sentry-compatible error tracking with scrubbing; privacy policy and DPIA drafts.

**ADRs:** hosting and scaling path (Render to Cloud Run); LLM provider and model (with eval results); install key issuance and abuse protection; parse request memory handling.

**Acceptance criteria**
- Parse accepts PDF and DOCX under the size limit and rejects other types and oversized files with a clear error.
- A scanned image-only PDF gets the message "upload a text-based PDF or DOCX".
- Canary test: a CV containing a unique marker string is parsed. The marker does not appear in logs, traces, error tracker events, the database or any file written during the request.
- Two-column and table-based CVs in the eval set parse with entries in the correct sections. Per-section accuracy is reported, and targets are agreed with you before the model is chosen.
- The eval shows projects are never placed in work, and each description stays with its own entry.
- Quota exhaustion returns `429` with `Retry-After`. The options page shows "N of 3 CV parses left today" and the reset time.
- With the LLM provider mocked as down, the backend fails over to the second provider. With both down, the user gets a clear message pointing to JSON import or manual entry.
- The review screen highlights the spec's listed parser mistakes. The user can move, merge, split, edit and delete entries. Nothing is saved before Confirm (verified by test).
- Declining consent never sends the file (verified by a network assertion in test).
- Deployed to Render in Frankfurt. Health checks and the uptime alert work.

## M4. Platform abstraction, Chromium implementation

**Features:** `platform/` module with one interface per browser difference (panel host, shadow root access, background lifecycle, permissions, session storage access, packaging); Chromium implementation; stub implementations for Firefox and Safari that fail loudly; panel mounted in Chrome's side panel with popup fallback; messaging layer with schema validation; activeTab and permission spike (Q1).

**ADRs:** browser abstraction; permission model (result of the Q1 spike).

**Acceptance criteria**
- No file outside `platform/` refers to a specific browser. Enforced by a lint rule.
- Every interface has a test against the Chromium implementation.
- An invalid message between any two contexts is rejected and logged, not processed.
- Spike result documented: what grants access to the page on a Fill click, verified on a live page and a fixture.
- Built manifest has no required all-sites host permission. CI check.
- Background killed mid-operation (via the Chrome DevTools Protocol in test) resumes correctly.

## M5. Core engine

**Features:** platform identification; form model builder; dictionary (`packages/vocab`) with priority coverage and exclude patterns; matcher with section-plus-field context and confidence threshold; fill plan; filling strategies (native setter, select, checkbox and radio, file upload via chunked transfer, rich text via paste and `beforeinput`); layered verification; repeating block add and remove in profile order, with form limits; repair mode with preview and confirmation; dropdown matching; constraints and description variants; undo; stop; pause on user typing; submit deny-list; session store (Q12); panel Fill tab checklist; shared text normalisation and scrubbing cases.

**ADRs:** mapping confidence thresholds; MAIN-world strategies (only those proven necessary); storage layout.

**Acceptance criteria**
- 90% branch coverage in `packages/core`.
- Every dictionary synonym and exclude pattern has a test. "Years of experience" does not match the work section.
- A field below the confidence threshold is never written. It shows as "Needs you".
- A fixture where React ignores the change shows a cross, not a tick.
- The engine never clicks a deny-listed element. A test runs the engine over a fixture full of submit-like buttons.
- Pressing Fill twice produces no duplicate entries.
- Stop mid-fill leaves every field either fully written or untouched.
- Typing into the page during a fill pauses it and asks whether to continue.
- A block re-rendered mid-fill is rebuilt and re-verified, with no writes to detached elements.
- The form limit case shows the "Form allows 3 jobs…" item.
- Undo restores field values, and the panel states what undo cannot reverse.
- Repair mode deletes nothing before the user confirms the preview, and never touches non-CV sections.
- Form model build takes under 100 ms on the reference fixture. Measured and reported.
- Shared text normalisation and scrubbing cases pass in TypeScript (the Python side joins in M10).

## M6. Fixture pages and Chromium end-to-end harness

**Features:** fixture pages listed in spec section 14.2; Playwright with a persistent context loading the unpacked extension; CI job.

**Acceptance criteria**
- Every fixture in spec section 14.2 exists and has a full-fill E2E test asserting every value and the checklist state.
- Hostile-label, ambiguous-section and non-English fixtures produce "Needs you" or flags, never wrong values.
- Cross-origin iframe and `srcdoc` fixtures fill after the permission flow decided in M4.
- The E2E job runs in CI and is required for merge.

## M7. Greenhouse adapter

**Features:** URL and DOM detection for both board versions and embeds (`gh_jid`); Job Board API schema fetch from the background, with `required` flags; combobox handling; school, degree and discipline search endpoints.

**Acceptance criteria**
- Recorded snapshots of both board versions and one embed fill with every value verified.
- API `required` flags drive the "Needs you" ordering.
- When the employer has not enabled education or employment sections, the adapter does not invent them.
- Manual smoke test on one live Greenhouse form, stopped before submit, recorded.

## M8. Lever adapter

**Features:** detection; CV upload first, wait for Lever's parser to settle, then overwrite; links block; location typeahead.

**Acceptance criteria**
- A fixture simulating Lever's parser overwriting fields after upload ends with our values in every field.
- The settle wait has an upper bound and a clear message when it is hit.
- Manual smoke test on one live Lever form, stopped before submit, recorded.

## M9. Generic engine on company-built forms

**Features:** tuning the generic path on a set of company-built forms; flagging unmatched sections.

**Acceptance criteria**
- A set of at least 10 company-built form snapshots (chosen with you) is added as fixtures. Each fill has zero wrong values. Every field is either ticked or flagged.
- Sections matching no profile type are flagged in the report, not guessed.
- Locale: non-English pages are flagged when no adapter covers them.

## M10. Events, scrubbing, report queue, corrections

**Features:** first-run telemetry opt-in (off by default); event schema; extension-side scrubbing; rotating install ID; offline queue with exponential backoff and jitter; `POST /v1/events` (max 500 per batch); server-side scrubbing using the shared cases; retention job; `DELETE /v1/installs/{id}/events`; "Report a problem" with preview and Send; `POST /v1/problem-reports`; admin-only list of problem reports (Q10); correction detection with trusted-input events; tracking suppressed while the engine writes.

**Acceptance criteria**
- With telemetry off, no event request is made (network assertion in E2E).
- The opt-in prompt is plain English and can be changed later in settings.
- A property test shows a scrubbed event never contains any string from a randomly generated profile.
- Shared scrubbing cases pass in both TypeScript and Python in CI.
- The problem-report preview shows exactly the payload that is sent, byte for byte.
- Events queue offline and send on reconnect. `Retry-After` is respected with no tight loop.
- The stored event table has no key ID, IP address or request ID column (Q7).
- Raw events older than the retention window are deleted by the retention job (test with a fake clock).
- A deletion request removes every event for the install's current and past IDs.
- A user edit after a fill is recorded as `corrected_by_user`. The engine's own writes are never recorded as corrections.

## Release 1 done when

- All M1–M10 criteria pass.
- Manual smoke checklist completed on live Greenhouse and Lever forms in Chrome and Edge (plus Brave, subject to Q3).
- Privacy policy published. Chrome Web Store listing drafted with the permission justification (Q2).
- README covers setup, loading the extension, running each test suite and running the backend.
