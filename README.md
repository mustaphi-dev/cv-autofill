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

Backend, from `backend/` (the tests need the local Postgres and Valkey from Docker Compose):

```sh
docker compose up -d --wait
uv run ruff check && uv run ruff format --check
uv run mypy
uv run pytest
```

The backend's profile models (`backend/app/profile_v1.py`) are generated from `packages/schema/profile.v1.schema.json`. After changing the schema, run `uv run datamodel-codegen` in `backend/`; CI fails if they differ. Validation rules JSON Schema cannot express live in `backend/app/profile.py`, and `packages/schema/fixtures/cases.json` is run by both the Zod and the Python tests so the two sides agree.

## Load the extension in Chrome (or another Chromium browser, version 148+)

```sh
pnpm --filter @cv-autofill/extension build
```

Open `chrome://extensions`, turn on Developer mode, click **Load unpacked** and choose `packages/extension/build/chrome-mv3`.

## Run the backend

From `backend/`, either directly:

```sh
uv run uvicorn app.main:app --reload
```

or in Docker (Docker must be running):

```sh
docker build -t cv-autofill-backend .
# host.docker.internal reaches the Compose services from inside the container
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql://cv:cv@host.docker.internal:5433/cv \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  cv-autofill-backend
```

Apply database migrations first with `uv run alembic upgrade head` (in Docker: `docker run … cv-autofill-backend alembic upgrade head`). A new migration starts with `uv run alembic revision -m "…"`; CI fails if the models and migrations disagree. The tests empty and drop tables, so they refuse to run unless the database and Valkey are on localhost.

Then `curl localhost:8000/healthz` returns `{"status":"ok"}`. `curl localhost:8000/readyz` also checks Postgres and Valkey (start them with `docker compose up -d --wait`; Postgres is on port 5433 so it never clashes with one already installed). Settings come from `DATABASE_URL` and `REDIS_URL`, which default to the Compose services locally and must be set on Render, and `TRUSTED_PROXY_HOPS`, the number of proxies that append to `X-Forwarded-For` (0 locally; must be set on Render, where it is 1). Logs are one JSON object per line and never include request bodies, query strings or real paths.

To revoke an install's key (for example a leaked one), run `python -m app.admin revoke <install_id>` on the server, or `uv run python -m app.admin revoke <install_id>` locally.
