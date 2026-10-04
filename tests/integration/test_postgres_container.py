import psycopg2
from testcontainers.postgres import PostgresContainer


def test_ci_starts_a_real_postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        connection_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql://", 1
        )
        connection = psycopg2.connect(connection_url)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                assert cursor.fetchone() == (1,)
        finally:
            connection.close()
