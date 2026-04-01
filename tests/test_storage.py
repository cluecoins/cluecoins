from datetime import date
from decimal import Decimal

from cluecoins.storage import LocalStorage


async def test_schema_creates_quotes_table(local_storage: LocalStorage) -> None:
    # If the table doesn't exist this will raise OperationalError
    await local_storage.cache_conn.execute('SELECT * FROM quotes')


async def test_add_and_get_quote(local_storage: LocalStorage) -> None:
    d = date(2024, 6, 1)
    await local_storage.add_quote(d, 'USD', 'EUR', Decimal('0.92'))
    await local_storage.commit()

    result = await local_storage.get_quote(d, 'USD', 'EUR')
    assert result == Decimal('0.92')


async def test_get_quote_missing(local_storage: LocalStorage) -> None:
    result = await local_storage.get_quote(date(2024, 1, 1), 'USD', 'EUR')
    assert result is None


async def test_get_quote_different_date(local_storage: LocalStorage) -> None:
    d = date(2024, 6, 1)
    await local_storage.add_quote(d, 'USD', 'EUR', Decimal('0.92'))
    await local_storage.commit()

    result = await local_storage.get_quote(date(2024, 6, 2), 'USD', 'EUR')
    assert result is None
