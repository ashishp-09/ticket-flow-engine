FROM python:3.13-slim AS base-builder
COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

WORKDIR /backend
COPY pyproject.toml ./

FROM base-builder AS test-env-builder
RUN uv sync --no-dev --group test --no-editable

FROM base-builder AS load-test-env-builder
RUN uv sync --no-dev --group load-test --no-editable

FROM base-builder AS lint-env-builder
RUN uv sync --no-dev --group lint --no-editable

FROM base-builder AS prod-env-builder
RUN uv sync --no-dev --no-editable

FROM python:3.13-slim AS tests
WORKDIR /backend
COPY --from=test-env-builder /backend/.venv /backend/.venv
COPY . .
ENV PATH="/backend/.venv/bin:$PATH"

FROM python:3.13-slim AS load-tests
WORKDIR /backend
COPY --from=load-test-env-builder /backend/.venv /backend/.venv
COPY . .
ENV PATH="/backend/.venv/bin:$PATH"

FROM python:3.13-slim AS lint
WORKDIR /backend
COPY --from=lint-env-builder /backend/.venv /backend/.venv
COPY . .
ENV PATH="/backend/.venv/bin:$PATH"

FROM python:3.13-slim AS app
WORKDIR /backend
COPY --from=prod-env-builder /backend/.venv /backend/.venv
COPY . .
ENV PATH="/backend/.venv/bin:$PATH"
