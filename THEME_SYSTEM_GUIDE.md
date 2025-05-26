# CivicForge Theme System Guide

## Overview

The CivicForge theme system allows boards to have custom visual themes that can be shared in a marketplace. This enables:

- **Rapid UX iteration** with LLMs and designers
- **Community expression** through custom board aesthetics  
- **Theme marketplace** for sharing and discovering themes
- **Consistent theming API** using CSS custom properties

## Quick Start

### Running the Themed Version

```bash
# From the project root
python -m src.board_mvp.run_themed

# Or with Docker
docker-compose up -d
# The themed version is available at http://localhost:8000
```

### Key URLs

- **Main Board**: http://localhost:8000 - The themed board interface
- **Theme Marketplace**: http://localhost:8000/themes - Browse and switch themes
- **Theme Editor**: http://localhost:8000/theme-editor/editor - Create custom themes
- **Theme Import**: http://localhost:8000/theme-editor/import - Import theme JSON

## Architecture

### Core Components

1. **`themes.py`** - Theme data models and manager
   - `Theme` dataclass with colors, typography, spacing, etc.
   - `ThemeManager` for loading/saving themes
   - Built-in theme collection

2. **`web_themed.py`** - Enhanced web interface with theme support
   - Theme-aware HTML generation
   - Theme switching via cookies
   - Theme marketplace UI
   - All original board functionality

3. **`theme_editor.py`** - Visual theme editor
   - Live preview while editing
   - Color pickers and controls
   - Export/import JSON
   - Custom CSS support

### Theme Structure

```python
@dataclass
class Theme:
    id: str                    # Unique identifier
    name: str                  # Display name
    description: str           # Theme description
    author: str               # Creator name
    version: str = "1.0.0"    # Semantic version
    
    # Visual properties
    colors: ThemeColors       # Primary, secondary, backgrounds, etc.
    typography: ThemeTypography    # Fonts and sizes
    spacing: ThemeSpacing     # Spacing units
    components: ThemeComponents    # Borders, shadows, etc.
    
    # Extras
    custom_css: str = ""      # Additional CSS
    preview_image: Optional[str]   # Screenshot URL
    tags: List[str]           # Searchable tags
    
    # Marketplace data
    downloads: int = 0        # Download count
    rating: float = 0.0       # User rating
```

## Built-in Themes

The system includes 5 starter themes:

1. **Default** - Clean and modern (blue/green)
2. **Earth & Nature** - Environmental theme (green/brown)
3. **Community Connect** - Warm neighborhood theme (red/orange)
4. **Tech Forward** - Dark mode tech theme (purple/pink)
5. **Civic Pride** - Professional government theme (blue/teal)

## Creating Custom Themes

### Method 1: Visual Editor (Recommended)

1. Login to your board
2. Navigate to http://localhost:8000/theme-editor/editor
3. Customize:
   - Basic info (name, description, tags)
   - Colors (with color pickers)
   - Typography (font family and sizes)
   - Components (border radius, shadows)
   - Custom CSS (advanced)
4. Preview changes live
5. Save or export theme

### Method 2: JSON Format

Create a theme JSON file:

```json
{
  "id": "my-theme",
  "name": "My Custom Theme",
  "description": "A beautiful custom theme",
  "author": "Your Name",
  "version": "1.0.0",
  "tags": ["custom", "modern"],
  "colors": {
    "primary": "#3b82f6",
    "secondary": "#10b981",
    "accent": "#f59e0b",
    "background": "#ffffff",
    "surface": "#f3f4f6",
    "text": "#111827",
    "text_secondary": "#6b7280",
    "error": "#ef4444",
    "success": "#10b981",
    "warning": "#f59e0b",
    "info": "#3b82f6"
  },
  "typography": {
    "font_family": "'Inter', sans-serif",
    "font_size_base": "16px",
    "font_size_small": "14px",
    "font_size_large": "18px",
    "font_size_heading": "24px",
    "line_height": "1.5"
  },
  "spacing": {
    "unit": "0.25rem",
    "small": "0.5rem",
    "medium": "1rem",
    "large": "1.5rem",
    "xlarge": "2rem"
  },
  "components": {
    "border_radius": "0.5rem",
    "border_width": "1px",
    "shadow_small": "0 1px 3px rgba(0,0,0,0.1)",
    "shadow_medium": "0 4px 6px rgba(0,0,0,0.1)",
    "shadow_large": "0 10px 15px rgba(0,0,0,0.1)",
    "transition": "all 0.2s ease"
  },
  "custom_css": "/* Optional custom CSS */"
}
```

Then import via http://localhost:8000/theme-editor/import

### Method 3: Python Code

```python
from src.board_mvp.themes import Theme, ThemeColors, theme_manager

# Create theme
my_theme = Theme(
    id="my-theme",
    name="My Theme",
    description="A custom theme",
    author="Me",
    colors=ThemeColors(
        primary="#e11d48",
        secondary="#0ea5e9",
        # ... other colors
    )
)

# Save theme
theme_manager.save_theme(my_theme)
```

## Theme API Endpoints

- `GET /api/themes` - List all themes
- `GET /api/themes?tags=dark,modern` - Filter by tags
- `GET /api/theme/{theme_id}` - Get specific theme
- `POST /api/theme` - Create new theme (requires auth)

## CSS Custom Properties

Themes use CSS custom properties for easy styling:

```css
/* Color variables */
--color-primary: #2563eb;
--color-secondary: #10b981;
--color-accent: #f59e0b;
--color-background: #ffffff;
--color-surface: #f3f4f6;
--color-text: #111827;
--color-text-secondary: #6b7280;
--color-error: #ef4444;
--color-success: #10b981;

/* Typography variables */
--font-family: system-ui, -apple-system, sans-serif;
--font-size-base: 16px;
--font-size-small: 14px;
--font-size-large: 18px;
--font-size-heading: 24px;
--line-height: 1.5;

/* Spacing variables */
--spacing-unit: 0.25rem;
--spacing-small: 0.5rem;
--spacing-medium: 1rem;
--spacing-large: 1.5rem;
--spacing-xlarge: 2rem;

/* Component variables */
--border-radius: 0.375rem;
--border-width: 1px;
--shadow-small: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-medium: 0 4px 6px rgba(0, 0, 0, 0.1);
--shadow-large: 0 10px 15px rgba(0, 0, 0, 0.1);
--transition: all 0.2s ease;
```

## Working with LLMs

The theme system is designed for easy iteration with LLMs:

1. **Structured Format**: Themes use clear JSON structure that LLMs understand
2. **Live Preview**: Changes update instantly for rapid feedback
3. **Export/Import**: Easy to share theme definitions with LLMs
4. **CSS Variables**: Standard approach that LLMs can generate

### Example LLM Prompt

```
Create a CivicForge theme inspired by ocean conservation with:
- Blues and teals for water
- Sandy beige for beaches  
- Coral accent colors
- Clean, modern typography
- Soft shadows and rounded corners

Export as JSON format.
```

## Theme Marketplace Features

- **Browse themes** by category/tags
- **Preview themes** before switching
- **Rate themes** (coming soon)
- **Download counts** track popularity
- **Author attribution** for creators
- **One-click switching** with cookies

## Best Practices

1. **Start with a base theme** - Modify existing themes rather than starting from scratch
2. **Use semantic color names** - `primary`, `secondary` instead of `blue`, `green`
3. **Test on different content** - Ensure readability with various quest types
4. **Keep accessibility in mind** - Maintain good color contrast ratios
5. **Version your themes** - Use semantic versioning for updates
6. **Add descriptive tags** - Help users discover your theme
7. **Include custom CSS sparingly** - Prefer using the built-in properties

## Future Enhancements

- Theme ratings and reviews
- Theme collections/bundles
- Seasonal/event themes
- Board-specific theme overrides
- Theme inheritance/variants
- A/B testing themes
- Theme analytics
- Premium themes marketplace

## Troubleshooting

**Theme not applying?**
- Check browser cookies are enabled
- Clear cache and reload
- Verify theme ID is correct

**Custom CSS not working?**
- Use CSS custom properties where possible
- Check for syntax errors
- Use browser dev tools to debug

**Theme editor not loading?**
- Ensure you're logged in
- Check JavaScript console for errors
- Try a different browser

## Contributing Themes

To contribute a theme to the official collection:

1. Create your theme using the editor
2. Export as JSON
3. Test thoroughly
4. Submit a PR with:
   - Theme JSON file
   - Screenshot/preview
   - Description of inspiration
   - Any special CSS features