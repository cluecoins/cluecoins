import sqlite3
from collections.abc import AsyncGenerator
from pathlib import Path

import aiosqlite
import pytest

from cluecoins.storage import LocalStorage


@pytest.fixture
def fydb_file(tmp_path: Path) -> Path:
    path = tmp_path / 'test.fydb'
    sqlite3.connect(path).close()
    return path


@pytest.fixture
def fydb_with_tables(tmp_path: Path) -> Path:
    path = tmp_path / 'test_tables.fydb'
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE TESTTABLE (id INTEGER PRIMARY KEY, name TEXT)')
    conn.execute("INSERT INTO TESTTABLE VALUES (1, 'foo')")
    conn.commit()
    conn.close()
    return path


@pytest.fixture
async def local_storage(tmp_path: Path) -> AsyncGenerator[LocalStorage, None]:
    db_path = tmp_path / 'db.sqlite3'
    cache_path = tmp_path / 'cache.sqlite3'
    storage = LocalStorage(db_path=db_path, cache_path=cache_path)
    async with storage.connect():
        await storage.create_schema()
        yield storage


@pytest.fixture
async def bluecoins_conn(tmp_path: Path) -> AsyncGenerator[aiosqlite.Connection, None]:
    path = tmp_path / 'test.fydb'
    async with aiosqlite.connect(path) as conn:
        await conn.executescript(
            """
            CREATE TABLE SETTINGSTABLE(settingsTableID INTEGER PRIMARY KEY, defaultSettings TEXT);
            INSERT INTO SETTINGSTABLE VALUES(1, 'USD');

            CREATE TABLE TRANSACTIONSTABLE(
                transactionsTableID INTEGER PRIMARY KEY,
                date TEXT,
                conversionRateNew REAL,
                transactionCurrency TEXT,
                amount INTEGER,
                transactionTypeID INTEGER,
                accountID INTEGER
            );
            INSERT INTO TRANSACTIONSTABLE VALUES(1, '2024-01-15T10:00:00', 1.5, 'EUR', 2500000, 3, 1);

            CREATE TABLE ACCOUNTSTABLE(
                accountsTableID INTEGER PRIMARY KEY,
                accountName TEXT,
                accountCurrency TEXT,
                accountConversionRateNew REAL
            );
            INSERT INTO ACCOUNTSTABLE VALUES(1, 'Checking', 'USD', 1.0);
            INSERT INTO ACCOUNTSTABLE VALUES(2, 'Crypto', 'USDT', 0.99);
            """
        )
        yield conn


# from collections.abc import Iterable
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
