"""
database.py — SQLite/PostgreSQL baglanti yonetimi
Varsayilan SQLite, opsiyonel PostgreSQL (env var ile).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from risk.models import Base

# Singleton engine with connection pooling (K97)
_ENGINE = None


def get_engine():
    """DATABASE_URL env var'i varsa PostgreSQL, yoksa SQLite kullanir.
    Engine singleton olarak cache'lenir — her cagri yeni engine olusturmaz."""
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        _ENGINE = create_engine(db_url, echo=False, pool_pre_ping=True, pool_size=5, max_overflow=10)
    else:
        db_path = os.getenv("SQLITE_PATH", "anatoliax.db")
        from sqlalchemy.pool import StaticPool
        _ENGINE = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return _ENGINE


def init_db(engine=None):
    """Tum tablolari olusturur."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None):
    """Yeni bir session olusturur. Varsayilan olarak singleton engine'i kullanir."""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def reset_engine():
    """Test veya yeniden baslatma icin engine cache'ini temizler."""
    global _ENGINE
    _ENGINE = None
