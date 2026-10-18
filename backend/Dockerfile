FROM ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 AS uv

FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170
RUN useradd --system --uid 10001 app
WORKDIR /srv
COPY --from=build /srv /srv
ENV PATH=/srv/.venv/bin:$PATH PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
# Render sets PORT.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
