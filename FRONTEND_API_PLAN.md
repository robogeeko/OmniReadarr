# Frontend API Integration Plan

## Overview

This document outlines the plan for integrating the media status and add-to-wanted APIs into the frontend search interface.

**✅ API Enhancement Complete:** The status API now returns both book and audiobook statuses in a single call, simplifying frontend implementation significantly.

## Key Improvements

1. **Single API Call:** Status API returns both book and audiobook statuses in one response
2. **Simplified Logic:** Frontend directly accesses `status.book` and `status.audiobook` objects
3. **Better Performance:** No need for multiple API calls or filtering
4. **Clear Structure:** Separate status objects make code more maintainable

## Current State

- Search page displays results in a table
- No status checking or "WANTED" buttons currently implemented
- Search results come from provider APIs (OpenLibrary, etc.)

## Goals

1. Display status for each search result (ebook and audiobook separately)
2. Show "WANTED" button if item doesn't exist, or show current status if it does
3. Allow users to add items to wanted list via button click
4. Update UI dynamically without page refresh
5. Preserve search results and form state during interactions

---

## Implementation Steps

### Step 1: Update Search Results Display

**Add columns to results table:**
- Add "Ebook" column
- Add "Audiobook" column
- Each column will show either:
  - "WANTED" button (if item doesn't exist)
  - Status text (if item exists: "Wanted", "Searching", "Downloading", etc.)

**Template Changes:**
- Update `search/templates/search/search.html`
- Add two new `<th>` elements for "Ebook" and "Audiobook"
- Add two new `<td>` elements per result row
- Include data attributes for metadata and provider info

---

### Step 2: Call Status API After Search

**When:** After search results are displayed

**What to do:**
1. Extract `provider` and `external_id` (from `provider_id`) from each search result
2. Build array of `{provider, external_id}` objects
3. Call `POST /api/media/status/` with the array
4. Store status results in JavaScript data structure
5. Update UI to show correct buttons/labels

**API Call Example:**
```javascript
const items = results.map(result => ({
    provider: result.provider,  // e.g., "openlibrary"
    external_id: result.provider_id  // e.g., "OL123456W"
}));

fetch('/api/media/status/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({ items })
})
.then(response => response.json())
.then(data => {
    // data.statuses is array matching items order
    // Update UI with statuses
});
```

**Status Mapping:**
- For each result, extract both `book` and `audiobook` status objects from API response
- Map `book` status to ebook column
- Map `audiobook` status to audiobook column
- Each status object contains: `exists`, `status`, `status_display`
- **Key improvement:** Single API call provides all needed information

---

### Step 3: Render Buttons/Labels Based on Status

**Logic:**
```javascript
function renderStatusCell(statusObj, mediaType, metadata) {
    if (!statusObj || !statusObj.exists) {
        // Show "Mark as Wanted" button
        return `<button class="want-button" 
                        data-media-type="${mediaType}"
                        data-provider="${metadata.provider}"
                        data-external-id="${metadata.provider_id}"
                        data-metadata='${JSON.stringify(metadata)}'
                        aria-label="Mark as Wanted: ${metadata.title}">
                    Mark as Wanted
                </button>`;
    } else {
        // Show status badge with appropriate styling
        const statusClass = `status-badge ${statusObj.status}`;
        const statusText = getStatusText(statusObj.status);
        return `<span class="${statusClass}" 
                      aria-label="Status: ${statusText}">
                    ${statusText}
                </span>`;
    }
}

function getStatusText(status) {
    const statusTexts = {
        'wanted': 'Already Wanted',
        'searching': 'Searching...',
        'downloading': 'Downloading...',
        'imported': 'Imported',
        'archived': 'Archived'
    };
    return statusTexts[status] || status;
}
```

**For each search result:**
- Find matching status from API response (by provider + external_id)
- Extract `book` status object → render ebook column using `status.book`
- Extract `audiobook` status object → render audiobook column using `status.audiobook`
- Each column independently shows button or status badge

**Key Improvement:** 
- ✅ Single API call returns both book and audiobook statuses
- No need for multiple API calls or filtering
- Frontend can directly access `status.book` and `status.audiobook` for each result

---

### Step 4: Handle WANTED Button Click

**Event Handler:**
```javascript
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('want-button')) {
        const button = e.target;
        const mediaType = button.dataset.mediaType;
        const provider = button.dataset.provider;
        const externalId = button.dataset.externalId;
        const metadata = JSON.parse(button.dataset.metadata);
        
        // Disable button, show loading state
        button.disabled = true;
        button.textContent = 'Adding...';
        
        // Call API
        fetch('/api/media/wanted/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                provider: provider,
                external_id: externalId,
                media_type: mediaType,
                metadata: metadata
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update button to show status
                button.textContent = data.status_display;
                button.classList.remove('want-button');
                button.classList.add('status-text');
                button.disabled = true;
            } else if (data.error === 'already_exists') {
                // Item was added by another request, show current status
                button.textContent = data.status_display;
                button.classList.remove('want-button');
                button.classList.add('status-text');
                button.disabled = true;
            } else {
                // Show error, re-enable button
                alert('Error: ' + (data.message || data.error));
                button.disabled = false;
                button.textContent = 'WANTED';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error adding to wanted list');
            button.disabled = false;
            button.textContent = 'WANTED';
        });
    }
});
```

---

### Step 5: Update Search Results Data Structure

**Current result structure:**
```python
{
    "title": "...",
    "authors": "...",
    "provider": "openlibrary",
    "provider_id": "OL123456W",
    # ... other fields
}
```

**Need to add:**
- Store full metadata object for API calls
- Include provider and external_id explicitly
- Make metadata available to JavaScript

**Template changes:**
- Include metadata as JSON in data attributes or script tags
- Use Django's `json_script` filter for safe JSON serialization

---

### Step 6: Handle Edge Cases

**Multiple status checks:**
- Since same external_id can exist as both book and audiobook
- Need to check status for both media types separately
- Current API returns first match, so we may need to:
  - Call status API with items marked as "book" type
  - Call status API again with items marked as "audiobook" type
  - OR: Enhance backend to return both statuses if they exist

**Race conditions:**
- User clicks button multiple times → disable after first click
- Another user adds same item → handle "already_exists" response
- Network errors → show error message, allow retry

**Loading states:**
- Show "Adding..." while API call in progress
- Disable button during request
- Handle timeout/network errors gracefully

---

## Detailed Implementation Plan

### Phase 1: Update Template Structure

1. **Add columns to table header**
   ```html
   <th scope="col" class="column-ebook">Ebook</th>
   <th scope="col" class="column-audiobook">Audiobook</th>
   ```

2. **Add cells to each result row**
   ```html
   <td class="field-ebook" data-result-index="{{ forloop.counter0 }}">
       <!-- Will be populated by JavaScript -->
   </td>
   <td class="field-audiobook" data-result-index="{{ forloop.counter0 }}">
       <!-- Will be populated by JavaScript -->
   </td>
   ```

3. **Include metadata in data attributes**
   ```html
   <tr data-provider="{{ result.provider }}" 
       data-external-id="{{ result.provider_id }}"
       data-metadata="{{ result.metadata_json|safe }}">
   ```

### Phase 2: JavaScript Status Checking

1. **After search results displayed:**
   - Extract provider and external_id from each result
   - Build items array for status API: `[{provider, external_id}, ...]`
   - Call status API **once** with all items
   - API returns both book and audiobook statuses for each item
   - Store statuses in a map: `{provider:external_id: statusObject}`
   - Each statusObject contains: `{book: {...}, audiobook: {...}}`

2. **Render status cells:**
   - For each result row, find matching status object by provider + external_id
   - Render ebook column using `statusObject.book`
   - Render audiobook column using `statusObject.audiobook`
   - Each column independently renders button or status badge

### Phase 3: Button Click Handling

1. **Attach event listeners:**
   - Use event delegation on document or results container
   - Listen for clicks on `.want-button` class

2. **Handle click:**
   - Extract metadata from button data attributes
   - Call add_wanted_media API
   - Update button state based on response
   - No page refresh needed

### Phase 4: Status API Enhancement ✅ COMPLETE

**Enhancement implemented:** Status API now returns both book and audiobook statuses

**Current implementation:**
- Single API call returns both statuses for each item
- Response includes separate `book` and `audiobook` objects
- Each object contains: `exists`, `status`, `status_display`
- No need for multiple API calls or filtering

**Benefits:**
- Reduced API calls (1 instead of 2)
- Simpler frontend logic
- Better performance
- Clearer data structure
- Frontend can directly access `status.book` and `status.audiobook`

---

## API Integration Details

### Status API Usage

**Endpoint:** `POST /api/media/status/`

**Request:**
```json
{
  "items": [
    {"provider": "openlibrary", "external_id": "OL123456W"},
    {"provider": "openlibrary", "external_id": "OL789012W"}
  ]
}
```

**Response:**
```json
{
  "statuses": [
    {
      "provider": "openlibrary",
      "external_id": "OL123456W",
      "book": {
        "exists": true,
        "status": "wanted",
        "status_display": "Wanted"
      },
      "audiobook": {
        "exists": false,
        "status": null,
        "status_display": null
      }
    },
    {
      "provider": "openlibrary",
      "external_id": "OL789012W",
      "book": {
        "exists": false,
        "status": null,
        "status_display": null
      },
      "audiobook": {
        "exists": true,
        "status": "downloading",
        "status_display": "Downloading"
      }
    }
  ]
}
```

**Note:** ✅ API enhanced - single call returns both book and audiobook statuses in separate objects

### Add Wanted API Usage

**Endpoint:** `POST /api/media/wanted/`

**Request:**
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
    // ... full metadata
  }
}
```

**Response (Success):**
```json
{
  "success": true,
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "wanted",
  "status_display": "Wanted"
}
```

**Response (Already Exists):**
```json
{
  "success": false,
  "error": "already_exists",
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "downloading",
  "status_display": "Downloading"
}
```

---

## UI/UX Considerations

### Button States

1. **Initial state:** "Mark as Wanted" button (if item doesn't exist)
2. **Loading state:** "Adding..." (disabled, during API call)
3. **Success state:** Status badge with appropriate text and color (e.g., "Already Wanted", "Searching...")
4. **Error state:** Show error, restore button to "Mark as Wanted"

### Visual Feedback

- Disable button immediately on click
- Show loading spinner or text
- Update button to status text on success
- Show error message on failure
- Use CSS classes for styling different states

### Accessibility

- Use semantic HTML (`<button>` not `<div>`)
- Include ARIA labels for screen readers
- Ensure keyboard navigation works
- Provide clear error messages

---

## Testing Checklist

- [ ] Status API called after search completes (single call)
- [ ] Statuses correctly mapped to ebook/audiobook columns (using book/audiobook objects)
- [ ] "Mark as Wanted" buttons shown for non-existent items
- [ ] Status badges shown for existing items with correct colors
- [ ] Button click calls add_wanted_media API
- [ ] Button updates to status badge after success
- [ ] Error handling works correctly
- [ ] Multiple clicks prevented (button disabled)
- [ ] Race conditions handled (already_exists response)
- [ ] Network errors handled gracefully
- [ ] Page doesn't refresh during interactions
- [ ] Search results preserved during button clicks
- [ ] Form state preserved (title, author, media type, provider)
- [ ] Both book and audiobook statuses displayed correctly

---

## Future Enhancements

1. **Batch status updates:** Refresh all statuses periodically
2. **Optimistic updates:** Update UI immediately, rollback on error
3. **Status polling:** Auto-refresh status for items being downloaded
4. **Toast notifications:** Show success/error messages as toasts
5. **Undo functionality:** Allow removing items from wanted list
6. **Bulk actions:** Select multiple items and add all at once

---

## Implementation Order

1. **Update search view** to include metadata_json in results
2. **Update template** to add ebook/audiobook columns with proper structure
3. **Add JavaScript** to call status API after search (single call)
4. **Render buttons/labels** based on status (using book/audiobook objects)
5. **Add click handlers** for "Mark as Wanted" buttons
6. **Update button states** after successful API calls
7. **Test and refine** error handling and edge cases

---

## Questions to Resolve

1. **Status API enhancement:** ✅ RESOLVED
   - **Solution:** Backend API enhanced to return both book and audiobook statuses in single call
   - **Benefit:** Simpler frontend implementation, better performance, single API call

2. **Metadata storage:** How to pass full metadata to JavaScript?
   - **Solution:** Use `json_script` filter or data attributes with JSON encoding

3. **CSRF token:** How to get CSRF token for API calls?
   - **Solution:** Include in template via `{% csrf_token %}` or use Django's `getCookie('csrftoken')`

4. **Error display:** Show errors inline or as alerts?
   - **Recommendation:** Start with alerts, enhance to inline messages later

