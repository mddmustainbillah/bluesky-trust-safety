.DEFAULT_GOAL := help

VENV_DIR ?= venv
PYTHON := $(if $(wildcard $(VENV_DIR)/bin/python),$(VENV_DIR)/bin/python,python)
COMPOSE := docker compose --env-file .env -f docker/docker-compose.yml

.PHONY: help install install-locked lock format format-check lint
.PHONY: unit integration test test-all pip-check check
.PHONY: up down ps logs health smoke

help:
	@echo "Development commands:"
	@echo "  make install         Install project and development dependencies"
	@echo "  make install-locked  Install exact versions from the lock file"
	@echo "  make lock            Regenerate the dependency lock file"
	@echo "  make format          Format Python code"
	@echo "  make lint            Run Ruff lint checks"
	@echo "  make unit            Run unit tests without Docker"
	@echo "  make integration     Start dependencies and run integration tests"
	@echo "  make test-all        Run unit and integration tests"
	@echo "  make check           Run the fast local quality gate"
	@echo "  make up              Start Redis and PostgreSQL"
	@echo "  make down            Stop containers but preserve data"
	@echo "  make health          Check Redis and PostgreSQL health"
	@echo "  make logs            Show recent container logs"
	@echo "  make smoke           Run a quick smoke test to verify configuration"
	@echo "  make pip-check       Check for broken dependencies"
	@echo "  make ps              Show running containers"

install:
	$(PYTHON) -m pip install -e ".[dev]"

install-locked:
	$(PYTHON) -m pip install -r requirements.lock.txt
	$(PYTHON) -m pip install -e . --no-deps

lock:
	$(PYTHON) -m pip freeze --exclude-editable > requirements.lock.txt

format:
	$(PYTHON) -m ruff format src tests

format-check:
	$(PYTHON) -m ruff format --check src tests

lint:
	$(PYTHON) -m ruff check src tests

unit:
	$(PYTHON) -m pytest -m unit -v

up:
	$(COMPOSE) up -d --wait --wait-timeout 60

integration: up
	$(PYTHON) -m pytest -m integration -v

test: unit

test-all: unit integration

pip-check:
	$(PYTHON) -m pip check

check: lint format-check unit pip-check

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs --tail=100

health: up
	$(COMPOSE) exec -T redis redis-cli ping
	$(COMPOSE) exec -T postgres sh -c 'pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

smoke:
	$(PYTHON) -c 'from bluesky_trust_safety.common.settings import Settings; settings = Settings(); print(f"configuration ok: environment={settings.environment}")'