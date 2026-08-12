"""Database engine initialization."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = None
SessionLocal = None


def init_db(app):
    global engine, SessionLocal
    engine = create_engine(
        app.config['DATABASE_URL'],
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db_session():
    """获取数据库会话，使用 with 语句自动关闭。"""
    return SessionLocal()
