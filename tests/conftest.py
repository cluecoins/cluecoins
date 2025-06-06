# import sqlite3
# from collections.abc import Iterable
# from pathlib import Path
# from sqlite3 import Connection

# import pytest

# from cluecoins.storage import Storage


# @pytest.fixture
# def initialization_storage(tmp_path: Path) -> Iterable[Storage]:
#     """Fixture to set up the temporary local database"""

#     db_path = tmp_path / 'cluecoins' / 'cluecoins.db'
#     storage = LocalStorage(db_path)
#     storage.create_schema()

#     yield storage


# @pytest.fixture
# def conn() -> Iterable[Connection]:
#     """Fixture to set up the in-memory Bluecoins database with test data"""

#     conn = sqlite3.connect(':memory:')

#     path = Path(__file__).parent / 'test_data.sql'
#     sql = path.read_text()
#     conn.executescript(sql)

#     yield conn


# @pytest.fixture
# def create_clue_tables(conn: Connection) -> None:
#     blue_tables = ['ACCOUNTSTABLE', 'TRANSACTIONSTABLE', 'LABELSTABLE']

#     for table in blue_tables:
#         query: str = (
#             conn.cursor()
#             .execute(
#                 'SELECT sql FROM sqlite_master WHERE name= ?',
#                 (table,),
#             )
#             .fetchone()[0]
#         )
#         clue_query = query.replace(table, f'CLUE_{table}')
#         conn.executescript(clue_query)
