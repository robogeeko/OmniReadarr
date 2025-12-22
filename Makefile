.PHONY: help test lint run makemigrations migrate

help:  ## Show this help message
	@echo "Available commands:"
	@echo "  make test           - Run unit tests"
	@echo "  make lint           - Run linter"
	@echo "  make run            - Start Docker containers and show logs"
	@echo "  make makemigrations - Create database migrations"
	@echo "  make migrate        - Apply database migrations"

test:  ## Run unit tests
	uv run pytest

lint:  ## Run linter
	uv run ruff check .

run:  ## Start Docker containers and show logs
	docker compose up --build

makemigrations:  ## Create database migrations
	uv run python manage.py makemigrations

migrate:  ## Apply database migrations
	uv run python manage.py migrate
