from etl_service.core.logging import configure_logging
from etl_service.db.connection import SessionLocal, check_database_connection


def main() -> None:
    configure_logging()
    with SessionLocal() as session:
        print(check_database_connection(session))


if __name__ == "__main__":
    main()

