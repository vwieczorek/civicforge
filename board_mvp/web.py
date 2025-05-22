from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from board_mvp import api

app = FastAPI(title="CivicForge Board Web UI")

# Mount the existing API under /api for convenience
app.mount("/api", api.app)


@app.get("/", response_class=HTMLResponse)
def index():
    """Simple page listing quests and a form to create new ones."""
    quests = api.list_quests()
    html = ["<h1>CivicForge Board</h1>"]
    html.append("<h2>Quests</h2><ul>")
    for q in quests:
        html.append(f"<li>{q.title} - {q.status}</li>")
    html.append("</ul>")
    html.append(
        """
        <h2>Create Quest</h2>
        <form action="/create" method="post">
            <input name="title" placeholder="Title" required>
            <input name="creator_id" type="number" placeholder="Creator ID" required>
            <button type="submit">Create</button>
        </form>
        """
    )
    return "".join(html)


@app.post("/create")
def create_quest(title: str = Form(...), creator_id: int = Form(...)):
    """Handle simple quest creation and redirect back to index."""
    try:
        api.create_quest(api.QuestCreate(title=title, creator_id=creator_id))
    except Exception:
        # TODO: surface error to the user in a nicer way
        pass
    return RedirectResponse("/", status_code=303)
