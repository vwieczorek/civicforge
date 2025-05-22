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

    # experience rewards
    perf_xp = api.get_user_experience(bob.id)
    ver_xp = api.get_user_experience(alice.id)
    assert perf_xp == 10
    assert ver_xp == 5

    # reputation updates
    perf_rep = api.get_user_by_id(bob.id).reputation
    ver_rep = api.get_user_by_id(alice.id).reputation
    assert perf_rep == 1
    assert ver_rep == 1


def test_decay(tmp_path):
    db_path = tmp_path / "decay.db"
    api = load_api(db_path)

    user = api.create_user(api.UserCreate(username="u", real_name="U", role="Org"))
    api.add_experience(user.id, 10, "bonus")
    assert api.get_user_experience(user.id) == 10
    api.run_decay(amount=2)
    assert api.get_user_experience(user.id) == 8


def test_multiple_decay_runs(tmp_path):
    db_path = tmp_path / "multi.db"
    api = load_api(db_path)

    user = api.create_user(api.UserCreate(username="m", real_name="M", role="Org"))
    api.add_experience(user.id, 10, "bonus")

    api.run_decay(amount=1)
    api.run_decay(amount=1)
    assert api.get_user_experience(user.id) == 8

    cur = api.conn.cursor()
    cur.execute("SELECT COUNT(*) FROM experience_ledger WHERE entry_type='decay'")
    count = cur.fetchone()[0]
    assert count == 2
