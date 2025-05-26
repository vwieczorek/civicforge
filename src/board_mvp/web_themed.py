"""Theme-enabled web interface for CivicForge Board MVP."""

from fastapi import FastAPI, Request, Response, Cookie, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import requests
import json
import os

from . import api
from .database import init_db
from .themes import theme_manager, Theme

app = FastAPI(title="CivicForge Board - Themed UI")

# Import and mount theme editor
try:
    from .theme_editor import app as editor_app
    app.mount("/theme-editor", editor_app)
except ImportError:
    pass  # Theme editor not available

# Initialize the database
init_db()

# Mount the existing API under /api
app.mount("/api", api.app)

# API Base URL
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api")


def get_auth_header(token: str) -> dict:
    """Get authorization header for API calls."""
    return {"Authorization": f"Bearer {token}"} if token else {}


def safe_get(path: str, **kwargs):
    """Make a safe GET request to the API."""
    if not path.startswith('/'):
        path = '/' + path
    url = API_BASE + path
    return requests.get(url, **kwargs)


def safe_post(path: str, **kwargs):
    """Make a safe POST request to the API."""
    if not path.startswith('/'):
        path = '/' + path
    url = API_BASE + path
    return requests.post(url, **kwargs)


def themed_html(content: str, token: Optional[str] = None, theme_id: str = "default", title: str = "CivicForge Board") -> str:
    """Wrap content in themed HTML with navigation."""
    nav_items = []
    if token:
        nav_items.extend([
            '<a href="/" class="nav-link">Board</a>',
            '<a href="/stats" class="nav-link">Stats</a>',
            '<a href="/themes" class="nav-link">Themes</a>',
            '<a href="/logout" class="nav-link">Logout</a>'
        ])
    else:
        nav_items.extend([
            '<a href="/login" class="nav-link">Login</a>',
            '<a href="/register" class="nav-link">Register</a>',
            '<a href="/themes" class="nav-link">Browse Themes</a>'
        ])
    
    nav = " | ".join(nav_items)
    
    # Get theme CSS
    theme_css = theme_manager.generate_theme_css(theme_id)
    
    # Get available themes for switcher
    themes = theme_manager.list_themes()
    theme_options = "".join([
        f'<option value="{t.id}" {"selected" if t.id == theme_id else ""}>{t.name}</option>'
        for t in themes
    ])
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            {theme_css}
            
            /* Additional themed styles */
            .nav-link {{
                padding: var(--spacing-small) var(--spacing-medium);
                margin: 0 var(--spacing-unit);
                border-radius: var(--border-radius);
                transition: var(--transition);
            }}
            
            .nav-link:hover {{
                background: color-mix(in srgb, var(--color-primary) 10%, transparent);
                text-decoration: none;
            }}
            
            .quest-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: var(--spacing-small);
            }}
            
            .quest-title {{
                font-size: var(--font-size-large);
                font-weight: 600;
                color: var(--color-text);
            }}
            
            .quest-meta {{
                display: flex;
                gap: var(--spacing-medium);
                font-size: var(--font-size-small);
                color: var(--color-text-secondary);
            }}
            
            .quest-actions {{
                display: flex;
                gap: var(--spacing-small);
                margin-top: var(--spacing-medium);
            }}
            
            .category-filter {{
                display: flex;
                gap: var(--spacing-small);
                flex-wrap: wrap;
                margin-bottom: var(--spacing-large);
            }}
            
            .category-link {{
                padding: var(--spacing-small) var(--spacing-medium);
                background: var(--color-surface);
                border-radius: var(--border-radius);
                transition: var(--transition);
            }}
            
            .category-link:hover {{
                background: var(--color-primary);
                color: white;
                text-decoration: none;
            }}
            
            .category-link.active {{
                background: var(--color-primary);
                color: white;
            }}
            
            .form-group {{
                margin-bottom: var(--spacing-medium);
            }}
            
            .form-label {{
                display: block;
                margin-bottom: var(--spacing-small);
                font-weight: 500;
            }}
            
            .boost-indicator {{
                color: var(--color-accent);
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: var(--spacing-medium);
                margin-bottom: var(--spacing-xlarge);
            }}
            
            .stat-card {{
                background: var(--color-surface);
                padding: var(--spacing-large);
                border-radius: var(--border-radius);
                box-shadow: var(--shadow-small);
            }}
            
            .stat-value {{
                font-size: calc(var(--font-size-heading) * 1.5);
                font-weight: 700;
                color: var(--color-primary);
            }}
            
            .stat-label {{
                color: var(--color-text-secondary);
                font-size: var(--font-size-small);
            }}
        </style>
        <script>
            function switchTheme(themeId) {{
                // Set cookie and reload
                document.cookie = `theme=${{themeId}}; path=/; max-age=31536000`;
                window.location.reload();
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <div class="nav">{nav}</div>
            {content}
            
            <div class="theme-switcher">
                <select onchange="switchTheme(this.value)" title="Switch theme">
                    {theme_options}
                </select>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    error: str = "",
    success: str = "",
    category: str = None,
    token: Optional[str] = Cookie(None),
    theme: Optional[str] = Cookie("default")
):
    """List quests with theme support."""
    content = ["<h1>CivicForge Board</h1>"]
    
    if error:
        content.append(f'<div class="error">{error}</div>')
    if success:
        content.append(f'<div class="success">{success}</div>')
    
    if not token:
        content.append("<p>Please <a href='/login'>login</a> or <a href='/register'>register</a> to participate.</p>")
        content.append("""
            <div class="quest">
                <h2>Welcome to CivicForge!</h2>
                <p>CivicForge transforms communities from audiences into actors. Join us to:</p>
                <ul>
                    <li>Create and complete meaningful local tasks</li>
                    <li>Earn experience points for verified work</li>
                    <li>Build trust through action, not just words</li>
                    <li>Customize your board with beautiful themes</li>
                </ul>
            </div>
        """)
        return themed_html("".join(content), token, theme)
    
    # Get current user info
    try:
        resp = safe_get("/me", headers=get_auth_header(token))
        if resp.status_code != 200:
            return RedirectResponse("/login?error=Session expired", status_code=303)
        current_user = resp.json()

        # Get user's XP balance
        xp_resp = safe_get(f"/users/{current_user['id']}/experience", headers=get_auth_header(token))
        xp_balance = xp_resp.json().get("experience_balance", 0) if xp_resp.status_code == 200 else 0

        content.append(f"""
            <div class="quest">
                <h2>Welcome back, {current_user['username']}!</h2>
                <p>You have <span class="stat-value">{xp_balance}</span> experience points.</p>
            </div>
        """)
    except:
        return RedirectResponse("/login?error=Session expired", status_code=303)

    # Get categories for filtering
    categories_resp = safe_get("/categories")
    categories = categories_resp.json().get("categories", []) if categories_resp.status_code == 200 else []

    # Show category filter
    content.append('<div class="category-filter">')
    content.append(f'<a href="/" class="category-link {"active" if not category else ""}">All Quests</a>')
    for cat in categories:
        is_active = "active" if category == cat['name'] else ""
        content.append(f'<a href="/?category={cat["name"]}" class="category-link {is_active}">{cat["name"].title()} ({cat["count"]})</a>')
    content.append('</div>')

    # Get quests
    if category:
        allowed = [cat.get("name") for cat in categories]
        if category not in allowed:
            return RedirectResponse("/?error=Invalid category", status_code=303)
        path = f"/quests?category={category}"
    else:
        path = "/quests"
    quests_resp = safe_get(path)
    quests = quests_resp.json() if quests_resp.status_code == 200 else []
    
    # Create quest form
    content.append(f"""
        <div class="quest">
            <h2>Create Quest (Costs {api.QUEST_CREATION_COST} XP)</h2>
            <form action="/create_quest" method="post">
                <div class="form-group">
                    <label class="form-label" for="title">Quest Title</label>
                    <input id="title" name="title" placeholder="What needs to be done?" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="description">Description</label>
                    <textarea id="description" name="description" placeholder="Provide details about the quest..." rows="3" style="width: 100%;"></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label" for="category">Category</label>
                    <select id="category" name="category">
                        <option value="general">General</option>
                        <option value="civic">Civic</option>
                        <option value="environmental">Environmental</option>
                        <option value="social">Social</option>
                        <option value="educational">Educational</option>
                        <option value="technical">Technical</option>
                    </select>
                </div>
                <button type="submit">Create Quest</button>
            </form>
        </div>
    """)
    
    # Show quests
    content.append("<h2>Active Quests</h2>")
    for q in quests:
        boost_indicator = '<span class="boost-indicator">⭐</span>' * q.get('boost_level', 0) if q.get('boost_level', 0) > 0 else ""
        
        content.append('<div class="quest">')
        content.append('<div class="quest-header">')
        content.append(f'<div class="quest-title">{boost_indicator} {q["title"]}</div>')
        content.append(f'<div class="quest-meta">')
        content.append(f'<span>{q.get("category", "general").title()}</span>')
        content.append(f'<span>{q["status"].replace("_", " ").title()}</span>')
        content.append('</div>')
        content.append('</div>')
        
        if q.get('description'):
            content.append(f'<p>{q["description"]}</p>')
        
        content.append('<div class="quest-actions">')
        
        # Show appropriate actions based on quest status and user role
        if q['status'] == api.QuestStatus.OPEN.value:
            content.append(f"""
                <form action="/claim_quest" method="post" style="display:inline;">
                    <input type="hidden" name="quest_id" value="{q['id']}">
                    <button type="submit">Claim Quest</button>
                </form>
            """)
            # Boost button
            content.append(f"""
                <form action="/boost_quest" method="post" style="display:inline;">
                    <input type="hidden" name="quest_id" value="{q['id']}">
                    <button type="submit">Boost ({api.QUEST_BOOST_COST} XP)</button>
                </form>
            """)
        elif q['status'] == api.QuestStatus.CLAIMED.value and q.get('performer_id') == current_user['id']:
            content.append(f"""
                <form action="/submit_work" method="post" style="display:inline;">
                    <input type="hidden" name="quest_id" value="{q['id']}">
                    <button type="submit">Submit Work</button>
                </form>
            """)
        elif q['status'] == api.QuestStatus.WORK_SUBMITTED.value and q.get('performer_id') != current_user['id']:
            content.append(f"""
                <form action="/verify_quest" method="post" style="display:inline;">
                    <input type="hidden" name="quest_id" value="{q['id']}">
                    <select name="result">
                        <option value="normal">Normal</option>
                        <option value="exceptional">Exceptional</option>
                        <option value="failed">Failed</option>
                    </select>
                    <button type="submit">Verify</button>
                </form>
            """)
        
        content.append('</div>')
        content.append('</div>')
    
    return themed_html("".join(content), token, theme)


@app.get("/themes", response_class=HTMLResponse)
def themes_page(
    request: Request,
    token: Optional[str] = Cookie(None),
    theme: Optional[str] = Cookie("default"),
    tag: Optional[str] = None
):
    """Theme marketplace page."""
    content = ["<h1>Theme Marketplace</h1>"]
    
    # Get themes
    tags = [tag] if tag else None
    themes = theme_manager.list_themes(tags)
    
    # Tag filter
    all_tags = set()
    for t in themes:
        all_tags.update(t.tags)
    
    content.append('<div class="category-filter">')
    content.append(f'<a href="/themes" class="category-link {"active" if not tag else ""}">All Themes</a>')
    for t in sorted(all_tags):
        is_active = "active" if tag == t else ""
        content.append(f'<a href="/themes?tag={t}" class="category-link {is_active}">{t.title()}</a>')
    content.append('</div>')
    
    # Theme grid
    content.append('<div class="stats-grid">')
    for t in themes:
        preview_style = f'style="background: {t.colors.primary}; color: white; padding: 20px; border-radius: 8px; text-align: center;"'
        
        content.append(f"""
            <div class="quest">
                <div {preview_style}>
                    <h3 style="margin: 0;">{t.name}</h3>
                </div>
                <div style="padding: var(--spacing-medium);">
                    <p>{t.description}</p>
                    <div class="quest-meta">
                        <span>by {t.author}</span>
                        <span>⬇ {t.downloads}</span>
                        <span>⭐ {t.rating:.1f}</span>
                    </div>
                    <div class="quest-actions">
                        <button onclick="switchTheme('{t.id}')">Use Theme</button>
                        <a href="/theme/{t.id}" class="button">View Details</a>
                    </div>
                </div>
            </div>
        """)
    content.append('</div>')
    
    return themed_html("".join(content), token, theme, "Theme Marketplace")


@app.get("/theme/{theme_id}", response_class=HTMLResponse)
def theme_detail(
    theme_id: str,
    token: Optional[str] = Cookie(None),
    theme: Optional[str] = Cookie("default")
):
    """Theme detail page."""
    t = theme_manager.get_theme(theme_id)
    if not t:
        return RedirectResponse("/themes?error=Theme not found", status_code=303)
    
    content = [f"<h1>{t.name}</h1>"]
    
    # Live preview in an iframe-like container
    content.append(f"""
        <div class="quest">
            <h2>Live Preview</h2>
            <div style="border: 1px solid var(--color-surface); border-radius: var(--border-radius); overflow: hidden;">
                <iframe src="/?theme={t.id}" style="width: 100%; height: 600px; border: none;"></iframe>
            </div>
        </div>
    """)
    
    # Theme details
    content.append(f"""
        <div class="quest">
            <h2>Theme Details</h2>
            <p>{t.description}</p>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{t.downloads}</div>
                    <div class="stat-label">Downloads</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{t.rating:.1f}</div>
                    <div class="stat-label">Rating</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{t.version}</div>
                    <div class="stat-label">Version</div>
                </div>
            </div>
        </div>
    """)
    
    # Color palette
    content.append("""
        <div class="quest">
            <h2>Color Palette</h2>
            <div class="stats-grid">
    """)
    
    for color_name, color_value in t.colors.__dict__.items():
        content.append(f"""
            <div style="text-align: center;">
                <div style="background: {color_value}; width: 100%; height: 80px; border-radius: var(--border-radius); margin-bottom: var(--spacing-small);"></div>
                <div class="stat-label">{color_name.replace('_', ' ').title()}</div>
                <code style="font-size: var(--font-size-small);">{color_value}</code>
            </div>
        """)
    
    content.append("""
            </div>
        </div>
    """)
    
    # Export theme
    content.append(f"""
        <div class="quest">
            <h2>Export Theme</h2>
            <p>Copy this JSON to create your own theme variant:</p>
            <textarea readonly style="width: 100%; height: 200px; font-family: monospace; font-size: var(--font-size-small);">
{json.dumps(t.to_dict(), indent=2)}
            </textarea>
        </div>
    """)
    
    return themed_html("".join(content), token, theme, f"{t.name} - Theme")


@app.get("/stats", response_class=HTMLResponse)
def stats_dashboard(
    token: Optional[str] = Cookie(None),
    theme: Optional[str] = Cookie("default")
):
    """Display board statistics dashboard."""
    if not token:
        return RedirectResponse("/login?error=Please login first", status_code=303)
    
    # Get board stats
    stats_resp = safe_get("/stats/board", headers=get_auth_header(token))
    if stats_resp.status_code != 200:
        return RedirectResponse("/?error=Failed to load statistics", status_code=303)
    
    stats = stats_resp.json()
    
    content = ["<h1>Board Statistics</h1>"]
    
    # Overview cards
    content.append('<div class="stats-grid">')
    content.append(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['quests']['total']}</div>
            <div class="stat-label">Total Quests</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['quests']['completion_rate']}%</div>
            <div class="stat-label">Completion Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['users']['total']}</div>
            <div class="stat-label">Total Users</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['users']['active_this_week']}</div>
            <div class="stat-label">Active This Week</div>
        </div>
    """)
    content.append('</div>')
    
    # Quest breakdown
    content.append('<div class="quest">')
    content.append('<h2>Quest Breakdown</h2>')
    content.append('<div class="stats-grid">')
    
    for status, count in stats['quests']['by_status'].items():
        content.append(f"""
            <div class="stat-card">
                <div class="stat-value">{count}</div>
                <div class="stat-label">{status.replace('_', ' ').title()}</div>
            </div>
        """)
    
    content.append('</div>')
    content.append('</div>')
    
    # Category breakdown
    content.append('<div class="quest">')
    content.append('<h2>Categories</h2>')
    content.append('<div class="stats-grid">')
    
    for category, count in stats['quests']['by_category'].items():
        content.append(f"""
            <div class="stat-card">
                <div class="stat-value">{count}</div>
                <div class="stat-label">{category.title()}</div>
            </div>
        """)
    
    content.append('</div>')
    content.append('</div>')
    
    # Experience stats
    content.append(f"""
        <div class="quest">
            <h2>Experience Economy</h2>
            <p>Total XP in circulation: <span class="stat-value">{stats['experience']['total_in_circulation']}</span></p>
        </div>
    """)
    
    return themed_html("".join(content), token, theme, "Board Statistics")


# Reuse auth endpoints from original web.py
@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = "", theme: Optional[str] = Cookie("default")):
    """Show login form."""
    content = ["<h1>Login to CivicForge</h1>"]
    if error:
        content.append(f'<div class="error">{error}</div>')
    
    content.append("""
        <div class="quest">
            <form action="/login" method="post">
                <div class="form-group">
                    <label class="form-label" for="username">Username</label>
                    <input id="username" name="username" placeholder="Enter your username" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="password">Password</label>
                    <input id="password" name="password" type="password" placeholder="Enter your password" required>
                </div>
                <button type="submit">Login</button>
            </form>
            <p style="margin-top: var(--spacing-large);">Don't have an account? <a href="/register">Register here</a></p>
        </div>
    """)
    
    return themed_html("".join(content), None, theme, "Login")


@app.post("/login")
def do_login(response: Response, username: str = Form(...), password: str = Form(...)):
    """Handle login form submission."""
    resp = safe_post(
        "/auth/login",
        json={"username": username, "password": password}
    )
    
    if resp.status_code == 200:
        data = resp.json()
        response = RedirectResponse("/?success=Login successful!", status_code=303)
        response.set_cookie(key="token", value=data["token"], httponly=True, max_age=86400)
        return response
    else:
        return RedirectResponse("/login?error=Invalid username or password", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_page(error: str = "", theme: Optional[str] = Cookie("default")):
    """Show registration form."""
    content = ["<h1>Join CivicForge</h1>"]
    if error:
        content.append(f'<div class="error">{error}</div>')
    
    content.append("""
        <div class="quest">
            <form action="/register" method="post">
                <div class="form-group">
                    <label class="form-label" for="username">Username</label>
                    <input id="username" name="username" placeholder="Choose a username" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="email">Email</label>
                    <input id="email" name="email" type="email" placeholder="Your email address" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="password">Password</label>
                    <input id="password" name="password" type="password" placeholder="Choose a strong password" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="real_name">Real Name</label>
                    <input id="real_name" name="real_name" placeholder="Your real name" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="role">Role</label>
                    <select id="role" name="role">
                        <option value="Participant">Participant - Complete quests and earn XP</option>
                        <option value="Organizer">Organizer - Create and manage quests</option>
                    </select>
                </div>
                <button type="submit">Register</button>
            </form>
            <p style="margin-top: var(--spacing-large);">Already have an account? <a href="/login">Login here</a></p>
        </div>
    """)
    
    return themed_html("".join(content), None, theme, "Register")


@app.post("/register")
def do_register(
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    real_name: str = Form(...),
    role: str = Form(...)
):
    """Handle registration form submission."""
    resp = safe_post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "real_name": real_name,
            "role": role
        }
    )
    
    if resp.status_code == 200:
        data = resp.json()
        response = RedirectResponse("/?success=Registration successful! Welcome to CivicForge!", status_code=303)
        response.set_cookie(key="token", value=data["token"], httponly=True, max_age=86400)
        return response
    else:
        error_detail = resp.json().get("detail", "Registration failed")
        return RedirectResponse(f"/register?error={error_detail}", status_code=303)


@app.get("/logout")
def logout(response: Response):
    """Logout by clearing the token cookie."""
    response = RedirectResponse("/login?success=Logged out successfully", status_code=303)
    response.delete_cookie(key="token")
    return response


# Quest action endpoints (same as original)
@app.post("/create_quest")
def create_quest(
    token: Optional[str] = Cookie(None),
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("general")
):
    """Handle quest creation."""
    if not token:
        return RedirectResponse("/login?error=Please login first", status_code=303)
    
    resp = safe_post(
        "/quests",
        json={"title": title, "description": description, "category": category},
        headers=get_auth_header(token)
    )
    
    if resp.status_code == 200:
        return RedirectResponse("/?success=Quest created successfully!", status_code=303)
    else:
        error_detail = resp.json().get("detail", "Failed to create quest")
        return RedirectResponse(f"/?error={error_detail}", status_code=303)


@app.post("/claim_quest")
def claim_quest(token: Optional[str] = Cookie(None), quest_id: int = Form(...)):
    """Handle quest claiming."""
    if not token:
        return RedirectResponse("/login?error=Please login first", status_code=303)
    
    resp = safe_post(
        f"/quests/{quest_id}/claim",
        headers=get_auth_header(token)
    )
    
    if resp.status_code == 200:
        return RedirectResponse("/?success=Quest claimed successfully!", status_code=303)
    else:
        error_detail = resp.json().get("detail", "Failed to claim quest")
        return RedirectResponse(f"/?error={error_detail}", status_code=303)


@app.post("/submit_work")
def submit_work(token: Optional[str] = Cookie(None), quest_id: int = Form(...)):
    """Handle work submission."""
    if not token:
        return RedirectResponse("/login?error=Please login first", status_code=303)
    
    resp = safe_post(
        f"/quests/{quest_id}/submit",
        headers=get_auth_header(token)
    )
    
    if resp.status_code == 200:
        return RedirectResponse("/?success=Work submitted successfully!", status_code=303)
    else:
        error_detail = resp.json().get("detail", "Failed to submit work")
        return RedirectResponse(f"/?error={error_detail}", status_code=303)


@app.post("/verify_quest")
def verify_quest(
    token: Optional[str] = Cookie(None),
    quest_id: int = Form(...),
    result: str = Form(...)
):
    """Handle quest verification."""
    if not token:
        return RedirectResponse("/login?error=Please login first", status_code=303)
    
    resp = safe_post(
        f"/quests/{quest_id}/verify",
        json={"result": result},
        headers=get_auth_header(token)
    )
    
    if resp.status_code == 200:
        return RedirectResponse("/?success=Quest verified successfully!", status_code=303)
    else:
        error_detail = resp.json().get("detail", "Failed to verify quest")
        return RedirectResponse(f"/?error={error_detail}", status_code=303)


@app.post("/boost_quest")
def boost_quest(token: Optional[str] = Cookie(None), quest_id: int = Form(...)):
    """Handle quest boosting."""
    if not token:
        return RedirectResponse("/login?error=Please login first", status_code=303)
    
    resp = safe_post(
        f"/quests/{quest_id}/boost",
        headers=get_auth_header(token)
    )
    
    if resp.status_code == 200:
        return RedirectResponse("/?success=Quest boosted successfully!", status_code=303)
    else:
        error_detail = resp.json().get("detail", "Failed to boost quest")
        return RedirectResponse(f"/?error={error_detail}", status_code=303)


# Theme API endpoints - using /theme-api to avoid conflict with /api mount
@app.get("/theme-api/themes")
def get_themes(tags: Optional[str] = Query(None)):
    """API endpoint to get themes."""
    tag_list = tags.split(",") if tags else None
    themes = theme_manager.list_themes(tag_list)
    return {"themes": [t.to_dict() for t in themes]}


@app.get("/theme-api/theme/{theme_id}")
def get_theme(theme_id: str):
    """API endpoint to get a specific theme."""
    theme = theme_manager.get_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme.to_dict()


@app.post("/theme-api/theme")
def create_theme(theme_data: dict, token: Optional[str] = Cookie(None)):
    """API endpoint to create a new theme (requires authentication)."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate theme data
    try:
        theme = Theme.from_dict(theme_data)
        theme_manager.save_theme(theme)
        return {"message": "Theme created successfully", "theme_id": theme.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))