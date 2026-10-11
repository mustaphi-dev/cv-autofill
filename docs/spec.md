# Claude Code prompt: CV Autofill Browser Extension + Backend

## 1. Who I am and what I want

I am a software and AI engineer. I apply to a lot of jobs. When I upload my CV, the ATS parser gets it wrong:
- Side projects become work experience.
- Entries end up in the wrong order.
- Fields are half filled.
- Role descriptions lose their formatting (bullet points and line breaks get mangled).
- The description for one job often shows up under a different job.
- Many parsers fail to extract the company name and job title from an experience entry at all.

I then have to clear everything and type it again.

Build me a cross-browser extension that fills the CV sections of job application forms from my own structured data, in my order, and verifies every field it touches. Also build a backend that (a) collects anonymous reports about how each fill went and (b) proxies AI field-mapping requests, so I can find and fix weak spots over time.

### Who uses it
Other people will use this, not just me. So from the start:
- Each user's profile stays in their own browser. The backend never stores CV data. The only time a CV reaches the backend is the one-time parse on upload (section 11), and it is discarded as soon as the parse returns.
- Telemetry is off by default. On first run the user is asked, in plain words, whether to turn it on. Nothing is sent unless they say yes, and they can turn it off at any time.
- The backend uses per-install keys with quotas (section 11). No shared key ships in the extension.
- We need a privacy policy, and data handling must meet UK GDPR. Plan for publishing on the Chrome Web Store first.

### The quality bar

Treat this as production software built by a senior engineering team, not a prototype. That means:
- The extension must never silently put wrong data in a field. If it is not confident, it flags the field and leaves it for me.
- Every design decision is written down with its reason (see Engineering standards).
- Every claim in this prompt about a browser or ATS is a hypothesis until you verify it.
- No shortcuts that "work for now": no `any`, no swallowed errors, no magic timeouts without a reason, no untested code paths in the fill engine.

### How to start

Start in plan mode. Read this whole prompt. Ask me the open questions in section 16. Then produce:
1. A short architecture document with diagrams (component view, data flow for one fill, multi-page session lifecycle).
2. A threat model (section 12).
3. A milestone plan with acceptance criteria per milestone.

Wait for my approval before writing code.

## 2. Scope

In scope (CV data only). Every section below is its own type. Nothing from one section may be filled into another.

- **Personal details**: first name, last name, preferred name, headline or current title, email, phone (country code and number stored separately), address (street, city, region, postcode, country)
- **Summary**: professional summary or profile statement
- **Links**: LinkedIn, GitHub, portfolio, personal website, Google Scholar, ORCID, other (label plus URL)
- **Work experience**: company, title, employment type (full-time, part-time, contract, internship, freelance), location, remote/hybrid/on-site, start date, end date, "currently working here", description (bullet list)
- **Projects** (never treated as work experience): name, role, organisation or context (personal, university, hackathon), start and end dates, URL, repository URL, technologies, description (bullet list)
- **Education**: school, degree, field of study, minor, start and end dates, grade or classification, thesis or dissertation title, relevant modules, description
- **Publications**: title, authors (in order), venue (journal or conference), publication date, DOI, URL, status (published, accepted, under review, preprint)
- **Certifications and licences**: name, issuer, issue date, expiry date, credential ID, URL
- **Skills**: grouped by category (languages, frameworks, tools, domains), optional proficiency level and years of experience
- **Languages**: language and proficiency (native, fluent, professional, conversational, basic)
- **Awards and honours**: title, issuer, date, description
- **Volunteering and leadership**: organisation, role, start and end dates, description
- **Training and courses**: name, provider, completion date
- **Professional memberships**: organisation, membership level, start date
- **Talks and presentations**: title, event, date, URL
- **Patents**: title, number, status, date
- **References**: name, title, organisation, email, phone, relationship (filled only if the user enables it for that application, since many forms do not need them)
- **Files**: CV upload and cover letter upload

If a form has a section that matches none of these types, flag it in the report rather than guessing which of my sections fits.

Out of scope:
- Screening questions (work authorisation, sponsorship, salary, notice period, "why us")
- EEO and demographic questions
- Account creation and login
- Clicking Submit. The extension must never submit an application.

Future features (design for them now, do not build them):
- Generating a tailored cover letter from the job description. Leave room for: a step that extracts the job description from the page, a cover letter slot that holds either a stored or a generated file, and a mandatory review step before anything generated is uploaded.
- Screening question answers from a saved answer bank.

## 3. Browser support

Support is added incrementally, easiest first:
1. **Chromium browsers first**: Chrome, Edge, Brave, Opera, Arc. They share one engine and one build, so this covers most users for the cost of one browser. Release 1 is Chromium only.
2. **Firefox** next, once Chromium is stable.
3. **Safari** last. It needs a Mac, Xcode and an app wrapper.

The architecture must not block Firefox or Safari, but do no Firefox or Safari work until I approve that release.

Use Manifest V3 for every browser. Use the `browser.*` namespace everywhere. Chrome only exposes `browser.*` from version 148, which is above our minimum, so Mozilla's `webextension-polyfill` or the build tool's equivalent wrapper is mandatory.

### Validated compatibility facts (October 2026, from MDN browser-compat-data and vendor docs)

| Capability | Chromium | Firefox | Safari | Design consequence |
|---|---|---|---|---|
| Background | Service worker only | Event page via `background.scripts` (no service worker support) | Event page by default | Ship both `background.service_worker` and `background.scripts` in the manifest. Chrome 121+ ignores `scripts`. Firefox 121+ ignores `service_worker`. Code must assume the background can be killed at any time in every browser. |
| Content script `world: "MAIN"` (manifest) | 111 | 128 | 18 | Sets the minimum versions below. |
| `scripting` `MAIN` world | 102 | 128 | 15.4 | Same. |
| `match_origin_as_fallback` | 99 | 128 | 18.4 | Needed for `about:blank` and `srcdoc` iframes. |
| `storage.session` | 102 | 115 | 16.4 | Available everywhere we target. |
| `storage.session.setAccessLevel` | 102 | **Not supported** | 16.4 | Content scripts cannot read session storage in Firefox. All session reads and writes go through the background via messages, in every browser, so there is one code path. |
| `sidePanel` API | 114 (`open` from 116) | **Not supported** (uses `sidebar_action`) | **Not supported** | Build the panel UI once as a standalone page. Mount it in Chrome's side panel, Firefox's sidebar, and a popup or in-page panel (inside a closed shadow root) for Safari. |
| `dom.openOrClosedShadowRoot` | 88 | Not supported, use `element.openOrClosedShadowRoot` (63+) | 26 | Wrap behind one helper. |
| `debugger` API | Yes, but it **cannot be an optional permission** | **Not implemented** | No | Not used in v1. Requiring it at install shows a strong warning and risks store review. Every widget must be fillable without it. |
| Host permissions in MV3 | Granted at install | Prompted at install from Firefox 127, can be revoked later | Granted per site by the user | Always check permissions at runtime with `permissions.contains` and request with `permissions.request`. Never assume they are granted. |
| `activeTab` | Temporary access to the main-frame origin, revoked on navigation to another site | Similar | Similar | Not enough on its own: it does not cover cross-origin iframes (Greenhouse embeds). See section 12 for the permission model. |
| Messaging serialisation | JSON | Structured clone | Varies | Only send plain JSON-safe objects between contexts. Validate every message with a schema. |
| Extension URL | Fixed ID | Random UUID per install | Varies | Never hard-code the extension origin. Set `browser_specific_settings.gecko.id` for Firefox. |
| Content script lifetime | Re-injected on navigation | Stays injected, but `window` properties are destroyed | Varies | Do not keep state on `window`. Re-initialise cleanly on every page lifecycle event. |
| Packaging | ZIP / CRX | XPI, signed by Mozilla | Must be wrapped in a macOS app with `xcrun safari-web-extension-packager` (formerly `safari-web-extension-converter`), needs Xcode | Add a Safari build script. Note it needs a Mac. |

Minimum versions: Chromium 116, Firefox 128 (current ESR line or newer), Safari 18.4. Confirm these against the latest compat data when you start, and tell me if anything has moved.

### Platform abstraction

All browser differences live in one module (`platform/`). The rest of the code never checks which browser it is running in. Each difference gets one interface and one implementation per browser, with a test.

## 4. Research findings about ATS platforms (validated October 2026)

Treat these as a starting point. Verify against current docs and live pages before building on them.

### Greenhouse
- Two hosted versions: `job-boards.greenhouse.io/{board}/jobs/{id}` (newer React app) and `boards.greenhouse.io/{board}/jobs/{id}` (older). Companies also embed the form on their own careers page, often in an iframe, with a `gh_jid` URL parameter.
- Public, unauthenticated Job Board API: `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true`. It returns the form schema: each question has a label, `required`, and fields with a `name` and `type`. Field types: `input_text`, `input_file`, `textarea`, `input_hidden`, `multi_value_single_select`, `multi_value_multi_select`. Fetch it from the background, not the content script.
- Structured education (school, degree, discipline, start/end month and year) and employment (company, title, start, end, current) only appear when the employer turns them on for that job. A live posting I checked had neither. Do not assume these sections exist.
- School, degree and discipline come from the employer's own option lists. Search endpoints: `/v1/boards/{token}/education/schools?term=...`, `/degrees`, `/disciplines`.
- Dropdowns are custom ARIA comboboxes, not native `<select>`. Click, type to search, wait for options, pick, verify.
- An existing open-source filler reports that searchable dropdowns behave differently between the old and new board.

### Lever
- Single-page form at `jobs.lever.co/{company}/{id}/apply`. Public postings API: `api.lever.co/v0/postings/{company}?mode=json`.
- Validated on a live form: CV upload comes first and Lever auto-reads it ("Analyzing resume..."), then fills Full name, Email, Phone, Current location (typeahead), Current company. A "Links" block has LinkedIn, GitHub and Portfolio. No structured experience or education sections.
- Upload the CV first, wait until parsing finishes, then overwrite what the parser touched.

### Workday
- Each company has its own tenant, usually `*.myworkdayjobs.com`, sometimes on a custom domain. Layout and required fields vary by tenant.
- Multi-step wizard inside a single-page React app. The URL may or may not change between steps.
- Elements carry `data-automation-id` attributes. A 2023 working script found experience blocks by `data-automation-id="workExperience-{n}"`, used "Add Work Experience" / "Add Another Work Experience" buttons, and removed parser-created entries with "Delete Work Experience" buttons. Labels were "Job Title", "Company", "From", "To", "Role Description".
- Dates in that script were split month and year segments with `role="spinbutton"`. Typing failed. Arrow keys worked. Verify on current tenants.
- Some elements only render at wider window sizes (reported by another open-source filler). Detect and warn.

### Ashby
- Hosted at `jobs.ashbyhq.com`. The public posting API lists jobs but does not describe the form. DOM-based detection only.

### Others
- iCIMS (often iframe-based), SmartRecruiters, Taleo, Jobvite, BambooHR, Workable, and many company-built forms. These go through the generic engine until the reports show they deserve an adapter.

### Filling techniques
- React controlled inputs ignore `el.value = x` from page code. Use the native prototype setter (`HTMLInputElement.prototype` and `HTMLTextAreaElement.prototype` are different, using the wrong one throws), then dispatch bubbling `input` and `change`. Some fields only validate on `blur`.
- Native `<select>`: set value, dispatch `change`.
- Checkboxes and radios: native `checked` setter, then `click` or `change` depending on the widget.
- File inputs: `File` into a `DataTransfer`, assign `input.files = dt.files`, dispatch `change` and `input`. For drop zones, dispatch `dragenter`, `dragover`, `drop` with the `DataTransfer`. Test this in all three browsers, since behaviour differs.
- Rich text editors (Quill, Draft.js, TipTap, ProseMirror, `contenteditable`) ignore the native setter. Use a paste event carrying a `DataTransfer` with `text/html` and `text/plain`, or `beforeinput` / `insertText`, and verify the editor's rendered content afterwards.
- Synthetic events have `isTrusted: false`. A few widgets ignore them. These widgets get flagged for manual entry in v1. A trusted-input fallback through the `debugger` API is possible on Chromium only, but `debugger` cannot be an optional permission, so it would need a separate opt-in "power" build. Do not build it in v1.
- Firefox content scripts see page objects through Xray wrappers. Test every filling strategy from the isolated world first in all browsers. Use the `MAIN` world only for strategies that are proven not to work from the isolated world, and record which ones in an ADR.

### Prior art to read first (learn from it, do not copy)
- `berellevy/job_app_filler` (BSD-3): content script plus page-injected script to fill React fields, MutationObserver field discovery, per-site field classes.
- `andrewmillercode/Autofill-Jobs`, `KR-16/job-fill-extension`: smaller per-ATS approaches.
- Check licences before reusing any code.

## 5. Architecture

### Repository layout (monorepo)
- `packages/core`: the fill engine. Pure TypeScript, no browser extension APIs, runs in a plain DOM. This is where most logic and most tests live.
- `packages/vocab`: the vocabulary dictionary (section 7) as versioned data plus its matcher.
- `packages/schema`: shared types and runtime schemas (profile, messages, report events, AI mapping contract). Generated JSON Schema is shared with the backend.
- `packages/extension`: the browser shell. Platform abstraction, UI, messaging, permissions.
- `packages/fixtures`: test pages that reproduce hard widgets and real-site snapshots.
- `backend/`: FastAPI service.
- `docs/adr/`: architecture decision records.

### Stack
- Extension: TypeScript in strict mode, MV3. Use a maintained cross-browser build tool. Evaluate WXT first (it supports per-browser builds and per-browser options like `world`; its docs say it defaults Firefox and Safari to MV2, so force MV3 for every target). Record the choice in an ADR.
- UI: React. Accessible (keyboard navigable, labelled controls, visible focus, works with a screen reader). Works in light and dark mode.
- Runtime validation: one schema library (for example Zod) for every message, stored object and API payload. Types are inferred from schemas, never written twice.
- Backend: Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy 2 or SQLModel, Alembic, Pydantic v2, Docker Compose. Pytest, Ruff, mypy in strict mode. Backend Pydantic models are generated from the shared JSON Schema so the TypeScript and Python sides never drift.
- Monorepo: pnpm workspaces for the TypeScript packages, `uv` for the Python backend, both in one repository.
- Hosting: Render. Backend as a Docker web service (start on the 1 CPU, 2 GB plan, since PDF processing needs memory), Render managed PostgreSQL with backups, Render Key Value for rate-limit counters. Confirm Render offers an EU or UK region before setup (UK GDPR) and deploy there. Everything runs from a Dockerfile so it can move to Google Cloud Run later without code changes, if usage grows. Write an ADR with this scaling path.
- The LLM itself is not hosted by us. It runs at a hosted inference provider (section 11). Our backend only relays requests to it.
- Text normalisation (cleaning labels before matching) and privacy scrubbing (removing personal details from reports) exist in both the extension (TypeScript) and the backend (Python). To stop the two drifting apart, keep one shared file of test cases (inputs and expected outputs) in `packages/textkit-cases`, and run it against both implementations in CI. Any change to either implementation must pass the shared cases.
- CV text extraction: `pdfplumber` (MIT) for PDF, `python-docx` (MIT) for DOCX. Do not use PyMuPDF: it is AGPL-licensed, which would force us to open-source the backend or buy a licence. Check the licence of every dependency added.
- LLM client: OpenAI-compatible API format, so changing provider is a configuration change.
- Error tracking: a hosted Sentry-compatible service on a free tier (Sentry's free plan or GlitchTip's), with strict scrubbing so no CV text or profile value ever reaches it. Keep the Sentry SDK so we can switch between the two, or self-host GlitchTip later, without code changes.
- Product metrics (installs, active users, fills, parse counts, success rates, quota hits) come from our own database and are shown in our own admin dashboard. Do not use a third-party analytics tool for these.

### Extension components
1. **Options page (profile editor)**: the user sets up their profile once by uploading either a JSON file or their CV. A CV is parsed once, on first upload, then reviewed by the user. The resulting profile is stored and reused for every application. Parsing only happens again if the user replaces or re-uploads their CV. Parsing is done by the backend with an LLM (section 11). Before the first upload, the user sees a plain-English notice that their CV is sent to our server for parsing, is not stored, and agrees to it. Users who decline can import JSON or fill the profile form by hand.
   - **Review screen (mandatory after every parse):** the parsed profile is shown section by section before anything is saved. It highlights the classic parser mistakes so the user checks them first: entries that may be projects rather than jobs, descriptions that may belong to a different entry, missing company names or job titles, dates that look wrong, and broken bullet points. The user can move an entry between sections, merge, split, edit or delete. Nothing is saved until they confirm. The options page also lets the user review and edit the profile, drag to reorder, store CV and cover letter files for upload fields, export JSON, telemetry and AI settings.

2. **Panel UI** (one app, mounted per browser as in section 3). Two tabs:
   - **Fill**: the Fill and Stop buttons, then a live checklist that updates field by field as the fill runs. Fields are grouped by section (Personal details, Work experience entry 1, entry 2, Education, and so on), each group collapsible, with a count per group (for example "Work experience: 9 of 10"). Each field shows one of three states:
     - **Tick**: filled and verified.
     - **Cross**: tried and failed.
     - **Needs you**: skipped on purpose because confidence was too low, or the field needs a user decision.
     Groups where every field is ticked collapse automatically. Groups with a cross or "Needs you" stay open, so users see only what needs attention.
     Clicking any item scrolls the page to that field and briefly outlines it, then the outline fades. The extension never leaves permanent styling on the page. Undo sits at the bottom.
     **Report a problem**: every cross or "Needs you" item, and the panel as a whole, has a "Report a problem" button. It is optional and never automatic. Clicking it shows the user exactly what will be sent before anything leaves the browser: the page's form structure (headings, labels, field types, layout, which fields failed and why), with every value removed and the text scrubbed, plus an optional comment box. Nothing is sent until the user clicks Send. No screenshots and no raw page copies are ever sent from users' browsers.
   - **Profile**: view and edit the stored profile, reorder entries, replace the CV. Edits apply to future fills.
   - **Floating Fill button**: while a fill session is active in a tab and the panel is closed, a small Fill button floats on the page. Clicking it fills the current step, exactly like the panel's Fill button. It never clicks Next or anything else on the page. On a step with nothing left to fill, it says so. It lives in a closed shadow root, reacts only to trusted clicks (`isTrusted`), is keyboard accessible, and is removed when the panel opens or the session ends. It leaves no styling on the page.
3. **Content script (isolated world)**: detection, planning, orchestration, filling and verification wherever the isolated world works. Talks to the background for storage and network.
4. **Page script (MAIN world)**: a small, dumb executor used only for strategies that do not work from the isolated world. The MAIN world cannot be secured: the page can read and tamper with anything in it, including any token. So the design must not depend on secrecy there. It receives one instruction at a time (field reference plus the single value going into that field, which the page will see anyway once filled). It never receives the profile. The content script never trusts anything it reports back: every result is verified by reading the field from the isolated world.
5. **Background**: owns all storage, network calls, session state and permissions. Holds nothing important in memory. Resumes correctly after being killed mid-fill.

File transfer: content scripts run on the page's origin, so they cannot open the extension's IndexedDB. The background reads the CV file and sends it to the content script in chunks (base64, fixed chunk size, with a total size limit and a checksum), since messages must be JSON-safe.

### Profile schema
Base it on the JSON Resume schema, extended:
- Separate arrays for every Scope section: `work`, `projects`, `education`, `publications`, `certifications`, `skills`, `languages`, `awards`, `volunteering`, `courses`, `memberships`, `talks`, `patents`, `references`. Projects never go into work fields. Publications never go into projects.
- Each entry has a stable `id` and an explicit `order` I control.
- Dates stored as `{year, month}` with `month` optional, plus `current: boolean`. Never formatted strings.
- Descriptions stored as structured bullets (array of strings) plus optional variants (short, long). The engine renders them per target: newline-separated `•` lines for plain textareas, real list markup for rich text editors.
- Optional aliases per entry (school name variants, company former names) to help dropdown matching.
- A `schemaVersion` field and tested migrations between versions.
- Files in IndexedDB. Profile in extension local storage.
- Optional at-rest encryption of the profile with a passphrase (Web Crypto, AES-GCM, key derived with PBKDF2 or better). Off by default, documented trade-off. The derived key is kept in `storage.session` (memory only, cleared when the browser closes), so the background can be killed and restarted without asking again. The user is prompted for the passphrase once per browser session.

## 6. The fill engine

Each stage is a separate module in `packages/core` with its own tests. Stages communicate through typed plans, not shared mutable state.

0. **User-initiated only.** The extension never scans pages or acts on its own. Nothing runs on a page until the user clicks Fill there. The only thing it shows on a page without a new click is the floating Fill button (section 5), and only during a fill session the user started. Every step below happens only after a Fill click.
1. **Identify the platform** (after the click): URL patterns, then DOM signatures, to pick the right adapter. Check inside iframes too.
2. **Build a form model**: a normalised tree of sections, repeating blocks and fields with every signal attached (label text from `<label for>`, `aria-labelledby`, `aria-label`, `name`, `id`, `placeholder`, `autocomplete`, nearby text, heading, block index, widget type, constraints like `maxlength`).
3. **Map the model to the profile**: section 8 describes the hybrid mapper. Output a fill plan where every field has a target profile key and a confidence score. Below threshold, flag and skip. Never guess.
4. **Respect the route the user chose.** The extension never picks between options like Workday's "Autofill with Resume" and "Apply Manually". The user chooses. The engine then works in one of two modes, detected from the page:
   - **Clean slate** (user applied manually, or the CV sections are empty): fill straight from the profile.
   - **Repair** (the site's parser already filled things): the profile is the source of truth. Wait until parsing has settled (loading indicators gone and field values stable across two consecutive checks, with an upper bound and a clear message if it is hit), then go to step 5.
   If the user uploads the CV through the extension on a page that parses on upload, upload first and wait for parsing to settle before filling, so the parser cannot overwrite our values.
5. **Repair parser output**: in repair mode, show a preview in the panel of what will change (entries to remove, fields to overwrite), then on confirmation clear the parser's CV-section entries and refill from the profile. Never delete anything outside CV sections.
6. **Fill in order**: make the number of repeating blocks equal the number of profile entries (add or remove), then fill block 1 with entry 1, and so on, in profile order. Wait for each new block to render. If the form has a limit (for example the "Add another" button disappears after three), fill the first entries in profile order up to the limit, then add a "Needs you" item to the checklist, for example "Form allows 3 jobs. Filled your 3 most recent. 3 not added." Users who want a different selection or order change it in the Profile tab. No per-application selection or presets in v1.
7. **Verify every field.** Reading the value back from the page is not enough. Frameworks like React keep their own copy of each field's value, and that copy is what gets submitted. If the framework did not register our change, the field shows our text but the form still submits the old value. So verification has layers:
   - Read the value back after a settle period (comboboxes: selected option text; rich text editors: rendered content).
   - Move focus away and back, which often makes the framework re-draw the field from its own copy. If our value disappears, the framework never accepted it.
   - Check for validation messages the site shows after blur (for example "This field is required").
   - On known platforms, adapters may use any stronger platform-specific check available.
   If a value did not stick, try the next strategy (native setter, simulated typing, keyboard events, paste). After all fail, flag it.
8. **Required and optional fields**: detect required fields from the `required` attribute, `aria-required`, asterisks or "(required)" in the label, and platform data where available (for example the Greenhouse API's `required` flag).
   - Fill required and optional fields alike when the profile has the data.
   - Required field with no matching profile data: "Needs you", listed at the top of the checklist.
   - Optional field with no matching profile data: left blank and shown as a quiet "Not in your profile" note, not as a problem.
   - The panel shows "All required fields filled" only when that is verified.
9. **Dropdown matching**: exact, then the user's aliases, then normalised, then fuzzy with a strict threshold. "Other" only if it exists and the user enabled it. Otherwise flag.
10. **Respect constraints**: `maxlength`, visible character counters, date format (MM/YYYY, date picker, month and year selects, spinbuttons). Pick the description variant that fits. Never cut mid-sentence.
11. **Report** in the panel and, if telemetry is on, queue the anonymised events.

Global rules:
- Never click Submit, Apply, Send or anything that sends the application. Enforce this with a deny-list check on every element the engine clicks, plus a test.
- Never touch screening, EEO or demographic questions.
- Undo restores field values only. It cannot bring back deleted entries or remove uploaded files, so the panel says that clearly. That is why repair mode always shows a preview and asks for confirmation before deleting anything.
- Idempotent: pressing Fill twice must not create duplicates.
- Stop button: cancels the fill immediately and leaves the page in a consistent state.
- If the user types into the page during a fill, the engine pauses and asks whether to continue.
- If the page re-renders a block mid-fill, the engine re-builds the form model for that block and re-verifies, rather than writing into detached elements.
- One active fill per tab. Fills in different tabs are fully independent.
- Correction tracking is suppressed while the engine is writing, so the engine's own events are never counted as the user's corrections.
- Locale: detect the page language. The v1 dictionary is English. Non-English forms are filled only by adapters and otherwise flagged. Date formats are detected per field, never assumed from the locale.
- Waits use observable conditions (MutationObserver, value stability), never bare `setTimeout` guesses. Every wait has a timeout and a clear failure message.
- Performance budget: building the form model on a typical page under 100 ms. Measure and report it.

## 7. Vocabulary and matching

Real forms use many words for the same thing ("Experience", "Work experience", "Professional experience", "Employment history", "Career history"). This must be handled systematically for every section and every field.

### The dictionary (`packages/vocab`)
- Versioned JSON data, one entry per section and per field (for example `work`, `work.title`, `work.company`, `work.start`, `projects`, `projects.name`, `education.school`).
- Each entry has: canonical key, synonyms, abbreviations, and **exclude patterns**.
- Priority: full coverage first for personal details, links, summary, work, projects, education, skills, certifications, languages and files. The rarer sections (publications, awards, volunteering, courses, memberships, talks, patents, references) stay in the profile schema from day one, but their vocabulary is expanded when reports show forms asking for them.
- Starter examples:
  - `work`: experience, work experience, professional experience, employment, employment history, work history, career history, relevant experience, positions held
  - `projects`: projects, personal projects, side projects, portfolio, selected work
  - `education`: education, academic background, qualifications, academic history
  - `work.title`: job title, title, position, role, designation
  - `work.company`: company, employer, organisation, organization, company name
  - `work.start`: from, start date, date started, start
- Exclude patterns stop false matches. "Experience" in "years of experience" or "describe your experience with Python" is a screening question, not the work section.

### Matching rules
- Normalise first: lowercase, strip punctuation and required-field asterisks, remove filler ("please enter", "your", "optional"), unify British and American spelling.
- Context decides. A field is matched as section plus field, never field alone. "Title" means job title in a work block, project name in a projects block, thesis title in education. If the section is unknown, confidence drops.
- Ambiguous sections ("Accomplishments", "Additional information") are flagged unless the AI mapper and the dictionary agree.
- The dictionary has its own test suite: every synonym and every exclude pattern has a test.

### Learning loop
Labels that failed, or that I corrected, show up in the backend as candidate synonyms. A human (me) approves them before they enter the dictionary. Nothing is added automatically. Approved entries ship with the next extension version.

## 8. Hybrid mapping: rules plus AI

AI understands the form. Code acts on it. Rules check the AI.

1. **Rules first.** Known platform adapters and the dictionary map what they can. On Greenhouse, Lever, Workday and Ashby this should cover nearly everything, so no AI call is needed.
2. **AI for the rest.** If any section or field is below the confidence threshold, the extension sends the form model to the backend `POST /v1/map` endpoint. Only structure is sent: headings, labels, attributes, widget types, block structure. **Never the user's profile data, never any field values.**
3. **The backend calls the LLM** with structured output constrained to a closed set: every field maps to one of the known profile keys or to `unknown`. The response is schema-validated. Anything outside the allowed set is rejected.
4. **Cross-check.** Where the AI and the dictionary agree, confidence is high. Where they disagree, the field is flagged. LLM confidence is not calibrated, so where only the AI has an answer, the default is "confirm before fill": the panel shows the proposed mapping and the user approves it with one click. Approvals are cached for that form. Auto-accepting AI-only mappings is allowed only after the eval set shows precision above a target I set, per section.
5. **Cache by form signature.** Hash the form structure (not the URL). Repeat visits reuse the cached mapping without a new call.
6. **Fail safe.** If the backend or LLM is down, slow, or over budget, the extension falls back to rules only and flags the rest. It never blocks the fill.
7. **Prompt injection.** Page text is untrusted input. A page could contain text like "ignore your instructions". The closed output set, schema validation and the fact that the LLM never sees the user's data or touches the page are the defence. Write tests with hostile labels.
8. **Keys stay on the server.** The LLM API key lives only in the backend. The extension never holds it.
9. **Evaluation.** Build a labelled set of form models (from fixtures and snapshots) and measure the mapper's precision and recall per section. Tune for precision: a wrong mapping is worse than a flagged field. In regular CI, replay recorded LLM responses so tests are free and deterministic. Run the live eval only when the prompt, model or provider changes.
10. **When to build it.** The rules engine and reporting ship first. Build the AI mapper once the reports show which forms and sections the rules cannot handle, and use those forms as the first eval set.

Provider: ask me (section 16). Keep the provider behind an interface so it can be swapped.

## 9. Multi-page forms

This is the hardest part. Design it carefully.

- A fill session per tab is stored by the background in `storage.session`: platform, job URL without query string, completed sections and entries, current step, session ID.
- The user clicks Fill on each step, either in the panel or on the floating Fill button (section 5). The extension never fills a new step on its own.
- The session remembers what earlier steps already filled, so each click only fills what is on the current step and never repeats or duplicates work.
- The session is tied to one application in one tab. It ends when the tab closes, the user leaves the application's site, or the user clicks "Start over".
- Content script lifetime differs between browsers (section 3), so the session lives in the background, not in the page.
- After a full reload, resume from the stored session.
- The panel shows whether the current step is fully verified before I click Next.
- The extension never clicks Next and never detects step changes to act on its own. The user moves between steps and clicks Fill on each one. That is the whole interaction.
- After a full page load during an active session, the background may put the floating Fill button back on the page, but only if it still has access to that page. It never asks for new access just to show the button. It does not read or fill anything until the button is clicked.
- Workday adapter must handle "My Information", "My Experience" (work, education, skills, CV upload) and the review step.

## 10. Reporting

### What the extension sends
Only when the user has opted in. One event per field per fill, batched. Never send CV content or any value the user typed or the extension filled.

Privacy note: install ID plus host plus time is effectively a list of every job the user applied to, and labels or nearby text can contain the user's name. So:
- The install ID rotates every 30 days.
- Timestamps are coarsened to the day.
- Every free-text signal (labels, nearby text, headings, placeholders, snippets) is scrubbed before sending: any substring matching the user's profile values is removed, plus anything that looks like an email, phone number, URL or person name.

Each event contains:
- rotating anonymous install ID, extension version, browser and version, date, event schema version
- host and path with query string and fragment removed
- detected platform and adapter version
- section and profile key it was matched to
- field signals: label text, `name`, `id`, `type`, `role`, `autocomplete`, `aria-label`, placeholder
- mapping source (adapter, dictionary, AI, AI plus dictionary) and confidence
- fill strategy that worked
- outcome: `filled`, `skipped_low_confidence`, `failed_to_stick`, `no_dropdown_match`, `ambiguous_section`, `corrected_by_user`
- for failures only: a DOM snippet of the field and its container with all `value` attributes, input contents, and anything that looks like an email, phone number or URL removed

Corrections are the most valuable signal. After a fill, watch fields we filled for trusted user `input` events (`isTrusted: true`). If I change a value, record `corrected_by_user`. If my new value matches a different profile key, send that key name, not the value.

Events queue locally when offline and retry with exponential backoff and jitter. The extension works fully with the backend down.

## 11. Backend

### Endpoints
- `POST /v1/events` (batch, max 500 events)
- `POST /v1/map` (AI mapping, section 8)
- `POST /v1/parse` (one-time CV parsing, see below)
- `GET /v1/stats/sites` failure rate by host, platform and browser
- `GET /v1/stats/fields` most common failing field signatures
- `GET /v1/stats/corrections` most common wrong-key matches
- `GET /v1/vocab/candidates` candidate synonyms for my review, `POST /v1/vocab/candidates/{id}/approve`
- `POST /v1/installs` issue a per-install key
- `POST /v1/problem-reports` user-submitted problem reports (scrubbed form structure plus optional comment). Stored with the same retention and deletion rules as events, and shown in the admin dashboard as a queue I can turn into test fixtures.
- `GET /v1/status` service status and the install's remaining quota
- `DELETE /v1/installs/{id}/events` deletion request for an install's events
- `GET /healthz`, `GET /readyz`

Stats and vocabulary endpoints require admin authentication, never install keys.

### LLM choice and uptime
- Use a cheap open-weight model for both CV parsing and form mapping.
- Do not self-host the model in v1. Running GPUs ourselves makes uptime our problem. Use a hosted inference provider that serves open-weight models.
- Choose the model by measured results on our eval sets (CV parsing and mapping), not by reputation. Shortlist two or three open-weight models, run the evals, pick the cheapest one that meets the accuracy targets. Record the result in an ADR.
- The provider must support schema-constrained JSON output, or we validate and retry. Prefer constrained output.
- The provider must offer no or minimal data retention for API requests. Verify current terms before choosing.
- Configure a second provider serving the same model (or the next-best model from the eval) as automatic failover, behind the same provider interface.
- Timeouts, retries with backoff, and a clear message to the user if parsing is unavailable, pointing them to JSON import or manual entry.
- Uptime basics from day one: health checks, an uptime monitor with alerts, and a status the extension can query before offering CV upload.

### CV parsing endpoint
- Accepts PDF and DOCX up to a size limit. Rejects anything else.
- Extracts text server-side with layout awareness. Two-column CVs are a major cause of bad parsing because plain extraction reads straight across both columns and mixes them. Use word positions from `pdfplumber` to detect columns and reading order before anything reaches the LLM. Include two-column and table-based CVs in the eval set.
- Then calls the LLM with structured output constrained to the profile schema. The response is schema-validated before it is returned.
- Option to evaluate, not to build by default: also sending page images to a vision-capable open-weight model, which can see the layout directly. Adopt it only if the eval shows a clear accuracy gain worth the extra cost.
- The prompt must specifically guard against the known parser failures: keep projects separate from work, keep each description attached to its own entry, keep bullet structure, always extract company and title.
- **Never stored.** The file and extracted text live in memory for the request only. They are never written to disk, the database, logs, error trackers or traces. Write a test that proves request bodies for this endpoint never reach logs.
- Use the LLM provider's zero or minimal data retention option where one exists, and state the provider's retention policy in our privacy policy. Verify the provider's current terms before choosing.
- Per-install quota (for example a few parses per day), since parsing costs money.
- Scanned image-only PDFs are out of scope for v1: detect them and tell the user to upload a text-based PDF or DOCX.
- Build an eval set of real-world CV layouts (one column, two column, tables, academic CVs with publications) with expected output, and measure accuracy per section before release.

### Requirements
- Auth by API key in a header, keys stored hashed. Key rotation supported.
- CORS is not access control: extension background requests bypass it. The API key is the only real control.
- The extension is published for other users, so any key shipped inside it would be public. Use per-install keys issued on first run, each with its own rate limit and daily LLM quota, and the ability to revoke one. Add basic abuse protection on key issuance.
- Support deletion requests: a user can ask for all events tied to their install IDs to be deleted.
- Rate limiting, request size limits, Pydantic validation.
- Rate limits are handled gracefully, never as raw errors:
  - Filling never depends on the backend. The rules engine runs entirely in the browser, so a user who hits a limit can still fill forms.
  - Only parsing, AI mapping and telemetry hit limits. Telemetry simply queues and retries later.
  - The panel shows remaining quota in plain words (for example "2 of 3 CV parses left today") and, when a limit is hit, when it resets and what still works.
  - The backend returns `429` with a `Retry-After` header. The extension respects it and never retries in a tight loop.
  - Counters are stored in Render Key Value (Redis-compatible).
- Server-side PII scrubbing as a second line of defence, with tests proving it.
- Data retention policy (for example raw events deleted after 90 days, aggregates kept). Configurable.
- LLM calls: timeouts, retries, per-day budget cap, response caching by form signature, logging of token usage (not content).
- Structured JSON logging with request IDs. No PII in logs.
- OpenAPI spec published. The extension's API client types are generated from it or checked against it in CI.
- Admin dashboard (my own, behind login): installs and active users, fills per day, fill success rates by platform, CV parses and parse failures, quota hits, LLM spend, top failing sites and fields, and the vocabulary review queue. Start small and add views feature by feature.

## 12. Security and privacy

Produce a short threat model before coding. At minimum cover:
- A hostile page reading or tampering with the MAIN world script.
- A hostile page injecting instructions into labels sent to the AI mapper.
- Leaking profile data through reports, logs, AI requests or error messages.
- A CV leaking from the parse endpoint (logs, crash reports, provider retention, memory dumps).
- A stolen API key.
- Overly broad host permissions.

Rules:
- Permission model: the toolbar click that opens the panel grants `activeTab` for the main frame. If that access has lapsed, Fill requests the page's origin at runtime. Cross-origin iframe origins (for example Greenhouse embeds) and the Greenhouse API are requested the same way, the first time a fill needs them. Because these origins cannot be listed in advance, `https://*/*` is declared under `optional_host_permissions` only. That grants nothing at install, and every request names one exact origin. Required host permissions are empty. Scripts are injected after a user click with `scripting.executeScript` (`allFrames` where permitted). No persistent content script registration. The one exception is re-injecting the floating Fill button into a tab with an active session (section 9). Never request access to all sites.
- No remote code. Everything ships in the package (required by store policies anyway).
- Strict Content Security Policy for extension pages.
- No secrets in the repo. Pre-commit secret scanning.
- Export and delete-all-my-data buttons in the options page.

## 13. Engineering standards

- TypeScript `strict`, no `any`, no non-null assertions without a comment explaining why. ESLint and Prettier. Ruff and mypy strict for the backend.
- Every error is handled or reported, never swallowed. A typed `Result` or error classes for expected failures in the engine.
- Structured logging with a debug mode I can turn on, and automatic redaction of profile values.
- ADRs in `docs/adr/` for every significant choice (build tool, schema library, mapping thresholds, browser abstraction, storage layout).
- Conventional commits. Semantic versioning. A changelog.
- CI (GitHub Actions): lint, type-check, unit tests, AI mapper eval, Chromium end-to-end tests, Firefox end-to-end tests, backend tests, build artefacts for every browser. Each job is added in the release that introduces it (Firefox end-to-end in Release 2, AI mapper eval in Release 3).
- Code review standard: if you would not approve it in a senior team's code review, do not commit it.

## 14. Testing (required)

1. **Unit tests** (`packages/core`, `packages/vocab`): form model building, matcher scoring, every dictionary entry, date handling, dropdown matching, description rendering, report scrubbing. Coverage target of 90% branch coverage for `packages/core` only. Other packages test what matters, without a number.
2. **Fixture pages**: React controlled input, ARIA combobox with async search, Workday-style spinbutton dates, repeating sections with Add/Delete, multi-step wizard, form inside a cross-origin iframe, `srcdoc` iframe, field inside a closed shadow root, drop-zone upload, rich text editor, a parser that overwrites fields after upload, a block that re-renders mid-fill, a page with hostile label text, a page with ambiguous sections, a non-English form.
3. **Real failures become fixtures** in two ways:
   - **User problem reports** (section 5, Report a problem): optional, previewed, scrubbed form structure. A script turns a report into a fixture page that rebuilds the same form structure.
   - **Developer snapshot tool** (developer builds only, run on click): saves a full copy of a page with all values stripped, for cases where the form structure alone is not enough to reproduce a bug.
4. **End-to-end, Chromium**: Playwright with a persistent context loading the unpacked extension. Full fill against every fixture. Assert every value and the report.
5. **End-to-end, Firefox**: Playwright cannot load Firefox extensions the same way. Research the current best option (candidates: `web-ext` with Selenium and geckodriver, or WebDriver BiDi's web extension install) and record it in an ADR. Same fixtures, same assertions.
6. **Safari**: a documented manual checklist, run on a Mac.
7. **Backend**: API, auth, validation, PII scrubbing, rate limits, mapping endpoint with a mocked LLM.
8. **AI mapper eval** (section 8): recorded responses in CI, live eval only on prompt or model changes.
9. **Manual smoke checklist**: one live Greenhouse, Lever, Workday and Ashby form per browser, filled and stopped before submit.

## 15. Build order

Work in releases. Each release is something I can actually use. Commit at the end of each milestone. Do not start the next until its acceptance criteria pass. The platform abstraction exists from day one, so later browsers are additions, not rewrites.

**Release 1: usable on Chromium**
1. Monorepo, tooling, CI skeleton, ADRs for build tool and schema library.
2. Shared schemas, profile model with migrations, options page with JSON import/export, manual editing, reorder and delete-all.
3. Backend skeleton plus the CV parse endpoint, consent notice and review screen.
4. Platform abstraction layer, with the Chromium implementation and interfaces for the others.
5. Core engine: form model, dictionary matcher, filling strategies (including rich text), verification, undo, stop, pause on user input.
6. Fixture pages and the Chromium end-to-end harness.
7. Greenhouse adapter using the Job Board API schema.
8. Lever adapter.
9. Generic engine on company-built forms.
10. Backend events endpoint, scrubbing, report queue, correction detection.

**Release 2: Workday, Ashby and Firefox**
11. Workday adapter with multi-page sessions.
12. Ashby adapter.
13. Firefox implementation of the platform layer and the Firefox end-to-end harness.

**Release 3: learning**
14. Stats views and the vocabulary review loop.
15. Hybrid AI mapper, mapping endpoint, cache and eval set, built from the failures Releases 1 and 2 reported.

**Release 4: Safari and hardening**
16. Safari implementation, packaging script and manual checklist.
17. Hardening from report data: iframes, shadow DOM, drop zones, character limits, performance budget.

## 16. Open questions to ask me before you start

1. Daily LLM budget, and which inference providers to shortlist (the model itself is chosen by eval, see section 11).
2. Do I have a Mac available for Safari builds and testing? (Only needed before the Safari release.)

Already decided: the extension is for other users too and will be published, starting with the Chrome Web Store. The backend is Python on Render.

## 17. Working rules for you

### Build feature by feature, never all at once
For every feature, follow this loop and stop at each checkpoint for my approval:
1. **Design note**: what the feature does, the options you considered, the trade-offs, and your recommendation.
2. **Devil's advocate**: argue against your own recommendation. List the strongest reasons it could fail, what it costs, and what a simpler option would give up. Then say whether you still recommend it.
3. **I approve or change the design.**
4. **Implement only that feature**, with its tests.
5. **Demo**: show me it working (test output, and a fixture or live page run where relevant).
6. **Feature summary**: a short plain-English summary, then a few succinct bullets covering what the feature added and how it works. No jargon I would need to look up.
7. **I approve**, then commit. Only then start the next feature.

Never implement more than one feature in a single step. Never start a feature I have not approved.

### General

- Verify any API, selector, browser behaviour or library detail against current documentation or a live page before relying on it. If something in this prompt is wrong, tell me what you found.
- When unsure about a design choice, ask me instead of guessing.
- Keep a `README.md` with setup, how to load the extension in each browser, how to run each test suite, and how to run the backend.