import os
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

# ── Settings ──────────────────────────────────────────────────────────────────
# Import lazily to avoid circular imports; fall back to env vars if config unavailable
try:
    from app.config import settings
    _DATABASE_URL = settings.DATABASE_URL
except Exception:
    _DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./loanwizard.db")

# ── URL handling ──────────────────────────────────────────────────────────────
_RAW_URL  = _DATABASE_URL
ASYNC_URL = _RAW_URL.replace("postgresql://", "postgresql+asyncpg://")

# SYNC_URL for Alembic (uses psycopg2/sqlite, not asyncpg/aiosqlite)
SYNC_URL = (
    _RAW_URL
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("sqlite+aiosqlite://",   "sqlite://")
)

_is_sqlite = "sqlite" in ASYNC_URL

async_engine = create_async_engine(
    ASYNC_URL,
    echo=False,
    **({} if _is_sqlite else {
        "pool_size":     10,
        "max_overflow":  20,
        "pool_pre_ping": True,
    }),
)

async_session_factory = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

_now = lambda: datetime.now(timezone.utc)


# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role            = Column(String, default="applicant")
    full_name       = Column(String, default="")
    created_at      = Column(DateTime(timezone=True), default=_now)


class Application(Base):
    __tablename__ = "applications"
    id             = Column(Integer, primary_key=True, index=True)
    session_id     = Column(String, unique=True, index=True, nullable=False)
    applicant_id   = Column(Integer, ForeignKey("users.id"), index=True)
    applicant_name = Column(String, default="")
    loan_product   = Column(String, default="personal")

    transcript     = Column(Text,    default="")
    income         = Column(Integer, default=0)
    consent        = Column(Boolean, default=False)
    risk_level     = Column(String,  default="medium")

    face_detected  = Column(Boolean, default=False)
    liveness_score = Column(Float,   default=0.0)
    spoof_detected = Column(Boolean, default=False)
    multiple_faces = Column(Boolean, default=False)
    screen_spoof   = Column(Boolean, default=False)

    status        = Column(String,  default="Pending", index=True)
    confidence    = Column(Float,   default=0.0)
    credit_band   = Column(String,  default="")
    model_version = Column(String,  default="")
    emi           = Column(Integer, nullable=True)
    tenure        = Column(String,  nullable=True)
    loan_amount   = Column(Integer, nullable=True)
    total_ms      = Column(Integer, default=0)

    auditor_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    auditor_note     = Column(Text,    default="")
    auditor_override = Column(String,  nullable=True)
    flagged          = Column(Boolean, default=False, index=True)

    created_at  = Column(DateTime(timezone=True), default=_now, index=True)
    updated_at  = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    version     = Column(Integer, default=0, nullable=False)

    reasons = relationship(
        "DecisionReason",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_applications_queue", "flagged", "created_at"),
    )


class DecisionReason(Base):
    __tablename__ = "decision_reasons"
    id             = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), index=True)
    kind           = Column(String, nullable=False)
    reason         = Column(Text,   nullable=False)

    application = relationship("Application", back_populates="reasons")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    actor_id   = Column(Integer)
    actor_role = Column(String)
    action     = Column(String, index=True)
    detail     = Column(Text, default="")
    timestamp  = Column(DateTime(timezone=True), default=_now, index=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
