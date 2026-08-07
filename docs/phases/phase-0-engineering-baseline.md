# Phase 0: Engineering Baseline

## Purpose

Phase 0 creates a development environment that is repeatable, testable, safe with
secrets, and ready for application code. The goal is not to implement ML logic. The
goal is to remove avoidable uncertainty before ingestion, models, databases, and cloud
deployment make the system more complex.

This guide documents the exact foundation used by the Bluesky Trust and Safety project
and explains how to reproduce the same pattern in a new Python MLOps project.

## Phase 0 outcome

At the end of this phase, the project has:

- a Git repository with generated files and secrets excluded;
- a repository-specific Python 3.11 runtime;
- an isolated virtual environment;
- an installable Python package using the `src` layout;
- direct and locked dependency declarations;
- validated, immutable application settings;
- unit and integration test separation;
- Ruff linting and formatting;
- Redis and PostgreSQL running through Docker Compose;
- service health checks and persistent named volumes;
- Python integration tests against real infrastructure;
- a Makefile providing one consistent developer interface;
- a verified exit gate that works even when the virtual environment is not activated.

---

## 1. Why Phase 0 matters in MLOps

An ML system has more moving parts than a normal script:

```text
data source
    -> validation
    -> feature transformations
    -> model artifact
    -> online inference
    -> database
    -> monitoring
    -> retraining
```

If the environment is not reproducible, a model failure can be confused with a package
version problem. If configuration is not validated, a database error can be caused by
a typo in an environment variable. If infrastructure is merely running but not healthy,
tests can fail intermittently. Phase 0 makes these failure categories explicit.

The main principle is:

> Establish deterministic engineering behavior before adding probabilistic ML behavior.

---

## 2. Prerequisites

This project uses:

- Git
- pyenv
- Python 3.11.4
- Docker Desktop
- Docker Compose
- Make

Verify them:

```bash
git --version
pyenv --version
python3.11 --version
docker --version
docker compose version
make --version
```

`docker --version` checks only the Docker command-line client. `docker info` also
contacts the Docker daemon:

```bash
docker info
```

If `docker --version` works but `docker info` fails, Docker Desktop may not be running.

---

## 3. Pin the Python runtime

Run from the repository root:

```bash
pyenv local 3.11.4
```

This creates `.python-version`:

```text
3.11.4
```

### Why repository-level pinning matters

Without a local pin, the project may silently use whatever global Python version is
currently selected. Different Python versions can change dependency resolution and
runtime behavior.

The pin states the project's runtime contract, while the virtual environment isolates
the installed packages.

---

## 4. Create and activate the virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

Verify both the version and executable:

```bash
python --version
which python
```

Expected:

```text
Python 3.11.4
<repository>/venv/bin/python
```

### Runtime pin versus virtual environment

They solve different problems:

| Mechanism | Responsibility |
|---|---|
| `.python-version` | Select the Python runtime version |
| `venv/` | Isolate packages installed for this project |

Do not commit the virtual environment. It contains machine-specific executables and can
be rebuilt from dependency declarations.

---

## 5. Protect Git from generated files and secrets

The project `.gitignore` excludes:

- `venv/` and `.venv/`;
- `__pycache__/` and compiled Python files;
- `.env` and other environment files, except `.env.example`;
- pytest and Ruff caches;
- generated data, models, reports, and MLflow runs;
- notebook checkpoints;
- operating-system files;
- package/build artifacts such as `*.egg-info/`.

The important secret rule is:

```gitignore
.env
*.env
!.env.example
```

This means:

- real configuration and secrets stay local;
- a safe template remains commit-worthy;
- new developers can discover required variable names.

Verify ignored files instead of assuming:

```bash
git check-ignore -v .env
git check-ignore -v venv/pyvenv.cfg
git check-ignore -v src/bluesky_trust_safety.egg-info/PKG-INFO
```

Never use `git add -f .env`.

---

## 6. Use a namespaced `src` layout

The application package is located at:

```text
src/bluesky_trust_safety/
```

The repository name uses hyphens:

```text
bluesky-trust-safety
```

The Python package uses underscores because hyphens are not valid in imports:

```python
import bluesky_trust_safety
```

The Phase 0 package structure is:

```text
src/bluesky_trust_safety/
├── __init__.py
├── buffer/
├── common/
├── contracts/
├── drift/
├── features/
├── ingestion/
├── labeling/
├── monitoring/
├── policy/
├── retraining/
├── serving/
├── store/
├── training/
└── validation/
```

Each package contains `__init__.py`. This makes the package boundary explicit and
supports imports such as:

```python
from bluesky_trust_safety.common.settings import Settings
```

### Why not place `common/` directly on the Python path?

Generic package names such as `common`, `store`, and `buffer` can conflict with other
installed packages. The `bluesky_trust_safety` namespace makes ownership unambiguous.

### Why use `src/`?

The `src` layout prevents tests from accidentally importing code merely because the
repository root is the current directory. Tests exercise the installed package, which
is closer to production behavior.

---

## 7. Configure packaging and developer tools with `pyproject.toml`

`pyproject.toml` is the central configuration for:

- the Python build backend;
- package metadata;
- package discovery;
- development dependencies;
- pytest behavior;
- Ruff linting and formatting.

### Build system

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

This tells pip how to build and install the project.

### Project contract

```toml
[project]
name = "bluesky-trust-safety"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dynamic = ["dependencies"]
```

`requires-python` makes the Python compatibility expectation machine-readable.

### Development dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest",
    "ruff",
]
```

These tools support development but are not application features.

Install the editable package and development tools:

```bash
python -m pip install -e ".[dev]"
```

`-e` means editable installation. Changes under `src/` are used immediately without
reinstalling after every edit.

### Package discovery

```toml
[tool.setuptools.packages.find]
where = ["src"]
```

This tells setuptools where importable packages live.

### Runtime dependency source

```toml
[tool.setuptools.dynamic]
dependencies = {file = ["requirements.txt"]}
```

This makes `requirements.txt` the single human-maintained list of runtime dependencies
instead of duplicating the list in `pyproject.toml`.

---

## 8. Separate direct dependencies from the lock file

### Direct dependencies

`requirements.txt` records intentional choices with compatible ranges:

```text
pydantic>=2,<3
pydantic-settings>=2,<3
python-dotenv>=1,<2
redis>=7,<9
sqlalchemy>=2,<3
psycopg2-binary>=2.9,<3
alembic>=1,<2
```

These are direct dependencies because application code uses them or the phase has an
explicit requirement for them.

### Transitive dependencies

A direct dependency can install other packages. For example:

```text
pydantic
    -> pydantic-core
    -> annotated-types
    -> typing-extensions
```

The application did not choose these packages directly, but exact versions still affect
reproducibility.

### Lock file

Generate exact installed versions:

```bash
python -m pip freeze --exclude-editable > requirements.lock.txt
```

The lock file is generated output. Do not edit it manually. Regenerate it after changing
direct dependencies.

Check the installed dependency graph:

```bash
python -m pip check
```

The current lock was generated on macOS with Python 3.11. Platform-specific packages may
require a separately validated lock strategy when Linux CI and production images are
introduced. For Phase 0, this file reproduces the tested local environment.

---

## 9. Understand linting, formatting, and testing

These tools answer different questions:

| Tool | Question |
|---|---|
| `ruff check` | Does static analysis find mistakes or rule violations? |
| `ruff format` | Is the source formatted consistently? |
| pytest | Does executed behavior meet the test expectations? |

### Ruff lint rules

The configured rules cover:

- important pycodestyle errors;
- undefined names and unused imports;
- import ordering;
- bug-prone Python patterns;
- modernization for Python 3.11.

Run linting:

```bash
python -m ruff check src tests
```

Preview or apply safe fixes:

```bash
python -m ruff check src tests --fix --diff
python -m ruff check src tests --fix
```

Run formatting:

```bash
python -m ruff format src tests
python -m ruff format --check src tests
```

The first command changes files. The second only verifies formatting and is appropriate
for CI.

### Why use `python -m`?

This command:

```bash
pytest
```

can resolve to a globally installed executable cached by the shell. This command:

```bash
python -m pytest
```

uses pytest installed for that exact Python interpreter. The same pattern applies to
pip and Ruff.

---

## 10. Test levels

The project registers three pytest markers:

```text
unit
integration
e2e
```

### Unit tests

Unit tests:

- do not require Docker or the internet;
- are fast and deterministic;
- test one behavior in isolation.

Run them:

```bash
python -m pytest -m unit -v
```

The initial smoke test proves the package is importable:

```python
@pytest.mark.unit
def test_package_is_importable() -> None:
    assert bluesky_trust_safety.__name__ == "bluesky_trust_safety"
```

This small test verifies package discovery, editable installation, pytest configuration,
and the active Python environment.

### Integration tests

Integration tests use real external components. Current tests verify:

- Python can connect to Redis and receive `PONG`;
- SQLAlchemy and psycopg2 can connect to PostgreSQL and execute `SELECT 1`.

Run them while containers are healthy:

```bash
python -m pytest -m integration -v
```

They are expected to fail if required infrastructure is unavailable. Silent skipping
would hide a real dependency failure.

### End-to-end tests

The `e2e` marker is registered now, but end-to-end tests arrive when the application has
a full workflow. A future example is:

```text
Jetstream fixture -> Redis -> worker -> model -> PostgreSQL prediction
```

---

## 11. Validate configuration with Pydantic Settings

Configuration is defined in:

```text
src/bluesky_trust_safety/common/settings.py
```

The `Settings` class reads `.env` and environment variables, validates types and allowed
values, requires infrastructure URLs, masks secret values, and prevents mutation.

### Prefix

```python
env_prefix="BTS_"
```

The field `database_url` maps to `BTS_DATABASE_URL`. Namespacing reduces collisions with
unrelated environment variables.

### Allowed values

```python
environment: Literal["local", "test", "staging", "production"]
```

An unsupported value fails at application startup instead of causing ambiguous behavior
later.

### Required settings

`redis_url` and `database_url` do not have defaults. Missing infrastructure configuration
raises a Pydantic `ValidationError`.

### Secret redaction

```python
database_url: SecretStr
```

`SecretStr` reduces accidental exposure through `repr()` and logs. It does not encrypt
the value. Application code retrieves the raw value only at the client boundary:

```python
settings.database_url.get_secret_value()
```

### Immutability

```python
frozen=True
```

Settings cannot be modified after construction. Runtime configuration changes should be
explicit, not silent mutations deep inside a service.

### Caching

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Application components can share one validated settings object instead of repeatedly
parsing the environment.

### Deterministic settings tests

Unit tests pass `_env_file=None` so they do not depend on the developer's real `.env`.
Pytest's `monkeypatch` temporarily sets or removes environment variables and restores the
original process environment afterward.

The settings tests prove:

- environment variables load correctly;
- defaults are applied;
- required fields fail when absent;
- invalid environment names fail;
- secret values do not appear in object representations.

---

## 12. Use `.env.example` as a safe contract

`.env.example` documents variable names and non-secret example values:

```dotenv
BTS_ENVIRONMENT=local
BTS_LOG_LEVEL=INFO
BTS_REDIS_URL=redis://localhost:6379/0
BTS_DATABASE_URL=postgresql+psycopg2://bluesky:replace-me@localhost:5433/bluesky_trust_safety
POSTGRES_USER=bluesky
POSTGRES_PASSWORD=replace-me
POSTGRES_DB=bluesky_trust_safety
```

Create the private local file:

```bash
cp .env.example .env
```

Replace placeholder secrets inside `.env`. The PostgreSQL password in
`BTS_DATABASE_URL` must match `POSTGRES_PASSWORD`.

Do not paste `.env` into issue trackers, chat messages, logs, or documentation.

Verify `.env.example` ends with a newline:

```bash
tail -c 1 .env.example | od -An -t x1
```

Expected hexadecimal byte:

```text
0a
```

---

## 13. Run infrastructure with Docker Compose

The local infrastructure file is:

```text
docker/docker-compose.yml
```

It defines:

- Redis 7.4;
- PostgreSQL 16;
- localhost-only port bindings;
- persistent named volumes;
- health checks;
- restart behavior.

### Redis durability

Redis is started with:

```text
--appendonly yes
--appendfsync everysec
```

Append-only-file persistence improves recovery across restarts. An every-second fsync
policy is a durability/performance tradeoff and is not an absolute no-data-loss
guarantee.

### Local-only ports

```yaml
ports:
  - "127.0.0.1:6379:6379"
```

Binding to `127.0.0.1` avoids exposing development services to other machines on the
network.

PostgreSQL maps host port 5433 to container port 5432:

```text
127.0.0.1:5433 -> container:5432
```

This avoids conflicts with a PostgreSQL server already using host port 5432.

### Required variables

Compose syntax such as:

```yaml
POSTGRES_USER: ${POSTGRES_USER:?POSTGRES_USER is required}
```

fails before startup with an actionable message if the variable is missing.

### Health checks

A running container is not necessarily a ready service. Redis health requires a
successful `PING`. PostgreSQL health requires `pg_isready` to accept a database
connection.

In the Compose health check, `$$` escapes Make/Compose host expansion so the variable is
expanded inside the container.

### Named volumes

```text
redis_data
postgres_data
```

persist service data when containers are replaced.

`docker compose down` removes containers and the project network but preserves named
volumes. `docker compose down -v` deletes those volumes and should not be used casually.

### Validate and start

```bash
docker compose --env-file .env -f docker/docker-compose.yml config --quiet
docker compose --env-file .env -f docker/docker-compose.yml config --services
docker compose --env-file .env -f docker/docker-compose.yml up -d --wait --wait-timeout 60
```

Avoid printing the full resolved Compose configuration in shared output because it may
contain the PostgreSQL password.

---

## 14. Test real infrastructure from Python

The integration tests use the same `Settings` class as the application.

### Redis connection lifecycle

```python
redis_client = Redis.from_url(
    settings.redis_url.get_secret_value(),
    decode_responses=True,
)
```

The test calls `ping()` and closes the client in `finally`, ensuring cleanup even if the
assertion fails.

### PostgreSQL connection lifecycle

```python
engine = create_engine(
    settings.database_url.get_secret_value(),
    pool_pre_ping=True,
)
```

`pool_pre_ping=True` checks a pooled connection before reuse, which helps detect stale
connections after a database restart.

The test executes:

```sql
SELECT 1;
```

and disposes the engine afterward. The test proves the complete local client path:

```text
Settings -> SQLAlchemy -> psycopg2 -> PostgreSQL
```

---

## 15. Standardize commands with Make

The Makefile prevents documentation, developers, and CI from inventing different command
variants.

Examples:

```bash
make check
make integration
make health
make down
```

### Interpreter detection

```makefile
VENV_DIR ?= venv
PYTHON := $(if $(wildcard $(VENV_DIR)/bin/python),$(VENV_DIR)/bin/python,python)
```

Make uses `venv/bin/python` when the local environment exists, even if it is not
activated. Otherwise it falls back to `python`.

This fixed an important portability issue: the original Makefile used `python`, which
resolved to global pyenv Python when run from a fresh shell. Ruff was installed only in
the virtual environment, so `make check` failed. Developer commands must not rely on a
prompt decoration such as `(venv)`.

### Compose command reuse

```makefile
COMPOSE := docker compose --env-file .env -f docker/docker-compose.yml
```

This centralizes the Compose path and environment file.

### Phony targets

```makefile
.PHONY: check unit integration up down
```

These names represent commands, not output files. Without `.PHONY`, a file named `unit`
could cause Make to skip the unit-test recipe.

### Dependency between targets

```makefile
integration: up
```

Infrastructure must become healthy before integration tests begin.

### Fast quality gate

```makefile
check: lint format-check unit pip-check
```

The fast gate does not require Docker. Integration tests remain a separate explicit
gate.

### Dollar signs inside recipes

Make interprets `$`, so container-side environment variables require `$$`:

```makefile
sh -c 'pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'
```

---

## 16. Final Phase 0 verification

The final gate was deliberately run after `deactivate` to prove Makefile portability.

### Fast checks

```bash
deactivate
make check
make smoke
```

Verified results:

- Ruff lint passed;
- 24 Python files were formatted;
- five unit tests passed;
- two integration tests were deselected from the unit run;
- pip reported no broken requirements;
- configuration loaded as `environment=local`.

### Infrastructure checks

```bash
make integration
make health
make down
```

Verified results:

- Redis and PostgreSQL became healthy;
- two integration tests passed;
- Redis returned `PONG`;
- PostgreSQL reported `accepting connections`;
- containers and network were removed;
- named volumes were preserved.

### Secret-safety check

```bash
git status --short
```

`.env` did not appear. `.env.example` did appear and is safe to commit after verifying
that it contains placeholders only.

---

## 17. Problems encountered and lessons learned

### Virtual environment name did not match `.gitignore`

The environment was created as `venv/`, while the initial ignore pattern covered only
`.venv/`. Git began reporting the environment.

Lesson: verify ignored behavior with `git status` and `git check-ignore`; do not assume a
pattern matches.

### The wrong pytest executable ran

The shell resolved a global pyenv pytest executable, so the editable package installed in
the virtual environment could not be imported.

Lesson: use `python -m pytest`, `python -m pip`, and `python -m ruff`, or explicitly use
the virtual-environment interpreter.

### Ruff reported visually identical formatting changes

The files lacked final newline characters. The visible source looked identical, but the
byte-level file format differed.

Lesson: formatter output can represent invisible whitespace; use `ruff format --diff` or
`xxd` when a diff looks identical.

### Ruff `I001` appeared although imports looked ordered

There was an extra blank line after the import block.

Lesson: import organization includes section spacing, not only alphabetical order.

### `.env.example` was accidentally duplicated

The second copy began on the same line as the final value because the first copy lacked a
newline.

Lesson: inspect complete templates, count repeated headings, and verify the final byte
when concatenation looks suspicious.

### Docker CLI existed but the daemon was unavailable

`docker --version` worked while `docker info` failed.

Lesson: client installation and daemon readiness are separate checks.

### Make worked only in an activated environment

The initial Makefile depended on shell state.

Lesson: shared project commands should locate their required interpreter explicitly and
work from a fresh terminal.

---

## 18. Reusing this phase in another project

For a new Python MLOps system, preserve the pattern but customize:

- repository and package names;
- Python version based on dependency compatibility;
- infrastructure services;
- configuration prefix;
- direct dependency list;
- database ports and names;
- test markers relevant to the architecture.

Do not blindly copy:

- old lock files into another operating system;
- `.env` or real passwords;
- service versions without checking project compatibility;
- unused directories or dependencies;
- PostgreSQL or Redis configuration when the new system does not require them.

The reusable sequence is:

```text
runtime pin
    -> virtual environment
    -> Git safety
    -> package layout
    -> packaging/tool configuration
    -> direct dependencies
    -> locked environment
    -> validated settings
    -> unit tests
    -> containerized dependencies
    -> health checks
    -> integration tests
    -> shared Make commands
    -> fresh-shell exit gate
    -> commit
```

---

## 19. Phase 0 definition of done

Phase 0 is complete only when all statements are true:

- [x] Python version is pinned.
- [x] Virtual environment is isolated and ignored.
- [x] Package imports through the `src` layout.
- [x] Direct dependencies are declared.
- [x] Exact installed dependencies are locked.
- [x] `pip check` reports no broken requirements.
- [x] Secrets are excluded from Git.
- [x] A safe `.env.example` exists.
- [x] Settings validate required fields and allowed values.
- [x] Secret representations are redacted.
- [x] Unit tests run without Docker.
- [x] Redis and PostgreSQL have persistent volumes and health checks.
- [x] Integration tests connect to real infrastructure.
- [x] Ruff lint and formatting checks pass.
- [x] Make commands work without activating the virtual environment.
- [x] Services shut down without deleting named volumes.
- [x] Phase documentation and reusable checklist exist.

Phase 1 may begin only after the Phase 0 files and documentation are reviewed and
committed.
