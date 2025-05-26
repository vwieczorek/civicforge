#!/usr/bin/env python3
"""Run the themed version of CivicForge Board."""

import uvicorn
from .web_themed import app
from .theme_editor import app as editor_app

# Mount the theme editor
app.mount("/theme-editor", editor_app)

if __name__ == "__main__":
    print("Starting CivicForge Board with Theme Support...")
    print("Visit http://localhost:8000 to see the themed interface")
    print("Visit http://localhost:8000/themes to browse themes")
    print("Visit http://localhost:8000/theme-editor/editor to create custom themes")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)