"""Theme editor for CivicForge - allows creating and customizing themes via web interface."""

from fastapi import FastAPI, Request, Cookie, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional
import json

from .themes import Theme, ThemeColors, theme_manager
from .web_themed import themed_html, get_auth_header, safe_get

app = FastAPI(title="CivicForge Theme Editor")


@app.get("/editor", response_class=HTMLResponse)
def theme_editor(
    token: Optional[str] = Cookie(None),
    theme: Optional[str] = Cookie("default"),
    base_theme: Optional[str] = "default"
):
    """Interactive theme editor."""
    if not token:
        return RedirectResponse("/login?error=Please login to create themes", status_code=303)
    
    # Load base theme
    base = theme_manager.get_theme(base_theme) or theme_manager.get_theme("default")
    
    content = ["""
        <h1>Theme Editor</h1>
        <div class="quest">
            <h2>Create Your Theme</h2>
            <p>Customize the appearance of your CivicForge board. Changes preview in real-time!</p>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-large);">
            <div>
                <form id="theme-form" onsubmit="saveTheme(event)">
                    <div class="quest">
                        <h3>Basic Information</h3>
                        <div class="form-group">
                            <label class="form-label">Theme Name</label>
                            <input name="name" placeholder="My Custom Theme" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Description</label>
                            <textarea name="description" placeholder="Describe your theme..." rows="2"></textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Theme ID (lowercase, no spaces)</label>
                            <input name="id" pattern="[a-z0-9-]+" placeholder="my-custom-theme" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Your Name</label>
                            <input name="author" placeholder="Your name" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Tags (comma-separated)</label>
                            <input name="tags" placeholder="modern, clean, professional">
                        </div>
                    </div>
                    
                    <div class="quest">
                        <h3>Colors</h3>
    """]
    
    # Color inputs
    for color_name, color_value in base.colors.__dict__.items():
        label = color_name.replace('_', ' ').title()
        content.append(f"""
            <div class="form-group">
                <label class="form-label">{label}</label>
                <div style="display: flex; gap: var(--spacing-small); align-items: center;">
                    <input type="color" name="color_{color_name}" value="{color_value}" 
                           onchange="updatePreview()" style="width: 60px; height: 40px;">
                    <input type="text" name="color_{color_name}_text" value="{color_value}" 
                           onchange="updateColorFromText('{color_name}')" style="flex: 1;">
                </div>
            </div>
        """)
    
    content.append("""
                    </div>
                    
                    <div class="quest">
                        <h3>Typography</h3>
                        <div class="form-group">
                            <label class="form-label">Font Family</label>
                            <select name="font_family" onchange="updatePreview()">
                                <option value="system-ui, -apple-system, sans-serif">System Default</option>
                                <option value="'Inter', sans-serif">Inter</option>
                                <option value="'Roboto', sans-serif">Roboto</option>
                                <option value="'Open Sans', sans-serif">Open Sans</option>
                                <option value="'Playfair Display', serif">Playfair Display</option>
                                <option value="'Georgia', serif">Georgia</option>
                                <option value="'Space Mono', monospace">Space Mono</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Base Font Size</label>
                            <input type="range" name="font_size_base" min="14" max="20" value="16" 
                                   onchange="updatePreview()" oninput="this.nextElementSibling.textContent = this.value + 'px'">
                            <span>16px</span>
                        </div>
                    </div>
                    
                    <div class="quest">
                        <h3>Components</h3>
                        <div class="form-group">
                            <label class="form-label">Border Radius</label>
                            <input type="range" name="border_radius" min="0" max="20" value="6" 
                                   onchange="updatePreview()" oninput="this.nextElementSibling.textContent = this.value + 'px'">
                            <span>6px</span>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Shadow Intensity</label>
                            <select name="shadow_intensity" onchange="updatePreview()">
                                <option value="none">None</option>
                                <option value="subtle" selected>Subtle</option>
                                <option value="medium">Medium</option>
                                <option value="strong">Strong</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="quest">
                        <h3>Custom CSS</h3>
                        <div class="form-group">
                            <label class="form-label">Additional CSS (Advanced)</label>
                            <textarea name="custom_css" rows="10" style="font-family: monospace; font-size: 14px;"
                                      placeholder="/* Add custom CSS here */"></textarea>
                        </div>
                    </div>
                    
                    <div class="quest-actions">
                        <button type="submit">Save Theme</button>
                        <button type="button" onclick="exportTheme()">Export JSON</button>
                        <button type="button" onclick="resetTheme()">Reset</button>
                    </div>
                </form>
            </div>
            
            <div>
                <div class="quest" style="position: sticky; top: var(--spacing-large);">
                    <h3>Live Preview</h3>
                    <div id="preview-container" style="border: 1px solid var(--color-surface); border-radius: var(--border-radius); padding: var(--spacing-large); background: var(--preview-bg, white);">
                        <style id="preview-styles"></style>
                        <div class="preview-content">
                            <h1 style="color: var(--preview-text, black);">Your Board Name</h1>
                            <p style="color: var(--preview-text-secondary, gray);">This is how your themed board will look.</p>
                            
                            <div style="background: var(--preview-surface, #f0f0f0); padding: var(--spacing-medium); border-radius: var(--preview-radius, 6px); margin: var(--spacing-medium) 0;">
                                <h3 style="color: var(--preview-text, black); margin-top: 0;">Sample Quest</h3>
                                <p style="color: var(--preview-text-secondary, gray);">Help organize the community garden cleanup this weekend.</p>
                                <div style="display: flex; gap: var(--spacing-small); margin-top: var(--spacing-medium);">
                                    <button style="background: var(--preview-primary, blue); color: white; border: none; padding: 8px 16px; border-radius: var(--preview-radius, 6px);">Claim Quest</button>
                                    <button style="background: var(--preview-secondary, green); color: white; border: none; padding: 8px 16px; border-radius: var(--preview-radius, 6px);">Boost</button>
                                </div>
                            </div>
                            
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--spacing-small); margin-top: var(--spacing-medium);">
                                <div style="background: var(--preview-surface, #f0f0f0); padding: var(--spacing-medium); border-radius: var(--preview-radius, 6px); text-align: center;">
                                    <div style="font-size: 24px; font-weight: bold; color: var(--preview-primary, blue);">42</div>
                                    <div style="color: var(--preview-text-secondary, gray); font-size: 14px;">Total Quests</div>
                                </div>
                                <div style="background: var(--preview-surface, #f0f0f0); padding: var(--spacing-medium); border-radius: var(--preview-radius, 6px); text-align: center;">
                                    <div style="font-size: 24px; font-weight: bold; color: var(--preview-success, green);">89%</div>
                                    <div style="color: var(--preview-text-secondary, gray); font-size: 14px;">Completion Rate</div>
                                </div>
                                <div style="background: var(--preview-surface, #f0f0f0); padding: var(--spacing-medium); border-radius: var(--preview-radius, 6px); text-align: center;">
                                    <div style="font-size: 24px; font-weight: bold; color: var(--preview-accent, orange);">156</div>
                                    <div style="color: var(--preview-text-secondary, gray); font-size: 14px;">Active Users</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            function updatePreview() {
                const form = document.getElementById('theme-form');
                const formData = new FormData(form);
                const preview = document.getElementById('preview-container');
                const styles = document.getElementById('preview-styles');
                
                // Update CSS variables
                const colors = {};
                const inputs = form.querySelectorAll('input[type="color"]');
                inputs.forEach(input => {
                    const name = input.name.replace('color_', '');
                    colors[name] = input.value;
                    input.nextElementSibling.value = input.value;
                });
                
                // Apply preview styles
                preview.style.setProperty('--preview-bg', colors.background);
                preview.style.setProperty('--preview-surface', colors.surface);
                preview.style.setProperty('--preview-text', colors.text);
                preview.style.setProperty('--preview-text-secondary', colors.text_secondary);
                preview.style.setProperty('--preview-primary', colors.primary);
                preview.style.setProperty('--preview-secondary', colors.secondary);
                preview.style.setProperty('--preview-accent', colors.accent);
                preview.style.setProperty('--preview-success', colors.success);
                preview.style.setProperty('--preview-error', colors.error);
                preview.style.setProperty('--preview-radius', formData.get('border_radius') + 'px');
                
                // Typography
                const fontFamily = formData.get('font_family');
                preview.style.fontFamily = fontFamily;
                preview.style.fontSize = formData.get('font_size_base') + 'px';
                
                // Shadows
                const shadowMap = {
                    'none': 'none',
                    'subtle': '0 1px 2px rgba(0, 0, 0, 0.05)',
                    'medium': '0 4px 6px rgba(0, 0, 0, 0.1)',
                    'strong': '0 10px 15px rgba(0, 0, 0, 0.15)'
                };
                const shadow = shadowMap[formData.get('shadow_intensity')] || shadowMap.subtle;
                preview.querySelectorAll('[style*="background"]').forEach(el => {
                    if (el.style.background.includes('surface')) {
                        el.style.boxShadow = shadow;
                    }
                });
            }
            
            function updateColorFromText(colorName) {
                const textInput = document.querySelector(`input[name="color_${colorName}_text"]`);
                const colorInput = document.querySelector(`input[name="color_${colorName}"]`);
                colorInput.value = textInput.value;
                updatePreview();
            }
            
            function saveTheme(event) {
                event.preventDefault();
                const form = event.target;
                const formData = new FormData(form);
                
                // Build theme object
                const theme = {
                    id: formData.get('id'),
                    name: formData.get('name'),
                    description: formData.get('description'),
                    author: formData.get('author'),
                    tags: formData.get('tags').split(',').map(t => t.trim()).filter(t => t),
                    colors: {},
                    typography: {
                        font_family: formData.get('font_family'),
                        font_size_base: formData.get('font_size_base') + 'px'
                    },
                    components: {
                        border_radius: formData.get('border_radius') + 'px'
                    },
                    custom_css: formData.get('custom_css')
                };
                
                // Get colors
                const colorInputs = form.querySelectorAll('input[type="color"]');
                colorInputs.forEach(input => {
                    const name = input.name.replace('color_', '');
                    theme.colors[name] = input.value;
                });
                
                // Save theme
                fetch('/theme-api/theme', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(theme)
                })
                .then(res => res.json())
                .then(data => {
                    if (data.theme_id) {
                        alert('Theme saved successfully!');
                        window.location.href = `/theme/${data.theme_id}`;
                    } else {
                        alert('Error saving theme: ' + (data.detail || 'Unknown error'));
                    }
                })
                .catch(err => {
                    alert('Error saving theme: ' + err);
                });
            }
            
            function exportTheme() {
                const form = document.getElementById('theme-form');
                const formData = new FormData(form);
                
                // Build theme object (same as save)
                const theme = {
                    id: formData.get('id'),
                    name: formData.get('name'),
                    description: formData.get('description'),
                    author: formData.get('author'),
                    version: "1.0.0",
                    tags: formData.get('tags').split(',').map(t => t.trim()).filter(t => t),
                    colors: {},
                    typography: {
                        font_family: formData.get('font_family'),
                        font_size_base: formData.get('font_size_base') + 'px',
                        font_size_small: "14px",
                        font_size_large: "18px",
                        font_size_heading: "24px",
                        line_height: "1.5"
                    },
                    components: {
                        border_radius: formData.get('border_radius') + 'px',
                        border_width: "1px",
                        shadow_small: "0 1px 2px rgba(0, 0, 0, 0.05)",
                        shadow_medium: "0 4px 6px rgba(0, 0, 0, 0.1)",
                        shadow_large: "0 10px 15px rgba(0, 0, 0, 0.1)",
                        transition: "all 0.2s ease"
                    },
                    spacing: {
                        unit: "0.25rem",
                        small: "0.5rem",
                        medium: "1rem",
                        large: "1.5rem",
                        xlarge: "2rem"
                    },
                    custom_css: formData.get('custom_css')
                };
                
                // Get colors
                const colorInputs = form.querySelectorAll('input[type="color"]');
                colorInputs.forEach(input => {
                    const name = input.name.replace('color_', '');
                    theme.colors[name] = input.value;
                });
                
                // Download as JSON
                const blob = new Blob([JSON.stringify(theme, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = theme.id + '.json';
                a.click();
                URL.revokeObjectURL(url);
            }
            
            function resetTheme() {
                if (confirm('Reset all changes?')) {
                    document.getElementById('theme-form').reset();
                    updatePreview();
                }
            }
            
            // Load Google Fonts for preview
            const link = document.createElement('link');
            link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Roboto:wght@400;500&family=Open+Sans:wght@400;600&family=Playfair+Display:wght@400;700&family=Space+Mono:wght@400;700&display=swap';
            link.rel = 'stylesheet';
            document.head.appendChild(link);
            
            // Initial preview update
            updatePreview();
        </script>
    """)
    
    return themed_html("".join(content), token, theme, "Theme Editor")


@app.get("/import", response_class=HTMLResponse)
def import_theme_page(
    token: Optional[str] = Cookie(None),
    theme: Optional[str] = Cookie("default")
):
    """Import theme from JSON."""
    if not token:
        return RedirectResponse("/login?error=Please login to import themes", status_code=303)
    
    content = ["""
        <h1>Import Theme</h1>
        <div class="quest">
            <h2>Import from JSON</h2>
            <p>Paste your theme JSON below to import it.</p>
            
            <form onsubmit="importTheme(event)">
                <div class="form-group">
                    <label class="form-label">Theme JSON</label>
                    <textarea name="theme_json" rows="20" style="font-family: monospace; font-size: 14px;" required></textarea>
                </div>
                <button type="submit">Import Theme</button>
            </form>
        </div>
        
        <script>
            function importTheme(event) {
                event.preventDefault();
                const form = event.target;
                const json = form.theme_json.value;
                
                try {
                    const theme = JSON.parse(json);
                    
                    fetch('/theme-api/theme', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: json
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.theme_id) {
                            alert('Theme imported successfully!');
                            window.location.href = `/theme/${data.theme_id}`;
                        } else {
                            alert('Error importing theme: ' + (data.detail || 'Unknown error'));
                        }
                    })
                    .catch(err => {
                        alert('Error importing theme: ' + err);
                    });
                } catch (e) {
                    alert('Invalid JSON: ' + e.message);
                }
            }
        </script>
    """]
    
    return themed_html("".join(content), token, theme, "Import Theme")