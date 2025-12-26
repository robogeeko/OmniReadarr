# Post-Processing Plan

## Overview

Post-processing handles downloaded media files after they complete downloading. It performs format conversion, file organization, and metadata management.

## Components

### 1. Processing Configuration

**Model**: `ProcessingConfiguration` (new model in `core` app)

**Fields**:
- `id` (UUID, primary key)
- `name` (CharField, max_length=100) - User-friendly name (e.g., "Default Configuration")
- `completed_downloads_path` (CharField, max_length=500) - SABnzbd completed downloads directory (e.g., `/downloads/complete`)
- `library_base_path` (CharField, max_length=500) - Base library directory path (e.g., `/library`)
- `calibre_ebook_convert_path` (CharField, max_length=500, blank=True) - Path to `ebook-convert` binary (default: `ebook-convert`)
- `enabled` (BooleanField, default=True)
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)

**Admin**:
- Add ProcessingConfiguration to admin console
- Allow users to configure:
  - Completed downloads directory (where SABnzbd saves files)
  - Library base path (where processed files go)
  - Calibre ebook-convert path (optional, defaults to `ebook-convert`)
- Validate that paths exist and are readable/writable

**Notes**:
- Only one active processing configuration needed for MVP
- Can support multiple configurations in future

---

### 2. Ebook Conversion

**Utility**: `ebook-convert` from Calibre

**Requirements**:
- Calibre must be installed on the system
- `ebook-convert` must be available in PATH or configured path

**Process**:
1. Find downloaded file:
   - Check `DownloadAttempt.raw_file_path` if set
   - Otherwise, search in `completed_downloads_path` from configuration
   - Match by `DownloadAttempt.release_title` or download client ID
   - Update `raw_file_path` when found
2. Check file extension
3. If file is not `.epub`, convert to EPUB using `ebook-convert`
4. Save EPUB to same directory as original (or temp directory)
5. Update `DownloadAttempt.post_processed_file_path` with new EPUB path
6. Keep original file (don't delete)

**Supported Input Formats** (via Calibre):
- MOBI, AZW, AZW3
- PDF
- TXT, RTF
- FB2, LIT
- And others supported by Calibre

**Error Handling**:
- If conversion fails, log error and keep original file
- Mark download attempt with conversion error status
- Allow manual retry

**Implementation**:
- Create `processing/utils/ebook_converter.py`
- Function: `convert_to_epub(input_path: str, output_path: str) -> str`
- Use `subprocess` to call `ebook-convert`
- Validate output file exists and is valid EPUB

---

### 3. File Organization

**Directory Structure**:
```
{library_base_path}/
    {author_name}/
        {book_title}/
            {book_title}.epub
            {book_title}.opf
            {book_title}.jpg (cover image)
```

**Rules**:
- Author name: Use `Media.author` field, sanitized for filesystem
- Book title: Use `Media.title` field, sanitized for filesystem
- Ebooks and audiobooks with same title go to same directory
- Handle special characters: Replace invalid filesystem chars with `_` or remove
- Handle duplicate titles: Append ` (Year)` if needed

**Sanitization**:
- Remove or replace: `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`
- Trim whitespace
- Limit path length (filesystem dependent)
- Handle empty author/title gracefully

**Process**:
1. Get library base path from `ProcessingConfiguration`
2. Sanitize author name and book title
3. Create directory structure if it doesn't exist
4. Move/copy processed file to library directory
5. Update `Media.library_path` field with final path
6. Update `DownloadAttempt.post_processed_file_path` with library path

**File Discovery**:
- When organizing, look for file in:
  1. `DownloadAttempt.post_processed_file_path` (if EPUB conversion was done)
  2. `DownloadAttempt.raw_file_path` (if set)
  3. Search in `completed_downloads_path` from configuration
     - Match by `DownloadAttempt.release_title` or download client ID
     - Update `raw_file_path` when found

**Implementation**:
- Create `processing/utils/file_organizer.py`
- Function: `organize_to_library(media: Media, file_path: str) -> str`
- Handle directory creation with proper permissions
- Handle file moves/copies (configurable)

---

### 4. Metadata Files (OPF)

**OPF File Format**:
- XML format following OPF 2.0 specification
- Contains book metadata (title, author, description, identifiers, etc.)
- Includes cover image reference

**Required Fields**:
- `dc:title` - Book title
- `dc:language` - Language (from `Media.language`)
- `dc:identifier` - ISBN or other identifier (from `Media.isbn` or `Media.isbn13`)
- `dc:creator` - Author name with `opf:file-as` for sorting
- `dc:description` - Book description (from `Media.description`)

**Optional Fields**:
- `dc:date` - Publication date (from `Media.publication_date`)
- `dc:publisher` - Publisher (from `Media.publisher`)
- `dc:subject` - Genres/tags (from `Media.genres` or `Media.tags`)
- `guide/reference` - Cover image reference

**Cover Image**:
- Download cover from `Media.cover_url` if available
- Save as `{book_title}.jpg` in library directory
- If download fails, skip cover (don't fail entire process)
- Update `Media.cover_path` with local path

**Process**:
1. Gather metadata from `Media` model
2. Generate OPF XML content
3. Save OPF file as `{book_title}.opf` in library directory
4. Download cover image if `Media.cover_url` exists
5. Save cover as `{book_title}.jpg` in library directory

**Implementation**:
- Create `processing/utils/metadata_generator.py`
- Function: `generate_opf(media: Media, output_path: str) -> str`
- Function: `download_cover(media: Media, output_path: str) -> str | None`
- Use `xml.etree.ElementTree` or `lxml` for XML generation
- Use `httpx` or `requests` for cover download

---

### 5. Post-Processing Service

**Service Layer**: `processing/services/post_process.py`

**Functions**:

1. **`convert_to_epub(attempt_id: UUID) -> dict`**
   - Get `DownloadAttempt` by ID
   - Verify download is complete (`status == DOWNLOADED`)
   - Verify file exists at `raw_file_path`
   - Check file extension
   - If not EPUB, convert using `ebook-convert`
   - Update `post_processed_file_path` with EPUB path (or keep original if already EPUB)
   - Return success/error status

2. **`organize_to_library(attempt_id: UUID) -> dict`**
   - Get `DownloadAttempt` by ID
   - Verify file exists (use `post_processed_file_path` if set, otherwise `raw_file_path`)
   - Get `ProcessingConfiguration` for library path
   - Create directory structure: `{library_base_path}/{author}/{book_title}/`
   - Move file to library directory
   - Generate OPF metadata file
   - Download cover image (if `Media.cover_url` exists)
   - Save OPF and cover to library directory
   - Update `Media.library_path` with final library path
   - Update `Media.cover_path` with local cover path
   - Update `DownloadAttempt.post_processed_file_path` with library file path
   - Return success/error status

**Error Handling**:
- Each function should be wrapped in try/except
- Return dict with `success` (bool) and `message` (str) or `error` (str)
- Log errors for debugging
- Don't update status automatically - let UI handle it

**File Discovery**:
- When converting: Look for downloaded file in `completed_downloads_path` from configuration
- Match file by `DownloadAttempt.release_title` or `DownloadAttempt.download_client_download_id`
- Update `DownloadAttempt.raw_file_path` when file is found

---

### 6. Integration Points

**Manual Triggers (MVP)**:
- Add two buttons to media detail page:
  1. **"Convert to EPUB"** button
     - Calls API: `POST /api/processing/convert/{attempt_id}/`
     - Shows loading state while processing
     - Shows success/error message
  2. **"Organize to Library"** button
     - Calls API: `POST /api/processing/organize/{attempt_id}/`
     - Shows loading state while processing
     - Shows success/error message
     - Only enabled if EPUB conversion completed (or file already EPUB)

**API Endpoints**:
- `POST /api/processing/convert/{attempt_id}/` - Convert ebook to EPUB
  - Returns: `{"success": bool, "message": str}` or `{"error": str}`
- `POST /api/processing/organize/{attempt_id}/` - Organize to library and generate metadata
  - Returns: `{"success": bool, "message": str}` or `{"error": str}`

**Frontend Integration**:
- Add buttons to `media/templates/media/detail.html`
- Show buttons only for `DownloadAttempt` records with `status == DOWNLOADED`
- Disable "Organize to Library" if conversion hasn't been run (check `post_processed_file_path`)
- Show file paths and status after each operation

---

### 7. Models Updates

**DownloadAttempt Model**:
- `post_processed_file_path` (CharField, max_length=500, blank=True) - Already exists
- `post_process_status` (CharField, choices) - NEW
  - `pending`, `converting`, `organizing`, `generating_metadata`, `completed`, `failed`
- `post_process_error` (TextField, blank=True) - NEW - Error details

**Media Model**:
- `library_path` (CharField, max_length=500, blank=True) - NEW - Final library path
- `cover_path` (CharField, max_length=500, blank=True) - NEW - Local cover image path

---

### 8. Configuration

**Settings** (stored in `ProcessingConfiguration` model):
- `completed_downloads_path` - Where SABnzbd saves completed downloads
- `library_base_path` - Where processed files go
- `calibre_ebook_convert_path` - Path to `ebook-convert` (default: `ebook-convert`)

**Environment Variables** (optional defaults):
- `DEFAULT_COMPLETED_DOWNLOADS_PATH` - Default completed downloads path
- `DEFAULT_LIBRARY_PATH` - Default library base path
- `CALIBRE_EBOOK_CONVERT_PATH` - Override Calibre path

---

### 9. Testing

**Unit Tests**:
- Test ebook conversion with various formats
- Test file organization with special characters
- Test OPF generation with various metadata combinations
- Test cover download success/failure cases
- Test sanitization functions

**Integration Tests**:
- Test full post-processing pipeline
- Test error handling at each step
- Test with missing metadata fields

**Manual Testing**:
- Download a book and verify post-processing
- Check library directory structure
- Verify OPF file content
- Verify cover image

---

### 10. Implementation Phases

**Phase 1: Configuration & Manual Conversion (MVP)**
- Add `ProcessingConfiguration` model
- Add admin interface for configuration
- Implement ebook conversion utility
- Add "Convert to EPUB" button and API endpoint
- File discovery in completed downloads directory

**Phase 2: Manual Organization & Metadata**
- Implement file organization utility
- Implement OPF generation
- Implement cover download
- Add "Organize to Library" button and API endpoint
- Update media detail page with both buttons

**Phase 3: Automation (Future)**
- Add Dramatiq task
- Auto-trigger on download completion
- Status tracking and error handling

**Phase 4: Polish (Future)**
- Better error messages
- Progress tracking
- Retry mechanisms
- Batch operations

---

## File Structure

```
processing/
├── __init__.py
├── models.py (ProcessingConfiguration)
├── services/
│   └── post_process.py (PostProcessingService)
├── utils/
│   ├── ebook_converter.py
│   ├── file_organizer.py
│   ├── metadata_generator.py
│   └── file_discovery.py (find downloaded files)
├── api.py (API endpoints)
├── urls.py (URL routing)
├── tasks.py (Dramatiq tasks - future)
└── admin.py
```

---

## Dependencies

**New Python Packages**:
- `lxml` (optional, for better XML handling) - or use built-in `xml.etree.ElementTree`
- No new packages needed - use `subprocess` for `ebook-convert`, `httpx` for cover downloads

**System Requirements**:
- Calibre installed with `ebook-convert` in PATH
- Write access to library directory
- Sufficient disk space

---

## Error Scenarios

1. **Calibre not installed**: Log error, skip conversion, keep original file
2. **Conversion fails**: Log error, keep original file, continue with organization
3. **Library path not writable**: Log error, mark attempt as failed
4. **Cover download fails**: Log warning, continue without cover
5. **Metadata missing**: Use defaults or skip fields gracefully
6. **File already exists**: Handle overwrite or rename logic

---

## Future Enhancements

- Support for audiobook post-processing (different structure)
- Support for multiple library configurations
- Custom naming templates
- Metadata enhancement from external sources
- Batch post-processing
- Progress tracking UI
- Post-processing history/audit log

