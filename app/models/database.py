"""
Database models — SQLAlchemy ORM
SQLite for local/Railway/Render (zero-config), swap DATABASE_URL for Postgres in prod
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, Text, ForeignKey, JSON, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import uuid, os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./ecovalue.db"

# Railway/Render Postgres fix: they give postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables on startup."""
    Base.metadata.create_all(bind=engine)


# ── Models ────────────────────────────────────────────────────────────────────

class ValuationRecord(Base):
    """Stores every /valuate request + result for history and analytics."""
    __tablename__ = "valuations"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at       = Column(DateTime, default=datetime.utcnow, index=True)

    # Input params
    ecosystem_type   = Column(String, nullable=False, index=True)
    ecosystem_name   = Column(String, nullable=False)
    area_hectares    = Column(Float, nullable=False)
    region           = Column(String, nullable=False, index=True)
    location_name    = Column(String, nullable=True)
    carbon_pricing   = Column(String, default="voluntary_market")
    discount_rate    = Column(Float, default=0.08)
    projection_years = Column(Integer, default=10)
    value_type       = Column(String, default="midpoint")

    # Key results (denormalised for fast queries)
    annual_value_mid   = Column(Float)
    annual_value_min   = Column(Float)
    annual_value_max   = Column(Float)
    npv                = Column(Float)
    carbon_annual_tonnes = Column(Float)
    carbon_annual_value  = Column(Float)
    climate_score      = Column(Integer)
    biodiversity_index = Column(Integer)

    # Full JSON result blob
    full_result      = Column(JSON)

    # Relationships
    scenarios        = relationship("ScenarioRecord",  back_populates="valuation", cascade="all, delete-orphan")
    reports          = relationship("ReportRecord",    back_populates="valuation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Valuation {self.id[:8]} | {self.ecosystem_name} | {self.area_hectares}ha>"


class ScenarioRecord(Base):
    """Stores /scenarios/compare results linked to a valuation."""
    __tablename__ = "scenario_comparisons"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    valuation_id     = Column(String, ForeignKey("valuations.id"), nullable=False, index=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    # Scenario inputs
    scenarios_requested = Column(JSON)   # list of scenario keys
    projection_years    = Column(Integer, default=10)
    discount_rate       = Column(Float, default=0.08)

    # Key aggregates
    baseline_eco_npv   = Column(Float)
    recommended        = Column(String)

    # Full results blob
    full_result        = Column(JSON)

    valuation          = relationship("ValuationRecord", back_populates="scenarios")

    def __repr__(self):
        return f"<Scenario {self.id[:8]} | recommended={self.recommended}>"


class ReportRecord(Base):
    """Tracks every generated PDF report."""
    __tablename__ = "reports"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    valuation_id     = Column(String, ForeignKey("valuations.id"), nullable=True, index=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    filename         = Column(String)
    size_bytes       = Column(Integer)
    location_name    = Column(String, nullable=True)
    prepared_for     = Column(String, nullable=True)
    has_narrative    = Column(Boolean, default=False)
    has_scenarios    = Column(Boolean, default=False)

    valuation        = relationship("ValuationRecord", back_populates="reports")

    def __repr__(self):
        return f"<Report {self.id[:8]} | {self.filename}>"
