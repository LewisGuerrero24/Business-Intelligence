from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from etl_service.core.config import get_settings


def build_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.sqlalchemy_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_database_connection(session: Session) -> dict[str, str]:
    row = session.execute(
        text(
            """
            SELECT
                current_database() AS database_name,
                current_user AS user_name,
                inet_server_addr()::text AS server_address,
                inet_server_port()::text AS server_port
            """
        )
    ).mappings().one()
    return dict(row)

