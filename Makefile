.PHONY: help test lint run makemigrations migrate

help:
	@echo "Available commands:"
	@echo "  make test           - Run unit tests"
	@echo "  make lint           - Run linter"
	@echo "  make run            - Start Docker containers and show logs"
	@echo "  make makemigrations - Create database migrations"
	@echo "  make migrate        - Apply database migrations"

test:
	uv run pytest

lint:
	uv run ruff check .

run:
	docker compose up --build

makemigrations:
	uv run python manage.py makemigrations

migrate:
	uv run python manage.py migrate
