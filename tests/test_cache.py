from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from cluecoins.quotes import CurrencyBeaconQuoteProvider
from cluecoins.storage import LocalStorage


@pytest.fixture
async def provider(local_storage: LocalStorage) -> CurrencyBeaconQuoteProvider:
    return CurrencyBeaconQuoteProvider(local_storage, log=lambda _: None)


def _make_timeseries_response(date_: date, quote: str, rate: float) -> dict:
    return {'response': {date_.strftime('%Y-%m-%d'): {quote: rate}}}


def _mock_session(response_data: dict) -> MagicMock:
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value=response_data)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


async def test_get_rate_same_currency(provider: CurrencyBeaconQuoteProvider) -> None:
    rate = await provider.get_rate(date(2024, 1, 15), 'USD', 'USD')
    assert rate == Decimal('1')


async def test_get_rate_cached(local_storage: LocalStorage, provider: CurrencyBeaconQuoteProvider) -> None:
    d = date(2024, 1, 15)
    await local_storage.add_quote(d, 'USD', 'EUR', Decimal('0.92'))
    await local_storage.commit()

    rate = await provider.get_rate(d, 'USD', 'EUR')
    assert rate == Decimal('0.92')


async def test_get_rate_fetches_when_missing(provider: CurrencyBeaconQuoteProvider) -> None:
    d = date(2024, 1, 15)
    with patch(
        'cluecoins.quotes.aiohttp.ClientSession', return_value=_mock_session(_make_timeseries_response(d, 'EUR', 0.92))
    ):
        rate = await provider.get_rate(d, 'USD', 'EUR')

    assert rate == Decimal('0.92')


async def test_get_rate_unknown_currency_returns_none(provider: CurrencyBeaconQuoteProvider) -> None:
    d = date(2024, 1, 15)
    response_data: dict = {'response': {d.strftime('%Y-%m-%d'): {}}}
    with patch('cluecoins.quotes.aiohttp.ClientSession', return_value=_mock_session(response_data)):
        rate = await provider.get_rate(d, 'USD', 'ZZZ')

    assert rate is None


async def test_fetch_quotes_skips_none_rates(
    local_storage: LocalStorage, provider: CurrencyBeaconQuoteProvider
) -> None:
    d = date(2024, 1, 15)
    response_data = {'response': {d.strftime('%Y-%m-%d'): {'EUR': None, 'GBP': 0.79}}}
    provider._quote_currencies = {'EUR', 'GBP'}
    with patch('cluecoins.quotes.aiohttp.ClientSession', return_value=_mock_session(response_data)):
        await provider._fetch_quotes(d, 'USD')

    assert await local_storage.get_quote(d, 'USD', 'EUR') is None
    assert await local_storage.get_quote(d, 'USD', 'GBP') == Decimal('0.79')


async def test_fetch_quotes_duplicate_ignored(
    local_storage: LocalStorage, provider: CurrencyBeaconQuoteProvider
) -> None:
    d = date(2024, 1, 15)
    await local_storage.add_quote(d, 'USD', 'EUR', Decimal('0.90'))
    await local_storage.commit()

    provider._quote_currencies = {'EUR'}
    with patch(
        'cluecoins.quotes.aiohttp.ClientSession', return_value=_mock_session(_make_timeseries_response(d, 'EUR', 0.92))
    ):
        await provider._fetch_quotes(d, 'USD')

    # Original value preserved (IntegrityError on duplicate silently ignored)
    assert await local_storage.get_quote(d, 'USD', 'EUR') == Decimal('0.90')
