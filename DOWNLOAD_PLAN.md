# Download System Plan

## Overview

This plan covers the implementation of a manual download system that integrates with Prowlarr for searching indexers (torrents and usenet) and managing downloads. Users manually trigger searches and select which files to download. The system will track download attempts, manage blacklists, and store file paths and status information.

**Scope**: Manual search and download workflow. Post-processing is out of scope for this phase. No scheduled/automatic tasks.

---

## Architecture Overview

### Flow
1. User navigates to media detail page
2. User clicks "Search" button
3. System searches Prowlarr using multiple search methods
4. System combines and deduplicates results
5. Results displayed on page for user to review
6. User clicks "Download" button on desired result
7. System sends download request to Prowlarr (which forwards to download client)
8. System tracks download progress and status
9. On completion, status changes to "Downloaded"

### Components
- **Prowlarr Integration**: Search indexers, manage indexer configuration
- **Download Client Integration**: Send downloads, monitor progress
- **Download Tracking**: Track attempts, blacklists, file paths
- **Status Management**: Update media status based on download state

---

## Database Models

### 1. ProwlarrConfiguration Model

**Purpose**: Store Prowlarr connection settings

**Fields**:
- `id` (UUID, primary key)
- `name` (CharField, max_length=100) - Configuration name
- `host` (CharField, max_length=255) - Prowlarr host/IP
- `port` (IntegerField) - Prowlarr port (default: 9696)
- `api_key` (CharField, max_length=255) - Prowlarr API key
- `use_ssl` (BooleanField, default=False) - Use HTTPS
- `base_path` (CharField, max_length=500, blank=True) - Base URL path if not root
- `enabled` (BooleanField, default=True) - Enable/disable this configuration
- `priority` (IntegerField, default=0) - Priority for multiple configs
- `timeout` (IntegerField, default=30) - Request timeout in seconds
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)

**Notes**:
- Only one ProwlarrConfiguration record allowed in the database
- API key should be encrypted in production (use Django's `encrypted_fields` or similar)
- API key is sent in HTTP header: `X-Api-Key: {api_key}` for all Prowlarr API requests

---


### 2. DownloadClientConfiguration Model

**Purpose**: Store download client connection settings (following Sonarr/Radarr pattern)

**Fields**:
- `id` (UUID, primary key)
- `name` (CharField, max_length=100) - Configuration name (e.g., "Main SABnzbd")
- `client_type` (CharField, choices) - "sabnzbd" (only SABnzbd supported for MVP)
- `host` (CharField, max_length=255) - SABnzbd host/IP
- `port` (IntegerField) - SABnzbd port (default: 8080)
- `use_ssl` (BooleanField, default=False) - Use HTTPS
- `api_key` (CharField, max_length=255) - SABnzbd API key
- `enabled` (BooleanField, default=True) - Enable/disable this configuration
- `priority` (IntegerField, default=0) - Priority for multiple configs (future)
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)

**Notes**:
- Only SABnzbd supported in MVP (usenet downloads)
- API key should be encrypted in production (use Django's `encrypted_fields` or similar)
- User configures SABnzbd in our app (also configured in Prowlarr for download forwarding)
- Following Sonarr/Radarr pattern: store download client config in our database

---

### 3. DownloadAttempt Model

**Purpose**: Track each attempt to download a file for a media item

**Fields**:
- `id` (UUID, primary key)
- `media` (ForeignKey to Media, CASCADE) - The media item being downloaded
- `indexer` (CharField, max_length=100) - Indexer name (from Prowlarr)
- `indexer_id` (CharField, max_length=100) - Indexer ID in Prowlarr
- `release_title` (CharField, max_length=500) - Title of the release
- `download_url` (CharField, max_length=1000) - URL/magnet link to download
- `file_size` (BigIntegerField, null=True) - File size in bytes
- `seeders` (IntegerField, null=True) - Number of seeders (torrents only)
- `leechers` (IntegerField, null=True) - Number of leechers (torrents only)
- `attempted_at` (DateTimeField, auto_now_add) - When download was attempted
- `status` (CharField, choices) - "pending", "sent", "downloading", "downloaded", "failed", "blacklisted"
- `error_type` (CharField, max_length=50, blank=True) - Error category if failed
- `error_reason` (TextField, blank=True) - Detailed error message
- `download_client` (ForeignKey to DownloadClientConfiguration, null=True) - Which download client was used
- `download_client_download_id` (CharField, max_length=100, blank=True) - SABnzbd job ID (nzo_id)
- `raw_file_path` (CharField, max_length=1000, blank=True) - Path to downloaded file
- `post_processed_file_path` (CharField, max_length=1000, blank=True) - Path after post-processing
- `post_process_status` (CharField, max_length=50, blank=True) - "pending", "processing", "completed", "failed"
- `post_process_error_type` (CharField, max_length=50, blank=True)
- `post_process_error_reason` (TextField, blank=True)
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)

**Indexes**:
- Index on `media` + `status`
- Index on `status`
- Index on `attempted_at`

**Notes**:
- One media item can have multiple download attempts
- Only one attempt can be active ("downloading" or "sent") at a time per media item
- User must delete existing active download attempt before starting a new one
- Failed attempts can be retried (unless blacklisted)

---

### 4. DownloadBlacklist Model

**Purpose**: Track releases that should not be downloaded again

**Fields**:
- `id` (UUID, primary key)
- `media` (ForeignKey to Media, CASCADE) - Media item this blacklist entry is for
- `indexer` (CharField, max_length=100) - Indexer name
- `indexer_id` (CharField, max_length=100) - Indexer ID
- `release_title` (CharField, max_length=500) - Release title
- `download_url` (CharField, max_length=1000) - URL/magnet that was blacklisted
- `reason` (CharField, choices) - "failed_download", "wrong_file", "corrupted", "low_quality", "manual"
- `reason_details` (TextField, blank=True) - Additional details
- `blacklisted_at` (DateTimeField, auto_now_add)
- `blacklisted_by` (CharField, max_length=50, blank=True) - "system" or "user"
- `created_at` (DateTimeField, auto_now_add)

**Indexes**:
- Unique constraint on `media` + `indexer` + `indexer_id` (prevent duplicates)
- Index on `media`
- Index on `blacklisted_at`

**Notes**:
- Prevents re-downloading known bad releases
- Can be manually added or automatically added on failure
- Should be checked before attempting downloads

---

## Prowlarr Integration

### Prowlarr Capabilities

**What Prowlarr Does**:
- Manages indexer configurations
- Searches multiple indexers simultaneously
- Returns normalized search results
- Can send results to download clients automatically

**What Prowlarr Does NOT Do**:
- Prowlarr does NOT download files itself
- Prowlarr does NOT manage download clients directly
- Prowlarr acts as a proxy/search aggregator

### Integration Approach

**We are using Prowlarr's "Send to Download Client" Feature**:
- Search Prowlarr for results
- User selects which result to download in our app
- Send download request to Prowlarr via API
- Prowlarr automatically forwards to configured SABnzbd (configured in Prowlarr)
- We poll SABnzbd API directly to track download status (SABnzbd configured in our app)
- Following Sonarr/Radarr pattern: download client config stored in our database

### Prowlarr API Endpoints Needed

#### 1. Search Endpoint

**Endpoint**: `GET /api/v1/search`

**Authentication**: Include API key in header: `X-Api-Key: {api_key}`

**Query Parameters**:
- `q` (string, required): The search query/term
- `cat` (string, optional): Category IDs (comma-separated). For books: `7000` (Books category)
- `indexer` (string, optional): Specific indexer name(s) to search (comma-separated). If omitted, searches all configured indexers
- `limit` (integer, optional): Maximum number of results to return (default varies)
- `offset` (integer, optional): Pagination offset (default: 0)
- `sortkey` (string, optional): Sort by attribute (`seeders`, `leechers`, `size`, `date`, etc.)
- `sortdir` (string, optional): Sort direction (`asc` or `desc`, default: `desc`)

**Example Request**:
```
GET /api/v1/search?q=Dune%20Frank%20Herbert&cat=7000&limit=50&sortkey=seeders&sortdir=desc
Headers: X-Api-Key: {api_key}
```

**Response Format**:
```json
[
  {
    "guid": "indexer-guid-123",
    "title": "Dune by Frank Herbert [EPUB]",
    "indexer": "ThePirateBay",
    "indexerId": 1,
    "size": 2621440,
    "publishDate": "2020-01-15T00:00:00Z",
    "seeders": 25,
    "peers": 30,
    "protocol": "torrent",
    "downloadUrl": "magnet:?xt=urn:btih:...",
    "infoUrl": "https://..."
  }
]
```

**Field Descriptions**:
- `guid`: Unique identifier for this release (used for download command)
- `title`: Release title as returned by indexer
- `indexer`: Name of the indexer
- `indexerId`: Numeric ID of the indexer (used for download command)
- `size`: File size in bytes
- `publishDate`: ISO 8601 date string
- `seeders`: Number of seeders (torrents only, may be null for usenet)
- `peers`: Total peers (seeders + leechers, torrents only, may be null for usenet)
- `protocol`: "torrent" or "usenet"
- `downloadUrl`: Magnet link (torrents) or NZB URL (usenet)
- `infoUrl`: Link to indexer page (optional, may be null)

**Notes**:
- Category `7000` is the standard Books category in Prowlarr
- Not all indexers support text-based search (`q` parameter) - some only support ID-based searches
- Some indexers may not support all sort keys
- Results are normalized by Prowlarr across different indexer formats

#### 2. Indexers Endpoint

**Endpoint**: `GET /api/v1/indexer`

**Authentication**: Include API key in header: `X-Api-Key: {api_key}`

**Query Parameters**: None

**Response**: List of configured indexers with their capabilities and settings

**Example Response**:
```json
[
  {
    "id": 1,
    "name": "ThePirateBay",
    "protocol": "torrent",
    "categories": [7000, 7010],
    "supportsRss": true,
    "supportsSearch": true,
    "supportsQuery": true,
    "supportsBookSearch": false
  }
]
```

#### 3. Download Command Endpoint

**Endpoint**: `POST /api/v1/command`

**Authentication**: Include API key in header: `X-Api-Key: {api_key}`

**Request Body**:
```json
{
  "name": "DownloadRelease",
  "indexerId": 1,
  "guid": "indexer-guid-123"
}
```

**Response**:
```json
{
  "id": 123,
  "name": "DownloadRelease",
  "message": "Download sent to download client",
  "body": {
    "downloadClientId": "qbt-456"
  }
}
```

**Notes**:
- `indexerId`: The ID of the indexer (from indexer list)
- `guid`: The unique identifier from the search result
- Prowlarr forwards the download to the configured download client
- Download client is configured in Prowlarr (not in our app)

#### 4. System Status Endpoint

**Endpoint**: `GET /api/v1/system/status`

**Authentication**: Include API key in header: `X-Api-Key: {api_key}`

**Purpose**: Verify Prowlarr is accessible and get system information

**Response**: System status information

### Download Client Integration

**Approach**: Following Sonarr/Radarr pattern - store download client configuration in our database.

**SABnzbd Support (MVP)**:
- User configures SABnzbd in our application (host, port, API key)
- Configuration stored in `DownloadClientConfiguration` model
- User also configures SABnzbd in Prowlarr (for download forwarding)
- We poll SABnzbd API directly to check download status

**Download Flow**:
1. User initiates download via our app
2. We send download request to Prowlarr
3. Prowlarr forwards to SABnzbd (configured in Prowlarr)
4. We poll SABnzbd API directly to track status
5. On completion, we get file path from SABnzbd

**Future**: Can add qBittorrent, Transmission, NZBGet support later

---

## Implementation Phases

### Phase 1: Database Models

**Tasks**:
1. Create `ProwlarrConfiguration` model (single instance only)
2. Create `DownloadClientConfiguration` model (SABnzbd only for MVP)
3. Create `DownloadAttempt` model
4. Create `DownloadBlacklist` model
5. Add migrations
6. Create admin interfaces for all models
7. Write unit tests for models

**Deliverables**:
- Models defined with proper fields and relationships
- Migrations applied
- Admin interfaces functional
- Tests passing

---

### Phase 2: Prowlarr Client

**Tasks**:
1. Create `ProwlarrClient` class in `indexers/prowlarr/client.py`
2. Implement connection testing
3. Implement search functionality
4. Implement indexer listing
5. Handle API errors and timeouts
6. Write unit tests with mocked responses

**API Methods**:
- `test_connection() -> bool`
- `search(query: str, media_type: str, **filters) -> list[SearchResult]`
- `get_indexers() -> list[IndexerInfo]`
- `get_indexer_capabilities(indexer_id: int) -> IndexerCapabilities`

**Authentication**:
- All Prowlarr API requests include header: `X-Api-Key: {api_key}`
- API key retrieved from ProwlarrConfiguration model

**Deliverables**:
- ProwlarrClient class with all methods
- Error handling
- Tests with mocked HTTP responses

---

### Phase 3: Prowlarr Download Integration

**Tasks**:
1. Implement `send_to_download_client()` method in ProwlarrClient
2. Handle Prowlarr's download command API
3. Parse download response and extract download client ID
4. Write unit tests with mocked responses

**Methods**:
- `send_to_download_client(indexer_id: int, guid: str) -> dict`
  - Sends download request to Prowlarr
  - Prowlarr forwards to configured download client
  - Returns response with download status

**Deliverables**:
- Download initiation via Prowlarr
- Error handling
- Tests

---

### Phase 3.5: SABnzbd Client

**Tasks**:
1. Create `SABnzbdClient` class in `downloads/clients/sabnzbd.py`
2. Implement connection testing
3. Implement queue status retrieval
4. Implement history retrieval
5. Implement job deletion
6. Handle API errors and timeouts
7. Write unit tests with mocked responses

**API Methods**:
- `test_connection() -> bool`
- `get_queue() -> list[QueueItem]`
- `get_history() -> list[HistoryItem]`
- `delete_job(nzo_id: str) -> bool`
- `get_job_status(nzo_id: str) -> JobStatus | None`

**SABnzbd API Endpoints**:
- Queue: `GET /api?mode=queue&apikey={key}&output=json`
- History: `GET /api?mode=history&apikey={key}&output=json`
- Delete: `GET /api?mode=queue&name=delete&value={nzo_id}&apikey={key}`

**Queue Response Format**:
```json
{
  "queue": {
    "slots": [
      {
        "nzo_id": "SABnzbd_nzo_abc123",
        "filename": "Dune by Frank Herbert [EPUB].nzb",
        "status": "Downloading",
        "mbleft": "45.2",
        "mb": "500.0",
        "timeleft": "00:15:30",
        "percentage": "90.96"
      }
    ]
  }
}
```

**Deliverables**:
- SABnzbdClient class with all methods
- Error handling
- Tests with mocked HTTP responses

---

### Phase 4: Search Service Layer

**Tasks**:
1. Create `SearchService` class
2. Implement multi-query search logic
3. Implement result deduplication
4. Implement blacklist checking
5. Write unit tests

**Service Methods**:
- `search_for_media(media: Media) -> list[SearchResult]`
  - Executes multiple search queries simultaneously
  - Combines and deduplicates results
  - Filters blacklisted results
  - Returns list of results (no scoring in MVP)

- `is_blacklisted(media: Media, release: SearchResult) -> bool`
  - Checks if release is in blacklist

**Deliverables**:
- SearchService with multi-query search
- Result deduplication logic
- Blacklist checking
- Tests

**Note**: Result scoring removed from MVP. Results will be returned ordered by search method priority (book-specific first, then general), then by indexer name. Limited to top 50 results.

---

### Phase 5: Download Service Layer

**Tasks**:
1. Create `DownloadService` class
2. Implement download initiation via Prowlarr
3. Implement download status tracking (poll Prowlarr or download client)
4. Implement blacklist management
5. Implement download deletion with file cleanup
6. Write unit tests

**Service Methods**:
- `initiate_download(media_id: UUID, result: SearchResult) -> DownloadAttempt`
  - Checks if media already has active download attempt (status="downloading" or "sent")
  - If active download exists, raises error (user must delete existing attempt first)
  - Gets enabled SABnzbd DownloadClientConfiguration
  - Creates DownloadAttempt record (links to DownloadClientConfiguration)
  - Sends download request to Prowlarr
  - Prowlarr forwards to SABnzbd
  - Updates DownloadAttempt with SABnzbd job ID (nzo_id) when available
  - Updates Media status to "DOWNLOADING"

- `get_download_status(attempt_id: UUID) -> DownloadAttempt`
  - Gets DownloadAttempt and associated DownloadClientConfiguration
  - Creates SABnzbdClient instance
  - Polls SABnzbd API: `GET /api?mode=queue&apikey={key}&output=json`
  - Matches download by `download_client_download_id` (nzo_id) or filename
  - Updates DownloadAttempt status based on SABnzbd status
  - When download completes, updates status to "downloaded" and sets raw_file_path
  - Updates Media status to "DOWNLOADED" when download completes

- `mark_as_blacklisted(attempt_id: UUID, reason: str) -> None`
  - Adds release to blacklist
  - Prevents future downloads of same release

- `delete_download_attempt(attempt_id: UUID) -> dict`
  - Gets DownloadAttempt and associated DownloadClientConfiguration
  - If download is still active, calls SABnzbd API to delete job: `GET /api?mode=queue&name=delete&value={nzo_id}&apikey={key}`
  - Deletes raw file from disk (if exists)
  - Deletes post-processed file from disk (if exists)
  - Updates Media status if this was the active download
  - Deletes DownloadAttempt record
  - Returns success status and messages

**Note**: Download status polling can be done via API calls (manual refresh) or optional background task (future enhancement). For now, status updates happen on page refresh or manual API call.

**Deliverables**:
- DownloadService with download initiation
- Status tracking logic
- Blacklist management
- File deletion logic
- Download client cleanup
- Tests

---

### Phase 6: API Endpoints

**Tasks**:
1. Create API endpoint `POST /api/downloads/search/{media_id}/`
   - Trigger search for media
   - Executes multiple search queries
   - Returns combined and deduplicated results (limited to 50)
   - Response: `{results: [SearchResult], total: int}`
   - Error handling: Returns error message if Prowlarr is unreachable

2. Create API endpoint `POST /api/downloads/initiate/`
   - Initiate download for a specific result
   - Body: `{media_id, indexer_id, guid}`
   - Validates no active download exists for media (returns error if exists)
   - Response: `{success: bool, attempt_id: UUID, status: str, error: str}`
   - Error handling: Returns error message if Prowlarr is unreachable or download fails

3. Create API endpoint `GET /api/downloads/attempts/{media_id}/`
   - Get all download attempts for media
   - Response: `{attempts: [DownloadAttempt]}`

4. Create API endpoint `GET /api/downloads/attempt/{attempt_id}/status/`
   - Get current status of download attempt
   - Polls SABnzbd API directly
   - Response: `{status: str, progress: float, error: str}`
   - Error handling: Returns error message if SABnzbd is unreachable

5. Create API endpoint `POST /api/downloads/blacklist/`
   - Manually blacklist a release
   - Body: `{attempt_id, reason, reason_details}`
   - Response: `{success: bool}`

6. Create API endpoint `DELETE /api/downloads/attempt/{attempt_id}/`
   - Delete a download attempt and associated files
   - Deletes raw file from disk (if exists)
   - Deletes post-processed file from disk (if exists)
   - Removes download from SABnzbd via SABnzbd API (if still active)
   - Deletes DownloadAttempt record
   - Updates Media status if this was the active download:
     - If status was "DOWNLOADING" → Changes to "WANTED"
     - If status was "DOWNLOADED" → Changes to "WANTED"
   - Response: `{success: bool, message: str}`

**Delete Behavior**:
- **File Deletion**: 
  - Checks if `raw_file_path` exists and is a file → Deletes it
  - Checks if `post_processed_file_path` exists and is a file → Deletes it
  - Handles errors gracefully (file not found, permission errors)
  - Logs deletion actions
  
- **Download Client Cleanup**:
  - If download is still active (`status="downloading"` or `status="sent"`):
    - Attempts to remove download from download client via Prowlarr
    - If removal fails, logs error but continues with file deletion
  
- **Status Updates**:
  - Only updates Media status if this DownloadAttempt was the current active download
  - Checks if there are other completed downloads for the media
  - If other downloads exist, doesn't change Media status
  
- **Safety Checks**:
  - Verifies file paths are within allowed directories (prevent directory traversal)
  - Confirms user has permission to delete
  - Validates attempt_id exists and belongs to user's media

**Deliverables**:
- REST API endpoints
- Request/response validation
- Error handling
- File deletion logic
- Download client cleanup
- Status update logic
- API documentation
- Tests

---

### Phase 7: UI Integration

**Tasks**:
1. Add "Search" button to media detail page
2. Add search results section on media detail page
3. Display search results in table with:
   - Release title
   - Indexer name
   - File size
   - Seeders (for torrents)
   - Download button
4. Show download attempts section with:
   - Current download status
   - Progress indicator
   - Error messages if failed
   - Blacklist button for failed attempts
5. Add Prowlarr configuration UI (admin or settings page)

**User Flow**:
1. User navigates to media detail page
2. User clicks "Search" button
3. Page shows loading state
4. Search results appear in table below (ordered by search method priority)
5. If error occurs, error message is displayed to user
6. User reviews results and clicks "Download" button on desired result
7. If active download exists, error message shown (user must delete existing attempt first)
8. Download attempt is created and initiated
9. Page shows download status
10. User can refresh to check download progress

**Deliverables**:
- Search button and results display
- Download initiation UI
- Download status display
- Blacklist management UI
- Prowlarr configuration UI

---

## Data Flow Examples

### Example 1: Manual Search and Download Flow

1. User navigates to media detail page (status = "WANTED")
2. User clicks "Search" button
3. Frontend calls `POST /api/downloads/search/{media_id}/`
4. Backend executes multiple search queries in parallel:
   - Book-specific search: `GET /api/v1/search?q=title:{title} author:{author}&cat=7000&limit=50&sortkey=seeders&sortdir=desc` (Headers: `X-Api-Key: {api_key}`)
   - Title+Author search: `GET /api/v1/search?q={title} {author}&cat=7000&limit=50&sortkey=seeders&sortdir=desc` (Headers: `X-Api-Key: {api_key}`)
   - Title-only search: `GET /api/v1/search?q={title}&cat=7000&limit=50&sortkey=seeders&sortdir=desc` (Headers: `X-Api-Key: {api_key}`)
   - ISBN search (if available): `GET /api/v1/search?q=isbn:{isbn}&cat=7000&limit=50&sortkey=seeders&sortdir=desc` (Headers: `X-Api-Key: {api_key}`)
   - Series search (if available): `GET /api/v1/search?q={series} {title}&cat=7000&limit=50&sortkey=seeders&sortdir=desc` (Headers: `X-Api-Key: {api_key}`)
5. Backend normalizes all results to SearchResult dataclass
6. Backend combines all results, deduplicates by (indexer_id, guid)
   - If same result found by multiple queries, keep from highest priority search method
7. Backend filters blacklisted results
8. Backend orders results by search method priority (book-specific first, then general)
9. Backend limits to top 50 results
10. Backend returns results to frontend
11. Frontend displays results in table
12. User reviews results and clicks "Download" on desired result
13. Frontend calls `POST /api/downloads/initiate/` with `{media_id, indexer_id, guid}`
14. Backend checks if media has active download (status="downloading" or "sent")
    - If active download exists, returns error (user must delete existing attempt first)
15. Backend creates `DownloadAttempt` record (status="pending")
16. Backend calls Prowlarr API: `POST /api/v1/command` 
    - Headers: `X-Api-Key: {api_key}`
    - Body: `{"name": "DownloadRelease", "indexerId": {indexer_id}, "guid": "{guid}"}`
17. Prowlarr forwards to configured download client
18. Backend updates `DownloadAttempt` (status="sent")
19. Backend updates Media status to "DOWNLOADING"
20. User refreshes page or clicks "Check Status"
21. Frontend calls `GET /api/downloads/attempt/{attempt_id}/status/`
22. Backend polls SABnzbd API directly:
    - Queries SABnzbd queue: `GET /api?mode=queue&apikey={key}&output=json`
    - Matches download by `download_client_download_id` (nzo_id) or filename
    - Gets status, progress, and file path
23. When download completes:
    - Updates `DownloadAttempt` (status="downloaded", raw_file_path="...", download_client_download_id="{nzo_id}")
    - Updates Media status to "DOWNLOADED"

### Example 2: Failed Download Flow

1. Download fails (corrupted file, wrong file, etc.)
2. User checks download status (manual refresh or status check)
3. Backend detects failure from download client
4. Updates `DownloadAttempt` (status="failed", error_type="corrupted", error_reason="...")
5. Frontend displays error message to user
6. User can click "Blacklist" button to prevent re-downloading
7. User can search again to find alternative results
8. User can delete failed attempt and manually retry with different result

### Example 3: Delete Download Flow

1. User views media detail page with download attempts
2. User clicks "Delete" button on a download attempt
3. Frontend calls `DELETE /api/downloads/attempt/{attempt_id}/`
4. Backend validates attempt exists and user has permission
5. Backend checks download status:
   - If active (`status="downloading"` or `status="sent"`):
     - Gets DownloadClientConfiguration from DownloadAttempt
     - Calls SABnzbd API to delete job: `GET /api?mode=queue&name=delete&value={nzo_id}&apikey={key}`
     - Logs result (success or failure)
6. Backend deletes files from disk:
   - Checks `raw_file_path` → Deletes file if exists
   - Checks `post_processed_file_path` → Deletes file if exists
   - Handles errors gracefully (file not found, permission errors)
7. Backend checks if this was the active download:
   - Checks if Media status is "DOWNLOADING" or "DOWNLOADED"
   - Checks if there are other downloaded attempts for this media
   - If no other downloaded attempts exist → Updates Media status to "WANTED"
   - If other downloaded attempts exist → Keeps Media status unchanged
8. Backend deletes `DownloadAttempt` record
9. Backend returns success response
10. Frontend refreshes download attempts list

---

## Key Design Decisions

### 1. Result Evaluation/Scoring (Future Enhancement)

**Note**: Scoring removed from MVP. Results returned in search method priority order.

**Future Implementation**: See detailed scoring algorithm below (for post-MVP).

**Overview**: Each search result is scored from 0-100 based on multiple factors. Higher scores indicate better matches. Results are sorted by score descending.

**Scoring Factors**:

#### Factor 1: Title Match Quality (0-40 points)

**Purpose**: Determine how well the release title matches the media title.

**Algorithm**:
```python
def score_title_match(release_title: str, media_title: str, media_authors: list[str]) -> float:
    score = 0.0
    
    # Normalize titles (lowercase, remove punctuation)
    release_normalized = normalize_title(release_title)
    media_normalized = normalize_title(media_title)
    
    # Exact match (case-insensitive)
    if release_normalized == media_normalized:
        score = 40.0
    # Title contains media title
    elif media_normalized in release_normalized:
        score = 35.0
    # Media title contains release title (partial match)
    elif release_normalized in media_normalized:
        score = 30.0
    # Word overlap calculation
    else:
        release_words = set(release_normalized.split())
        media_words = set(media_normalized.split())
        overlap = len(release_words & media_words)
        total_words = len(media_words)
        if total_words > 0:
            overlap_ratio = overlap / total_words
            score = 20.0 * overlap_ratio  # 0-20 points based on word overlap
    
    # Author bonus (if authors found in release title)
    if media_authors:
        for author in media_authors:
            author_normalized = normalize_title(author)
            if author_normalized in release_normalized:
                score += 5.0  # Bonus for author match
                break
    
    return min(score, 40.0)  # Cap at 40 points
```

**Examples**:
- "Dune by Frank Herbert" vs "Dune" → 40 points (exact match)
- "Dune - Frank Herbert" vs "Dune" → 35 points (contains title)
- "Dune Messiah" vs "Dune" → 30 points (title contains release)
- "Dune Chronicles" vs "Dune" → 20 points (word overlap)
- "Random Book" vs "Dune" → 0 points (no match)

---

#### Factor 2: Search Method Weight (0-20 points)

**Purpose**: Prioritize results from more reliable search methods.

**Algorithm**:
```python
def score_search_method(search_method: str) -> float:
    method_scores = {
        "book_specific": 20.0,      # Book-specific search (most targeted)
        "isbn": 18.0,                # ISBN search (very specific)
        "title_author": 12.0,       # Title + Author search
        "title_only": 8.0,           # Title-only search
        "general": 5.0,             # General search (least targeted)
    }
    return method_scores.get(search_method, 5.0)
```

**Rationale**:
- Book-specific searches are most reliable when they work
- ISBN searches are highly accurate but may not always return results
- Title+Author is a good balance
- Title-only is less reliable
- General search casts widest net but lowest precision

---

#### Factor 3: File Quality Match (0-20 points)

**Purpose**: Evaluate if file characteristics match expected values.

**Sub-factors**:

**3a. File Size Match (0-10 points)**:
```python
def score_file_size(file_size_bytes: int, media_type: str) -> float:
    # Expected size ranges (in MB)
    expected_ranges = {
        "book": {
            "min_mb": 0.5,      # Very short book
            "max_mb": 50.0,     # Very long book
            "typical_min_mb": 1.0,
            "typical_max_mb": 10.0,
        },
        "audiobook": {
            "min_mb": 50.0,     # Short audiobook
            "max_mb": 2000.0,   # Very long audiobook
            "typical_min_mb": 100.0,
            "typical_max_mb": 500.0,
        },
    }
    
    range_config = expected_ranges.get(media_type, expected_ranges["book"])
    size_mb = file_size_bytes / (1024 * 1024)
    
    if range_config["typical_min_mb"] <= size_mb <= range_config["typical_max_mb"]:
        return 10.0  # Perfect size match
    elif range_config["min_mb"] <= size_mb <= range_config["max_mb"]:
        # Within acceptable range, score based on distance from typical
        if size_mb < range_config["typical_min_mb"]:
            ratio = size_mb / range_config["typical_min_mb"]
        else:
            ratio = range_config["typical_max_mb"] / size_mb
        return 10.0 * ratio  # 0-10 points
    else:
        return 0.0  # Outside acceptable range
```

**3b. File Format Preference (0-10 points)**:
```python
def score_file_format(release_title: str, media_type: str) -> float:
    # Extract file extension from release title
    extension = extract_extension(release_title).lower()
    
    format_preferences = {
        "book": {
            "epub": 10.0,
            "mobi": 9.0,
            "azw3": 9.0,
            "pdf": 7.0,
            "txt": 5.0,
            "default": 3.0,
        },
        "audiobook": {
            "m4b": 10.0,
            "mp3": 8.0,
            "flac": 9.0,
            "aac": 7.0,
            "default": 3.0,
        },
    }
    
    preferences = format_preferences.get(media_type, {})
    return preferences.get(extension, preferences.get("default", 0.0))
```

**Examples**:
- Book: EPUB file → 10 points, PDF → 7 points, unknown format → 3 points
- Audiobook: M4B file → 10 points, MP3 → 8 points, unknown → 3 points

---

#### Factor 4: Indexer Quality (0-10 points)

**Purpose**: Prioritize results from reputable indexers.

**Algorithm**:
```python
def score_indexer(indexer_name: str) -> float:
    # Indexer reputation scores (can be configured)
    indexer_reputation = {
        "high": ["ThePirateBay", "1337x", "RARBG", "Nyaa"],      # 10 points
        "medium": ["TorrentGalaxy", "Torlock", "Zooqle"],        # 7 points
        "low": ["Unknown", "NewIndexer"],                        # 5 points
    }
    
    for tier, indexers in indexer_reputation.items():
        if indexer_name in indexers:
            return {"high": 10.0, "medium": 7.0, "low": 5.0}[tier]
    
    return 5.0  # Default for unknown indexers
```

**Rationale**:
- High-reputation indexers are more reliable
- Medium-reputation indexers are acceptable
- Low/unknown indexers get baseline score
- Can be configured per-instance based on user experience

---

#### Factor 5: Torrent Health (0-10 points, torrents only)

**Purpose**: Evaluate torrent viability based on seeders/leechers.

**Algorithm**:
```python
def score_torrent_health(seeders: int, leechers: int) -> float:
    if seeders is None or leechers is None:
        return 5.0  # Unknown health, neutral score
    
    # Calculate health ratio
    total_peers = seeders + leechers
    if total_peers == 0:
        return 0.0  # No peers, dead torrent
    
    health_ratio = seeders / total_peers if total_peers > 0 else 0.0
    
    # Score based on seeders and health ratio
    if seeders >= 10 and health_ratio >= 0.8:
        return 10.0  # Excellent health
    elif seeders >= 5 and health_ratio >= 0.6:
        return 8.0   # Good health
    elif seeders >= 2 and health_ratio >= 0.4:
        return 6.0   # Acceptable health
    elif seeders >= 1:
        return 4.0   # Poor health but downloadable
    else:
        return 0.0   # Dead torrent
```

**Examples**:
- 50 seeders, 5 leechers → 10 points (excellent)
- 8 seeders, 2 leechers → 8 points (good)
- 3 seeders, 2 leechers → 6 points (acceptable)
- 1 seeder, 0 leechers → 4 points (poor but viable)
- 0 seeders → 0 points (dead)

**Note**: This factor only applies to torrents. Usenet results get 5.0 (neutral) for this factor.

---

#### Factor 6: Publication Date Match (0-5 points, bonus)

**Purpose**: Bonus for releases that match publication year.

**Algorithm**:
```python
def score_publication_date(release_title: str, media_publication_date: date) -> float:
    if not media_publication_date:
        return 0.0
    
    # Extract year from release title (common patterns: "Book Title (2020)", "2020 - Book Title")
    release_year = extract_year_from_title(release_title)
    
    if not release_year:
        return 0.0
    
    media_year = media_publication_date.year
    
    if release_year == media_year:
        return 5.0  # Exact year match
    elif abs(release_year - media_year) <= 1:
        return 3.0  # Within 1 year
    elif abs(release_year - media_year) <= 5:
        return 1.0  # Within 5 years
    else:
        return 0.0  # Too far off
```

**Examples**:
- Release: "Dune (1965)" vs Media: 1965 → 5 points
- Release: "Dune (1966)" vs Media: 1965 → 3 points
- Release: "Dune (1970)" vs Media: 1965 → 1 point
- Release: "Dune (2020)" vs Media: 1965 → 0 points

---

### Complete Scoring Algorithm

**Total Score Calculation**:
```python
def calculate_relevance_score(
    result: SearchResult,
    media: Media,
    search_method: str
) -> float:
    """
    Calculate relevance score (0-100) for a search result.
    
    Args:
        result: SearchResult from Prowlarr
        media: Media object being searched for
        search_method: Which search method found this result
        
    Returns:
        Score from 0-100
    """
    score = 0.0
    
    # Factor 1: Title match (0-40 points)
    score += score_title_match(result.release_title, media.title, media.authors)
    
    # Factor 2: Search method weight (0-20 points)
    score += score_search_method(search_method)
    
    # Factor 3: File quality (0-20 points)
    score += score_file_size(result.file_size, media.__class__.__name__.lower())
    score += score_file_format(result.release_title, media.__class__.__name__.lower())
    
    # Factor 4: Indexer quality (0-10 points)
    score += score_indexer(result.indexer_name)
    
    # Factor 5: Torrent health (0-10 points, torrents only)
    if result.protocol == "torrent":
        score += score_torrent_health(result.seeders, result.leechers)
    else:
        score += 5.0  # Neutral score for usenet
    
    # Factor 6: Publication date match (0-5 points, bonus)
    score += score_publication_date(result.release_title, media.publication_date)
    
    return min(score, 100.0)  # Cap at 100
```

---

### Scoring Examples

#### Example 1: Perfect Match
- **Release**: "Dune by Frank Herbert (1965) [EPUB]"
- **Media**: Book "Dune" by Frank Herbert, published 1965
- **Search Method**: Book-specific search
- **Indexer**: ThePirateBay (high reputation)
- **File Size**: 2.5 MB (typical for book)
- **Format**: EPUB
- **Seeders**: 25

**Score Breakdown**:
- Title match: 40 (exact match + author bonus)
- Search method: 20 (book-specific)
- File size: 10 (perfect size)
- File format: 10 (EPUB preferred)
- Indexer: 10 (high reputation)
- Torrent health: 10 (excellent seeders)
- Publication date: 5 (exact match)
- **Total: 105 → Capped at 100**

#### Example 2: Good Match
- **Release**: "Dune - Frank Herbert"
- **Media**: Book "Dune" by Frank Herbert
- **Search Method**: Title+Author search
- **Indexer**: Medium reputation indexer
- **File Size**: 15 MB (acceptable but large)
- **Format**: PDF
- **Seeders**: 5

**Score Breakdown**:
- Title match: 35 (contains title + author)
- Search method: 12 (title+author search)
- File size: 7 (acceptable but large)
- File format: 7 (PDF, acceptable)
- Indexer: 7 (medium reputation)
- Torrent health: 8 (good seeders)
- Publication date: 0 (no year in title)
- **Total: 73**

#### Example 3: Poor Match
- **Release**: "Random Book Title"
- **Media**: Book "Dune" by Frank Herbert
- **Search Method**: General search
- **Indexer**: Unknown indexer
- **File Size**: 500 MB (way too large for book)
- **Format**: Unknown
- **Seeders**: 0

**Score Breakdown**:
- Title match: 0 (no match)
- Search method: 5 (general search)
- File size: 0 (way too large)
- File format: 3 (unknown format)
- Indexer: 5 (unknown)
- Torrent health: 0 (dead torrent)
- Publication date: 0 (no match)
- **Total: 13**

---

### Result Sorting and Filtering

**After Scoring**:
1. **Filter blacklisted results**: Remove any results that match blacklist entries
2. **Sort by score**: Descending order (highest score first)
3. **Deduplicate**: If same result appears from multiple search methods, keep highest-scored version
4. **Limit results**: Return top 50 results (or configurable limit)

**Display Order**:
- Results shown in score order (best matches first)
- Score displayed to user for transparency
- User can still manually select lower-scored results if desired

---

### Configuration and Tuning

**Configurable Parameters**:
- File size ranges per media type
- Format preferences per media type
- Indexer reputation tiers
- Torrent health thresholds
- Weight adjustments for each factor

**Future Enhancements**:
- Machine learning to improve scoring based on user selections
- User feedback to adjust scoring weights
- A/B testing different scoring algorithms

### 2. Blacklist Strategy

**When to blacklist**:
- User manually blacklists (primary method)
- File is corrupted
- Wrong file/content
- File quality too low

**Blacklist Granularity**:
- Per release (indexer + indexer_id + release_title)
- Allows retrying different releases for same media
- User-controlled (no automatic blacklisting)

### 3. Download Client Selection

**Strategy**:
- Prowlarr forwards downloads to SABnzbd (configured in Prowlarr)
- We poll SABnzbd API directly to track status (SABnzbd configured in our app)
- Following Sonarr/Radarr pattern: download client config stored in our database
- Only SABnzbd supported in MVP (usenet downloads)

### 4. File Path Management

**Raw File Path**:
- Set when download completes
- Path as downloaded from client
- Used for post-processing (future)

**Post-Processed File Path**:
- Set after post-processing completes
- Final library location
- Used for media access

---

## Testing Strategy

### Unit Tests
- Model validation
- ProwlarrClient with mocked responses
- SABnzbdClient with mocked API responses
- DownloadService logic
- Result scoring algorithm (future)

### Integration Tests
- End-to-end download flow (with test Prowlarr instance)
- Download client integration (with test clients)
- Blacklist functionality
- Status updates

### Manual Testing
- Configure real Prowlarr instance
- Configure real download client
- Test search and download flow
- Verify file paths and status updates

---

## Future Enhancements (Out of Scope)

- Post-processing pipeline
- Automatic search and download (scheduled tasks)
- Automatic quality upgrades
- Download scheduling/bandwidth management
- Download client health monitoring
- Advanced result filtering (by indexer, by quality, etc.)
- Download history and analytics
- Real-time download progress updates (WebSocket)

---

## Questions to Resolve

1. **Prowlarr Configuration**: Single instance or multiple?
   - **Decision**: Only one ProwlarrConfiguration record allowed

2. **Download Client**: How to manage?
   - **Decision**: Store DownloadClientConfiguration in our database (following Sonarr/Radarr pattern)
   - Only SABnzbd supported in MVP
   - User configures SABnzbd in both Prowlarr (for forwarding) and our app (for status tracking)

3. **Result Selection**: Automatic or manual?
   - **Decision**: Manual - user selects which result to download

4. **Blacklist Auto-Add**: When to automatically blacklist?
   - **Decision**: Manual only - user controls blacklisting

5. **File Path Storage**: Store relative or absolute?
   - **Decision**: Absolute paths for now, can add relative path support later

6. **Status Updates**: Real-time or manual refresh?
   - **Decision**: Manual refresh for now (page reload or status check button)
   - Future: Can add WebSocket for real-time updates

7. **Search Method Priority**: Which search methods to prioritize?
   - **Decision**: Execute all methods, score by relevance, combine results

---

## File Structure

```
indexers/
├── __init__.py
├── models.py              # ProwlarrConfiguration, DownloadClientConfiguration
├── admin.py
├── prowlarr/
│   ├── __init__.py
│   ├── client.py          # ProwlarrClient (search + download)
│   └── results.py         # SearchResult dataclass
└── tests/
    └── test_prowlarr.py

downloads/
├── __init__.py
├── models.py              # DownloadAttempt, DownloadBlacklist
├── admin.py
├── service.py             # SearchService, DownloadService
├── clients/
│   ├── __init__.py
│   ├── base.py            # DownloadClient abstract base class
│   └── sabnzbd.py         # SABnzbdClient implementation
├── api.py                 # API endpoints
└── tests/
    ├── test_models.py
    ├── test_service.py
    ├── test_clients.py
    └── test_api.py
```

---

## Dependencies

- `httpx` - Already in use for HTTP requests
- `dramatiq` - Already configured for task queue
- No new major dependencies needed

---

## Timeline Estimate

- Phase 1: 2-3 days (Database models)
- Phase 2: 3-4 days (Prowlarr client with multi-query search)
- Phase 3: 1-2 days (Prowlarr download integration)
- Phase 4: 3-4 days (Search service with multi-query search)
- Phase 5: 2-3 days (Download service)
- Phase 6: 2-3 days (API endpoints)
- Phase 7: 3-4 days (UI integration)

**Total**: ~16-23 days of development

---

## Success Criteria

1. ✅ Can configure Prowlarr connection (single configuration)
2. ✅ Can configure SABnzbd connection (for download status tracking)
3. ✅ Can manually search for media via Prowlarr (multiple search methods)
4. ✅ Search results are combined, deduplicated, and displayed (limited to 50)
5. ✅ User can select which result to download
6. ✅ Can initiate downloads via Prowlarr (only one active download per media)
7. ✅ Can check download status by polling SABnzbd API (manual refresh)
8. ✅ Can blacklist bad releases (manual)
9. ✅ Media status updates correctly (WANTED → DOWNLOADING → DOWNLOADED)
10. ✅ All download attempts are recorded
11. ✅ Download attempts show file paths and errors
12. ✅ Error messages displayed to user when Prowlarr or SABnzbd is unreachable

