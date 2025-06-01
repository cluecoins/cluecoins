from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
from aiosqlite import Connection
from aiosqlite import OperationalError

from cluecoins.storage import BluecoinsStorage
from cluecoins.storage import Storage


async def test_create_database(initialization_storage: Storage) -> None:
    try:
        conn = initialization_storage.db

        conn.execute(
            'SELECT * FROM quotes;',
        )
    except OperationalError:
        raise pytest.fail('Table does not exist') from None


async def test_add_quote(initialization_storage: Storage) -> None:
    quote_test_data: dict[str, Any] = {
        'date': datetime(2022, 7, 15),
        'base_currency': 'USDT',
        'quote_currency': 'USD',
        'price': Decimal('1230.23'),
    }

    conn = initialization_storage.db

    initialization_storage.add_quote(**quote_test_data)

    quote_data = await conn.execute(
        'SELECT * FROM quotes',
    )
    expected_quote_data = await quote_data.fetchall()

    assert expected_quote_data == [('2022-07-15 00:00:00', 'USDT', 'USD', 1230.23)]


async def test_get_quote(initialization_storage: Storage) -> None:
    quote_test_data: dict[str, Any] = {
        'date': datetime(2022, 7, 15),
        'base_currency': 'USDT',
        'quote_currency': 'USD',
        'price': Decimal('1230.23'),
    }

    await initialization_storage.add_quote(**quote_test_data)

    expected_quote_price = await initialization_storage.get_quote(
        date=quote_test_data['date'],
        base_currency=quote_test_data['base_currency'],
        quote_currency=quote_test_data['quote_currency'],
    )

    assert expected_quote_price == Decimal('1230.23')


async def test_create_account(conn: Connection) -> None:
    storage = BluecoinsStorage(conn)
    storage.create_account('Archive', 'USD')

    account_data = await conn.execute(
        'SELECT accountName, accountCurrency FROM ACCOUNTSTABLE WHERE accountName = ?',
        ('Archive',),
    )
    expected_account_data = account_data.fetchone()

    assert expected_account_data == ('Archive', 'USD')


async def test_get_account_id(conn: Connection) -> None:
    storage = BluecoinsStorage(conn)
    expected_id = storage.get_account_id('Checking')

    assert expected_id == 1


async def test_add_label(conn: Connection) -> None:
    storage = BluecoinsStorage(conn)
    storage.add_label(3, 'clue_test')

    transactions_list = conn.execute('SELECT * FROM LABELSTABLE WHERE labelName = ?', ('clue_test',))
    expected_transactions_list = len(transactions_list.fetchall())

    assert expected_transactions_list == 526
