import logging
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

from aiosqlite import connect
from textual import on
from textual.app import App
from textual.app import ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Button
from textual.widgets import DataTable
from textual.widgets import DirectoryTree
from textual.widgets import RichLog
from textual.widgets import Static
from zandev_textual_widgets import MenuScreen
from zandev_textual_widgets.menu import Menu
from zandev_textual_widgets.menu import MenuItem

from cluecoins.database import count_accounts
from cluecoins.database import count_items
from cluecoins.database import count_transactions
from cluecoins.database import fetch_accounts_page
from cluecoins.database import fetch_items_page
from cluecoins.database import fetch_transactions_page
from cluecoins.database import rename_item
from cluecoins.storage import LocalStorage
from cluecoins.ui import menu

if TYPE_CHECKING:
    from aiosqlite import Connection


# TODO: cleanup
_file_logger = logging.getLogger('file_logger')
_file_logger.setLevel(logging.DEBUG)
_file_handler = logging.FileHandler('cluecoins.log')
_file_handler.setLevel(logging.DEBUG)
_file_formatter = logging.Formatter('%(asctime)s - %(message)s')
_file_handler.setFormatter(_file_formatter)
_file_logger.addHandler(_file_handler)

orig_write = RichLog.write


def write(*a, **kw) -> None:
    orig_write(*a, **kw)
    _file_logger.debug(a[1])


RichLog.write = write  # type: ignore[method-assign,assignment]

WELCOME_TEXT = """
Welcome to Cluecoins!

To get started, select "Open File" from the File menu to open a database file.
"""


class BaseScreen(Screen):
    """Base screen with always-visible menubar, log, and status bar."""

    app: 'CluecoinsApp'

    def compose(self) -> ComposeResult:
        yield menu.bar()
        with Container(classes='window'):
            yield from self.compose_content()
        yield RichLog(id='log')
        yield Static('not connected', id='status_bar')

    def compose_content(self) -> ComposeResult:
        yield from ()

    def on_mount(self) -> None:
        log = self.query_one('#log', RichLog)
        for msg in self.app._log_history:
            log.write(msg)
        self.query_one('#status_bar', Static).update(self.app._status_text)


class MainScreen(BaseScreen):
    def compose_content(self) -> ComposeResult:
        yield Static(WELCOME_TEXT, id='welcome_text')


class FetchQuotesScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self._log = RichLog()

    def compose_content(self) -> ComposeResult:
        yield Static('Fetch quotes for accounts and transactions from CurrencyBeacon API\n')
        yield self._log
        yield Container(
            Button('Back', id='back'),
            Button('OK', id='ok'),
            classes='button-group',
        )

    @on(Button.Pressed, '#ok')
    async def on_ok_pressed(self, event):
        from cluecoins.cli import convert

        self.query_one('#status_bar', Static).update('fetching quotes...')
        self.query_one('#ok').disabled = True
        self.query_one('#back').disabled = True
        self.app._is_busy = True
        self.app.refresh_menu_state()

        try:
            await convert('USD', str(self.app._db_path), self.app.log_write)
        finally:
            self.app._is_busy = False
            self.app.refresh_menu_state()

        self.app._status_text = 'quotes fetched'
        self.query_one('#status_bar', Static).update(self.app._status_text)
        self.query_one('#ok').disabled = False
        self.query_one('#back').disabled = False

    @on(Button.Pressed, '#back')
    async def on_back_pressed(self, event):
        self.app.switch_screen(MainScreen())


class QuotesScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self._data = DataTable()

    async def on_mount(self):
        super().on_mount()
        storage = LocalStorage()

        quotes = defaultdict(int)
        async with storage.connect():
            await storage.create_schema()

            # TODO: sql
            async for date, base_currency, quote_currency in await storage.cache_conn.execute(
                'SELECT date, base_currency, quote_currency FROM quotes ORDER BY base_currency, quote_currency, date'
            ):
                quotes[f'{base_currency}{quote_currency} {date[:4]}'] += 1

        self._data.add_column('year')
        self._data.add_column('ticker')
        self._data.add_column('count')

        for group, count in quotes.items():
            year, ticker = group.split(' ')
            self._data.add_row(year, ticker, count)

    def compose_content(self) -> ComposeResult:
        yield Static('Quotes fetched from CurrencyBeacon API\n')
        yield self._data


class TableRowsScreen(BaseScreen):
    """Screen that displays rows of a selected table."""

    def __init__(self, db_path: Path, table_name: str):
        super().__init__()
        self._db_path = db_path
        self._table_name = table_name
        self._data: DataTable = DataTable()

    async def _get_columns(self, conn) -> list[str]:
        cur = await conn.execute(f"PRAGMA table_info('{self._table_name}')")
        rows = await cur.fetchall()
        return [row[1] for row in rows]

    async def _get_primary_key(self, conn) -> str | None:
        cur = await conn.execute(f"PRAGMA table_info('{self._table_name}')")
        rows = await cur.fetchall()
        pk_cols = sorted(
            [(row[1], row[5]) for row in rows if row[5] > 0],
            key=lambda x: x[1],
        )
        if pk_cols:
            return ', '.join(f"'{col[0]}'" for col in pk_cols)
        return None

    async def on_mount(self):
        super().on_mount()
        async with connect(self._db_path) as conn:
            columns = await self._get_columns(conn)
            if not columns:
                self.app.log_write(f"no columns found for table '{self._table_name}'")
                return

            for col in columns:
                self._data.add_column(col, key=col)

            pk_clause = await self._get_primary_key(conn)
            order_by = f' ORDER BY {pk_clause}' if pk_clause else ''

            cur = await conn.execute(f"SELECT * FROM '{self._table_name}'{order_by}")
            rows = await cur.fetchall()

            for row in rows:
                self._data.add_row(*[str(v) if v is not None else '' for v in row])

    def compose_content(self) -> ComposeResult:
        yield Static(f'Rows of: {self._table_name}')
        yield self._data
        yield Container(
            Button('Back', id='table-rows-back'),
            id='table-rows-footer',
        )

    def _go_back(self) -> None:
        self.app.switch_screen(StatisticsScreen())

    @on(Button.Pressed, '#table-rows-back')
    async def on_back_pressed(self, event):
        self._go_back()

    def key_escape(self) -> None:
        self._go_back()


class StatisticsScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self._data = DataTable()

    async def on_mount(self):
        super().on_mount()
        db_path = self.app._db_path

        self._data.add_column('table')
        self._data.add_column('count')
        self._data.cursor_type = 'row'

        if not db_path:
            self.app.log_write('no database connected')
            return

        async with connect(db_path) as conn:
            cur = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            tables = await cur.fetchall()

            for (table_name,) in tables:
                try:
                    cnt_cur = await conn.execute(f"SELECT COUNT(*) FROM '{table_name}'")
                    cnt_row = await cnt_cur.fetchone()
                    count = cnt_row[0] if cnt_row is not None else 0
                except Exception:
                    count = 'err'

                self._data.add_row(table_name, count, key=table_name)

    def compose_content(self) -> ComposeResult:
        yield Static('Database table row counts')
        yield self._data
        yield Container(
            Button('Back', id='statistics-back'),
            id='statistics-footer',
        )

    async def on_data_table_row_selected(self, event: DataTable.RowSelected):
        table_name = str(event.row_key.value)
        db_path = self.app._db_path
        if db_path:
            self.app.switch_screen(TableRowsScreen(db_path=db_path, table_name=table_name))

    def _go_back(self) -> None:
        self.app.switch_screen(MainScreen())

    @on(Button.Pressed, '#statistics-back')
    async def on_back_pressed(self, event):
        self._go_back()

    def key_escape(self) -> None:
        self._go_back()


class PaginatedTableScreen(BaseScreen):
    PAGE_SIZE = 1000
    _default_sort_col: str
    _default_sort_asc: bool

    def __init__(self) -> None:
        super().__init__()
        self._page = 0
        self._sort_col = self._default_sort_col
        self._sort_asc = self._default_sort_asc
        self._total_rows = 0
        self._columns_added = False
        self._data: DataTable = DataTable()

    async def _fetch_page(self, conn: 'Connection', offset: int, limit: int, sort_col: str, sort_asc: bool) -> tuple:
        raise NotImplementedError

    async def _count_rows(self, conn: 'Connection') -> int:
        raise NotImplementedError

    def _title(self) -> str:
        raise NotImplementedError

    def _back_screen(self) -> Screen:
        raise NotImplementedError

    async def on_mount(self) -> None:  # type: ignore[override]
        super().on_mount()
        await self._reload()

    async def _reload(self) -> None:
        db_path = self.app._db_path
        if not db_path:
            return
        offset = self._page * self.PAGE_SIZE
        async with connect(db_path) as conn:
            self._total_rows = await self._count_rows(conn)
            columns, rows = await self._fetch_page(conn, offset, self.PAGE_SIZE, self._sort_col, self._sort_asc)
        self._data.clear()
        if not self._columns_added:
            for col in columns:
                self._data.add_column(col, key=col)
            self._columns_added = True
        for row in rows:
            self._data.add_row(*[str(v) if v is not None else '' for v in row])
        self._update_page_info()

    def _update_page_info(self) -> None:
        total_pages = max(1, (self._total_rows + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        info = f'Page {self._page + 1} / {total_pages}  ({self._total_rows} rows)'
        self.query_one('#page-info', Static).update(info)
        self.query_one('#page-prev', Button).disabled = self._page == 0
        self.query_one('#page-next', Button).disabled = (self._page + 1) >= total_pages

    async def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        col_key = str(event.column_key.value)
        if col_key == self._sort_col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col_key
            self._sort_asc = True
        self._page = 0
        await self._reload()

    @on(Button.Pressed, '#page-prev')
    async def on_prev_pressed(self, event: Button.Pressed) -> None:
        self._page -= 1
        await self._reload()

    @on(Button.Pressed, '#page-next')
    async def on_next_pressed(self, event: Button.Pressed) -> None:
        self._page += 1
        await self._reload()

    def compose_content(self) -> ComposeResult:
        yield Static(self._title())
        yield self._data
        yield Container(
            Button('Back', id='paged-back'),
            Button('◀ Prev', id='page-prev'),
            Static('', id='page-info'),
            Button('Next ▶', id='page-next'),
            id='pagination-footer',
        )

    def _go_back(self) -> None:
        self.app.switch_screen(self._back_screen())

    @on(Button.Pressed, '#paged-back')
    async def on_back_pressed(self, event: Button.Pressed) -> None:
        self._go_back()

    def key_escape(self) -> None:
        self._go_back()


class TransactionsScreen(PaginatedTableScreen):
    _default_sort_col = 'date'
    _default_sort_asc = False

    async def _fetch_page(self, conn: 'Connection', offset: int, limit: int, sort_col: str, sort_asc: bool) -> tuple:
        return await fetch_transactions_page(conn, offset, limit, sort_col, sort_asc)

    async def _count_rows(self, conn: 'Connection') -> int:
        return await count_transactions(conn)

    def _title(self) -> str:
        return 'Transactions'

    def _back_screen(self) -> Screen:
        return MainScreen()


class AccountsScreen(PaginatedTableScreen):
    _default_sort_col = 'accountsTableID'
    _default_sort_asc = True

    async def _fetch_page(self, conn: 'Connection', offset: int, limit: int, sort_col: str, sort_asc: bool) -> tuple:
        return await fetch_accounts_page(conn, offset, limit, sort_col, sort_asc)

    async def _count_rows(self, conn: 'Connection') -> int:
        return await count_accounts(conn)

    def _title(self) -> str:
        return 'Accounts'

    def _back_screen(self) -> Screen:
        return MainScreen()


class ItemsScreen(PaginatedTableScreen):
    _default_sort_col = 'itemTableID'
    _default_sort_asc = True

    def __init__(self) -> None:
        super().__init__()
        self._data.cursor_type = 'row'
        self._selected_item_id: int | None = None
        self._selected_item_name: str = ''

    async def _fetch_page(self, conn: 'Connection', offset: int, limit: int, sort_col: str, sort_asc: bool) -> tuple:
        return await fetch_items_page(conn, offset, limit, sort_col, sort_asc)

    async def _count_rows(self, conn: 'Connection') -> int:
        return await count_items(conn)

    def _title(self) -> str:
        return 'Items'

    def _back_screen(self) -> Screen:
        return MainScreen()

    def compose_content(self) -> ComposeResult:
        yield Static(self._title())
        yield self._data
        yield Container(
            Button('Back', id='paged-back'),
            Button('◀ Prev', id='page-prev'),
            Static('', id='page-info'),
            Button('Next ▶', id='page-next'),
            Button('Edit', id='items-edit', disabled=True),
            id='pagination-footer',
        )

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row = self._data.get_row(event.row_key)
        self._selected_item_id = int(row[0])
        self._selected_item_name = str(row[1])
        self.query_one('#items-edit', Button).disabled = False

    @on(Button.Pressed, '#items-edit')
    async def on_edit_pressed(self, event: Button.Pressed) -> None:
        if self._selected_item_id is not None:
            self.app.switch_screen(RenameItemScreen(self._selected_item_id, self._selected_item_name))


class RenameItemScreen(BaseScreen):
    def __init__(self, item_id: int, item_name: str) -> None:
        super().__init__()
        self._item_id = item_id
        self._item_name = item_name

    def compose_content(self) -> ComposeResult:
        from textual.widgets import Input

        yield Static(f'Rename item: {self._item_name}')
        yield Input(value=self._item_name, placeholder='Item name', id='rename-input')
        yield Container(
            Button('Cancel', id='rename-cancel'),
            Button('Save', id='rename-save'),
            classes='button-group',
        )

    @on(Button.Pressed, '#rename-save')
    async def on_save_pressed(self, event: Button.Pressed) -> None:
        from textual.widgets import Input

        new_name = self.query_one('#rename-input', Input).value.strip()
        if not new_name:
            return
        db_path = self.app._db_path
        if db_path:
            async with connect(db_path) as conn:
                await rename_item(conn, self._item_id, new_name)
                await conn.commit()
        self.app.switch_screen(ItemsScreen())

    @on(Button.Pressed, '#rename-cancel')
    async def on_cancel_pressed(self, event: Button.Pressed) -> None:
        self.app.switch_screen(ItemsScreen())


class OpenFileScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self._tree = None
        self._selected = None

    def compose_content(self) -> ComposeResult:
        if not self._tree:
            self._tree = DirectoryTree('./')

        yield Static('\nOpen database file (*.fydb):\n')
        yield self._tree
        yield Container(
            Button('Cancel', id='open-file-cancel'),
            Button('Open', id='open-file-open'),
            classes='button-group',
        )

    @on(DirectoryTree.FileSelected)
    async def on_tree_selected(self, event):
        self._selected = event.path

    @on(Button.Pressed, '#open-file-cancel')
    async def on_cancel_pressed(self, event):
        self.app.switch_screen(MainScreen())

    @on(Button.Pressed, '#open-file-open')
    async def on_open_pressed(self, event):
        if not self._selected:
            return
        if not self._selected.name.endswith('.fydb'):
            self.app.log_write('Please select a fydb file')
            return

        self.app.database_connect(self._selected)
        self.app.switch_screen(MainScreen())


class CluecoinsMenuScreen(MenuScreen):
    """MenuScreen that hosts the dropdown menu widgets."""

    app: 'CluecoinsApp'

    _DB_REQUIRED_IDS: ClassVar[tuple[str, ...]] = (
        '#statistics_menu_item',
        '#fetch_quotes_menu_item',
        '#disconnect_menu_item',
        '#transactions_menu_item',
        '#accounts_menu_item',
        '#labels_menu_item',
    )
    _BUSY_LOCKED_IDS: ClassVar[tuple[str, ...]] = (
        '#open_file_menu_item',
        '#statistics_menu_item',
        '#fetch_quotes_menu_item',
        '#disconnect_menu_item',
        '#cached_quotes_menu_item',
        '#transactions_menu_item',
        '#accounts_menu_item',
        '#labels_menu_item',
    )

    def _apply_db_state(self) -> None:
        has_db = self.app._db_path
        for item_id in self._DB_REQUIRED_IDS:
            self.query_one(item_id, MenuItem).disabled = not has_db

    def _apply_busy_state(self) -> None:
        is_busy = self.app._is_busy
        has_db = self.app._db_path
        for item_id in self._BUSY_LOCKED_IDS:
            item = self.query_one(item_id, MenuItem)
            if is_busy:
                item.disabled = True
            else:
                item.disabled = item_id in self._DB_REQUIRED_IDS and not has_db

    async def on_mount(self) -> None:
        self._apply_db_state()
        self._apply_busy_state()

    def on_screen_resume(self) -> None:
        self._apply_db_state()
        self._apply_busy_state()

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Menu(
            MenuItem('Open File', menu_action='app.open_file', id='open_file_menu_item'),
            MenuItem('Open Device', disabled=True),
            MenuItem('Disconnect', id='disconnect_menu_item'),
            MenuItem('Exit', menu_action='app.exit'),
            name='File',
            id='file_menu',
        )
        yield Menu(
            MenuItem('Transactions', menu_action='app.transactions', id='transactions_menu_item'),
            MenuItem('Accounts', menu_action='app.accounts', id='accounts_menu_item'),
            MenuItem('Items', menu_action='app.labels', id='labels_menu_item'),
            name='Edit',
            id='edit_menu',
        )
        yield Menu(
            MenuItem('Statistics', menu_action='app.statistics', id='statistics_menu_item'),
            MenuItem('Cached Quotes', menu_action='app.cached_quotes', id='cached_quotes_menu_item'),
            name='View',
            id='view_menu',
        )
        yield Menu(
            MenuItem('Fetch Quotes', menu_action='app.fetch_quotes', id='fetch_quotes_menu_item'),
            MenuItem('Change Currency', disabled=True),
            name='Tools',
            id='tools_menu',
        )
        yield Menu(
            MenuItem('About', disabled=True),
            name='Help',
            id='help_menu',
        )


class CluecoinsApp(App):
    """A Textual app to manage Cluecoinses."""

    BINDINGS: ClassVar = [
        ('q', 'quit', 'Quit the app'),
    ]
    CSS_PATH = 'style.tcss'
    SCREENS = {  # noqa: RUF012
        'menu': CluecoinsMenuScreen,
    }

    def __init__(self) -> None:
        super().__init__()
        self._db_path: Path | None = None
        self._db_conn: Connection | None = None
        self._status_text: str = 'not connected'
        self._log_history: list = []
        self._is_busy: bool = False

    def log_write(self, message) -> None:
        self._log_history.append(message)
        try:
            self.screen.query_one('#log', RichLog).write(message)
        except NoMatches:
            pass

    def refresh_menu_state(self) -> None:
        if isinstance(self.screen, CluecoinsMenuScreen):
            self.screen._apply_db_state()
            self.screen._apply_busy_state()

    def database_connect(self, db_path: Path) -> None:
        self._db_path = db_path
        self.refresh_menu_state()

        res = subprocess.run(
            ('file', str(db_path)),
            capture_output=True,
            text=True,
            check=True,
        )
        self.log_write(f'connected to `{db_path}`')
        self.log_write(res.stdout.split(':')[1].strip())
        self._status_text = f'connected to `{db_path.name}`'
        try:
            self.screen.query_one('#status_bar', Static).update(self._status_text)
        except NoMatches:
            pass
        try:
            self.screen.query_one('#welcome_text', Static).update(
                f'Connected to `{db_path.name}`.\n\nSelect command from the menu bar.'
            )
        except NoMatches:
            pass

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def action_exit(self) -> None:
        self.exit()

    def action_open_file(self) -> None:
        self.switch_screen(OpenFileScreen())

    def action_cached_quotes(self) -> None:
        self.switch_screen(QuotesScreen())

    def action_statistics(self) -> None:
        self.switch_screen(StatisticsScreen())

    def action_fetch_quotes(self) -> None:
        self.switch_screen(FetchQuotesScreen())

    def action_transactions(self) -> None:
        self.switch_screen(TransactionsScreen())

    def action_accounts(self) -> None:
        self.switch_screen(AccountsScreen())

    def action_labels(self) -> None:
        self.switch_screen(ItemsScreen())


def run() -> None:
    app = CluecoinsApp()
    app.run()


if __name__ == '__main__':
    run()
