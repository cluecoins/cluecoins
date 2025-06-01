import logging
from collections.abc import Callable
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import xdg

# from cluecoins.database import ENCODED_LABEL_PREFIX
from cluecoins.database import connect_local_db

# from cluecoins.database import create_archived_account
# from cluecoins.database import delete_label
# from cluecoins.database import find_labels_by_transaction_id
# from cluecoins.database import find_transactions_by_label
# from cluecoins.database import get_base_currency
# from cluecoins.database import get_transactions_list
from cluecoins.database import iter_accounts
from cluecoins.database import iter_transactions

# from cluecoins.database import move_transactions_to_account_with_id
from cluecoins.database import set_base_currency
from cluecoins.database import update_account
from cluecoins.database import update_transaction
from cluecoins.quotes import CurrencyBeaconQuoteProvider

# from cluecoins.storage import BluecoinsStorage
from cluecoins.storage import Storage

logging.basicConfig(level=logging.DEBUG)


def q(v: Decimal, prec: int = 2) -> Decimal:
    return v.quantize(Decimal(f'0.{prec * "0"}'))


# def cli(path: str) -> None:
#     """Manual path database selection."""

#     backup_path = Path(path).parent / (Path(path).name + '.bak')
#     backup_path.write_bytes(Path(path).read_bytes())


async def convert(base_currency: str, db_path: str, log: Callable) -> None:
    conn = connect_local_db(db_path)

    storage = Storage(Path(xdg.xdg_data_home()) / 'cluecoins' / 'cluecoins.db')

    async with conn, storage.db:
        cache = CurrencyBeaconQuoteProvider(storage)
        await storage.create_quote_table()

        await set_base_currency(conn, base_currency)

        async for date, id_, rate, currency, amount in iter_transactions(conn):
            true_rate = await cache.get_rate(date, base_currency, currency)

            if true_rate == rate:
                continue

            amount_original = amount * rate
            amount_quote = amount_original / true_rate

            await update_transaction(conn, id_, true_rate, amount_quote)
            log(
                f'==> transaction {id_}: {q(amount_original)} {currency} -> {q(amount_quote)} {base_currency} ({q(true_rate)} {base_currency}{currency})'
            )

        today = datetime.now() - timedelta(days=1)
        async for id_, currency, rate in iter_accounts(conn):
            true_rate = await cache.get_rate(today, base_currency, currency)

            if true_rate == rate:
                continue

            await update_account(conn, id_, true_rate)
            log(f'==> account {id_}: {q(rate)} {currency} -> {q(true_rate)} {base_currency}{currency}')

        await storage.commit()
        await conn.commit()


# async def archive(
#     account_name: str,
#     db_path: str,
# ) -> None:
#     """Archive account:
#     1. Create CLUE tables, if doesn't exist: 'CLUE_ACCOUNTSTABLE', 'CLUE_TRANSACTIONSTABLE', 'CLUE_LABELSTABLE'
#     2. Move the account, transactions, and labels to CLUE tables.
#     """

#     conn = connect_local_db(db_path)

#     bluecoins_storage = BluecoinsStorage(conn)

#     async with conn:
#         account_id = await bluecoins_storage.get_account_id(account_name)
#         if account_id is None:
#             raise Exception(f'Account {account_name} does not exist')

#         necessary_tables = ['ACCOUNTSTABLE', 'TRANSACTIONSTABLE', 'LABELSTABLE']
#         await bluecoins_storage.create_clue_tables(necessary_tables)

#         transactions_list = await get_transactions_list(conn, account_id)
#         for transaction_id in transactions_list:
#             await bluecoins_storage.move_data_to_table_by_id('LABELSTABLE', 'transactionIDLabels', transaction_id[0])

#         await bluecoins_storage.move_data_to_table_by_id('TRANSACTIONSTABLE', 'accountID', account_id)

#         # NOTE: what to do if account already exist in CLUE_ACCOUNTSTABLE?
#         # If account exist - add _2 in the end name of account
#         await bluecoins_storage.move_data_to_table_by_id('ACCOUNTSTABLE', 'accountsTableID', account_id)


# async def unarchive(
#     account_name: str,
#     db_path: str,
# ) -> None:
#     conn = connect_local_db(db_path)

#     bluecoins_storage = BluecoinsStorage(conn)

#     async with conn:
#         # create account
#         account_info = await bluecoins_storage.decode_account_info(account_name)
#         await create_archived_account(conn, account_info)

#         label_name = 'clue_' + account_name
#         id_transactions = await find_transactions_by_label(conn, label_name)

#         # get account IDs
#         acc_new_id = bluecoins_storage.get_account_id(account_name)
#         if acc_new_id is None:
#             raise Exception(f'Account {account_name} does not exist')

#         # move transactions
#         for id in id_transactions:
#             await move_transactions_to_account_with_id(conn, id[0], acc_new_id)

#             await delete_label(conn, label_name)

#             labels_list = await find_labels_by_transaction_id(conn, id[0])
#             for label in labels_list:
#                 if label[0].startswith(ENCODED_LABEL_PREFIX):
#                     await delete_label(conn, label[0])


# async def create_account(
#     account_name: str,
#     db_path: str,
# ) -> None:
#     conn = connect_local_db(db_path)

#     bluecoins_storage = BluecoinsStorage(conn)

#     async with conn:
#         account_currency = await get_base_currency(conn)
#         await bluecoins_storage.create_account(account_name, account_currency)


# async def add_label(
#     account_name: str,
#     label_name: str,
#     db_path: str,
# ) -> None:
#     conn = connect_local_db(db_path)

#     bluecoins_storage = BluecoinsStorage(conn)

#     async with conn:
#         account_id = await bluecoins_storage.get_account_id(account_name)
#         if account_id is None:
#             return print('account is not exist')
#         await bluecoins_storage.add_label(account_id, label_name)
#         return None


# async def _unarchive_v2(
#     account: str,
#     db_path: str,
# ) -> None:
#     """Move all data: account, transactions, labels; from Cluecoins tables to Bluecoins Tables"""

#     conn = connect_local_db(db_path)

#     bluecoins_storage = BluecoinsStorage(conn)

#     async with conn:
#         account_id = await bluecoins_storage.get_account_id(account, True)
#         if account_id is None:
#             raise Exception(f'Account {account} does not exist')

#         transactions_list = await get_transactions_list(conn, account_id)
#         for transaction_id in transactions_list:
#             await bluecoins_storage.move_data_to_table_by_id(
#                 'LABELSSTABLE', 'transactionIDLabels', transaction_id[0], True
#             )

#         await bluecoins_storage.move_data_to_table_by_id('TRANSACTIONSTABLE', 'accountID', account_id, True)

#         # NOTE: what to do if account already exist in CLUE_ACCOUNTSTABLE?
#         # If account exist - add _2 in the end name of account
#         await bluecoins_storage.move_data_to_table_by_id('ACCOUNTSTABLE', 'accountsTableID', account_id, True)
