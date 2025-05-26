from fastapi import FastAPI, Request, Response, Cookie, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import requests
from urllib.parse import urljoin

from . import api
from .database import init_db

app = FastAPI(title="CivicForge Board Web UI")

# Initialize the database
init_db()

# Run migrations on startup
def run_migrations():
    """Run database migrations on startup."""
    try:
        from .migrations_pg import run_migrations as pg_migrations
        from .database import get_db
        db = get_db()
        # Check if we're using PostgreSQL
        if hasattr(db.adapter, 'connection_string') and 'postgresql' in db.adapter.connection_string:
            print("Running PostgreSQL migrations...")
            pg_migrations()
            print("Migrations completed successfully")
    except Exception as e:
        print(f"Warning: Could not run migrations: {e}")

# Run migrations when the app starts
run_migrations()

# Mount the existing API under /api for convenience
app.mount("/api", api.app)

# Base URL for API calls - use environment variable or default to localhost
import os
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api")


def get_auth_header(token: str) -> dict:
    """Get authorization header for API calls."""
    return {"Authorization": f"Bearer {token}"} if token else {}

def safe_get(path: str, **kwargs):
    """Make a safe GET request to the API, validating the URL against API_BASE."""
    # Simple string concatenation instead of urljoin
    if not path.startswith('/'):
        path = '/' + path
    url = API_BASE + path
    return requests.get(url, **kwargs)

def safe_post(path: str, **kwargs):
    """Make a safe POST request to the API, validating the URL against API_BASE."""
    # Simple string concatenation instead of urljoin
    if not path.startswith('/'):
        path = '/' + path
    url = API_BASE + path
    return requests.post(url, **kwargs)


def base_html(content: str, token: Optional[str] = None) -> str:
    """Wrap content in base HTML with navigation."""
    nav_items = []
    if token:
        nav_items.extend([
            '<a href="/">Board</a>',
            '<a href="/stats">Stats</a>',
            '<a href="/logout">Logout</a>'
        ])
    else:
        nav_items.extend([
            '<a href="/login">Login</a>',
            '<a href="/register">Register</a>'
        ])
    
    nav = " | ".join(nav_items)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CivicForge Board</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .nav {{ margin-bottom: 20px; padding: 10px; background: #f0f0f0; }}
            .error {{ color: red; margin: 10px 0; }}
            .success {{ color: green; margin: 10px 0; }}
            .quest {{ border: 1px solid #ddd; padding: 10px; margin: 10px 0; }}
            .quest-actions {{ margin-top: 10px; }}
            form {{ margin: 10px 0; }}
            input, select, button {{ margin: 5px 0; padding: 5px; }}
        </style>
    </head>
    <body>
        <div class="nav">{nav}</div>
        {content}
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def index(request: Request, error: str = "", success: str = "", category: str = None, token: Optional[str] = Cookie(None)):
    """List quests and provide forms for quest actions."""
    content = ["<h1>CivicForge Board</h1>"]
    
    if error:
        content.append(f'<p class="error">{error}</p>')
    if success:
        content.append(f'<p class="success">{success}</p>')
    
    if not token:
        content.append("<p>Please <a href='/login'>login</a> or <a href='/register'>register</a> to participate.</p>")
        return base_html("".join(content), token)
    
    # Get current user info
    try:
        resp = safe_get("/me", headers=get_auth_header(token))
        if resp.status_code != 200:
            return RedirectResponse("/login?error=Session expired", status_code=303)
        current_user = resp.json()

        # Get user's XP balance
        xp_resp = safe_get(f"/users/{current_user['id']}/experience", headers=get_auth_header(token))
        xp_balance = xp_resp.json().get("experience_balance", 0) if xp_resp.status_code == 200 else 0

        content.append(f"<p>Welcome, {current_user['username']}! You have {xp_balance} XP.</p>")
    except HTTPException:
        raise
    except:
        return RedirectResponse("/login?error=Session expired", status_code=303)

    # Get categories for filtering
    categories_resp = safe_get("/categories")
    categories = categories_resp.json().get("categories", []) if categories_resp.status_code == 200 else []

    # Show category filter
    content.append("<h2>Quest Categories</h2>")
    content.append("<a href='/'>All Quests</a> | ")
    for cat in categories:
        content.append(f"<a href='/?category={cat['name']}'>{cat['name'].title()} ({cat['count']})</a> | ")

    # Get quests, validating category parameter
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
        <h2>Create Quest (Costs {api.QUEST_CREATION_COST} XP)</h2>
        <form action='/create_quest' method='post'>
            <input name='title' placeholder='Quest Title' required><br>
            <textarea name='description' placeholder='Quest Description' rows='3' cols='50'></textarea><br>
            <select name='category'>
                <option value='general'>General</option>
                <option value='civic'>Civic</option>
                <option value='environmental'>Environmental</option>
                <option value='social'>Social</option>
                <option value='educational'>Educational</option>
                <option value='technical'>Technical</option>
            </select><br>
            <button type='submit'>Create Quest</button>
        </form>
    """)
    
    # Show quests
    content.append("<h2>Active Quests</h2>")
    for q in quests:
        boost_indicator = "⭐" * q.get('boost_level', 0) if q.get('boost_level', 0) > 0 else ""
        content.append(f"<div class='quest'>")
        content.append(f"<strong>{boost_indicator} {q['title']}</strong> - [{q.get('category', 'general')}] - Status: {q['status']}<br>")
        if q.get('description'):
            content.append(f"<em>{q['description']}</em><br>")
        
        content.append("<div class='quest-actions'>")
        
        # Show appropriate actions based on quest status and user role
        if q['status'] == api.QuestStatus.OPEN.value:
            content.append(f"""
                <form action='/claim_quest' method='post' style='display:inline;'>
                    <input type='hidden' name='quest_id' value='{q['id']}'>
                    <button type='submit'>Claim Quest</button>
                </form>
            """)
            # Boost button
            content.append(f"""
                <form action='/boost_quest' method='post' style='display:inline;'>
                    <input type='hidden' name='quest_id' value='{q['id']}'>
                    <button type='submit'>Boost ({api.QUEST_BOOST_COST} XP)</button>
                </form>
            """)
        elif q['status'] == api.QuestStatus.CLAIMED.value and q.get('performer_id') == current_user['id']:
            content.append(f"""
                <form action='/submit_work' method='post' style='display:inline;'>
                    <input type='hidden' name='quest_id' value='{q['id']}'>
                    <button type='submit'>Submit Work</button>
                </form>
            """)
        elif q['status'] == api.QuestStatus.WORK_SUBMITTED.value and q.get('performer_id') != current_user['id']:
            content.append(f"""
                <form action='/verify_quest' method='post' style='display:inline;'>
                    <input type='hidden' name='quest_id' value='{q['id']}'>
                    <select name='result'>
                        <option value='normal'>Normal</option>
                        <option value='exceptional'>Exceptional</option>
                        <option value='failed'>Failed</option>
                    </select>
                    <button type='submit'>Verify</button>
                </form>
            """)
        
        content.append("</div></div>")
    
    return base_html("".join(content), token)


@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    """Show login form."""
    content = ["<h1>Login</h1>"]
    if error:
        content.append(f'<p class="error">{error}</p>')
    
    content.append("""
        <form action='/login' method='post'>
            <input name='username' placeholder='Username' required><br>
            <input name='password' type='password' placeholder='Password' required><br>
            <button type='submit'>Login</button>
        </form>
        <p>Don't have an account? <a href='/register'>Register here</a></p>
    """)
    
    return base_html("".join(content))


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
def register_page(error: str = ""):
    """Show registration form."""
    content = ["<h1>Register</h1>"]
    if error:
        content.append(f'<p class="error">{error}</p>')
    
    content.append("""
        <form action='/register' method='post'>
            <input name='username' placeholder='Username' required><br>
            <input name='email' type='email' placeholder='Email' required><br>
            <input name='password' type='password' placeholder='Password' required><br>
            <input name='real_name' placeholder='Real Name' required><br>
            <select name='role'>
                <option value='Participant'>Participant</option>
                <option value='Organizer'>Organizer</option>
            </select><br>
            <button type='submit'>Register</button>
        </form>
        <p>Already have an account? <a href='/login'>Login here</a></p>
    """)
    
    return base_html("".join(content))


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


@app.get("/stats", response_class=HTMLResponse)
def stats_dashboard(token: Optional[str] = Cookie(None)):
    """Display board statistics dashboard."""
    if not token:
        return RedirectResponse("/login?error=Please login first", status_code=303)
    
    # Get board stats
    stats_resp = safe_get(f"/stats/board", headers=get_auth_header(token))
    if stats_resp.status_code != 200:
        return RedirectResponse("/?error=Failed to load statistics", status_code=303)
    
    stats = stats_resp.json()
    
    content = ["<h1>CivicForge Board Statistics</h1>"]
    
    # Quest statistics
    content.append("<h2>Quest Statistics</h2>")
    content.append(f"<p>Total Quests: {stats['quests']['total']}</p>")
    content.append(f"<p>Completion Rate: {stats['quests']['completion_rate']}%</p>")
    
    content.append("<h3>Quests by Status</h3><ul>")
    for status, count in stats['quests']['by_status'].items():
        content.append(f"<li>{status}: {count}</li>")
    content.append("</ul>")
    
    content.append("<h3>Quests by Category</h3><ul>")
    for category, count in stats['quests']['by_category'].items():
        content.append(f"<li>{category}: {count}</li>")
    content.append("</ul>")
    
    # User statistics
    content.append("<h2>User Statistics</h2>")
    content.append(f"<p>Total Users: {stats['users']['total']}</p>")
    content.append(f"<p>Active Users (this week): {stats['users']['active_this_week']}</p>")
    
    content.append("<h3>Users by Role</h3><ul>")
    for role, count in stats['users']['by_role'].items():
        content.append(f"<li>{role}: {count}</li>")
    content.append("</ul>")
    
    # Experience statistics
    content.append("<h2>Experience Statistics</h2>")
    content.append(f"<p>Total XP in Circulation: {stats['experience']['total_in_circulation']}</p>")
    
    return base_html("".join(content), token)