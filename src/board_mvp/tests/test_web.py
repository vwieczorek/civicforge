import os
import importlib


def load_web(path):
    os.environ["BOARD_DB_PATH"] = str(path)
    if "board_mvp.api" in importlib.sys.modules:
        importlib.reload(importlib.import_module("board_mvp.api"))
    if "board_mvp.web" in importlib.sys.modules:
        importlib.reload(importlib.import_module("board_mvp.web"))
    return importlib.import_module("board_mvp.web")


def test_web_forms(tmp_path):
    db_path = tmp_path / "web.db"
    web = load_web(db_path)
    api = importlib.import_module("board_mvp.api")

    alice = api.create_user(api.UserCreate(username="alice", real_name="Alice", role="Organizer"))
    bob = api.create_user(api.UserCreate(username="bob", real_name="Bob", role="Participant"))

    resp = web.create_quest(title="Clean", creator_id=alice.id)
    assert resp.status_code == 303
    quest = api.list_quests()[0]

    resp = web.claim_quest(quest_id=quest.id, performer_id=bob.id)
    assert resp.status_code == 303
    assert api.get_quest(quest.id).status == api.QuestStatus.CLAIMED

    resp = web.submit_work(quest_id=quest.id, performer_id=bob.id)
    assert resp.status_code == 303
    assert api.get_quest(quest.id).status == api.QuestStatus.WORK_SUBMITTED

    resp = web.verify_quest(
        quest_id=quest.id,
        verifier_id=alice.id,
        result="normal",
    )
    assert resp.status_code == 303
    assert api.get_quest(quest.id).status == api.QuestStatus.LOGGED_COMPLETED

