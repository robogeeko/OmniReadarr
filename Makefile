.PHONY: help test lint run

help:  ## Show this help message
	@echo "Available commands:"
	@echo "  make test  - Run unit tests"
	@echo "  make lint  - Run linter"
	@echo "  make run   - Start Docker containers and show logs"

test:  ## Run unit tests
	uv run pytest

lint:  ## Run linter
	uv run ruff check .

run:  ## Start Docker containers and show logs
	docker compose up --build
