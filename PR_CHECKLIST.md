# Pull Request Checklist: Theme System

## Overview
This PR adds a comprehensive theme system to CivicForge, enabling custom UI themes and a theme marketplace.

## Changes Summary

### New Files
- [ ] `src/board_mvp/themes.py` - Core theme models and manager
- [ ] `src/board_mvp/web_themed.py` - Enhanced web interface with theme support  
- [ ] `src/board_mvp/theme_editor.py` - Visual theme editor
- [ ] `src/board_mvp/run_themed.py` - Runner script for themed version
- [ ] `src/board_mvp/test_themes.py` - Theme system tests
- [ ] `THEME_SYSTEM_GUIDE.md` - Comprehensive documentation
- [ ] `THEME_TESTING_CHECKLIST.md` - Testing guide

### Modified Files
- [ ] `docker-compose.yml` - Updated to use themed interface

## Pre-PR Testing

### Automated Tests
```bash
# Run theme system tests
python -m src.board_mvp.test_themes

# Run existing tests to ensure no regression
python -m src.board_mvp.run_tests
```

### Manual Testing
- [ ] Complete THEME_TESTING_CHECKLIST.md
- [ ] Test with both Docker and local setup
- [ ] Verify all existing functionality works
- [ ] Test theme persistence across sessions
- [ ] Create and save a custom theme
- [ ] Import/export theme JSON

## Code Quality

### Style & Standards
- [ ] Python code follows PEP 8
- [ ] Consistent naming conventions
- [ ] No hardcoded values
- [ ] Proper error handling
- [ ] Type hints where appropriate

### Security
- [ ] No sensitive data exposed
- [ ] Theme IDs sanitized
- [ ] JSON imports validated
- [ ] XSS prevention in custom CSS
- [ ] CSRF protection maintained

### Performance
- [ ] Theme CSS efficiently loaded
- [ ] No blocking operations
- [ ] Minimal database queries
- [ ] Fast theme switching

## Documentation

- [ ] THEME_SYSTEM_GUIDE.md is complete
- [ ] Code comments explain complex logic
- [ ] API endpoints documented
- [ ] Example themes provided
- [ ] Migration path clear

## Backwards Compatibility

- [ ] Original web.py still functional
- [ ] API endpoints unchanged
- [ ] Database schema compatible
- [ ] Can switch between versions

## Future Considerations

### Enhancements Noted
- Theme ratings and reviews
- Theme analytics
- Premium themes
- Board-specific overrides
- A/B testing support

### Known Limitations
- Themes stored in filesystem (not DB)
- No theme versioning yet
- Limited mobile optimization
- No theme inheritance

## Deployment Notes

### Docker Update
```bash
# The docker-compose.yml now uses:
uvicorn src.board_mvp.web_themed:app --host 0.0.0.0 --port 8000 --reload
```

### Rollback Plan
```bash
# To rollback, change docker-compose.yml back to:
uvicorn src.board_mvp.web:app --host 0.0.0.0 --port 8000 --reload
```

## PR Description Template

```markdown
## 🎨 Theme System for CivicForge

This PR introduces a comprehensive theme system that allows boards to have custom visual themes and share them in a marketplace.

### Key Features
- **5 Built-in Themes**: Professional themes for different board types
- **Visual Theme Editor**: Create themes with live preview
- **Theme Marketplace**: Browse and instantly switch themes
- **LLM-Friendly**: JSON format for easy AI collaboration

### Technical Implementation
- CSS custom properties for consistent theming
- Cookie-based theme persistence
- Modular architecture (themes.py, web_themed.py, theme_editor.py)
- Full backwards compatibility

### Testing
- Automated tests: `python -m src.board_mvp.test_themes`
- Manual testing checklist completed
- No regression in existing functionality

### Documentation
- Comprehensive guide: THEME_SYSTEM_GUIDE.md
- Testing checklist: THEME_TESTING_CHECKLIST.md

### Screenshots
[Add screenshots of different themes and editor]

Fixes #[issue]
```

## Final Checks

- [ ] All tests pass
- [ ] Docker builds successfully
- [ ] No console errors in browser
- [ ] Theme data persists correctly
- [ ] Performance acceptable
- [ ] Ready for review

## Reviewer Notes

Key areas to review:
1. Theme data model design
2. CSS variable approach
3. Security of custom CSS
4. API endpoint structure
5. Docker configuration changes