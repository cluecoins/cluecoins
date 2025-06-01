from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from os import environ as env

import aiohttp

from cluecoins.storage import Storage

CB_API_URL = 'https://api.currencybeacon.com'
CB_API_KEY = env.get('CB_API_KEY', 'BF178aNPAdfPW6YjqbYGL5CmztO4qLNY')


class CurrencyBeaconQuoteProvider:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage
        self._quote_currencies: set[str] = set()
        self._request_count = 0

    async def _fetch_quotes(
        self,
        date: datetime,
        base_currency: str,
    ) -> None:
        """Getting quotes from the Exchangerate API and writing them to the local database"""
        from cluecoins.ui import LOG

        _key = CB_API_KEY

        start_date = date - timedelta(days=180)
        params = {
            'api_key': _key,
            # FIXME: Overkill
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': date.strftime('%Y-%m-%d'),
            'base': base_currency,
            'symbols': ','.join(self._quote_currencies),
        }
        async with aiohttp.ClientSession() as session:
            LOG.write(f'Fetching quotes for {base_currency} {date}...')
            LOG.write(f'Request count: {self._request_count}')
            self._request_count += 1

            async with session.get(
                url=f'{CB_API_URL}/v1/timeseries',
                params=params,
            ) as response:
                response_json = await response.json()
                LOG.write(response_json)

        for quote_date, items in response_json['response'].items():
            for quote_currency, price in items.items():
                await self._storage.add_quote(
                    datetime.strptime(quote_date, '%Y-%m-%d'),
                    base_currency,
                    quote_currency,
                    Decimal(str(price)),
                )

    # FIXME: Cache me
    async def get_rate(
        self,
        date: datetime,
        base_currency: str,
        quote_currency: str,
    ) -> Decimal:
        if base_currency == quote_currency:
            return Decimal('1')

        price = await self._storage.get_quote(date, base_currency, quote_currency)
        if not price:
            self._quote_currencies.add(quote_currency)
            await self._fetch_quotes(date, base_currency)
            price = await self._storage.get_quote(date, base_currency, quote_currency)

        if not price:
            raise Exception(f'No quote for {date} {base_currency} {quote_currency}')

        return price
