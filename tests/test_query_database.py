from datetime import datetime
from decimal import Decimal
from pathlib import Path

import aiosqlite
import pytest

from cluecoins.database import connect_local_db
from cluecoins.database import iter_accounts
from cluecoins.database import iter_transactions
from cluecoins.database import set_base_currency
from cluecoins.database import update_account
from cluecoins.database import update_transaction


def test_connect_local_db_valid(fydb_file: Path) -> None:
    conn = connect_local_db(str(fydb_file))
    assert conn is not None


def test_connect_local_db_invalid_extension(tmp_path: Path) -> None:
    path = tmp_path / 'test.db'
    path.touch()
    with pytest.raises(Exception):
        connect_local_db(str(path))


async def test_set_base_currency(bluecoins_conn: aiosqlite.Connection) -> None:
    await set_base_currency(bluecoins_conn, 'EUR')
    row = await (
        await bluecoins_conn.execute('SELECT defaultSettings FROM SETTINGSTABLE WHERE settingsTableID = 1')
    ).fetchone()
    assert row is not None
    assert row[0] == 'EUR'


async def test_iter_transactions_yields_correct_types(bluecoins_conn: aiosqlite.Connection) -> None:
    rows = [row async for row in iter_transactions(bluecoins_conn)]
    assert len(rows) == 1
    date_, id_, rate, currency, amount = rows[0]
    assert isinstance(date_, datetime)
    assert isinstance(id_, int)
    assert isinstance(rate, Decimal)
    assert isinstance(currency, str)
    assert isinstance(amount, Decimal)


async def test_iter_transactions_amount_scaling(bluecoins_conn: aiosqlite.Connection) -> None:
    rows = [row async for row in iter_transactions(bluecoins_conn)]
    _, _, _, _, amount = rows[0]
    # raw 2500000 / 1_000_000 = 2.5
    assert amount == Decimal('2.5')


async def test_update_transaction(bluecoins_conn: aiosqlite.Connection) -> None:
    new_rate = Decimal('1.23')
    new_amount = Decimal('5.0')
    await update_transaction(bluecoins_conn, 1, new_rate, new_amount)

    row = await (
        await bluecoins_conn.execute(
            'SELECT conversionRateNew, amount FROM TRANSACTIONSTABLE WHERE transactionsTableID = 1'
        )
    ).fetchone()
    assert row is not None
    assert Decimal(str(row[0])) == new_rate
    assert row[1] == int(new_amount * 1_000_000)


async def test_iter_accounts_currency_replacement(bluecoins_conn: aiosqlite.Connection) -> None:
    rows = [row async for row in iter_accounts(bluecoins_conn, old_currency='USDT', new_currency='USD')]
    currencies = {row[1] for row in rows}
    assert 'USDT' not in currencies
    assert 'USD' in currencies


async def test_update_account(bluecoins_conn: aiosqlite.Connection) -> None:
    new_rate = Decimal('1.05')
    await update_account(bluecoins_conn, 1, new_rate)

    row = await (
        await bluecoins_conn.execute(
            'SELECT accountConversionRateNew FROM ACCOUNTSTABLE WHERE accountsTableID = 1'
        )
    ).fetchone()
    assert row is not None
    assert Decimal(str(row[0])) == new_rate
