import os
import importlib
from board_mvp import models


def load_api(path):
    os.environ["BOARD_DB_PATH"] = str(path)
    if "board_mvp.api" in importlib.sys.modules:
        importlib.reload(importlib.import_module("board_mvp.api"))
    return importlib.import_module("board_mvp.api")


def test_quest_lifecycle(tmp_path):
    db_path = tmp_path / "api.db"
    api = load_api(db_path)

    # create users
    alice = api.create_user(api.UserCreate(username="alice", real_name="Alice", role="Organizer"))
    bob = api.create_user(api.UserCreate(username="bob", real_name="Bob", role="Participant"))

    # create quest
    quest = api.create_quest(api.QuestCreate(title="Clean park", description="Pick up trash", reward=10, creator_id=alice.id))

    # claim quest
    quest = api.claim_quest(quest.id, api.ClaimRequest(performer_id=bob.id))
    assert quest.status == api.QuestStatus.CLAIMED

    # submit work
    quest = api.submit_work(quest.id, api.SubmitRequest(performer_id=bob.id))
    assert quest.status == api.QuestStatus.WORK_SUBMITTED

    # verify quest
    quest = api.verify_quest(quest.id, api.VerificationRequest(verifier_id=alice.id, result="normal"))
    assert quest.status == api.QuestStatus.LOGGED_COMPLETED
