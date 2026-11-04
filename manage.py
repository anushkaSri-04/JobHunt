"""python manage.py <command>
   createuser NAME | passwd NAME | seed | run [--mock] [--email] | clear | email
   profile seed|list|add|remove [NAME] | rematch
"""
import argparse, getpass, sys
from argon2 import PasswordHasher
from sqlalchemy import select
from app.db import SessionLocal, engine, Base
from app import models as m
from app.runner import run_pipeline, seed_companies, seed_profile, rematch_all, profile_skills
from engine.skills import canonical


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    cu = sub.add_parser("createuser"); cu.add_argument("username")
    pw = sub.add_parser("passwd"); pw.add_argument("username")
    r = sub.add_parser("run"); r.add_argument("--mock", action="store_true"); r.add_argument("--email", action="store_true")
    pf = sub.add_parser("profile"); pf.add_argument("action", choices=["seed", "list", "add", "remove"]); pf.add_argument("name", nargs="?")
    for name in ("seed", "clear", "email", "rematch"):
        sub.add_parser(name)
    a = p.parse_args()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if a.cmd == "createuser":
            if db.scalar(select(m.AppUser.id).limit(1)):
                sys.exit("A user already exists (single-user app).")
            pw1 = getpass.getpass("Password (12+ chars): ")
            if len(pw1) < 12 or pw1 != getpass.getpass("Repeat: "):
                sys.exit("Password too short or mismatch.")
            db.add(m.AppUser(username=a.username, password_hash=PasswordHasher().hash(pw1)))
            db.commit(); print("User created.")
        elif a.cmd == "passwd":
            user = db.scalar(select(m.AppUser).where(m.AppUser.username == a.username))
            if not user:
                sys.exit(f"No such user: {a.username}")
            pw1 = getpass.getpass("New password (12+ chars): ")
            if len(pw1) < 12 or pw1 != getpass.getpass("Repeat: "):
                sys.exit("Password too short or mismatch.")
            user.password_hash = PasswordHasher().hash(pw1)
            db.commit(); print("Password updated.")
        elif a.cmd == "seed":
            print(f"Seeded {seed_companies(db)} companies.")
        elif a.cmd == "run":
            seed_companies(db)
            run = run_pipeline(db, mock=a.mock, trigger="cli")
            print(run.counts); print(run.log)
            if a.email:
                from app.emailer import send_daily
                print(send_daily(db))
        elif a.cmd == "clear":
            db.query(m.Job).delete()
            db.query(m.Run).delete()
            db.commit(); print("Jobs and runs cleared.")
        elif a.cmd == "email":
            from app.emailer import send_daily
            print(send_daily(db))
        elif a.cmd == "rematch":
            print(f"Rematched {rematch_all(db)} jobs.")
        elif a.cmd == "profile":
            if a.action == "seed":
                found, unknown = seed_profile(db)
                print(f"Profile now has {len(profile_skills(db))} skills:", ", ".join(sorted(profile_skills(db))))
                if unknown:
                    print("Not in the dictionary (add them to engine/skills.yaml):", ", ".join(unknown))
                print(f"Rematched {rematch_all(db)} jobs.")
            elif a.action == "list":
                print("\n".join(sorted(profile_skills(db))) or "(empty)")
            else:
                name = canonical(a.name or "")
                if not name:
                    sys.exit(f"'{a.name}' is not in engine/skills.yaml. Add it there first.")
                row = db.scalar(select(m.ProfileSkill).where(m.ProfileSkill.name == name))
                if a.action == "add" and not row:
                    db.add(m.ProfileSkill(name=name))
                elif a.action == "remove" and row:
                    db.delete(row)
                db.commit()
                print(f"{a.action}: {name}. Rematched {rematch_all(db)} jobs.")


if __name__ == "__main__":
    main()