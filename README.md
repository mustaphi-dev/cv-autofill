# CV Autofill

Browser extension that fills the CV sections of job application forms from your own structured profile, plus a small backend. The specification is in [docs/spec.md](docs/spec.md); the architecture, threat model and plan are next to it.

## Prerequisites

- Node 24 LTS or newer
- pnpm 12 (`npm i -g pnpm@12`)
- uv (Python 3.14 is installed by uv on first run)
- gitleaks (`brew install gitleaks`). The git hooks need it: `pnpm install` sets `core.hooksPath` to `.githooks`, which blocks commits containing secrets or without a [conventional commit](https://www.conventionalcommits.org) message. CI runs the same checks.

## Setup

```sh
pnpm install
cd backend && uv sync
```

## Checks

TypeScript packages, from the repository root:

```sh
pnpm lint          # ESLint (type-aware)
pnpm format:check  # Prettier
pnpm typecheck     # tsc in every package
pnpm test          # Vitest in every package, with coverage
```

Backend, from `backend/`:

```sh
uv run ruff check && uv run ruff format --check
uv run mypy
uv run pytest
```

## Load the extension in Chrome (or another Chromium browser, version 148+)

```sh
pnpm --filter @cv-autofill/extension build
```

Open `chrome://extensions`, turn on Developer mode, click **Load unpacked** and choose `packages/extension/build/chrome-mv3`.

Running the backend is documented here once it exists (M3).
