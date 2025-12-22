# OmniReadarr - Django Apps Architecture

## App Overview

### 1. **core/** ✅ (Exists)
**Purpose**: Shared models, utilities, and base functionality

**Responsibilities**:
- `BaseModel` - UUID primary key, timestamps
- `Media` - Abstract base model for all media types
- `MediaStatus` - Status choices enum
- Shared utilities and helpers
- Common mixins and base classes

**Models**:
- `BaseModel` (abstract)
- `Media` (abstract)

**No external dependencies** - Other apps depend on this

---

### 2. **media/** 🔄 (In Progress)
**Purpose**: Concrete media type models and media management

**Responsibilities**:
- Define concrete media models (Book, Audiobook, Manga, Comic)
- Media CRUD operations
- Media metadata management
- Media status tracking

**Models**:
- `Book` (extends Media)
- `Audiobook` (extends Media)
- `Manga` (extends Media)
- `Comic` (extends Media)

**Dependencies**: `core`

**Key Features**:
- Media type-specific fields
- Media status transitions
- Metadata storage

---

### 3. **search/** 📚
**Purpose**: Metadata search and discovery from external providers

**Responsibilities**:
- Search metadata providers (Google Books, OpenLibrary, MangaDex, ComicVine, etc.)
- Fetch and normalize metadata from different sources
- Search result ranking and deduplication
- Metadata provider authentication and rate limiting

**Models**:
- `SearchProvider` - Provider configuration
- `SearchQuery` - Search history/logging
- `MetadataCache` - Cached metadata results

**Dependencies**: `core`, `media`

**Dramatiq Tasks**:
- `search_metadata_providers(query, media_type)`
- `fetch_metadata_from_provider(provider, identifier)`
- `normalize_metadata(raw_metadata, provider)`

**External APIs**:
- Google Books API
- OpenLibrary API
- MangaDex API
- ComicVine API
- Goodreads (scraping)
- AniList API

---

### 4. **indexers/** 🔍
**Purpose**: Prowlarr integration for searching download sources

**Responsibilities**:
- Prowlarr API client
- Indexer configuration and management
- Search indexers for wanted media
- RSS feed monitoring
- Search result storage and ranking

**Models**:
- `Indexer` - Prowlarr indexer configuration
- `SearchResult` - Search results from indexers
- `RSSFeed` - RSS feed configuration
- `BlacklistedRelease` - Blacklisted releases

**Dependencies**: `core`, `media`

**Dramatiq Tasks**:
- `search_indexers(media_id)` - Search all indexers for media
- `monitor_rss_feeds()` - Periodic RSS monitoring
- `rank_search_results(media_id)` - Score and rank results
- `test_indexer_connection(indexer_id)` - Test indexer connectivity

**External APIs**:
- Prowlarr API

**Key Features**:
- Quality scoring algorithm
- Release matching logic
- Duplicate detection
- Blacklist management

---

### 5. **downloads/** ⬇️
**Purpose**: Download client integration and download management

**Responsibilities**:
- Download client API clients (qBittorrent, Transmission, SABnzbd, NZBGet)
- Download queue management
- Download progress tracking
- Download completion handling
- Failed download retry logic

**Models**:
- `DownloadClient` - Download client configuration
- `DownloadItem` - Active download tracking
- `DownloadHistory` - Download history log
- `DownloadBlacklist` - Blacklisted downloads

**Dependencies**: `core`, `media`, `indexers`

**Dramatiq Tasks**:
- `monitor_downloads()` - Periodic download status check
- `start_download(search_result_id)` - Start new download
- `import_completed_download(download_id)` - Process completed download
- `retry_failed_download(download_id)` - Retry failed download
- `cancel_download(download_id)` - Cancel active download

**External APIs**:
- qBittorrent API
- Transmission RPC
- SABnzbd API
- NZBGet API

**Key Features**:
- Multi-client support
- Download priority management
- Bandwidth management
- Automatic retry with exponential backoff

---

### 6. **processing/** ⚙️
**Purpose**: Post-processing pipeline for downloaded files

**Responsibilities**:
- File verification and validation
- Format conversion (EPUB, MOBI, AZW3, M4B, CBZ)
- Metadata extraction from files
- Cover art download and processing
- File optimization
- Series metadata file generation

**Models**:
- `ProcessingJob` - Processing job tracking
- `ConversionProfile` - Conversion settings
- `ProcessingLog` - Processing history

**Dependencies**: `core`, `media`, `downloads`

**Dramatiq Tasks**:
- `verify_download(file_path)` - Verify file integrity
- `convert_media(file_path, target_format)` - Convert file format
- `extract_metadata(file_path)` - Extract embedded metadata
- `download_cover_art(media_id)` - Fetch cover art
- `optimize_file(file_path)` - Optimize file size
- `create_series_metadata(series_name)` - Generate series.json

**Key Features**:
- Format detection
- Quality validation
- Metadata embedding
- Chapter extraction (for audiobooks)
- Reading order correction (for manga)

---

### 7. **library/** 📁
**Purpose**: Library organization and file management

**Responsibilities**:
- File organization into library structure
- Naming template application
- Duplicate detection and handling
- Library scanning
- File metadata synchronization
- Library statistics

**Models**:
- `LibraryFile` - File tracking in library
- `LibraryPath` - Library path configuration
- `NamingTemplate` - Naming template configuration
- `DuplicateGroup` - Duplicate file groups

**Dependencies**: `core`, `media`, `processing`

**Dramatiq Tasks**:
- `organize_to_library(media_id)` - Move file to library location
- `scan_library()` - Scan library for new files
- `detect_duplicates()` - Find duplicate files
- `sync_file_metadata(file_id)` - Sync file metadata
- `generate_library_stats()` - Calculate library statistics

**Key Features**:
- Configurable naming templates
- Automatic folder creation
- Duplicate detection algorithms
- File checksum verification
- Library health checks

---

### 8. **config/** ⚙️
**Purpose**: Application configuration and settings

**Responsibilities**:
- Quality profile management
- Library path configuration
- Naming template management
- Application settings
- User preferences

**Models**:
- `QualityProfile` - Quality profile configuration
- `LibraryPath` - Library path settings
- `NamingTemplate` - Naming template settings
- `ApplicationSetting` - App-wide settings

**Dependencies**: `core`

**Key Features**:
- Profile inheritance
- Template validation
- Setting validation
- Default configuration management

---

### 9. **api/** 🌐
**Purpose**: REST API endpoints

**Responsibilities**:
- REST API views and serializers
- API authentication and authorization
- API documentation
- Request/response formatting
- Rate limiting

**Dependencies**: All other apps

**Endpoints**:
- `/api/media/` - Media CRUD
- `/api/search/` - Search endpoints
- `/api/downloads/` - Download management
- `/api/library/` - Library operations
- `/api/settings/` - Configuration endpoints

**Key Features**:
- Django REST Framework
- JWT authentication
- API versioning
- OpenAPI/Swagger documentation
- Pagination and filtering

---

### 10. **tasks/** 🔄 (Optional - could be in omnireadarr/tasks.py)
**Purpose**: Dramatiq task definitions and scheduling

**Responsibilities**:
- Task definitions
- Task scheduling configuration
- Task priority management
- Task result handling

**Dependencies**: All other apps

**Tasks**:
- Search tasks
- Download tasks
- Processing tasks
- Library tasks
- Maintenance tasks

**Key Features**:
- Task prioritization
- Scheduled tasks (periodic_search_wanted, monitor_rss_feeds, etc.)
- Task retry logic
- Task result storage

---

## App Dependencies Graph

```
core (no dependencies)
  ↑
  ├── media
  ├── config
  │
  ├── search ──→ media
  │
  ├── indexers ──→ media
  │
  ├── downloads ──→ media, indexers
  │
  ├── processing ──→ media, downloads
  │
  ├── library ──→ media, processing
  │
  └── api ──→ (all apps)
```

---

## Implementation Order (Recommended)

### Phase 1: Foundation
1. ✅ **core** - Base models (done)
2. 🔄 **media** - Concrete models (in progress)
3. **config** - Configuration models

### Phase 2: Discovery & Search
4. **search** - Metadata providers
5. **indexers** - Prowlarr integration

### Phase 3: Download & Processing
6. **downloads** - Download clients
7. **processing** - Post-processing pipeline

### Phase 4: Organization & API
8. **library** - Library management
9. **api** - REST API

### Phase 5: Tasks & Scheduling
10. **tasks** - Task definitions (or keep in omnireadarr/tasks.py)

---

## Notes

- **tasks/** app is optional - tasks could live in `omnireadarr/tasks.py` or be organized by domain in each app
- **config/** could be merged into **core/** if it's simple enough
- Consider **notifications/** app if you need email/push notifications
- Consider **analytics/** app for metrics and monitoring
- Each app should have its own `admin.py`, `tests.py`, `views.py` (if needed)

