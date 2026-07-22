"""Optional startup seeding of fixed dev accounts from environment
variables. Lets a super-admin and a Product & CX account exist right after
a fresh (or just-wiped, e.g. by the test suite's truncation fixture)
database, without going through backend/create_admin.py or the UI.

Each account is only seeded when both its *_EMAIL and *_PASSWORD env vars
are set (see ticket_router/config.py), and only if that email doesn't
already exist - an existing account's password is never touched, so
rotating a real password in the DB isn't silently undone by a restart.
"""

from backend.models import Role
from backend.services import ticket_service
from backend.supabase_client import client
from ticket_router.config import config
from ticket_router.logger import logger


def _seed_one(email: str, password: str, *, role: Role, label: str) -> None:
    if not email or not password:
        return
    if ticket_service.get_user_by_email(client, email) is not None:
        return
    ticket_service.create_user(client, name=label, email=email, password=password, role=role)
    logger.info(f"Seeded {label} account from environment variables", {"email": email})


def seed_accounts() -> None:
    _seed_one(
        config.SUPER_ADMIN_EMAIL, config.SUPER_ADMIN_PASSWORD, role=Role.ADMIN, label="Super Admin"
    )
    _seed_one(
        config.PRODUCT_CX_EMAIL,
        config.PRODUCT_CX_PASSWORD,
        role=Role.PRODUCT_CX,
        label="Product & CX",
    )
