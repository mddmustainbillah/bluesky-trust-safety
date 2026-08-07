# ADR 0001: Project Foundation

- **Status:** Accepted
- **Date:** 2026-08-07
- **Decision owners:** Project maintainer
- **Scope:** Phase 0 engineering baseline

## Context

The Bluesky Trust and Safety project will eventually combine live WebSocket ingestion,
Redis Streams, multiple ML tasks, PostgreSQL, MLflow, monitoring, drift evaluation,
retraining, CI/CD, and AWS deployment.

Before implementing those components, the repository needs predictable answers to these
questions:

- Which Python runtime does the project support?
- How is application code imported and packaged?
- How are direct and exact dependencies recorded?
- How are local and production configurations validated?
- How are secrets kept out of Git?
- Which tests can run without infrastructure?
- How are local dependencies started and proven healthy?
- Which commands do developers and CI use?

Without explicit decisions, individual phases could introduce incompatible conventions,
and environment failures could be confused with application or ML failures.

## Decisions

### 1. Use Python 3.11 for the initial system

The repository pins Python 3.11.4 with `.python-version` and declares:

```toml
requires-python = ">=3.11,<3.12"
```

#### Rationale

- It is compatible with the project's planned classical ML and MLOps stack.
- It provides modern typing and language features.
- A narrow initial range reduces untested runtime variation.

#### Consequence

Python upgrades require an explicit compatibility test and lock regeneration rather than
silent adoption.

### 2. Use a repository-local virtual environment

The default directory is `venv/`, and `.venv/` is also ignored for developer
convenience.

#### Rationale

Project packages must not modify or depend on the global Python environment.

#### Consequence

The environment is disposable and rebuilt from declarations. It is never committed.

### 3. Use a namespaced `src` package layout

Application code lives under:

```text
src/bluesky_trust_safety/
```

#### Alternatives considered

- Put modules directly in the repository root.
- Put generic packages such as `common/` and `ingestion/` directly under `src/`.

#### Rationale

- Tests exercise an installed package instead of accidental root imports.
- The project namespace avoids collisions with generic package names.
- Distribution and import naming conventions remain clear.

#### Consequence

The distribution is `bluesky-trust-safety`, while Python imports use
`bluesky_trust_safety`.

### 4. Use setuptools and `pyproject.toml`

Setuptools is the initial build backend. `pyproject.toml` centralizes project metadata,
package discovery, optional developer dependencies, pytest configuration, and Ruff
configuration.

#### Rationale

- It uses standard Python packaging behavior.
- Editable installation makes the `src` layout convenient during development.
- Centralized configuration reduces scattered tool files.

#### Consequence

The package must be installed with `pip install -e ".[dev]"` or through the provided
Make target before direct use outside pytest.

### 5. Separate direct dependencies from exact locked versions

Human-maintained runtime choices live in `requirements.txt`. Exact installed versions,
including transitive packages, live in generated `requirements.lock.txt`.

Setuptools reads runtime dependencies dynamically from `requirements.txt`.

#### Alternatives considered

- Keep only unpinned requirements.
- Manually duplicate dependencies in `pyproject.toml` and `requirements.txt`.
- Add a new dependency-management tool during Phase 0.

#### Rationale

- Version ranges communicate compatibility intent.
- Exact versions reproduce the tested local environment.
- One direct-dependency source avoids declaration drift.
- The initial approach uses the existing toolchain while the system is small.

#### Consequences

- The lock file must be regenerated after dependency changes.
- The current lock is validated on macOS. Linux CI/container reproducibility must be
  validated and may justify a stronger multi-platform locking mechanism later.
- Dependencies are added phase by phase rather than installing the entire future stack
  immediately.

### 6. Use Ruff for linting and formatting

Ruff checks source and tests and targets Python 3.11.

#### Rationale

- One fast tool covers formatting, import ordering, unused/undefined names, modernization,
  and several bug-prone patterns.
- A deterministic formatter reduces style-only review discussion.

#### Consequence

Both `ruff check` and `ruff format --check` are required because linting and formatting
verify different properties.

### 7. Use pytest with explicit test levels

The registered levels are:

- `unit`
- `integration`
- `e2e`

#### Rationale

- Unit tests must remain fast and independent of Docker.
- Integration tests should prove real client/server compatibility.
- End-to-end tests should be limited to complete workflows.

#### Consequence

The fast local quality gate excludes integration tests, while a separate target starts
infrastructure and runs them explicitly.

### 8. Use Pydantic Settings for configuration

The settings model:

- reads environment variables and `.env`;
- uses the `BTS_` prefix;
- restricts environment and log-level values;
- requires Redis and PostgreSQL URLs;
- uses `SecretStr` for connection strings;
- is immutable;
- can be cached for application use.

#### Alternatives considered

- Read `os.environ` throughout the codebase.
- Hardcode local service URLs.
- Use an unvalidated dictionary loaded from `.env`.

#### Rationale

Configuration errors should fail early with validation errors. Components should depend
on one typed contract rather than independently interpreting strings.

#### Consequences

- `.env` remains local and ignored.
- `.env.example` documents required variables using placeholders.
- `SecretStr` prevents common accidental display but does not provide encryption.
- Unit tests disable `.env` loading to remain deterministic.

### 9. Use Redis and PostgreSQL through Docker Compose locally

Redis provides the future event buffer. PostgreSQL provides durable application and
prediction storage. Both run as versioned containers with named volumes and health
checks.

#### Alternatives considered

- Install both services directly on the developer workstation.
- Use remote cloud services during early development.
- Mock infrastructure without a local integration environment.

#### Rationale

- Containers make service setup repeatable.
- Local development avoids cloud cost and network dependency.
- Real integration tests catch driver, URL, port, authentication, and readiness problems
  that mocks cannot catch.

#### Consequences

- Docker Desktop must be running for integration work.
- A running container is not considered ready until its health check passes.
- Redis and PostgreSQL bind only to localhost.
- Normal shutdown preserves named volumes.
- Redis AOF with every-second fsync is a documented durability tradeoff, not a no-loss
  guarantee.

### 10. Use Make as the developer command interface

Make targets cover installation, locking, formatting, linting, tests, Compose lifecycle,
health checks, logs, and smoke checks.

#### Alternatives considered

- Document raw commands only.
- Depend on an activated shell environment.
- Introduce a more complex task runner.

#### Rationale

- Long commands have one reviewed definition.
- Developers and CI can call the same interface.
- Target dependencies can require healthy infrastructure before integration tests.

#### Consequences

- Recipe indentation requires tabs.
- Make escaping requires `$$` for variables intended for a nested shell/container.
- The Makefile discovers `venv/bin/python` so commands work from a fresh terminal.

### 11. Defer advanced infrastructure

Kafka/Redpanda, Kubernetes, model-serving platforms, a feature store, Terraform/CDK,
OpenTelemetry, distributed compute, and transformer models are not Phase 0 tools.

#### Rationale

Each additional platform adds operational and debugging complexity. The project will add
advanced tools only after a measured limitation or deliberate next-stage learning goal
justifies them.

#### Consequence

Phase 0 remains focused on a reliable local foundation rather than architecture theater.

## Validation evidence

Phase 0 was validated from a shell where the virtual environment had been deactivated.

The following passed:

- Ruff lint check;
- Ruff formatting check across 24 files;
- five unit tests;
- pip dependency check;
- configuration smoke test;
- Redis and PostgreSQL Compose health checks;
- two Python infrastructure integration tests;
- Redis `PING`;
- PostgreSQL readiness check;
- safe Compose shutdown preserving volumes.

Git status confirmed that `.env` and the virtual environment were ignored.

## Follow-up decisions

Future ADRs should cover at least:

- Jetstream cursor recovery and idempotency;
- Redis Streams at-least-once delivery;
- event and schema versioning;
- PostgreSQL idempotency keys and deletion handling;
- MLflow champion/challenger promotion;
- drift-triggered labeling versus automatic retraining;
- AWS networking, secret storage, and cost architecture.
