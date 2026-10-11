# CV Autofill

Browser extension that fills the CV sections of job application forms from your own structured profile, plus a small backend. The specification is in [docs/spec.md](docs/spec.md); the architecture, threat model and plan are next to it.

## Prerequisites

- Node 24 LTS or newer
- pnpm 12 (`npm i -g pnpm@12`)
- uv (Python 3.14 is installed by uv on first run)

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

Loading the extension and running the backend are documented here as those parts are built.
