"""One-off CLI to provision an admin account. There is no self-service admin
registration endpoint by design (admin login must not be reachable through
the normal user-facing flow) - this script is how the first, and every
subsequent, admin account gets created.

Usage:
    python -m backend.create_admin --name "Ops Admin" --email admin@example.com --password <pw>
    python -m backend.create_admin --name "Jane" --email jane@example.com --password <pw> \
        --department Engineering
"""

import argparse
import sys

from backend.db import run_migrations
from backend.models import Role
from backend.services import ticket_service
from backend.supabase_client import client
from ticket_router.models import ASSIGNED_TEAMS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--department",
        choices=ASSIGNED_TEAMS,
        default=None,
        help="Scope this admin to one team's tickets. Omit for a super-admin who sees every team.",
    )
    args = parser.parse_args()

    run_migrations()
    try:
        user = ticket_service.create_user(
            client,
            name=args.name,
            email=args.email,
            password=args.password,
            role=Role.ADMIN,
            department=args.department,
        )
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    scope = args.department or "all departments (super-admin)"
    print(f"Created admin '{user['name']}' <{user['email']}> scoped to: {scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
