# OmniReadarr

Universal media management application built with Django, Dramatiq, and PostgreSQL.

## Tech Stack

- **Python 3.12+**
- **UV** - Package manager
- **Django 6.x** - Web framework
- **Dramatiq** - Task queue with RabbitMQ
- **PostgreSQL** - Database
- **Docker** - Containerization

## Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.12+
- UV package manager

### Quick Start

1. Start services with Docker:
   ```bash
   make run
   ```

3. Access the application:
   - Web: http://localhost:8000
   - Admin: http://localhost:8000/admin
   - RabbitMQ Management: http://localhost:15672 (guest/guest)

### Local Development

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Start PostgreSQL and RabbitMQ:
   ```bash
   docker-compose up postgres rabbitmq
   ```

3. Run migrations:
   ```bash
   uv run python manage.py migrate
   ```

4. Create superuser:
   ```bash
   uv run python manage.py createsuperuser
   ```

5. Run development server:
   ```bash
   uv run python manage.py runserver
   ```

6. Run Dramatiq worker (in another terminal):
   ```bash
   uv run python manage.py rundramatiq
   ```

## Makefile Commands

The project includes a Makefile with convenient commands:

- `make test` - Run unit tests
- `make lint` - Run linter
- `make run` - Start Docker containers and show logs
- `make help` - Show all available commands

## Testing

```bash
make test
```

## Type Checking

```bash
uv run ty check
```

## Code Formatting

Linting (checking):
```bash
make lint
```

Formatting (auto-fix):
```bash
uv run ruff format .
```

## Project Structure

```
OmniReadarr/
├── omnireadarr/          # Django project
│   ├── settings.py       # Django settings
│   ├── urls.py          # URL routing
│   ├── tasks.py         # Dramatiq tasks
│   └── wsgi.py          # WSGI application
├── tests/               # Test suite
├── docker-compose.yml   # Docker services
├── Dockerfile           # Web application
├── Dockerfile.worker    # Dramatiq worker
└── manage.py           # Django management
```

## License

MIT
