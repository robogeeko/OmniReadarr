# Download Status Tracking Options

## Problem Statement

After sending a download request to Prowlarr, we need to track the download status (progress, completion, failures). Prowlarr forwards downloads to configured download clients but doesn't maintain download status itself.

## Options Analysis

### Option 1: Poll Download Clients Directly (Recommended)

**Approach**: Connect directly to download client APIs (SABnzbd, qBittorrent, Transmission, NZBGet) to check download status.

**Pros**:
- ✅ Most direct and reliable method
- ✅ Real-time status information
- ✅ Can get detailed progress (percentage, speed, ETA)
- ✅ Can detect failures immediately
- ✅ Standard approach used by other applications
- ✅ Download clients have well-documented APIs

**Cons**:
- ❌ Need to know which download client was used
- ❌ Need download client connection info (host, port, API key)
- ❌ Must support multiple download client APIs
- ❌ Download clients configured in Prowlarr, not our app

**Implementation Requirements**:
1. **Store Download Client Info**: When Prowlarr sends download, it returns `downloadClientId`. We need to:
   - Query Prowlarr API to get download client configuration
   - Store download client type and connection info in `DownloadAttempt`
   - OR: Store download client connection info in our database

2. **Support Multiple Clients**:
   - **SABnzbd**: REST API (`/api?mode=queue&apikey={key}`)
   - **qBittorrent**: REST API (`/api/v2/torrents/info`)
   - **Transmission**: RPC API (JSON-RPC)
   - **NZBGet**: JSON-RPC API

3. **Polling Strategy**:
   - Poll every 30 seconds (configurable)
   - Match downloads by filename/title or download client's internal ID
   - Update `DownloadAttempt` status and progress

**Download Client APIs**:

#### SABnzbd API
```
GET /api?mode=queue&apikey={key}&output=json
```
Returns queue with jobs including:
- `status`: "Downloading", "Paused", "Completed"
- `mbleft`: MB remaining
- `timeleft`: Estimated time remaining
- `nzo_id`: Job ID
- `filename`: Job filename

#### qBittorrent API
```
GET /api/v2/torrents/info
POST /api/v2/auth/login (username/password)
```
Returns torrent list with:
- `hash`: Torrent hash
- `name`: Torrent name
- `state`: Status ("downloading", "completed", etc.)
- `progress`: Progress percentage (0-1)
- `dlspeed`: Download speed
- `eta`: Estimated time remaining

#### Transmission RPC API
```
POST /transmission/rpc
Body: {"method": "torrent-get", "arguments": {"fields": ["id", "name", "status", "percentDone"]}}
```
Returns torrents with:
- `id`: Torrent ID
- `name`: Torrent name
- `status`: Status code
- `percentDone`: Progress (0-1)

#### NZBGet API
```
POST /jsonrpc
Body: {"method": "status", "params": []}
```
Returns queue with:
- `NZBID`: Job ID
- `NZBName`: Job name
- `Status`: Status string
- `FileSizeMB`: Total size
- `RemainingSizeMB`: Remaining size

---

### Option 2: Query Prowlarr for Download Status

**Approach**: Check if Prowlarr has any API endpoints to track downloads it has sent.

**Pros**:
- ✅ Single API to query
- ✅ No need to manage multiple download client connections

**Cons**:
- ❌ Prowlarr doesn't track downloads after forwarding
- ❌ Would require Prowlarr to maintain download state (it doesn't)
- ❌ Less reliable than direct client polling

**Verdict**: ❌ **Not viable** - Prowlarr doesn't maintain download status

---

### Option 3: Monitor Download Directories

**Approach**: Watch download directories for completed files.

**Pros**:
- ✅ Simple - just check if file exists
- ✅ No API calls needed

**Cons**:
- ❌ Can't track progress (only completion)
- ❌ Can't detect failures
- ❌ Need to know download directory paths
- ❌ File naming might not match exactly
- ❌ Race conditions (file might be moved/renamed)

**Verdict**: ❌ **Not recommended** - Too unreliable, no progress tracking

---

### Option 4: Webhooks/Callbacks

**Approach**: Configure download clients to send webhooks on status changes.

**Pros**:
- ✅ Real-time updates
- ✅ No polling needed

**Cons**:
- ❌ Not all download clients support webhooks
- ❌ Requires webhook endpoint in our app
- ❌ More complex setup
- ❌ Security considerations (webhook authentication)

**Verdict**: ⚠️ **Future enhancement** - Good for real-time updates but complex for MVP

---

## Recommended Solution: Option 1 (Direct Download Client Polling)

### Implementation Plan

#### Step 1: Get Download Client Info from Prowlarr

When Prowlarr sends download, it returns response with download client info. We need to:

1. **Query Prowlarr API** for download client configuration:
   ```
   GET /api/v1/downloadclient
   ```
   Returns list of configured download clients with:
   - `id`: Download client ID
   - `name`: Client name
   - `implementation`: Client type ("Sabnzbd", "Qbittorrent", etc.)
   - `host`: Host address
   - `port`: Port number
   - `apiKey`: API key (if applicable)

2. **Store in DownloadAttempt**:
   - `download_client_type`: "sabnzbd", "qbittorrent", "transmission", "nzbget"
   - `download_client_host`: Host address
   - `download_client_port`: Port number
   - `download_client_api_key`: API key (encrypted)
   - `download_client_id`: ID from download client (for matching)

#### Step 2: Create Download Client Abstraction

Create abstract base class and implementations for each client:

```python
class DownloadClient(ABC):
    @abstractmethod
    def get_download_status(self, download_id: str) -> DownloadStatus:
        """Get status of a specific download"""
        pass
    
    @abstractmethod
    def list_downloads(self) -> list[DownloadStatus]:
        """List all active downloads"""
        pass

class SabnzbdClient(DownloadClient):
    def __init__(self, host: str, port: int, api_key: str):
        self.base_url = f"http://{host}:{port}"
        self.api_key = api_key
    
    def get_download_status(self, nzo_id: str) -> DownloadStatus:
        # Query SABnzbd API
        pass

class QbittorrentClient(DownloadClient):
    # Similar implementation
    pass
```

#### Step 3: Polling Logic

```python
def get_download_status(attempt: DownloadAttempt) -> DownloadStatus:
    client = get_download_client(attempt)
    
    # Try to match by download client ID first
    if attempt.download_client_id:
        status = client.get_download_status(attempt.download_client_id)
        if status:
            return status
    
    # Fallback: search by filename/title
    downloads = client.list_downloads()
    for download in downloads:
        if matches_release(attempt.release_title, download.name):
            return download
    
    return None  # Not found
```

#### Step 4: Update DownloadAttempt

When polling detects status change:
- Update `DownloadAttempt.status`
- Update `DownloadAttempt.raw_file_path` when completed
- Update `Media.status` to "DOWNLOADED" when completed

---

## DownloadClientConfiguration Model

**Add back to database models**:

```python
class DownloadClientConfiguration(BaseModel):
    id = UUID primary key
    name = CharField(max_length=100)  # User-friendly name
    client_type = CharField(choices)  # "sabnzbd", "qbittorrent", "transmission", "nzbget"
    host = CharField(max_length=255)
    port = IntegerField()
    use_ssl = BooleanField(default=False)
    api_key = CharField(max_length=255)  # Encrypted
    username = CharField(max_length=100, blank=True)  # For qBittorrent/Transmission
    password = CharField(max_length=255, blank=True)  # Encrypted, for qBittorrent/Transmission
    enabled = BooleanField(default=True)
    priority = IntegerField(default=0)  # For multiple clients
    created_at = DateTimeField(auto_now_add)
    updated_at = DateTimeField(auto_now)
```

**Notes**:
- User configures download clients in our app UI
- Can have multiple download clients (for failover/priority)
- API keys and passwords should be encrypted
- This matches Sonarr/Radarr pattern

---

## How Sonarr and Radarr Handle This

**Key Finding**: Sonarr and Radarr **store download client configuration in their own database** and connect directly to download clients.

**Their Approach**:
1. **User configures download clients in Sonarr/Radarr UI**:
   - Download client type (SABnzbd, qBittorrent, Transmission, etc.)
   - Host, port, API key/credentials
   - Category settings
   - Download directory mappings

2. **Configuration stored in database** (not queried from Prowlarr)

3. **Direct polling of download clients**:
   - Poll every 60 seconds (default)
   - Match downloads by category + filename/title
   - Track progress and completion

4. **Post-processing on completion**:
   - Import files
   - Rename according to naming conventions
   - Move to library directories

**Why This Approach**:
- ✅ **Simpler**: No need to query Prowlarr for download client config
- ✅ **More control**: Can configure multiple download clients, priorities, categories
- ✅ **Standard pattern**: This is how all *arr applications work
- ✅ **Reliable**: Direct connection to download client is most reliable

**Trade-off**:
- ⚠️ User must configure download clients in both Prowlarr AND our app
- ⚠️ Configuration can get out of sync
- ✅ But this is acceptable - it's the standard pattern

---

## Recommendation

**Follow Sonarr/Radarr pattern: Store download client configuration in our database**

**Use Option 1 (Direct Download Client Polling)** with the following approach:

1. **Add DownloadClientConfiguration model** (store download client config in our database)
2. **User configures download clients in our app** (similar to Sonarr/Radarr)
3. **When initiating download**: Select appropriate download client based on media type/protocol
4. **Store download client reference** in `DownloadAttempt` model:
   - `download_client` (ForeignKey to DownloadClientConfiguration)
   - `download_client_download_id` (ID from download client response, e.g., nzo_id for SABnzbd, hash for qBittorrent)

3. **Create download client abstraction** with implementations for:
   - SABnzbd
   - qBittorrent
   - Transmission
   - NZBGet

4. **Poll download clients** every 30 seconds (on status check API call)

5. **Match downloads** by:
   - Download client ID (preferred)
   - Filename/title matching (fallback)

This is the cleanest and most reliable approach, and it's what other applications (like *arr apps) do.

