# Media API Plan

## Overview

This document outlines the API design for managing media status and adding items to the wanted list.

## Database Changes

### Add `provider` and `external_id` fields to Media model

- **`provider` Field**:
  - **Field Type**: `CharField(max_length=50)`
  - **Purpose**: Provider name (e.g., `"openlibrary"`, `"google_books"`)
  - **Index**: Yes (composite index with external_id)
  - **Nullable**: No (required field)

- **`external_id` Field**:
  - **Field Type**: `CharField(max_length=500)`
  - **Purpose**: Provider-specific identifier (e.g., `"OL123456W"`, `"abc123"`)
  - **Index**: Yes (composite index with provider)
  - **Nullable**: No (required field)

- **Composite Index**: `(provider, external_id)` for fast lookups
- **Uniqueness**: Not unique globally (same provider+external_id can exist as both Book and Audiobook)

**Rationale**: 
- Normalized design separates concerns
- Allows efficient queries on provider or external_id independently
- Composite index enables fast lookups by both fields together
- More flexible for future queries and filtering

## API Endpoints

### 1. Get Media Status

**Endpoint**: `GET /api/media/status/`

**Query Parameters**:
- `providers` (required): Comma-separated list of provider names
- `external_ids` (required): Comma-separated list of external IDs
  - Example: `?providers=openlibrary,openlibrary&external_ids=OL123456W,OL789012W`
  - Both lists must have the same length and be paired by index

**Alternative**: `POST /api/media/status/` (for large lists)

**Request Body** (POST only):
```json
{
  "items": [
    {
      "provider": "openlibrary",
      "external_id": "OL123456W"
    },
    {
      "provider": "openlibrary",
      "external_id": "OL789012W"
    }
  ]
}
```

**Response**:
```json
{
  "statuses": [
    {
      "provider": "openlibrary",
      "external_id": "OL123456W",
      "exists": true,
      "media_type": "book",
      "status": "wanted",
      "status_display": "Wanted"
    },
    {
      "provider": "openlibrary",
      "external_id": "OL789012W",
      "exists": false,
      "media_type": null,
      "status": null,
      "status_display": null
    }
  ]
}
```

**Logic**:
- Query both Book and Audiobook tables for each (provider, external_id) pair
- Return the first match found (or null if none)
- Include both the status code and human-readable display
- Response order matches request order

**Error Handling**:
- 400: Missing or invalid providers/external_ids parameters, mismatched list lengths
- 200: Always returns success, with null values for non-existent items

---

### 2. Add Wanted Media

**Endpoint**: `POST /api/media/wanted/`

**Request Body**:
```json
{
  "provider": "openlibrary",
  "external_id": "OL123456W",
  "media_type": "book",
  "metadata": {
    "provider": "openlibrary",
    "provider_id": "OL123456W",
    "title": "Example Book",
    "authors": ["Author Name"],
    "description": "...",
    "publisher": "...",
    "publication_date": "2020-01-01",
    "cover_url": "https://...",
    "language": "en",
    "genres": ["Fiction"],
    "tags": [],
    "isbn": "1234567890",
    "isbn13": "1234567890123",
    "page_count": 300,
    "edition": "1st",
    "narrators": [],
    "duration_seconds": null,
    "bitrate": null,
    "chapters": null
  }
}
```

**Response (Success)**:
```json
{
  "success": true,
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "wanted",
  "status_display": "Wanted"
}
```

**Response (Already Exists)**:
```json
{
  "success": false,
  "error": "already_exists",
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "downloading",
  "status_display": "Downloading"
}
```

**Response (Error)**:
```json
{
  "success": false,
  "error": "invalid_media_type",
  "message": "Media type must be 'book' or 'audiobook'"
}
```

**Logic**:
- Check if media with this (provider, external_id) combination already exists (for the specified media_type)
- If exists, return current status
- If not exists, create new Book or Audiobook with status="wanted"
- Store provider and external_id fields from request
- Store full metadata from request
- Return created/existing media ID and status

**Error Handling**:
- 400: Missing required fields (provider, external_id, media_type), invalid media_type, invalid metadata
- 409: Media already exists (optional - could also return 200 with exists flag)
- 500: Server error

---

## Implementation Steps

1. **Add `provider` and `external_id` fields to Media model**
   - Add both field definitions
   - Create migration
   - Add composite index on (provider, external_id)

2. **Create API views**
   - `get_media_status(request)` - handles GET/POST for status lookup
   - `add_wanted_media(request)` - handles POST for adding media

3. **Create URL routes**
   - `/api/media/status/` → `get_media_status`
   - `/api/media/wanted/` → `add_wanted_media`

4. **Add serializers/validation**
   - Validate provider and external_id are provided
   - Validate metadata structure
   - Handle BookMetadata conversion

5. **Write tests**
   - Test status lookup for existing/non-existing items
   - Test adding new media
   - Test duplicate prevention
   - Test error cases

---

## Questions to Consider

1. **Provider validation**: Should we validate provider names against a known list?
   - **Decision**: Validate against ProviderType enum for consistency

2. **Uniqueness**: Should (provider, external_id) be unique globally, or per media_type?
   - **Decision**: Per media_type (same book can be both ebook and audiobook)

3. **Metadata storage**: Should we store full metadata or just essential fields?
   - **Decision**: Store full metadata for future use

4. **Status lookup**: Should we return both Book and Audiobook statuses if both exist?
   - **Decision**: Return first match found (can enhance later to return array of matches)

5. **Query format**: GET with query params vs POST with body?
   - **Decision**: Support both - GET for simple cases, POST for large lists

5. **API versioning**: Should we version the API from the start?
   - **Decision**: Start simple, add versioning later if needed

