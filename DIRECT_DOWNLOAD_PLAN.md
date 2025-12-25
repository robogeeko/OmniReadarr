# Direct Download via SABnzbd - Implementation Plan

## Overview

Instead of using Prowlarr's `send_to_download_client` API, we will download directly from SABnzbd using the download URL from search results. This bypasses Prowlarr's download client configuration requirements.

## Changes Required

### 1. SABnzbdClient - Add Download Method

**File**: `downloaders/clients/sabnzbd.py`

**New Method**: `add_download(url: str, category: str | None = None, priority: str | None = None) -> dict`

**SABnzbd API**:
- Endpoint: `GET /api?mode=addurl&name={url}&apikey={key}&output=json`
- Optional parameters:
  - `cat`: Category name (e.g., "books")
  - `priority`: Priority level ("Default", "High", "Normal", "Low")
  - `nzbname`: Custom name for the NZB

**Response Format**:
```json
{
  "status": true,
  "nzo_ids": ["SABnzbd_nzo_abc123"]
}
```

**Implementation**:
- Add `add_download()` method that calls SABnzbd's `addurl` mode
- Handle URL encoding for the download URL
- Return the `nzo_id` from the response
- Handle errors (invalid URL, SABnzbd errors, etc.)

**Error Handling**:
- Invalid URL format
- SABnzbd API errors
- Network timeouts
- Authentication failures

---

### 2. DownloadAttempt Model - No Changes Needed

**File**: `downloaders/models.py`

**Current Fields** (already sufficient):
- `download_url`: Stores the NZB URL from search results ✅
- `download_client`: References DownloadClientConfiguration ✅
- `download_client_download_id`: Will store SABnzbd `nzo_id` ✅
- `status`: Tracks download status ✅

**No migration needed** - existing fields are sufficient.

---

### 3. DownloadService - Remove Prowlarr Dependency

**File**: `downloaders/services/download.py`

**Changes to `initiate_download()` method**:

**Remove**:
- Prowlarr `send_to_download_client()` call
- Indexer verification logic (no longer needed)
- Prowlarr client dependency for downloads

**Add**:
- Direct call to `SABnzbdClient.add_download()` with the `download_url` from search result
- Extract `nzo_id` from SABnzbd response
- Store `nzo_id` in `download_client_download_id` field
- Set status to `DOWNLOADING` (or `SENT` if we want to keep the same flow)

**Updated Flow**:
1. Check for active downloads (unchanged)
2. Get SABnzbd configuration (unchanged)
3. Create `DownloadAttempt` record (unchanged)
4. **NEW**: Call `sabnzbd_client.add_download(result.download_url)`
5. **NEW**: Extract `nzo_id` from response
6. **NEW**: Update `DownloadAttempt` with `nzo_id` and set status to `DOWNLOADING`
7. Update media status to `DOWNLOADING` (unchanged)

**Error Handling**:
- Invalid download URL format
- SABnzbd connection errors
- SABnzbd API errors
- Update `DownloadAttempt` status to `FAILED` on error

**Constructor Changes**:
- Remove `prowlarr_client` parameter (no longer needed for downloads)
- Keep `sabnzbd_client_factory` parameter

---

### 4. SearchResult Validation

**File**: `downloaders/services/download.py` (in `initiate_download()`)

**Add validation**:
- Verify `result.download_url` is not empty
- Verify `result.protocol` is "usenet" (SABnzbd only supports Usenet)
- Verify download URL is a valid NZB URL (starts with `http://` or `https://`)

**Error Messages**:
- "Download URL is missing"
- "SABnzbd only supports Usenet downloads (protocol: {result.protocol})"
- "Invalid download URL format"

---

### 5. SABnzbdClient Tests

**File**: `downloaders/clients/tests.py`

**New Test Class**: `TestSABnzbdClientAddDownload`

**Test Cases**:
1. `test_add_download_success()` - Successful download addition
2. `test_add_download_with_category()` - Add download with category
3. `test_add_download_with_priority()` - Add download with priority
4. `test_add_download_invalid_url()` - Invalid URL handling
5. `test_add_download_api_error()` - SABnzbd API error handling
6. `test_add_download_authentication_error()` - Auth failure handling
7. `test_add_download_timeout()` - Timeout handling

**Mock Responses**:
- Success: `{"status": True, "nzo_ids": ["SABnzbd_nzo_abc123"]}`
- Error: `{"status": False, "error": "Invalid URL"}`

---

### 6. DownloadService Tests

**File**: `downloaders/services/test_download.py`

**Update Existing Tests**:
- Remove Prowlarr client mocks from `test_initiate_download_success()`
- Add SABnzbd client mock for `add_download()`
- Verify `add_download()` is called with correct URL
- Verify `nzo_id` is stored correctly

**New Test Cases**:
- `test_initiate_download_missing_url()` - Missing download URL
- `test_initiate_download_torrent_protocol()` - Torrent protocol rejection
- `test_initiate_download_sabnzbd_error()` - SABnzbd error handling

---

### 7. API Endpoint - No Changes Needed

**File**: `downloaders/api.py`

**No changes required** - the API endpoint calls `DownloadService.initiate_download()` which will handle the new flow internally.

---

## Implementation Steps

### Step 1: Add SABnzbd `add_download()` Method
1. Add `add_download()` method to `SABnzbdClient`
2. Implement URL encoding and API call
3. Parse response to extract `nzo_id`
4. Add error handling
5. Write unit tests

### Step 2: Update DownloadService
1. Remove Prowlarr `send_to_download_client()` call
2. Remove indexer verification logic
3. Add SABnzbd `add_download()` call
4. Add download URL validation
5. Update error handling
6. Update tests

### Step 3: Update Constructor Dependencies
1. Remove `prowlarr_client` from `DownloadService.__init__()`
2. Update all `DownloadService` instantiations
3. Update tests

### Step 4: Testing
1. Run unit tests
2. Test with real SABnzbd instance
3. Verify downloads are added correctly
4. Verify status tracking works

---

## Benefits

1. **Simpler Architecture**: No dependency on Prowlarr's download client configuration
2. **More Reliable**: Direct connection to SABnzbd eliminates Prowlarr as a potential failure point
3. **Better Error Messages**: Direct SABnzbd errors are clearer than Prowlarr proxy errors
4. **Easier Debugging**: Can test SABnzbd connection independently

## Limitations

1. **Usenet Only**: SABnzbd only supports Usenet (NZB files), not torrents
2. **Single Client**: Currently only supports SABnzbd (future: add NZBGet support)
3. **No Prowlarr Features**: Lose any Prowlarr-specific download features (if any)

## Future Enhancements

1. **NZBGet Support**: Add `NZBGetClient` with similar `add_download()` method
2. **Torrent Support**: Add torrent client support (qBittorrent, Transmission) for future
3. **Category Mapping**: Map media types to SABnzbd categories (books → "books" category)
4. **Priority Settings**: Allow users to set download priority per media type

