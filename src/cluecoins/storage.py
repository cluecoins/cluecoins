from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

import xdg
from aiosqlite import Connection
from aiosqlite import connect

DEFAULT_DB_PATH = xdg.XDG_DATA_HOME / 'cluecoins' / 'db.sqlite3'
DEFAULT_CACHE_PATH = xdg.XDG_CACHE_HOME / 'cluecoins' / 'cache.sqlite3'


class LocalStorage:
    def __init__(
        self,
        db_path: Path | None = None,
        cache_path: Path | None = None,
    ) -> None:
        self._db_path = db_path or DEFAULT_DB_PATH
        self._cache_path = cache_path or DEFAULT_CACHE_PATH
        self._db_conn: Connection | None = None
        self._cache_conn: Connection | None = None

    @property
    def db_conn(self) -> Connection:
        if self._db_conn is None:
            raise Exception
        return self._db_conn

    @property
    def cache_conn(self) -> Connection:
        if self._cache_conn is None:
            raise Exception
        return self._cache_conn

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[None, None]:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path.touch(exist_ok=True)

        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.touch(exist_ok=True)

        self._db_conn = connect(self._db_path)
        self._cache_conn = connect(self._cache_path)

        async with self._db_conn, self._cache_conn:
            yield

        self._db_conn = None
        self._cache_conn = None

    async def create_schema(self) -> None:
        await self.cache_conn.execute(
            'CREATE TABLE IF NOT EXISTS quotes (date date, base_currency text, quote_currency text, rate text, PRIMARY KEY (date, base_currency, quote_currency))'
        )

    async def commit(self) -> None:
        await self.db_conn.commit()
        await self.cache_conn.commit()

    async def get_quote(self, date: date, base_currency: str, quote_currency: str) -> Decimal | None:
        res = await (
            await self.cache_conn.execute(
                'SELECT rate FROM quotes WHERE date = ? AND base_currency = ? AND quote_currency = ?',
                (date, base_currency, quote_currency),
            )
        ).fetchone()
        if res:
            return Decimal(str(res[0]))
        return None

    async def add_quote(self, date: date, base_currency: str, quote_currency: str, rate: Decimal) -> None:
        await self.cache_conn.execute(
            'INSERT INTO quotes (date, base_currency, quote_currency, rate) VALUES (?, ?, ?, ?)',
            (date, base_currency, quote_currency, str(rate)),
        )


class BluecoinsStorage:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    # async def create_account(self, account_name: str, account_currency: str) -> bool:
    #     if (await db.find_account(self.conn, account_name)) is None:
    #         await db.create_new_account(self.conn, account_name, account_currency)
    #         return True
    #     return False

    # async def get_account_id(self, account_name: str, revert: bool = False) -> int | None:
    #     account_info = await db.find_account(self.conn, account_name, revert)
    #     if account_info is not None:
    #         return int(account_info[0])
    #     return None

    # async def add_label(self, account_id: int, label_name: str) -> Any:
    #     # find all transation with ID account and add labels with id transactions to LABELSTABEL
    #     async for transaction_id_tuple in db.find_account_transactions_id(self.conn, account_id):
    #         transaction_id = transaction_id_tuple[0]
    #         await db.add_label_to_transaction(self.conn, label_name, transaction_id)

    # async def encode_account_info(self, account_name: str) -> str | None:
    #     """All this is true if the ACCOUNTSTABLE table has a schema:

    #     CREATE TABLE ACCOUNTSTABLE(
    #                     accountsTableID INTEGER PRIMARY KEY,
    #                     accountName VARCHAR(63),
    #                     accountTypeID INTEGER,
    #                     accountHidden INTEGER,
    #                     accountCurrency VARCHAR(5),
    #                     accountConversionRateNew REAL,
    #                     currencyChanged INTEGER,
    #                     creditLimit INTEGER,
    #                     cutOffDa INTEGER,
    #                     creditCardDueDate INTEGER,
    #                     cashBasedAccounts INTEGER,
    #                     accountSelectorVisibility INTEGER,
    #                     accountsExtraColumnInt1 INTEGER,
    #                     accountsExtraColumnInt2 INTEGER,
    #                     accountsExtraColumnString1 VARCHAR(255),
    #                     accountsExtraColumnString2 VARCHAR(255)
    #                 );
    #     CREATE INDEX 'accountsTable1' ON ACCOUNTSTABLE(accountTypeID);
    #     """

    #     account_info = await db.find_account(self.conn, account_name)

    #     if account_info is None:
    #         return None

    #     delimiter = ','
    #     info: str = delimiter.join([str(value) for value in account_info])

    #     info_bytes = info.encode('utf-8')

    #     base64_bytes = base64.b64encode(info_bytes)
    #     return base64_bytes.decode('utf-8')

    # async def decode_account_info(self, account_name: str) -> tuple[Any, ...]:
    #     label_name = f'clue_{account_name}'
    #     transaction_id = await db.find_transactions_by_label(self.conn, label_name)[0][0]

    #     labels_list = await db.find_labels_by_transaction_id(self.conn, transaction_id)

    #     for label in labels_list:
    #         if not label[0].startswith(ENCODED_LABEL_PREFIX):
    #             continue

    #         label_parts = label[0].split('_')
    #         account_info_base64 = label_parts[-1]

    #         base64_bytes = account_info_base64.encode('utf-8')

    #         sample_string_bytes = base64.b64decode(base64_bytes)
    #         sample_string: str = sample_string_bytes.decode('utf-8')

    #         account_info_tuple = tuple(sample_string.split(','))

    #     account_info_list: list[str | None] = list(account_info_tuple)

    #     for i, info in enumerate(account_info_list):
    #         if info == 'None':
    #             account_info_list[i] = None

    #     account_info_list.pop(0)
    #     return tuple(account_info_list)

    # async def create_clue_tables(self, necessary_tables: list[str]) -> None:
    #     """Create CLUE tables if not exists"""

    #     # TODO: get table from currently Bluecoins DB
    #     path = Path(__file__).parent / 'bluecoins.sql'
    #     schema = path.read_text()
    #     queries = schema.split(';')

    #     for query in queries:
    #         regex = 'CREATE TABLE (\w*)'

    #         re_query = re.search(regex, query)
    #         if re_query is None:
    #             continue

    #         table_blue = re_query.group(1)
    #         if table_blue not in necessary_tables:
    #             continue
    #         part_of_blue_query = re_query.group(0)

    #         create_table_query = query.replace(part_of_blue_query, f'CREATE TABLE IF NOT EXISTS CLUE_{table_blue}')
    #         await db.execute_command(self.conn, create_table_query)

    # async def move_data_to_table_by_id(self, table: str, filter: str, filter_id: int, revert: bool = False) -> None:
    #     await db.copy_data_to_table_by_id(self.conn, table, filter, filter_id, revert)
    #     await db.delete_data_by_id(self.conn, table, filter, filter_id, revert)
