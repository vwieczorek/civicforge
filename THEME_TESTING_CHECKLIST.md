# Theme System Testing Checklist

## Pre-Testing Setup
- [ ] Docker containers running (`docker-compose up`)
- [ ] Access http://localhost:8000 to verify themed interface loads
- [ ] Have test accounts ready (admin/admin123 and dev/dev123)

## 1. Basic Theme Functionality

### Theme Switching
- [ ] Visit http://localhost:8000 without login - verify default theme shows
- [ ] Use theme switcher dropdown (bottom right) to switch themes
- [ ] Verify each built-in theme applies correctly:
  - [ ] Default (blue/green)
  - [ ] Earth & Nature (green/brown) 
  - [ ] Community Connect (red/orange)
  - [ ] Tech Forward (dark theme)
  - [ ] Civic Pride (blue/teal)
- [ ] Refresh page - verify theme persists (cookie test)
- [ ] Login - verify theme remains after auth

### Visual Elements
For each theme, verify these elements update:
- [ ] Background colors change
- [ ] Button colors match theme
- [ ] Navigation bar styling updates
- [ ] Quest cards use theme colors
- [ ] Success/error messages styled correctly
- [ ] Form inputs match theme

## 2. Theme Marketplace

### Browse Themes (http://localhost:8000/themes)
- [ ] All 5 built-in themes display
- [ ] Theme preview cards show:
  - [ ] Theme name
  - [ ] Description
  - [ ] Author
  - [ ] Download count
  - [ ] Rating
- [ ] "Use Theme" button switches theme immediately
- [ ] "View Details" link works

### Theme Filtering
- [ ] Click tag filters (official, modern, clean, etc.)
- [ ] Verify filtering works correctly
- [ ] "All Themes" filter shows all themes again

### Theme Detail Page
- [ ] Click "View Details" on any theme
- [ ] Live preview iframe shows themed board
- [ ] Color palette displays all theme colors
- [ ] Export JSON section shows valid JSON
- [ ] Can copy JSON from textarea

## 3. Theme Editor

### Access & Basic UI (http://localhost:8000/theme-editor/editor)
- [ ] Requires login (redirects if not authenticated)
- [ ] Editor layout has form on left, preview on right
- [ ] All form fields present:
  - [ ] Basic info (name, description, ID, author, tags)
  - [ ] Color pickers for all color properties
  - [ ] Typography controls
  - [ ] Component controls
  - [ ] Custom CSS textarea

### Live Preview
- [ ] Change primary color - preview updates immediately
- [ ] Change background color - preview background changes
- [ ] Change font family - preview text updates
- [ ] Adjust border radius slider - preview corners update
- [ ] All color changes reflect in preview quest cards

### Theme Creation
- [ ] Fill in all required fields:
  - [ ] Theme name: "Test Theme"
  - [ ] Description: "A test theme"
  - [ ] Theme ID: "test-theme" (lowercase, no spaces)
  - [ ] Author: "Tester"
- [ ] Modify some colors
- [ ] Click "Save Theme"
- [ ] Verify redirect to theme detail page
- [ ] Verify new theme appears in marketplace

### Export/Import
- [ ] In editor, click "Export JSON"
- [ ] Verify JSON file downloads
- [ ] Visit http://localhost:8000/theme-editor/import
- [ ] Paste the exported JSON
- [ ] Click "Import Theme"
- [ ] Verify theme imports successfully

## 4. Core Functionality Preservation

### Quest Operations (with any theme active)
- [ ] Create a new quest
- [ ] Claim a quest
- [ ] Submit work on a quest
- [ ] Verify a quest (with different account)
- [ ] Boost a quest
- [ ] All quest actions work regardless of theme

### Navigation & Auth
- [ ] All navigation links work
- [ ] Login/logout functionality intact
- [ ] Registration works
- [ ] Stats page displays correctly

## 5. Edge Cases & Error Handling

### Theme System Robustness
- [ ] Delete cookies and verify default theme loads
- [ ] Try switching themes rapidly - no errors
- [ ] Invalid theme ID in cookie - falls back to default
- [ ] Theme editor with missing fields - shows validation
- [ ] Import invalid JSON - shows error message
- [ ] Create theme with duplicate ID - appropriate error

### Responsive Design
- [ ] Resize browser window - themes remain functional
- [ ] Theme switcher accessible on mobile sizes
- [ ] Theme editor usable on tablet size
- [ ] Preview updates work on smaller screens

## 6. Performance & UX

### Loading & Transitions
- [ ] Theme switches instantly (no page flash)
- [ ] No layout shift when changing themes
- [ ] Theme CSS loads efficiently
- [ ] Preview updates are smooth

### Accessibility
- [ ] All themes maintain readable contrast
- [ ] Form labels properly associated
- [ ] Keyboard navigation works
- [ ] Theme switcher keyboard accessible

## 7. API Testing

### Theme API Endpoints
- [ ] GET `/api/themes` returns theme list
- [ ] GET `/api/themes?tags=official` filters correctly
- [ ] GET `/api/theme/default` returns theme JSON
- [ ] GET `/api/theme/invalid` returns 404
- [ ] POST `/api/theme` requires authentication

## Known Issues to Check

1. **Cookie Persistence**: Themes should persist across sessions
2. **Theme Editor Preview**: Should update without lag
3. **Custom CSS**: Should apply after theme variables
4. **Import Validation**: Should handle malformed JSON gracefully

## Test Data Creation

For thorough testing, create:
1. Multiple quests in different categories
2. Quests in various states (open, claimed, submitted)
3. A custom theme via editor
4. An imported theme via JSON

## Regression Testing

After theme testing, verify original features still work:
- [ ] Original web.py interface (if needed, change docker-compose back)
- [ ] API endpoints under /api/*
- [ ] Database migrations
- [ ] Authentication flow
- [ ] XP system and calculations

## Browser Testing

Test in multiple browsers if possible:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge

## Notes Section

Document any issues found:

### Bugs:
- 

### Improvements:
- 

### Questions:
-