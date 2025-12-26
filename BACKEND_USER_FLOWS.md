# OmniReadarr Backend User Flow Documentation

## Table of Contents
1. [Overview](#overview)
2. [Core User Flows](#core-user-flows)
3. [Component Details](#component-details)
4. [Data Models](#data-models)
5. [API Endpoints](#api-endpoints)
6. [Areas for Improvement](#areas-for-improvement)

## Overview

OmniReadarr is a Django-based media management system for books and audiobooks. The backend handles metadata search, download management, post-processing, and library organization through a series of interconnected services.

### Architecture Components
- **Media Models**: Book and Audiobook models extending base Media
- **Search System**: Provider-based metadata search (OpenLibrary currently)
- **Indexer Integration**: Prowlarr for Usenet/torrent search
- **Download Management**: SABnzbd client integration
- **Post-Processing**: File conversion and library organization
- **Task Queue**: Dramatiq with RabbitMQ (configured)

## Core User Flows

### Flow 1: Search and Add Media to Want List

**Endpoint**: `POST /api/media/wanted/`

**Steps**:
1. User searches metadata providers via `/search/` view
2. User selects a result and calls `add_wanted_media` API
3. API validates provider, external_id, and media_type
4. Checks for existing Book/Audiobook with same provider+external_id
5. Creates new Book or Audiobook with status=WANTED
6. Stores metadata from BookMetadata object
7. Returns media_id and status

**Key Files**:
- `media/api.py` - `add_wanted_media()` function
- `search/views.py` - `search_view()` for provider search
- `search/providers/openlibrary.py` - OpenLibraryProvider implementation
- `media/models.py` - Book and Audiobook models

**Status Transition**: None → WANTED

---

### Flow 2: Search Indexers for Wanted Media

**Endpoint**: `POST /api/downloads/search/<media_id>/`

**Steps**:
1. User triggers search for a WANTED media item
2. `SearchService.search_for_media()` is called
3. Builds multiple search queries:
   - Priority 0: ISBN/ISBN13 (if available)
   - Priority 1: "Title Author"
   - Priority 2: "Author Title"
   - Priority 3: "Title" only
4. For each query, calls `ProwlarrClient.search()` with appropriate category:
   - Books: category 7020
   - Audiobooks: category 3030
5. Results are deduplicated by GUID
6. Blacklisted releases are filtered out
7. Results sorted by query priority, then indexer name, then title
8. Returns up to 50 results

**Key Files**:
- `downloaders/services/search.py` - SearchService class
- `indexers/prowlarr/client.py` - ProwlarrClient.search()
- `downloaders/models.py` - DownloadBlacklist model

**Status Transition**: None (Media status remains WANTED)

---

### Flow 3: Initiate Download

**Endpoint**: `POST /api/downloads/initiate/`

**Steps**:
1. User selects a search result and calls `initiate_download` API
2. Validates media exists (Book or Audiobook)
3. Checks for active downloads (status SENT or DOWNLOADING)
4. Gets enabled SABnzbd download client configuration
5. Creates DownloadAttempt with status=PENDING
6. Resolves download URL:
   - If localhost, replaces with "prowlarr"
   - If direct HTTP/HTTPS URL, uses directly
   - If GUID is URL, extracts GUID parameter
   - Otherwise, calls Prowlarr API to get download URL
7. Validates protocol is "usenet" (SABnzbd limitation)
8. Calls `SABnzbdClient.add_download()` with URL
9. Updates DownloadAttempt status to DOWNLOADING
10. Updates Media status to DOWNLOADING
11. Stores SABnzbd job ID (nzo_id)

**Key Files**:
- `downloaders/api.py` - `initiate_download()` function
- `downloaders/services/download.py` - DownloadService.initiate_download()
- `downloaders/clients/sabnzbd.py` - SABnzbdClient.add_download()
- `indexers/prowlarr/client.py` - ProwlarrClient.get_download_url()

**Status Transition**: WANTED → DOWNLOADING

---

### Flow 4: Monitor Download Status

**Endpoint**: `GET /api/downloads/attempt/<attempt_id>/status/`

**Steps**:
1. User polls download status
2. `DownloadService.get_download_status()` is called
3. Fetches DownloadAttempt from database
4. If download_client and download_client_download_id exist:
   - Calls `SABnzbdClient.get_job_status()` with nzo_id
   - Checks queue first, then history (up to 1000 items)
5. Updates DownloadAttempt status based on SABnzbd status:
   - "Completed" → DOWNLOADED (stores raw_file_path)
   - "Downloading"/"Queued"/"Paused" → DOWNLOADING
   - "Failed"/"Deleted" → FAILED
6. Updates Media status accordingly
7. Returns current status and progress percentage

**Key Files**:
- `downloaders/api.py` - `get_download_status()` function
- `downloaders/services/download.py` - DownloadService.get_download_status()
- `downloaders/clients/sabnzbd.py` - SABnzbdClient.get_job_status()

**Status Transition**: DOWNLOADING → DOWNLOADED (or FAILED)

---

### Flow 5: Convert to EPUB

**Endpoint**: `POST /api/processing/convert/<attempt_id>/`

**Steps**:
1. User triggers conversion for a DOWNLOADED attempt
2. `convert_to_epub_for_attempt()` is called
3. Gets ProcessingConfiguration (enabled)
4. Finds downloaded file:
   - Uses raw_file_path if exists
   - Otherwise calls `find_downloaded_file()` to search completed_downloads_path
5. If file is already EPUB, skips conversion
6. Calls `convert_to_epub()` with ebook-convert (Calibre)
7. Updates DownloadAttempt.post_processed_file_path
8. Returns success/failure

**Key Files**:
- `processing/api.py` - `convert_to_epub()` function
- `processing/services/post_process.py` - `convert_to_epub_for_attempt()`
- `processing/utils/ebook_converter.py` - `convert_to_epub()`
- `processing/utils/file_discovery.py` - `find_downloaded_file()`

**Status Transition**: None

---

### Flow 6: Organize to Library

**Endpoint**: `POST /api/processing/organize/<attempt_id>/`

**Steps**:
1. User triggers library organization
2. `organize_to_library_for_attempt()` is called
3. Gets ProcessingConfiguration
4. Determines file to organize:
   - Prefers post_processed_file_path
   - Falls back to raw_file_path
   - Otherwise searches for downloaded file
5. Gets first author from media.authors (or "Unknown Author")
6. Calls `organize_to_library()` or `organize_directory_to_library()`:
   - Creates directory: `library_base_path/Author/Title/`
   - Copies file(s) to library directory
   - Sanitizes filenames
7. Generates OPF metadata file using `generate_opf()`
8. Downloads cover art using `download_cover()` if cover_url exists
9. Updates Media.library_path and Media.cover_path
10. Updates DownloadAttempt.post_processed_file_path

**Key Files**:
- `processing/api.py` - `organize_to_library()` function
- `processing/services/post_process.py` - `organize_to_library_for_attempt()`
- `processing/utils/file_organizer.py` - File organization logic
- `processing/utils/metadata_generator.py` - `generate_opf()`
- `processing/utils/cover_downloader.py` - `download_cover()`

**Status Transition**: None (Media status remains unchanged)

---

### Flow 7: Blacklist Release

**Endpoint**: `POST /api/downloads/blacklist/`

**Steps**:
1. User blacklists a failed/bad release
2. `DownloadService.mark_as_blacklisted()` is called
3. Creates or gets DownloadBlacklist entry
4. Updates DownloadAttempt status to BLACKLISTED
5. Future searches will filter out blacklisted releases

**Key Files**:
- `downloaders/api.py` - `blacklist_release()` function
- `downloaders/services/download.py` - DownloadService.mark_as_blacklisted()
- `downloaders/services/search.py` - SearchService._filter_blacklisted()

---

### Flow 8: Delete Download Attempt

**Endpoint**: `DELETE /api/downloads/attempt/<attempt_id>/`

**Steps**:
1. User deletes a download attempt
2. `DownloadService.delete_download_attempt()` is called
3. If status is SENT or DOWNLOADING:
   - Calls SABnzbdClient.delete_job() to remove from queue
4. Deletes raw_file_path if exists
5. Deletes post_processed_file_path if exists
6. Deletes DownloadAttempt record
7. If no other active downloads exist, resets Media status to WANTED

**Key Files**:
- `downloaders/api.py` - `delete_download_attempt()` function
- `downloaders/services/download.py` - DownloadService.delete_download_attempt()

---

## Component Details

### Search Providers

**Current Implementation**: OpenLibrary only

**Provider System**:
- BaseProvider abstract class defines interface
- Registry pattern maps ProviderType to provider classes
- SearchProvider model stores configuration
- Supports multiple providers per media type

**Search Flow**:
1. User selects provider and media type
2. Provider instance created from SearchProvider model
3. Provider.search() called with query parameters
4. Results normalized to BookMetadata
5. Displayed to user for selection

**Files**:
- `search/providers/base.py` - BaseProvider abstract class
- `search/providers/openlibrary.py` - OpenLibraryProvider
- `search/providers/registry.py` - Provider registry
- `search/providers/results.py` - BookMetadata dataclass

---

### Prowlarr Integration

**Purpose**: Unified indexer management for Usenet/torrent search

**Key Features**:
- Search across multiple indexers
- Category filtering (7020 for books, 3030 for audiobooks)
- Download URL resolution (handles proxy URLs)
- Indexer capability checking

**Client Methods**:
- `search()` - Search indexers with query and category
- `get_download_url()` - Resolve download URL from GUID
- `get_indexers()` - List configured indexers
- `test_connection()` - Verify API connectivity

**Files**:
- `indexers/prowlarr/client.py` - ProwlarrClient class
- `indexers/prowlarr/results.py` - SearchResult dataclass

---

### Download Client (SABnzbd)

**Purpose**: Manage Usenet downloads

**Key Features**:
- Add downloads via URL
- Monitor queue and history
- Get job status and progress
- Delete jobs

**Client Methods**:
- `add_download()` - Add NZB URL to queue
- `get_job_status()` - Get status from queue or history
- `get_queue()` - List active downloads
- `get_history()` - List completed downloads
- `delete_job()` - Remove from queue
- `test_connection()` - Verify API connectivity

**Files**:
- `downloaders/clients/sabnzbd.py` - SABnzbdClient class
- `downloaders/clients/results.py` - JobStatus, QueueItem, HistoryItem

---

### Post-Processing Pipeline

**Components**:

1. **File Discovery** (`file_discovery.py`):
   - Searches completed_downloads_path for downloaded files
   - Matches by release_title and download_client_id
   - Handles both single files and directories
   - Supports ebook and audio file formats

2. **Ebook Conversion** (`ebook_converter.py`):
   - Uses Calibre's ebook-convert command
   - Converts various formats to EPUB
   - Handles timeouts and errors

3. **File Organization** (`file_organizer.py`):
   - Creates library directory structure: `Author/Title/`
   - Sanitizes filenames (removes invalid chars)
   - Copies files to library
   - Handles both files and directories

4. **Metadata Generation** (`metadata_generator.py`):
   - Generates OPF (Open Packaging Format) XML files
   - Includes title, authors, ISBN, description, etc.
   - Compatible with Calibre and other ebook readers

5. **Cover Download** (`cover_downloader.py`):
   - Downloads cover images from URLs
   - Saves as JPG in library directory
   - Handles HTTP errors and timeouts

**Files**:
- `processing/services/post_process.py` - Main orchestration
- `processing/utils/*.py` - Individual utilities

---

## Data Models

### Media Models

**Base Model**: `core.models.Media`
- Abstract base class
- Common fields: title, authors, series, status, etc.
- Status choices: WANTED, SEARCHING, DOWNLOADING, DOWNLOADED, POST_PROCESSED_FAILED, POST_PROCESSED_SUCCESS, ARCHIVED

**Concrete Models**:
- `media.models.Book` - Extends Media, adds ISBN, page_count, edition
- `media.models.Audiobook` - Extends Media, adds narrators, duration_seconds, bitrate, chapters

**Key Fields**:
- `provider` - Metadata provider name (e.g., "openlibrary")
- `external_id` - Provider-specific ID
- `library_path` - Final location in library
- `cover_path` - Local cover image path

---

### Download Models

**DownloadAttempt** (`downloaders.models.DownloadAttempt`):
- GenericForeignKey to Media (Book or Audiobook)
- Tracks indexer, release_title, download_url
- Status: PENDING, SENT, DOWNLOADING, DOWNLOADED, FAILED, BLACKLISTED
- Stores download_client and download_client_download_id
- Tracks raw_file_path and post_processed_file_path
- post_process_status: PENDING, PROCESSING, COMPLETED, FAILED

**DownloadBlacklist** (`downloaders.models.DownloadBlacklist`):
- Prevents re-downloading failed/bad releases
- Unique constraint on (content_type, object_id, indexer, indexer_id)
- Stores reason and reason_details

**DownloadClientConfiguration** (`downloaders.models.DownloadClientConfiguration`):
- Stores SABnzbd connection details
- Supports priority ordering
- Currently only SABNZBD client type

---

### Configuration Models

**ProwlarrConfiguration** (`indexers.models.ProwlarrConfiguration`):
- Stores Prowlarr API connection details
- Supports SSL, base_path, timeout
- Priority ordering for multiple instances

**ProcessingConfiguration** (`core.models_processing.ProcessingConfiguration`):
- Stores post-processing settings
- completed_downloads_path - Where SABnzbd saves files
- library_base_path - Where to organize files
- calibre_ebook_convert_path - Path to ebook-convert command

**SearchProvider** (`search.models.SearchProvider`):
- Stores metadata provider configuration
- provider_type, api_key, base_url
- supports_media_types array
- Priority ordering

---

## API Endpoints

### Media Endpoints

- `GET /api/media/status/` - Check if media exists by provider+external_id
- `POST /api/media/wanted/` - Add media to want list

### Search Endpoints

- `GET /search/` - Search metadata providers (HTML form)
- `GET /api/providers/` - Get providers for media type

### Download Endpoints

- `POST /api/downloads/search/<media_id>/` - Search indexers for media
- `POST /api/downloads/initiate/` - Start download
- `GET /api/downloads/attempts/<media_id>/` - List download attempts
- `GET /api/downloads/attempt/<attempt_id>/status/` - Get download status
- `POST /api/downloads/blacklist/` - Blacklist a release
- `DELETE /api/downloads/attempt/<attempt_id>/` - Delete download attempt

### Processing Endpoints

- `POST /api/processing/convert/<attempt_id>/` - Convert to EPUB
- `POST /api/processing/organize/<attempt_id>/` - Organize to library

---

## Areas for Improvement

### 1. Status Management

**Issue**: Media status transitions are incomplete and inconsistent.

**Problems**:
- Media status never transitions to SEARCHING when search is triggered
- Media status never transitions to POST_PROCESSED_SUCCESS after organization
- DownloadAttempt.post_process_status is not updated during conversion/organization
- No automatic status updates based on DownloadAttempt state

**Recommendations**:
- Add status transition logic in SearchService.search_for_media()
- Update Media status to POST_PROCESSED_SUCCESS in organize_to_library_for_attempt()
- Update DownloadAttempt.post_process_status during conversion
- Create a status synchronization service to keep Media and DownloadAttempt in sync

---

### 2. Automated Workflow

**Issue**: No automated workflow from WANTED → DOWNLOADED → POST_PROCESSED_SUCCESS.

**Problems**:
- User must manually trigger each step
- No periodic search for WANTED items
- No automatic download initiation
- No automatic post-processing when downloads complete

**Recommendations**:
- Implement Dramatiq tasks for:
  - Periodic search for WANTED media (every 6 hours)
  - Monitor downloads and trigger post-processing when DOWNLOADED
  - Automatic conversion and organization pipeline
- Add task scheduling configuration
- Implement task retry logic with exponential backoff

---

### 3. Download Monitoring

**Issue**: Download status must be manually polled.

**Problems**:
- No automatic monitoring of active downloads
- No notification when downloads complete
- Status updates only happen when user polls

**Recommendations**:
- Implement periodic Dramatiq task to check active downloads
- Update DownloadAttempt and Media status automatically
- Trigger post-processing when download completes
- Add webhook support from SABnzbd (if available)

---

### 4. Error Handling and Retry Logic

**Issue**: Limited error handling and no retry mechanisms.

**Problems**:
- Failed downloads are not automatically retried
- No exponential backoff for API failures
- Limited error categorization
- No dead letter queue for permanently failed tasks

**Recommendations**:
- Add retry decorators to Dramatiq tasks
- Implement exponential backoff for API calls
- Categorize errors (transient vs permanent)
- Add dead letter queue for failed tasks
- Implement automatic retry for failed downloads (up to N attempts)

---

### 5. File Discovery Reliability

**Issue**: File discovery relies on filename matching which can be unreliable.

**Problems**:
- Filename matching is fragile (release titles may not match)
- No tracking of SABnzbd job completion path
- May find wrong files if multiple downloads exist

**Recommendations**:
- Store SABnzbd completion path in DownloadAttempt when job completes
- Use download_client_download_id for more reliable matching
- Add file hash verification to ensure correct file
- Implement file size validation

---

### 6. Post-Processing Status Tracking

**Issue**: Post-processing status is not properly tracked.

**Problems**:
- DownloadAttempt.post_process_status is never set
- No way to track conversion progress
- No way to retry failed conversions
- Media status doesn't reflect post-processing state

**Recommendations**:
- Update post_process_status during conversion/organization
- Add progress tracking for long-running conversions
- Implement retry logic for failed conversions
- Add separate status fields for conversion vs organization

---

### 7. Library Organization

**Issue**: Library organization is basic and doesn't handle all cases.

**Problems**:
- Only handles single author (uses first author)
- No series-based organization
- No duplicate detection
- No handling of existing files

**Recommendations**:
- Support multiple authors in directory structure
- Add series-based organization: `Author/Series/Title/`
- Implement duplicate detection (by file hash)
- Handle existing files (skip, overwrite, or rename)
- Add configuration for naming templates

---

### 8. Search Query Optimization

**Issue**: Search queries may not be optimal for all indexers.

**Problems**:
- Fixed query priority may not work for all indexers
- No query result quality scoring
- No learning from successful downloads

**Recommendations**:
- Make query priority configurable per indexer
- Add quality scoring based on:
  - Title match percentage
  - Author match
  - File size reasonableness
  - Seeders/peers (for torrents)
- Track which queries lead to successful downloads
- Adjust query priority based on success rate

---

### 9. Blacklist Management

**Issue**: Blacklist filtering happens but could be improved.

**Problems**:
- No automatic blacklisting of failed downloads
- No expiration of old blacklist entries
- No way to un-blacklist entries

**Recommendations**:
- Automatically blacklist after N failed download attempts
- Add expiration date to blacklist entries
- Add admin interface to manage blacklist
- Allow un-blacklisting with reason

---

### 10. API Consistency

**Issue**: API responses are inconsistent.

**Problems**:
- Some endpoints return `{"success": True}`, others return data directly
- Error messages are inconsistent
- No standard error response format

**Recommendations**:
- Standardize API response format:
  ```json
  {
    "success": true/false,
    "data": {...},
    "error": "...",
    "error_code": "..."
  }
  ```
- Use consistent HTTP status codes
- Add API versioning
- Document all endpoints with OpenAPI/Swagger

---

### 11. Database Query Optimization

**Issue**: Some queries may be inefficient.

**Problems**:
- No select_related/prefetch_related in some views
- May cause N+1 queries
- No database indexes on frequently queried fields

**Recommendations**:
- Add select_related for ForeignKey relationships
- Add prefetch_related for ManyToMany/Reverse FK
- Review and add database indexes:
  - DownloadAttempt.status + attempted_at
  - Media.status + added_date
  - DownloadBlacklist.content_type + object_id + indexer
- Use database query logging in development

---

### 12. Configuration Management

**Issue**: Configuration is scattered and not user-friendly.

**Problems**:
- ProcessingConfiguration has only one enabled config
- No way to have different configs for different media types
- No validation of configuration values

**Recommendations**:
- Add configuration validation
- Support multiple processing configs with media type mapping
- Add configuration testing endpoints
- Add admin UI for configuration management

---

### 13. Logging and Monitoring

**Issue**: Logging exists but could be more comprehensive.

**Problems**:
- No structured logging
- No metrics collection
- No alerting for critical failures
- Limited context in log messages

**Recommendations**:
- Add structured logging (JSON format)
- Add correlation IDs for request tracing
- Implement metrics collection:
  - Download success/failure rates
  - Search result quality
  - Post-processing times
  - API response times
- Add alerting for:
  - High failure rates
  - Stuck downloads
  - Configuration errors

---

### 14. Testing Coverage

**Issue**: Limited test coverage visible.

**Problems**:
- No integration tests for complete workflows
- No tests for error scenarios
- No tests for edge cases

**Recommendations**:
- Add integration tests for:
  - Complete workflow: Search → Download → Process → Organize
  - Error scenarios (failed downloads, conversion failures)
  - Concurrent operations
- Add unit tests for:
  - Service classes
  - Utility functions
  - API endpoints
- Add test fixtures for common scenarios

---

### 15. Download URL Resolution

**Issue**: Download URL resolution is complex and may fail.

**Problems**:
- Multiple fallback strategies make code complex
- May fail silently in some cases
- No validation of resolved URLs

**Recommendations**:
- Simplify URL resolution logic
- Add comprehensive logging for each resolution step
- Validate resolved URLs before use
- Add unit tests for URL resolution edge cases

---

### 16. Media Type Support

**Issue**: Currently only supports Books and Audiobooks.

**Problems**:
- Manga and Comics models not implemented
- Search providers don't support manga/comics
- Post-processing doesn't handle manga/comic formats

**Recommendations**:
- Implement Manga and Comic models
- Add manga/comic search providers (MangaDex, ComicVine)
- Add CBZ conversion and organization
- Update Prowlarr categories for manga/comics

---

### 17. Task Queue Usage

**Issue**: Dramatiq is configured but barely used.

**Problems**:
- Only example tasks exist
- No actual workflow tasks implemented
- No task prioritization

**Recommendations**:
- Implement tasks for:
  - Periodic search
  - Download monitoring
  - Post-processing pipeline
  - Metadata refresh
- Add task prioritization
- Implement task result tracking
- Add task monitoring dashboard

---

### 18. Security

**Issue**: Some security considerations missing.

**Problems**:
- No API authentication
- No rate limiting
- No input validation on some endpoints
- File paths not validated (potential directory traversal)

**Recommendations**:
- Add API authentication (JWT tokens)
- Implement rate limiting
- Add input validation using Django forms/serializers
- Validate file paths to prevent directory traversal
- Sanitize user inputs

---

### 19. Code Organization

**Issue**: Some code organization could be improved.

**Problems**:
- Large service classes with many responsibilities
- Some utility functions could be classes
- Inconsistent error handling patterns

**Recommendations**:
- Split large service classes into smaller, focused classes
- Use dependency injection for better testability
- Standardize error handling (custom exceptions)
- Add service interfaces for better abstraction

---

### 20. Documentation

**Issue**: Limited inline documentation.

**Problems**:
- No docstrings on most functions
- No API documentation
- No architecture diagrams

**Recommendations**:
- Add docstrings to all public functions/classes
- Generate API documentation (OpenAPI/Swagger)
- Create architecture diagrams
- Add README for each app explaining its purpose

---

## Summary

The OmniReadarr backend provides a solid foundation for media management with clear separation of concerns and well-structured components. The main areas for improvement are:

1. **Automation**: Implement automated workflows using Dramatiq tasks
2. **Status Management**: Complete status transition logic throughout the system
3. **Error Handling**: Add comprehensive error handling and retry logic
4. **Monitoring**: Implement proper monitoring and alerting
5. **Testing**: Increase test coverage, especially integration tests
6. **API Consistency**: Standardize API responses and error handling
7. **Configuration**: Improve configuration management and validation

The system is well-architected and ready for these enhancements to make it production-ready.

