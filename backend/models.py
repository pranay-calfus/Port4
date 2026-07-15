"""ORM models for the backend API: users (both roles), tickets, the
persisted message thread, and the audit trail. Category/priority/department
values are validated at the Pydantic schema layer (backend/schemas.py)
against the existing ticket_router.models Literals - they're plain strings
here since SQLAlchemy's Enum type would need updating every time a category
is added, and that validation already lives in one place.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class TicketStatus(StrEnum):
    NEW = "NEW"
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_CUSTOMER = "PENDING_CUSTOMER"
    ON_HOLD = "ON_HOLD"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SenderType(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"
    AI = "AI"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.USER, nullable=False)
    # Only meaningful for ADMIN rows: the one team this admin can see. NULL
    # means a super-admin with visibility into every team. Always NULL for
    # USER rows.
    department: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    department: Mapped[str] = mapped_column(String(50))
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.NEW, nullable=False
    )
    assigned_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_emotion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # The AI's own priority suggestion, immutable once set - kept separate
    # from the mutable `priority` column above (which starts out equal to
    # this, but can be overridden by the customer at creation time or
    # reassigned by an admin later) so the UI can show "AI suggested X, you
    # chose Y" the way the original Router tab did.
    ai_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # How long the route_ticket() call itself took, in milliseconds - shown
    # against an admin's own manual-triage time in the admin dashboard's
    # "Manual Routing" comparison panel.
    ai_processing_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    assigned_admin = relationship("User", foreign_keys=[assigned_admin_id])
    messages = relationship(
        "TicketMessage",
        back_populates="ticket",
        order_by="TicketMessage.created_at",
        cascade="all, delete-orphan",
    )
    activity = relationship(
        "TicketActivity",
        back_populates="ticket",
        order_by="TicketActivity.created_at",
        cascade="all, delete-orphan",
    )


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    sender_type: Mapped[SenderType] = mapped_column(Enum(SenderType), nullable=False)
    # NULL for AI-authored messages; set for USER/ADMIN messages.
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    # Reserved for future file-upload support - no upload UI/endpoint yet.
    attachments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    ticket = relationship("Ticket", back_populates="messages")


class TicketActivity(Base):
    __tablename__ = "ticket_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    ticket = relationship("Ticket", back_populates="activity")
