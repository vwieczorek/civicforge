import argparse
import os
from board_mvp import api


def main():
    parser = argparse.ArgumentParser(description="CivicForge Board CLI")
    parser.add_argument("--db", default=api.DB_PATH, help="Path to SQLite database")
    subparsers = parser.add_subparsers(dest="command")

    p_create_user = subparsers.add_parser("create-user", help="Create a new user")
    p_create_user.add_argument("username")
    p_create_user.add_argument("real_name")
    p_create_user.add_argument("role")

    subparsers.add_parser("list-users", help="List all users")

    p_view_user = subparsers.add_parser("view-user", help="View a user")
    p_view_user.add_argument("user_id", type=int)

    p_create_quest = subparsers.add_parser("create-quest", help="Create a new quest")
    p_create_quest.add_argument("title")
    p_create_quest.add_argument("creator_id", type=int)
    p_create_quest.add_argument("--description", default="")
    p_create_quest.add_argument("--reward", type=int, default=0)

    p_claim = subparsers.add_parser("claim-quest", help="Claim a quest")
    p_claim.add_argument("quest_id", type=int)
    p_claim.add_argument("performer_id", type=int)

    p_submit = subparsers.add_parser("submit-work", help="Submit quest work")
    p_submit.add_argument("quest_id", type=int)
    p_submit.add_argument("performer_id", type=int)

    p_verify = subparsers.add_parser("verify-quest", help="Verify quest completion")
    p_verify.add_argument("quest_id", type=int)
    p_verify.add_argument("verifier_id", type=int)
    p_verify.add_argument("result", choices=["normal", "exceptional", "failed"])

    subparsers.add_parser("list-quests", help="List all quests")

    p_view = subparsers.add_parser("view-quest", help="View a quest")
    p_view.add_argument("quest_id", type=int)

    p_exp = subparsers.add_parser("user-exp", help="Show a user's experience")
    p_exp.add_argument("user_id", type=int)

    subparsers.add_parser("run-decay", help="Apply weekly experience decay")

    args = parser.parse_args()

    os.environ["BOARD_DB_PATH"] = args.db

    if args.command == "create-user":
        user = api.create_user(api.UserCreate(username=args.username, real_name=args.real_name, role=args.role))
        print(user)
    elif args.command == "list-users":
        for u in api.list_users():
            print(u)
    elif args.command == "view-user":
        print(api.get_user_by_id(args.user_id))
    elif args.command == "create-quest":
        quest = api.create_quest(
            api.QuestCreate(
                title=args.title,
                description=args.description,
                reward=args.reward,
                creator_id=args.creator_id,
            )
        )
        print(quest)
    elif args.command == "claim-quest":
        quest = api.claim_quest(args.quest_id, api.ClaimRequest(performer_id=args.performer_id))
        print(quest)
    elif args.command == "submit-work":
        quest = api.submit_work(args.quest_id, api.SubmitRequest(performer_id=args.performer_id))
        print(quest)
    elif args.command == "verify-quest":
        quest = api.verify_quest(args.quest_id, api.VerificationRequest(verifier_id=args.verifier_id, result=args.result))
        print(quest)
    elif args.command == "list-quests":
        for q in api.list_quests():
            print(q)
    elif args.command == "view-quest":
        print(api.get_quest(args.quest_id))
    elif args.command == "user-exp":
        print(api.get_user_experience(args.user_id))
    elif args.command == "run-decay":
        api.run_decay()
        print("Decay applied")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
