install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

up:
	docker-compose -f docker/docker-compose.yml --env-file .env up -d

down:
	docker-compose -f docker/docker-compose.yml --env-file .env down