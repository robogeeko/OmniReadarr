# Download Plan Review - Remaining Issues

## Issues to Discuss

### 1. ProwlarrConfiguration Selection Logic (Issue #5)

**Current State**: Plan specifies only one ProwlarrConfiguration record allowed.

**Questions to Resolve**:
- How do we enforce single record constraint? (Database constraint, application logic, or admin UI restriction?)
- What happens if user tries to create a second configuration?
- Should we add a unique constraint or just enforce in application logic?

**Recommendation**: 
- Add database-level unique constraint if only one record should ever exist
- Or use application logic to prevent multiple records
- Admin UI should show clear message if trying to add second configuration

---

### 2. Prowlarr Search API Details (Issue #15) - RESOLVED

**Status**: ✅ Researched and documented

**Findings**:
- Search endpoint: `GET /api/v1/search`
- Query parameter is `q` (not `query`)
- Category parameter is `cat` (not `categories`)
- Books category ID: `7000`
- API key sent in header: `X-Api-Key: {api_key}` (not query parameter)
- Download command: `POST /api/v1/command` with body `{"name": "DownloadRelease", "indexerId": {id}, "guid": "{guid}"}`

**Documented in Plan**:
- Complete API endpoint documentation added
- Request/response examples included
- All query parameters documented
- Field descriptions for search results added

---

## Resolved Issues

All other issues from the original review have been addressed:
- ✅ Scoring references removed
- ✅ DownloadClientConfiguration removed
- ✅ Prowlarr integration approach clarified (using send-to-client feature)
- ✅ DownloadAttempt status clarified (uses "downloaded" not "completed")
- ✅ Error handling simplified (show user error messages)
- ✅ Duplicate file structure removed
- ✅ Quality score field removed
- ✅ Prowlarr API authentication documented
- ✅ Concurrent download restriction added (one per media)
- ✅ Search result limit added (50 results)
- ✅ File path detection and download completion detection deferred for discussion
