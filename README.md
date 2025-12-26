# OmniReadarr

Universal media management system for books and audiobooks. OmniReadarr automates the process of searching for media, downloading from Usenet/torrent indexers, and organizing files into a structured library.

## Features

- **Metadata Search**: Search for books and audiobooks using metadata providers (OpenLibrary)
- **Indexer Integration**: Unified search across multiple Usenet/torrent indexers via Prowlarr
- **Download Management**: Automatic download initiation and monitoring via SABnzbd
- **Post-Processing**: Convert ebooks to EPUB format and organize files into library structure
- **Library Organization**: Automatic file organization with metadata generation and cover art
- **Blacklist Management**: Prevent re-downloading failed or incorrect releases
- **REST API**: Full API for integration with frontend applications

## Tech Stack

- **Python 3.12+** - Core language
- **Django 6.x** - Web framework
- **PostgreSQL 16** - Database
- **Dramatiq** - Task queue with RabbitMQ
- **UV** - Fast Python package manager
- **Docker** - Containerization

## Prerequisites

Before setting up OmniReadarr, you need to have the following services running:

### 1. SABnzbd

SABnzbd is a Usenet binary downloader that handles the actual file downloads.

**Installation**: Follow the [SABnzbd installation guide](https://sabnzbd.org/wiki/installation/installation-guide)

**Configuration**:
- Enable the API in SABnzbd settings
- Note your API key (Settings → General → API Key)
- Note the host and port (default: `localhost:8080`)
- Configure a category for books (e.g., "books")
- Set up a completed downloads folder

### 2. Prowlarr

Prowlarr manages indexer configurations and provides a unified search API.

**Installation**: Follow the [Prowlarr installation guide](https://wiki.servarr.com/prowlarr/installation)

**Configuration**:
- Enable the API in Prowlarr settings
- Note your API key (Settings → General → API Key)
- Note the host and port (default: `localhost:9696`)
- Add and configure indexers for books/audiobooks:
  - Books: Category 7020
  - Audiobooks: Category 3030
- Test indexer connections

### 3. Calibre (Optional but Recommended)

Calibre provides the `ebook-convert` tool for converting ebooks to EPUB format.

**Installation**: Follow the [Calibre installation guide](https://calibre-ebook.com/download)

**Note**: Ensure `ebook-convert` is in your PATH, or note the full path for configuration.

## Getting Started

### Step 1: Clone and Setup

```bash
git clone <repository-url>
cd OmniReadarr
```

### Step 2: Start Services

#### Option A: Using Docker (Recommended)

Start all services including PostgreSQL and RabbitMQ:

```bash
make run
```

This will:
- Start PostgreSQL database
- Start RabbitMQ message broker
- Start Django web server
- Start Dramatiq worker

#### Option B: Local Development

Start only dependencies:

```bash
make deps
```

In separate terminals:

```bash
# Terminal 1: Django development server
make live

# Terminal 2: Dramatiq worker
make worker
```

### Step 3: Run Migrations

If using Docker:

```bash
docker compose exec web python manage.py migrate
```

If running locally:

```bash
make migrate
```

### Step 4: Create Superuser

Create an admin user to access the Django admin console:

If using Docker:

```bash
docker compose exec web python manage.py createsuperuser
```

If running locally:

```bash
make createsuperuser
```

Follow the prompts to create your admin account.

### Step 5: Access Admin Console

Navigate to: http://localhost:8000/admin

Log in with your superuser credentials.

### Step 6: Configure SABnzbd

1. In the admin console, navigate to **Downloaders** → **Download Client Configurations**
2. Click **Add Download Client Configuration**
3. Fill in the form:
   - **Name**: A descriptive name (e.g., "My SABnzbd")
   - **Client Type**: Select "SABnzbd"
   - **Host**: Your SABnzbd host (e.g., `sabnzbd` if in Docker, `localhost` if local)
   - **Port**: Your SABnzbd port (default: `8080`)
   - **Use SSL**: Check if SABnzbd uses HTTPS
   - **API Key**: Your SABnzbd API key
   - **Enabled**: Check this box
   - **Priority**: Set to `0` (lower numbers = higher priority)
4. Click **Save**
5. Click **Test Connection** to verify the configuration works

### Step 7: Configure Prowlarr

1. In the admin console, navigate to **Indexers** → **Prowlarr Configurations**
2. Click **Add Prowlarr Configuration**
3. Fill in the form:
   - **Name**: A descriptive name (e.g., "My Prowlarr")
   - **Host**: Your Prowlarr host (e.g., `prowlarr` if in Docker, `localhost` if local)
   - **Port**: Your Prowlarr port (default: `9696`)
   - **Use SSL**: Check if Prowlarr uses HTTPS
   - **Base Path**: Leave empty unless Prowlarr is behind a reverse proxy
   - **API Key**: Your Prowlarr API key
   - **Enabled**: Check this box
   - **Priority**: Set to `0`
   - **Timeout**: Default `30` seconds
4. Click **Save**
5. Click **Test Connection** to verify the configuration works

**Important**: Only one Prowlarr configuration should be enabled at a time.

### Step 8: Configure OpenLibrary Search Provider

1. In the admin console, navigate to **Search** → **Search Providers**
2. Click **Add Search Provider**
3. Fill in the form:
   - **Name**: "OpenLibrary" (or any name)
   - **Provider Type**: Select "OpenLibrary"
   - **Base URL**: `https://openlibrary.org` (pre-filled)
   - **API Key**: Leave empty (OpenLibrary doesn't require an API key)
   - **Enabled**: Check this box
   - **Priority**: Set to `0`
   - **Rate Limit Per Minute**: `60` (default)
   - **Supports Media Types**: Select `book` and `audiobook`
4. Click **Save**
5. Click **Test Connection** to verify it works
6. Optionally click **Test Search** to verify search functionality

### Step 9: Configure Processing Settings

1. In the admin console, navigate to **Core** → **Processing Configurations**
2. Click **Add Processing Configuration**
3. Fill in the form:
   - **Name**: "Default Configuration" (or any name)
   - **Completed Downloads Path**: Path where SABnzbd saves completed downloads
     - Example: `/downloads/complete` (Docker volume)
     - Example: `/Users/username/downloads/complete` (local)
   - **Library Base Path**: Path where organized files should be stored
     - Example: `/library` (Docker volume)
     - Example: `/Users/username/library` (local)
   - **Calibre Ebook Convert Path**: Path to `ebook-convert` command
     - If Calibre is in PATH: `ebook-convert`
     - Full path example: `/usr/bin/ebook-convert`
     - Docker example: `/usr/bin/ebook-convert` (if Calibre is installed in container)
   - **Enabled**: Check this box
4. Click **Save**

**Important**: 
- Ensure the paths are accessible from the Docker container (if using Docker)
- The completed downloads path should match your SABnzbd configuration
- Only one ProcessingConfiguration should be enabled at a time

### Step 10: Verify Configuration

1. **SABnzbd**: Test connection button should show success
2. **Prowlarr**: Test connection button should show success
3. **OpenLibrary**: Test connection and test search should work
4. **Processing**: Verify paths exist and are accessible

## Usage

### Basic Workflow

1. **Search for Media**: 
   - Navigate to `/search/` in your browser
   - Select media type (book or audiobook)
   - Select search provider (OpenLibrary)
   - Enter title and/or author
   - Click search

2. **Add to Want List**:
   - Review search results
   - Click "Add to Want List" on desired item
   - Media is added with status "WANTED"

3. **Search Indexers**:
   - Navigate to media detail page
   - Click "Search Indexers"
   - Review available downloads from Prowlarr

4. **Initiate Download**:
   - Select a download result
   - Click "Download"
   - Download is sent to SABnzbd
   - Status changes to "DOWNLOADING"

5. **Monitor Download**:
   - View download progress on media detail page
   - Status updates automatically when polled
   - When complete, status changes to "DOWNLOADED"

6. **Convert to EPUB** (optional):
   - On media detail page, click "Convert to EPUB"
   - File is converted using Calibre
   - Post-processed file path is updated

7. **Organize to Library**:
   - Click "Organize to Library"
   - File is copied to library directory structure
   - OPF metadata file is generated
   - Cover art is downloaded (if available)
   - Media library_path is updated

### API Usage

See `BACKEND_USER_FLOWS.md` for detailed API endpoint documentation.

Key endpoints:
- `POST /api/media/wanted/` - Add media to want list
- `POST /api/downloads/search/<media_id>/` - Search indexers
- `POST /api/downloads/initiate/` - Start download
- `GET /api/downloads/attempt/<attempt_id>/status/` - Get download status
- `POST /api/processing/convert/<attempt_id>/` - Convert to EPUB
- `POST /api/processing/organize/<attempt_id>/` - Organize to library

## Development

### Project Structure

```
OmniReadarr/
├── core/                    # Core models and utilities
│   ├── models.py            # Base Media model
│   └── models_processing.py # ProcessingConfiguration
├── media/                   # Media models (Book, Audiobook)
│   ├── models.py
│   ├── api.py              # Media API endpoints
│   └── views.py            # Media views
├── search/                  # Metadata search providers
│   ├── models.py            # SearchProvider model
│   ├── providers/           # Provider implementations
│   │   ├── base.py          # BaseProvider abstract class
│   │   ├── openlibrary.py   # OpenLibrary provider
│   │   └── registry.py     # Provider registry
│   └── views.py            # Search views
├── indexers/                # Prowlarr integration
│   ├── models.py            # ProwlarrConfiguration
│   └── prowlarr/            # Prowlarr client
│       ├── client.py        # ProwlarrClient
│       └── results.py       # SearchResult dataclass
├── downloaders/             # Download management
│   ├── models.py            # DownloadAttempt, DownloadBlacklist
│   ├── api.py              # Download API endpoints
│   ├── services/            # Business logic
│   │   ├── download.py     # DownloadService
│   │   └── search.py       # SearchService
│   └── clients/            # Download client implementations
│       ├── sabnzbd.py      # SABnzbdClient
│       └── results.py      # JobStatus, QueueItem
├── processing/              # Post-processing pipeline
│   ├── api.py              # Processing API endpoints
│   ├── services/            # Post-processing orchestration
│   │   └── post_process.py
│   └── utils/              # Processing utilities
│       ├── ebook_converter.py
│       ├── file_discovery.py
│       ├── file_organizer.py
│       ├── metadata_generator.py
│       └── cover_downloader.py
├── omnireadarr/            # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── tasks.py            # Dramatiq tasks
├── tests/                  # Test suite
├── docker-compose.yml      # Docker services
├── Dockerfile              # Web application container
├── Dockerfile.worker        # Worker container
└── Makefile               # Convenience commands
```

### Running Tests

```bash
make test
```

### Linting

```bash
make lint
```

### Type Checking

```bash
uv run ty check
```

### Code Formatting

```bash
# Check formatting
make lint

# Auto-fix formatting
uv run ruff format .
```

### Database Migrations

```bash
# Create migrations
make makemigrations

# Apply migrations
make migrate
```

### Makefile Commands

- `make test` - Run unit tests
- `make lint` - Run linter and type checker
- `make run` - Start Docker containers
- `make deps` - Start PostgreSQL and RabbitMQ only
- `make live` - Start Django dev server
- `make worker` - Start Dramatiq worker
- `make makemigrations` - Create database migrations
- `make migrate` - Apply database migrations
- `make createsuperuser` - Create Django superuser
- `make help` - Show all available commands

## Configuration Reference

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://omnireadarr:omnireadarr_dev@localhost:5432/omnireadarr

# RabbitMQ
RABBITMQ_URL=amqp://omnireadarr:omnireadarr_dev@localhost:5672/%2F

# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Docker Volumes

When using Docker, ensure volumes are mounted correctly:

```yaml
volumes:
  - /path/to/downloads/complete:/downloads/complete
  - /path/to/library:/library
```

## Troubleshooting

### SABnzbd Connection Failed

- Verify SABnzbd is running and accessible
- Check API key is correct
- Verify host/port settings
- Check firewall rules if accessing remotely

### Prowlarr Connection Failed

- Verify Prowlarr is running and accessible
- Check API key is correct
- Verify host/port/base_path settings
- Ensure at least one indexer is configured

### File Discovery Fails

- Verify completed downloads path exists
- Check file permissions
- Ensure SABnzbd is saving files to the configured path
- Check Docker volume mounts if using Docker

### Conversion Fails

- Verify Calibre is installed
- Check `ebook-convert` path is correct
- Ensure input file format is supported
- Check file permissions

### Library Organization Fails

- Verify library base path exists
- Check write permissions
- Ensure sufficient disk space
- Verify paths are accessible from container (if using Docker)

## Documentation

- [Backend User Flows](BACKEND_USER_FLOWS.md) - Detailed documentation of backend workflows and API endpoints

## Contributing

1. Follow Django and Python best practices
2. Type hints are required (checked by `ty`)
3. Run `make lint` before committing
4. Write tests for new features
5. Update documentation as needed
6. Use conventional commit messages

## License

MIT
