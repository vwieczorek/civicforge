from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from board_mvp import api

app = FastAPI(title="CivicForge Board Web UI")

# Mount the existing API under /api for convenience
app.mount("/api", api.app)


@app.get("/", response_class=HTMLResponse)
def index(error: str = ""):
    """List quests and provide forms for quest actions."""
    quests = api.list_quests()
    html = ["<h1>CivicForge Board</h1>"]
    if error:
        html.append(f"<p style='color:red;'>{error}</p>")
    html.append("<h2>Quests</h2><ul>")
    for q in quests:
        html.append(f"<li>{q.title} - {q.status}")
        if q.status == api.QuestStatus.OPEN.value:
            html.append(f"""
            <form action='/claim' method='get'>
                <input type='hidden' name='quest_id' value='{q.id}'>
                <input name='performer_id' type='number' placeholder='Performer ID' required>
                <button type='submit'>Claim</button>
            </form>
            """)
        elif q.status == api.QuestStatus.CLAIMED.value:
            html.append(f"""
            <form action='/submit' method='get'>
                <input type='hidden' name='quest_id' value='{q.id}'>
                <input name='performer_id' type='number' placeholder='Performer ID' required>
                <button type='submit'>Submit Work</button>
            </form>
            """)
        elif q.status == api.QuestStatus.WORK_SUBMITTED.value:
            html.append(f"""
            <form action='/verify' method='get'>
                <input type='hidden' name='quest_id' value='{q.id}'>
                <input name='verifier_id' type='number' placeholder='Verifier ID' required>
                <select name='result'>
                    <option value='normal'>normal</option>
                    <option value='exceptional'>exceptional</option>
                    <option value='failed'>failed</option>
                </select>
                <button type='submit'>Verify</button>
            </form>
            """)
        html.append("</li>")
    html.append("</ul>")
    html.append(
        """
        <h2>Create Quest</h2>
        <form action='/create' method='get'>
            <input name='title' placeholder='Title' required>
            <input name='creator_id' type='number' placeholder='Creator ID' required>
            <button type='submit'>Create</button>
        </form>
        """
    )
    return "".join(html)


@app.get("/create")
def create_quest(title: str, creator_id: int):
    """Create a quest via the form."""
    try:
        api.create_quest(api.QuestCreate(title=title, creator_id=creator_id))
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/?error={getattr(e, 'detail', str(e))}", status_code=303)


@app.get("/claim")
def claim_quest(quest_id: int, performer_id: int):
    try:
        api.claim_quest(quest_id, api.ClaimRequest(performer_id=performer_id))
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/?error={getattr(e, 'detail', str(e))}", status_code=303)


@app.get("/submit")
def submit_work(quest_id: int, performer_id: int):
    try:
        api.submit_work(quest_id, api.SubmitRequest(performer_id=performer_id))
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/?error={getattr(e, 'detail', str(e))}", status_code=303)


@app.get("/verify")
def verify_quest(
    quest_id: int,
    verifier_id: int,
    result: str,
):
    try:
        api.verify_quest(
            quest_id,
            api.VerificationRequest(verifier_id=verifier_id, result=result),
        )
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/?error={getattr(e, 'detail', str(e))}", status_code=303)
