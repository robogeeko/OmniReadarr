# Button UX Design - Search Results Table

## Button States and Text

### Status-Based Button Text

| Status | Button Text | Description |
|--------|------------|-------------|
| **Not in DB** | "Mark as Wanted" | Action button - user can click to add |
| **Wanted** | "Already Wanted" | Informational - item is in wanted list |
| **Searching** | "Searching..." | In progress - actively searching for downloads |
| **Downloading** | "Downloading..." | In progress - file is being downloaded |
| **Imported** | "Imported" | Completed - item is in library |
| **Archived** | "Archived" | Completed - item has been archived |

### Button Types

1. **Action Button** (Not in DB)
   - Text: "Mark as Wanted"
   - Clickable: Yes
   - Purpose: Add item to wanted list

2. **Status Badge** (In DB)
   - Text: Status-specific text (see above)
   - Clickable: No (disabled)
   - Purpose: Show current status

---

## Color Scheme

### Color Palette

**Primary Action (Mark as Wanted):**
- Background: `#417690` (Django admin blue - matches existing theme)
- Text: `#ffffff` (white)
- Hover: `#345f75` (darker blue)
- Border: `#417690`

**Status Colors:**

1. **Wanted** (Informational)
   - Background: `#e8f4f8` (light blue)
   - Text: `#417690` (blue)
   - Border: `#417690`
   - Icon: ✓ (checkmark)

2. **Searching** (In Progress)
   - Background: `#fff3cd` (light yellow)
   - Text: `#856404` (dark yellow/brown)
   - Border: `#ffc107` (yellow)
   - Icon: 🔍 (search icon) or spinner

3. **Downloading** (In Progress)
   - Background: `#d1ecf1` (light cyan)
   - Text: `#0c5460` (dark cyan)
   - Border: `#17a2b8` (cyan)
   - Icon: ⬇️ (download icon) or spinner

4. **Imported** (Success)
   - Background: `#d4edda` (light green)
   - Text: `#155724` (dark green)
   - Border: `#28a745` (green)
   - Icon: ✓ (checkmark)

5. **Archived** (Neutral)
   - Background: `#e2e3e5` (light gray)
   - Text: `#383d41` (dark gray)
   - Border: `#6c757d` (gray)
   - Icon: 📦 (archive icon)

---

## Visual Design

### Button Styles

**Action Button (Mark as Wanted):**
```css
.want-button {
    background-color: #417690;
    color: white;
    border: 1px solid #417690;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: bold;
    transition: background-color 0.2s;
}

.want-button:hover {
    background-color: #345f75;
}

.want-button:active {
    background-color: #2a4d5f;
}

.want-button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
    opacity: 0.6;
}
```

**Status Badge Styles:**
```css
.status-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    border: 1px solid;
    white-space: nowrap;
}

.status-badge.wanted {
    background-color: #e8f4f8;
    color: #417690;
    border-color: #417690;
}

.status-badge.searching {
    background-color: #fff3cd;
    color: #856404;
    border-color: #ffc107;
}

.status-badge.downloading {
    background-color: #d1ecf1;
    color: #0c5460;
    border-color: #17a2b8;
}

.status-badge.imported {
    background-color: #d4edda;
    color: #155724;
    border-color: #28a745;
}

.status-badge.archived {
    background-color: #e2e3e5;
    color: #383d41;
    border-color: #6c757d;
}
```

**Loading State:**
```css
.want-button.loading {
    background-color: #6c757d;
    cursor: wait;
    position: relative;
}

.want-button.loading::after {
    content: "...";
    animation: dots 1.5s steps(4, end) infinite;
}

@keyframes dots {
    0%, 20% { content: "."; }
    40% { content: ".."; }
    60%, 100% { content: "..."; }
}
```

---

## Button Text Variations

### Detailed Text Options

**Option 1: Simple (Recommended)**
- Not in DB: "Mark as Wanted"
- Wanted: "Already Wanted"
- Searching: "Searching..."
- Downloading: "Downloading..."
- Imported: "Imported"
- Archived: "Archived"

**Option 2: More Descriptive**
- Not in DB: "Mark as Wanted"
- Wanted: "In Wanted List"
- Searching: "Searching for Downloads"
- Downloading: "Downloading File"
- Imported: "In Library"
- Archived: "Archived"

**Option 3: With Icons**
- Not in DB: "➕ Mark as Wanted"
- Wanted: "✓ Already Wanted"
- Searching: "🔍 Searching..."
- Downloading: "⬇️ Downloading..."
- Imported: "✓ Imported"
- Archived: "📦 Archived"

**Recommendation:** Use Option 1 (Simple) - clear, concise, matches Django admin style

---

## Interaction States

### Button States

1. **Default (Not in DB)**
   - Text: "Mark as Wanted"
   - Style: Primary action button
   - State: Enabled, clickable

2. **Hover**
   - Darker background color
   - Slight scale effect (optional)
   - Cursor: pointer

3. **Loading (After Click)**
   - Text: "Adding..."
   - Style: Disabled, gray
   - State: Not clickable
   - Show spinner or dots animation

4. **Success (After API Success)**
   - Text: "Already Wanted" (or current status)
   - Style: Status badge
   - State: Disabled, not clickable
   - Smooth transition animation

5. **Error**
   - Text: "Mark as Wanted" (restored)
   - Style: Primary button with error state
   - State: Enabled, clickable
   - Show error message (tooltip or alert)

---

## Accessibility

### ARIA Labels

```html
<!-- Action Button -->
<button class="want-button" 
        aria-label="Mark as Wanted: Book Title by Author"
        data-media-type="book">
    Mark as Wanted
</button>

<!-- Status Badge -->
<span class="status-badge wanted" 
      aria-label="Status: Already Wanted">
    Already Wanted
</span>
```

### Keyboard Navigation

- Tab to focus button
- Enter/Space to activate
- Focus visible outline
- Disabled buttons not focusable

---

## Implementation Notes

### CSS Classes

```css
/* Base button class */
.want-button { ... }

/* Status badge classes */
.status-badge { ... }
.status-badge.wanted { ... }
.status-badge.searching { ... }
.status-badge.downloading { ... }
.status-badge.imported { ... }
.status-badge.archived { ... }

/* State classes */
.want-button.loading { ... }
.want-button.error { ... }
```

### JavaScript State Management

```javascript
// Status to text mapping
const statusTexts = {
    'wanted': 'Already Wanted',
    'searching': 'Searching...',
    'downloading': 'Downloading...',
    'imported': 'Imported',
    'archived': 'Archived'
};

// Status to CSS class mapping
const statusClasses = {
    'wanted': 'wanted',
    'searching': 'searching',
    'downloading': 'downloading',
    'imported': 'imported',
    'archived': 'archived'
};
```

---

## Color Rationale

### Why These Colors?

1. **Primary Blue (#417690)**
   - Matches Django admin theme
   - Professional and trustworthy
   - Good contrast for accessibility

2. **Light Blue for Wanted**
   - Softer than primary blue
   - Indicates informational state
   - Still related to primary color

3. **Yellow for Searching**
   - Standard "in progress" color
   - Attention-grabbing but not alarming
   - Matches Bootstrap warning color

4. **Cyan for Downloading**
   - Distinct from searching
   - Indicates active download
   - Matches Bootstrap info color

5. **Green for Imported**
   - Standard success color
   - Indicates completion
   - Matches Bootstrap success color

6. **Gray for Archived**
   - Neutral, inactive state
   - Indicates item is stored but not active
   - Matches Bootstrap secondary color

---

## Responsive Design

### Mobile Considerations

- Buttons should be at least 44x44px for touch targets
- Text should remain readable at small sizes
- Status badges should wrap gracefully
- Consider icon-only on very small screens

---

## Examples

### HTML Structure

```html
<!-- Not in DB - Action Button -->
<td class="field-ebook">
    <button class="want-button" 
            data-media-type="book"
            data-provider="openlibrary"
            data-external-id="OL123456W">
        Mark as Wanted
    </button>
</td>

<!-- In DB - Status Badge -->
<td class="field-ebook">
    <span class="status-badge wanted" 
          aria-label="Status: Already Wanted">
        Already Wanted
    </span>
</td>

<!-- Loading State -->
<td class="field-ebook">
    <button class="want-button loading" disabled>
        Adding...
    </button>
</td>
```

---

## Summary

**Recommended Approach:**

1. **Button Text:**
   - Not in DB: "Mark as Wanted"
   - Status badges: Simple, clear text (Already Wanted, Searching..., etc.)

2. **Colors:**
   - Primary action: Django admin blue (#417690)
   - Status badges: Color-coded by status type
   - Consistent with Django admin theme

3. **States:**
   - Clear visual feedback for all states
   - Smooth transitions
   - Accessible and keyboard-friendly

4. **Implementation:**
   - Use CSS classes for styling
   - JavaScript for state management
   - ARIA labels for accessibility

