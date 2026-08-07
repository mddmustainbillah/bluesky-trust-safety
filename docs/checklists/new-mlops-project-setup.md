# New MLOps Project: Phase 0 Setup Checklist

Use this checklist when starting a new Python MLOps repository. It is intentionally
generic. Replace names, versions, services, and ports according to the new project's
requirements.

## 1. Define the project contract

- [ ] Write the problem, users, scope, and non-goals.
- [ ] Define the first vertical slice.
- [ ] Separate core tools from optional future tools.
- [ ] Define what Phase 0 must prove before application work begins.
- [ ] Choose the supported operating systems and Python version.

Questions:

- What is the smallest useful end-to-end workflow?
- Which services are genuinely required now?
- Which tools are being added only to make the architecture look advanced?

## 2. Initialize Git safely

```bash
git init
git status --short --branch
```

- [ ] Create `.gitignore` before generating a virtual environment or data.
- [ ] Ignore virtual environments.
- [ ] Ignore `.env` and secret files.
- [ ] Explicitly allow `.env.example`.
- [ ] Ignore Python caches and build metadata.
- [ ] Ignore test, lint, notebook, data, model, and report artifacts as appropriate.
- [ ] Verify important paths with `git check-ignore -v`.
- [ ] Confirm no secret or generated environment appears in `git status`.

Never commit:

- real credentials;
- access tokens;
- cloud key files;
- production connection strings;
- a local virtual environment;
- raw private data.

## 3. Pin and isolate Python

```bash
pyenv install <python-version>
pyenv local <python-version>
python -m venv venv
source venv/bin/activate
python --version
which python
```

- [ ] `.python-version` contains the intended runtime.
- [ ] `which python` points inside the repository environment.
- [ ] The environment directory is ignored by Git.
- [ ] The supported version range is also recorded in `pyproject.toml`.

## 4. Create a namespaced package

Recommended pattern:

```text
src/<project_package>/
├── __init__.py
├── common/
├── contracts/
├── ingestion/
├── features/
├── training/
├── serving/
├── store/
├── monitoring/
└── retraining/
```

- [ ] Repository/distribution name may use hyphens.
- [ ] Python import package uses underscores.
- [ ] Avoid generic top-level imports such as `common` or `store`.
- [ ] Create only directories justified by the architecture.
- [ ] Keep production logic under `src/`, not notebooks or scripts.

## 5. Configure `pyproject.toml`

- [ ] Select a build backend.
- [ ] Add package name, version, description, and Python range.
- [ ] Configure package discovery under `src`.
- [ ] Define development dependencies.
- [ ] Configure pytest test paths and markers.
- [ ] Configure Ruff Python target and lint rules.
- [ ] Install the project in editable mode.

```bash
python -m pip install -e ".[dev]"
python -m pip show <distribution-name>
```

## 6. Define dependency policy

- [ ] Store intentional direct runtime dependencies in one human-maintained source.
- [ ] Add libraries only when a current phase needs them.
- [ ] Use compatible version ranges for direct dependencies.
- [ ] Generate an exact lock for the tested environment.
- [ ] Never manually edit the generated lock.
- [ ] Run dependency compatibility checks.
- [ ] Document platform limitations of the lock strategy.

```bash
python -m pip install -e ".[dev]"
python -m pip check
python -m pip freeze --exclude-editable > requirements.lock.txt
```

Before production/CI, verify that the chosen lock strategy is reproducible for the target
Linux image, not only the developer workstation.

## 7. Establish test categories

- [ ] Unit tests run without external services.
- [ ] Integration tests use real local dependencies.
- [ ] End-to-end tests are reserved for full workflows.
- [ ] Markers are registered in `pyproject.toml`.
- [ ] A package-import smoke test exists.
- [ ] Tests use `python -m pytest`.

```bash
python -m pytest -m unit -v
python -m pytest -m integration -v
python -m pytest -m e2e -v
```

Do not silently skip a required integration dependency in a test that is explicitly
being run as an integration gate.

## 8. Configure code quality

- [ ] Ruff lint rules are documented.
- [ ] Formatter and lint commands are separate.
- [ ] Formatting can be checked without changing files.
- [ ] Source and tests are both checked.
- [ ] Automatic fixes are reviewed before broad application.

```bash
python -m ruff format src tests
python -m ruff format --check src tests
python -m ruff check src tests
python -m ruff check src tests --fix --diff
```

## 9. Create validated configuration

- [ ] Create `.env.example` with placeholders only.
- [ ] Copy it to an ignored `.env` for local development.
- [ ] Namespace application variables with a prefix.
- [ ] Validate types and allowed values at startup.
- [ ] Require settings that have no safe default.
- [ ] Mask secret representations.
- [ ] Keep settings immutable.
- [ ] Cache settings only when appropriate.
- [ ] Prevent unit tests from reading the developer's real `.env`.
- [ ] Test missing, invalid, default, and secret-redaction behavior.

Remember: secret-redaction types reduce accidental display; they do not encrypt values.

## 10. Containerize local dependencies

For every local service:

- [ ] Use an explicit compatible image version instead of `latest`.
- [ ] Bind development ports to `127.0.0.1` unless external access is required.
- [ ] Use named volumes for required persistence.
- [ ] Add a service-specific health check.
- [ ] Set reasonable health-check timeouts and retries.
- [ ] Require essential environment variables.
- [ ] Document durability tradeoffs.
- [ ] Avoid hardcoded secrets in Compose YAML.
- [ ] Validate configuration before startup.

```bash
docker compose --env-file .env -f docker/docker-compose.yml config --quiet
docker compose --env-file .env -f docker/docker-compose.yml up -d --wait
docker compose --env-file .env -f docker/docker-compose.yml ps
```

Distinguish:

- Docker CLI installed;
- Docker daemon reachable;
- container running;
- service healthy;
- application able to connect.

They are separate checks.

## 11. Write infrastructure integration tests

- [ ] Use the application's validated settings.
- [ ] Exercise the real Python client and driver.
- [ ] Use a minimal read-only health operation where possible.
- [ ] Close clients, connections, and pools in `finally` or context managers.
- [ ] Avoid printing connection strings or secrets on failure.
- [ ] Verify tests fail meaningfully when dependencies are unavailable.

Examples:

- Redis `PING`;
- PostgreSQL `SELECT 1`;
- object-storage list/head operation;
- MLflow tracking-server health call.

## 12. Create one developer command interface

- [ ] Add `make help` or an equivalent command runner.
- [ ] Centralize long Docker Compose commands.
- [ ] Provide install and locked-install targets.
- [ ] Provide format, lint, unit, integration, and full-test targets.
- [ ] Provide up, down, health, logs, and status targets.
- [ ] Do not delete volumes from the normal `down` command.
- [ ] Make commands locate the local Python interpreter without relying on activation.
- [ ] Mark command targets as phony.
- [ ] Keep the fast quality gate independent of Docker.

Test from a new shell:

```bash
deactivate 2>/dev/null || true
make check
make smoke
make integration
make health
make down
```

## 13. Perform the secret and repository audit

```bash
git status --short
git diff --check
git check-ignore -v .env
```

- [ ] `.env` is not staged or untracked.
- [ ] `.env.example` contains placeholders only.
- [ ] No credential appears in source, tests, documentation, or Compose files.
- [ ] No virtual environment, cache, generated package metadata, data, or model artifact
  will be committed unintentionally.
- [ ] Text files end with newline characters.
- [ ] Generated lock files are present when required.

## 14. Run the Phase 0 exit gate

- [ ] Lint passes.
- [ ] Format check passes.
- [ ] Unit tests pass without Docker.
- [ ] Dependency check passes.
- [ ] Configuration smoke test passes.
- [ ] Infrastructure becomes healthy.
- [ ] Integration tests pass.
- [ ] Health commands pass.
- [ ] Normal shutdown preserves data volumes.
- [ ] All commands work from a fresh, non-activated shell.
- [ ] Phase documentation exists.

## 15. Commit checkpoint

Review before staging:

```bash
git status --short
git diff --check
```

Stage explicit project paths rather than blindly staging secrets:

```bash
git add \
  .env.example \
  .gitignore \
  .python-version \
  Makefile \
  docker \
  docs \
  pyproject.toml \
  requirements.txt \
  requirements.lock.txt \
  src \
  tests
```

Inspect the staged change:

```bash
git diff --cached --stat
git diff --cached
```

Then commit with a phase-level message:

```bash
git commit -m "Complete Phase 0 engineering baseline"
```

Do not push until the staged diff has been reviewed and the user intends to publish the
change.

## Generic definition of done

A new MLOps repository is ready for Phase 1 when another developer can clone it, follow
documented setup commands, reproduce the environment, start healthy dependencies, run
fast and integration checks, and do so without receiving any private secret from the
original developer.
