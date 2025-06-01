# from datetime import datetime
# from decimal import Decimal
# from typing import Any

# from cluecoins.quotes import CurrencyBeaconQuoteProvider
# from cluecoins.storage import Storage


# async def test_fetch_quotes(initialization_storage: Storage) -> None:
#     currency_info: dict[str, Any] = {
#         'date': datetime(2022, 7, 15),
#         'base_currency': 'USD',
#         'quote_currency': 'UYU',
#     }

#     cache = CurrencyBeaconQuoteProvider(initialization_storage)
#     conn = initialization_storage.db
#     await cache._fetch_quotes(**currency_info)

#     quote_data = await conn.execute(
#         'SELECT * FROM quotes',
#     )

#     expected_quote_data = len(await quote_data.fetchall())

#     assert expected_quote_data == 365


# async def test_get_rate(initialization_storage: Storage) -> None:
#     currency_info: dict[str, Any] = {
#         'date': datetime(2022, 7, 15),
#         'base_currency': 'USD',
#         'quote_currency': 'UYU',
#     }

#     cache = CurrencyBeaconQuoteProvider(initialization_storage)
#     conn = initialization_storage.db

#     expected_quote_price = cache.get_rate(**currency_info)

#     price = await conn.execute(
#         'SELECT * FROM quotes WHERE date = "2022-07-15 00:00:00"',
#     )

#     quote_price = (await price.fetchall())[0][3]

#     assert expected_quote_price == Decimal(f'{quote_price}')
