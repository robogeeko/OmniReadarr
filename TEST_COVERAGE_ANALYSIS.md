# Test Coverage Analysis

## Files Completely Untested and Easy to Test

### 1. `media/utils.py` ⭐⭐⭐ (Very Easy)
**Function**: `get_media_by_id(media_id: UUID) -> Media | None`

**Why Easy**: Pure function with database queries, straightforward logic
- Test: Returns Book when Book exists
- Test: Returns Audiobook when Audiobook exists  
- Test: Returns None when neither exists
- Test: Handles UUID format correctly

**Estimated Test Lines**: ~30-40 lines

---

### 2. `downloaders/clients/results.py` ⭐⭐⭐ (Very Easy)
**Classes**: `QueueItem`, `HistoryItem`, `JobStatus`

**Why Easy**: Dataclasses with `from_dict()` class methods - pure data transformation
- Test `QueueItem.from_dict()` with various data formats
- Test `HistoryItem.from_dict()` with string/int size conversions
- Test `JobStatus.from_queue_item()` conversion
- Test `JobStatus.from_history_item()` conversion
- Test edge cases (missing fields, None values, type conversions)

**Estimated Test Lines**: ~80-100 lines

---

### 3. `indexers/prowlarr/results.py` ⭐⭐⭐ (Very Easy)
**Classes**: `SearchResult`, `IndexerCapabilities`, `IndexerInfo`

**Why Easy**: Dataclasses with `from_dict()` methods - pure data transformation
- Test `SearchResult.from_dict()` with various date formats
- Test `SearchResult.from_dict()` handles missing optional fields
- Test `IndexerCapabilities.from_dict()` with defaults
- Test `IndexerInfo.from_dict()` nested capabilities
- Test date parsing edge cases (Z timezone, invalid dates)

**Estimated Test Lines**: ~60-80 lines

---

### 4. `search/providers/results.py` ⭐⭐⭐ (Very Easy)
**Classes**: `BaseNormalizedMetadata`, `BookMetadata`

**Why Easy**: Dataclasses with `to_dict()` and `from_dict()` methods
- Test `BookMetadata.to_dict()` serialization
- Test `BookMetadata.from_dict()` with various date formats
- Test `BookMetadata.from_dict()` handles series_index conversion
- Test edge cases (None values, empty strings, date parsing)

**Estimated Test Lines**: ~70-90 lines

---

### 5. `search/providers/registry.py` ⭐⭐ (Easy)
**Functions**: `get_provider_instance()`, `get_enabled_providers()`

**Why Easy**: Simple factory functions with database queries
- Test `get_provider_instance()` returns correct provider type
- Test `get_provider_instance()` raises ValueError for unknown type
- Test `get_provider_instance()` passes config correctly
- Test `get_enabled_providers()` filters by media_type
- Test `get_enabled_providers()` orders by priority

**Estimated Test Lines**: ~50-70 lines

---

### 6. `media/views.py` - `format_duration()` function ⭐⭐⭐ (Very Easy)
**Function**: `format_duration(seconds: int) -> str`

**Why Easy**: Pure function with simple logic
- Test: Formats hours correctly (e.g., 3661 seconds = "1h 1m 1s")
- Test: Formats minutes only (e.g., 125 seconds = "2m 5s")
- Test: Formats seconds only (e.g., 45 seconds = "45s")
- Test: Handles zero correctly
- Test: Handles large values

**Estimated Test Lines**: ~20-30 lines

**Note**: The view functions themselves are harder to test (require Django request/response setup)

---

### 7. `core/models.py` - `BaseModel` and `Media` ⭐⭐ (Easy)
**Classes**: `BaseModel`, `MediaStatus`, `Media`

**Why Easy**: Django models with simple save() logic
- Test `BaseModel` creates UUID automatically
- Test `BaseModel` sets created_at/updated_at
- Test `Media.save()` sets sort_title from title if empty
- Test `MediaStatus` choices are correct
- Test `Media` field defaults and validators

**Estimated Test Lines**: ~40-60 lines

---

### 8. `core/models_processing.py` - `ProcessingConfiguration` ⭐⭐ (Easy)
**Class**: `ProcessingConfiguration`

**Why Easy**: Simple Django model
- Test model creation with defaults
- Test `__str__()` method
- Test field validations
- Test ordering

**Estimated Test Lines**: ~20-30 lines

---

## Files That Are Harder to Test (But Still Possible)

### `downloaders/services/search.py` ⭐ (Moderate)
**Class**: `SearchService`

**Why Harder**: Requires mocking ProwlarrClient, has complex logic with multiple queries
- Would need to mock `ProwlarrClient.search()`
- Test query building logic
- Test deduplication
- Test blacklist filtering
- Test sorting

**Estimated Test Lines**: ~150-200 lines

---

### View Functions ⭐ (Moderate)
**Files**: `media/views.py`, `search/views.py`, `downloaders/views.py`, `indexers/views.py`

**Why Harder**: Require Django request/response setup, template rendering
- Need to set up Django test client
- Need to mock database queries
- Need to verify template context
- More integration-style tests

**Estimated Test Lines**: ~50-100 lines per view

---

## Summary

**Top 5 Easiest to Test (Recommended Priority)**:

1. **`media/utils.py`** - Single function, ~30-40 lines
2. **`media/views.py` - `format_duration()`** - Pure function, ~20-30 lines  
3. **`downloaders/clients/results.py`** - Dataclasses, ~80-100 lines
4. **`indexers/prowlarr/results.py`** - Dataclasses, ~60-80 lines
5. **`search/providers/results.py`** - Dataclasses, ~70-90 lines

**Total Estimated Lines for Top 5**: ~260-340 lines of test code

These files are all **pure functions or dataclasses** with minimal dependencies, making them ideal for unit testing. They would provide good coverage with relatively little effort.

