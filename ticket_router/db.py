from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from ticket_router.config import config
from ticket_router.logger import logger
from ticket_router.models import TicketRouteResult

Base = declarative_base()


class RoutedTicket(Base):
    """One row per successfully routed ticket: the original message plus
    the AI's routing decision. This is the persistence layer's only table -
    intentionally minimal (ticket + routing decision), not a full
    conversation/audit log.
    """

    __tablename__ = "routed_tickets"

    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)
    priority = Column(String(16), nullable=False)
    assigned_team = Column(String(64), nullable=False)
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    model_used = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    return _engine


def _get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine())
    return _SessionLocal()


def init_db() -> bool:
    """Creates tables if they don't already exist. Returns True on success,
    False if Postgres is unreachable - persistence is best-effort so the
    app still boots and routes tickets without a database running.
    """
    try:
        Base.metadata.create_all(_get_engine())
        return True
    except Exception as error:  # noqa: BLE001 - DB availability must never crash the app
        logger.warning("Database unavailable, ticket persistence disabled", {"error": str(error)})
        return False


def save_routing_decision(message: str, result: TicketRouteResult) -> None:
    """Best-effort persistence of a routed ticket. Never raises - a
    database outage must not break ticket routing for the user.
    """
    try:
        session = _get_session()
        try:
            session.add(
                RoutedTicket(
                    message=message,
                    category=result.category,
                    priority=result.priority,
                    assigned_team=result.assigned_team,
                    reasoning=result.reasoning,
                    confidence=result.confidence,
                    model_used=result.model_used,
                )
            )
            session.commit()
        finally:
            session.close()
    except Exception as error:  # noqa: BLE001 - DB availability must never crash the app
        logger.warning("Failed to persist routed ticket", {"error": str(error)})
