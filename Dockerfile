# syntax=docker/dockerfile:1

# One file, two images (see compose.yaml):
#
#   --target api   the budgeting engine behind its HTTP API
#   --target web   the built web UI on nginx, which also forwards /api to the engine
#
# They share the first stage on purpose: the web build generates its TypeScript
# types from the API's OpenAPI document, so it needs the Python package to
# produce that document. One source of truth, no copy checked in.

ARG PYTHON_VERSION=3.14
ARG NODE_VERSION=24
ARG UV_VERSION=0.11.21

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# --- Python: dependencies, then the package itself ----------------------------
FROM python:${PYTHON_VERSION}-slim AS python-build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies first, from the lock file alone: this layer is rebuilt only when
# the lock changes, not on every source edit.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

# The version normally comes from the git tag (hatch-vcs, docs/RELEASING.md).
# There is no .git in a build context, so it is passed in instead. The variable
# is set for this one command only: every dependency is already installed, so
# Monay is the only package it can apply to.
ARG MONAY_VERSION=0.0.0.dev0
COPY pyproject.toml uv.lock ./
COPY monay ./monay
RUN --mount=type=cache,target=/root/.cache/uv \
    SETUPTOOLS_SCM_PRETEND_VERSION=${MONAY_VERSION} \
    uv sync --frozen --no-dev --no-editable

# --- api: just the virtualenv, run as an unprivileged user --------------------
FROM python:${PYTHON_VERSION}-slim AS api
RUN groupadd --system --gid 10001 monay \
    && useradd --system --uid 10001 --gid monay --no-create-home --home-dir /data monay \
    && install --directory --owner monay --group monay /data
COPY --from=python-build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MONAY_DB_URL=sqlite:////data/monay.db \
    MONAY_API_HOST=0.0.0.0 \
    MONAY_API_PORT=8000
USER monay
WORKDIR /data
# The database lives here; compose mounts a named volume over it.
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
CMD ["python", "-m", "monay.api"]

# --- the API's contract, for the web build ------------------------------------
FROM python-build AS openapi
RUN /app/.venv/bin/python -m monay.api.openapi /openapi.json

# --- web: build the React app --------------------------------------------------
FROM node:${NODE_VERSION}-alpine AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY web/ ./
COPY --from=openapi /openapi.json ./openapi.json
# `build` generates the API types and token CSS, type-checks, then bundles.
RUN npm run build

# --- web: serve it -------------------------------------------------------------
FROM nginxinc/nginx-unprivileged:stable-alpine AS web
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /web/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD ["wget", "--quiet", "--spider", "http://127.0.0.1:8080/"]
