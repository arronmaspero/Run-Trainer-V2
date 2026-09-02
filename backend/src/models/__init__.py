from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config import settings

# For SQLite, we require connect_args={"check_same_thread": False}
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Import all models to register them on the Base metadata
from src.models.user import User, AthleteProfile
from src.models.activity import ConnectedAccount, Activity
from src.models.plan import TrainingPlan, TrainingSession, WeeklyEvaluation
from src.models.changelog import PlanChangeLog
from src.models.chat_message import ChatMessage

# Create all tables in the database
Base.metadata.create_all(bind=engine)

# ── Incremental column migrations (safe to run on every startup) ──────────────
def _run_column_migrations():
    """Add any columns that may be missing from existing databases."""
    with engine.connect() as conn:
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        # activities.name — added in v2 to store Strava activity names
        cols = [c["name"] for c in inspector.get_columns("activities")]
        if "name" not in cols:
            conn.execute(text("ALTER TABLE activities ADD COLUMN name VARCHAR(255)"))
            conn.commit()
        # connected_accounts.garth_tokens — added to cache Garmin session tokens
        ca_cols = [c["name"] for c in inspector.get_columns("connected_accounts")]
        if "garth_tokens" not in ca_cols:
            conn.execute(text("ALTER TABLE connected_accounts ADD COLUMN garth_tokens TEXT"))
            conn.commit()

_run_column_migrations()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
