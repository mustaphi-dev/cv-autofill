# Architecture

Status: draft for review. Source of truth for requirements is [spec.md](spec.md). Each significant choice listed here gets an ADR in `docs/adr/` when its milestone starts.

Release 1 covers Chromium only. Diagrams show the full design, so Firefox and Safari can be added later without rework. Where a part is not built in Release 1, the text says so.

## 1. System overview

```mermaid
flowchart LR
    user(["User"])

    subgraph browser["User's browser"]
        direction TB
        subgraph ext["Extension (extension origin)"]
            panel["Panel UI<br/>Fill tab + Profile tab<br/>(Chrome side panel)"]
            options["Options page<br/>profile editor, CV upload,<br/>review screen, settings"]
            bg["Background<br/>(service worker)<br/>storage, network,<br/>sessions, permissions"]
            store[("Extension storage<br/>local: profile, settings, event queue<br/>session: fill sessions, derived key<br/>IndexedDB: CV and cover letter files")]
        end
        subgraph page["Job application page (page origin)"]
            cs["Content script<br/>(isolated world)<br/>detect, plan, fill, verify"]
            ps["Page script<br/>(MAIN world)<br/>dumb executor, one value at a time"]
            dom["Page DOM<br/>ATS form, iframes"]
        end
    end

    subgraph backend["Our backend (Render, Frankfurt)"]
        api["FastAPI service<br/>/v1/parse, /v1/events,<br/>/v1/problem-reports, /v1/installs,<br/>/v1/status, /v1/map (Release 3)"]
        db[("PostgreSQL<br/>install key hashes,<br/>scrubbed events,<br/>problem reports")]
        kv[("Render Key Value<br/>(Redis-compatible)<br/>rate-limit and quota counters")]
    end

    llm["Hosted LLM provider<br/>open-weight model,<br/>zero data retention<br/>+ failover provider"]
    sentry["Error tracker<br/>(Sentry-compatible,<br/>scrubbed)"]
    gh["Greenhouse Job Board API<br/>(public, read-only)"]

    user --> panel
    user --> options
    panel <-->|"runtime messages<br/>(schema-validated JSON)"| bg
    options <-->|"runtime messages"| bg
    bg <--> store
    bg -->|"scripting.executeScript<br/>on Fill click only"| cs
    cs <-->|"runtime messages"| bg
    cs -->|"reads and writes fields"| dom
    cs -->|"one instruction"| ps
    ps -->|"writes one field"| dom
    bg -->|"HTTPS + per-install key"| api
    bg -->|"form schema fetch"| gh
    api <--> db
    api <--> kv
    api -->|"CV text (parse) or<br/>form structure (map)"| llm
    api -.->|"errors, no payloads"| sentry
```

**What it shows.** The extension has four parts. The panel and options page are the user interface. The background owns everything that must survive: storage, network calls, fill sessions and permissions. The content script is injected into the job page only when the user clicks Fill, and does all detection, filling and checking. The page script runs inside the page's own JavaScript context and is used only for the few widgets that ignore the content script; it gets one value at a time and is never trusted.

Every network call goes out from the background. The backend relays CV text (one-time parse) or form structure (AI mapping, Release 3) to a hosted LLM, stores only scrubbed telemetry and problem reports in PostgreSQL, and keeps rate-limit counters in Key Value. Filling itself never needs the backend: if the backend is down, the extension still fills with its built-in rules.

## 2. Fill flow (one step of one form)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant P as Panel
    participant B as Background
    participant C as Content script
    participant M as Page script (MAIN)
    participant D as Page DOM

    U->>P: Click Fill
    P->>B: fill.start(tabId)
    B->>B: Check permissions for page and iframe origins
    opt Cross-origin iframe origin not yet granted
        B->>P: Ask for that origin
        P->>U: Permission prompt (user gesture)
        U-->>P: Allow
    end
    B->>B: Load or create fill session for this tab
    B->>C: Inject (allFrames where permitted) and send session + profile slice
    C->>D: Identify platform (URL, then DOM signatures)
    C->>D: Build form model (sections, blocks, fields, signals)
    C->>C: Map model to profile (adapter, then dictionary) with confidence
    C->>C: Detect mode: clean slate or repair
    alt Repair mode (site parser filled things)
        C->>C: Wait until values are stable (bounded)
        C->>P: Preview of entries to remove and fields to overwrite
        U->>P: Confirm
    end
    C->>P: Checklist skeleton (all fields pending)
    loop Each block in profile order, each field in block
        C->>C: Deny-list check before any click
        alt Isolated-world strategy works for this widget
            C->>D: Set value (native setter, events, paste...)
        else Widget proven to need MAIN world
            C->>M: One instruction: field ref + one value
            M->>D: Set value
            M-->>C: Done (not trusted)
        end
        C->>D: Verify: read back after settle, blur and refocus, look for validation errors
        alt Value stuck
            C->>P: Tick
        else Low confidence or needs a user decision
            C->>P: Needs you
        else All strategies failed
            C->>P: Cross
        end
        C->>B: Record field done in session
    end
    C->>P: Summary: required fields verified or not
    P->>U: Groups with only ticks collapse, crosses and Needs you stay open
    opt Telemetry on
        C->>B: Field events (values never included)
        B->>B: Scrub, queue, send later in batches
    end
```

**What it shows.** Nothing runs until the user clicks Fill. The background checks and, if needed, asks for permission, then injects the content script. The content script works out which platform it is on, builds a model of the form, and matches each field to a profile key with a confidence score. If the site's own CV parser has already filled things, the user sees a preview of what will be changed and must confirm. Each field is then filled using the safest strategy that works, and every field is checked by reading it back and blurring it, so a value that only looks filled is caught. The panel updates live: a tick for verified, a cross for failed, "Needs you" where the extension chose not to guess. Low-confidence fields are never filled. Telemetry, if the user turned it on, records only what happened, never what was typed.

Stop and pause on user typing (not drawn) cancel the loop between fields; the content script always finishes or rolls back the current field before stopping, so the page is never left half-written.

## 3. Multi-step flow (fill session lifecycle)

```mermaid
stateDiagram-v2
    [*] --> NoSession
    NoSession --> Active: User clicks Fill on a supported page
    Active --> Filling: Fill clicked on current step
    Filling --> Active: Step finished (fields recorded in session)
    Filling --> Active: User clicks Stop
    Active --> Active: User moves to next step (extension does nothing)
    Active --> Active: Page reload or background restarted (session read back from storage.session)
    Active --> Ended: User clicks Start over
    Active --> Ended: Tab closed
    Active --> Ended: User leaves the application's site
    Ended --> [*]: Session deleted
```

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant P as Panel
    participant B as Background
    participant S as storage.session
    participant C as Content script

    U->>P: Fill (step 1)
    P->>B: fill.start(tabId)
    B->>S: get session[tabId]
    S-->>B: none
    B->>S: create {sessionId, platform, jobUrl without query, step 1, done: []}
    B->>C: Inject + session
    C->>B: field done (repeated)
    B->>S: append to done
    Note over U,C: User clicks the site's own Next button. The extension does not react.
    U->>P: Fill (step 2)
    P->>B: fill.start(tabId)
    B->>S: get session[tabId]
    S-->>B: session (step 1 done list)
    B->>C: Inject + session
    C->>C: Skip anything already in done, fill only this step
    Note over B,S: Background may be killed at any time. Every write goes to S first, nothing important is kept in memory.
    U->>U: Closes tab
    B->>S: tabs.onRemoved: delete session[tabId]
```

**What it shows.** A fill session belongs to one tab and one application. The background keeps it in `storage.session` (in memory, cleared when the browser closes), never in the page, because content scripts are thrown away on navigation. Each Fill click reads the session, fills only what is new on the current step, and writes progress back field by field, so a reload or a killed background loses nothing. The extension never presses Next and never reacts to step changes. The session ends when the tab closes, the user leaves the site, or the user clicks "Start over".

Release 1 note: Greenhouse and Lever are single-page forms. See plan.md, question Q12, on whether the multi-step session belongs in Release 1 or Release 2 (Workday).

## 4. CV setup flow

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant O as Options page
    participant B as Background
    participant A as Backend /v1/parse
    participant L as LLM provider

    U->>O: Open options, choose "Upload CV"
    O->>U: Plain-English notice: CV is sent to our server for parsing, never stored
    alt User declines
        U->>O: Decline
        O->>U: Offer JSON import or manual form
    else User agrees
        U->>O: Agree, pick PDF or DOCX
        O->>B: parse.request(file)
        B->>A: GET /v1/status (quota, service up)
        alt Unavailable or quota used up
            A-->>B: status or 429 + Retry-After
            B-->>O: Plain message with reset time, offer JSON or manual entry
        else OK
            B->>A: POST /v1/parse (file, install key)
            A->>A: Check type, size, text layer (reject scanned PDFs)
            A->>A: Extract text in memory with column-aware reading order
            A->>L: Text + schema-constrained prompt (zero retention)
            L-->>A: JSON
            A->>A: Validate against profile schema
            A-->>B: Parsed profile (file and text dropped from memory)
            B-->>O: Parsed profile
            O->>U: Review screen, section by section, likely parser mistakes highlighted
            U->>O: Move, merge, split, edit, delete entries
            U->>O: Confirm
            O->>B: profile.save
            B->>B: Validate, store profile in local storage, CV file in IndexedDB
        end
    end
```

**What it shows.** Before a CV leaves the browser the user is told, in plain words, where it goes and that it is not stored, and must agree. Users who decline can import JSON or type their profile. The backend checks quota and the file, pulls the text out in memory (reading two-column layouts in the right order), asks the LLM for output that must match the profile schema, validates it, returns it, and keeps nothing. The review screen is mandatory: nothing is saved until the user confirms, and the entries most likely to be wrong (a project filed as a job, a description under the wrong entry, a missing company or title) are shown first. Parsing only happens again if the user uploads a new CV.

## 5. Data flow and privacy

```mermaid
flowchart TB
    subgraph local["Never leaves the browser"]
        profile["Profile (all CV sections)"]
        files["Stored CV and cover letter files"]
        values["Every value filled or typed into a form"]
        session["Fill sessions"]
        passkey["Encryption passphrase and derived key"]
    end

    subgraph transient["Reaches the backend, never stored"]
        cvparse["CV file and extracted text<br/>(only on upload, only after consent)"]
        formstruct["Form structure for AI mapping<br/>(labels, attributes, widget types,<br/>no values, Release 3)"]
    end

    subgraph stored["Reaches the backend and is stored (opt-in only)"]
        events["Field events: scrubbed labels and signals,<br/>outcome, strategy, host + path,<br/>day-level date, rotating install ID"]
        reports["Problem reports: scrubbed form structure<br/>+ optional comment, previewed before Send"]
        keys["Install key hash, quota counters"]
    end

    subgraph never["Never stored anywhere on our side"]
        nolog["CV content in logs, traces,<br/>error tracker, database or disk"]
        noval["Field values, screenshots, raw page copies"]
    end

    profile -->|"page sees only the values it is filled with"| page["Job site"]
    profile -->|"scrub list: profile values removed<br/>from every outgoing text"| scrub["Scrubber in extension"]
    scrub --> events
    scrub --> reports
    cvparse --> llmp["LLM provider<br/>(zero retention, relay only)"]
    formstruct --> llmp
    events --> pg[("PostgreSQL<br/>raw events deleted after 90 days,<br/>aggregates kept")]
    reports --> pg
    keys --> pg
    cvparse -. "explicitly prevented, tested" .-> never
```

**What it shows.** The profile, stored files, filled values, fill sessions and the encryption key never leave the user's browser. The only things that can reach our backend are:

- The CV itself, once, at upload time, after consent. It is held in memory for that one request and passed to the LLM provider under a zero-retention setting. It is never written to disk, the database, logs or the error tracker, and a test proves request bodies for this endpoint never reach logs.
- Form structure (labels and field types, never values) for the AI mapper, from Release 3.
- If the user opts in: per-field events and problem reports. Both are scrubbed in the browser first, removing every substring that matches a profile value plus anything that looks like an email, phone number, URL or name. The backend scrubs again as a second line of defence. The install ID rotates every 30 days and dates are rounded to the day, so events cannot easily be joined into a list of applications.

The job site itself sees only the values the extension writes into its form, which is what the user wanted to send it anyway.
