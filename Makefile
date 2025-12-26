.PHONY: help test lint run makemigrations migrate createsuperuser collectstatic live deps worker

help:
	@echo "Available commands:"
	@echo "  make test             - Run unit tests"
	@echo "  make lint             - Run linter"
	@echo "  make run              - Start Docker containers and show logs"
	@echo "  make makemigrations   - Create database migrations"
	@echo "  make migrate         - Apply database migrations"
	@echo "  make createsuperuser - Create Django superuser"
	@echo "  make collectstatic   - Collect static files"
	@echo "  make deps             - Start PostgreSQL and RabbitMQ (foreground)"
	@echo "  make live             - Start Django dev server with auto-reload"
	@echo "  make worker           - Start Dramatiq worker"

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ty check .

run:
	docker compose up --build

makemigrations:
	uv run python manage.py makemigrations

migrate:
	uv run python manage.py migrate

createsuperuser:
	uv run python manage.py createsuperuser

createsuperuser-docker:
	docker compose exec web python manage.py createsuperuser

collectstatic:
	uv run python manage.py collectstatic --noinput

deps:
	docker compose up postgres rabbitmq

live:
	uv run python manage.py runserver

worker:
	uv run python manage.py rundramatiq
