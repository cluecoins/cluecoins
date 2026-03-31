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

        await convert('USD', str(self.app._db_path), self.app.log_write)

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

    async def on_mount(self) -> None:
        if not self.app._db_path:
            self.query_one('#statistics_menu_item', MenuItem).disabled = True

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Menu(
            MenuItem('Open File', menu_action='app.open_file'),
            MenuItem('Open Device', disabled=True),
            MenuItem('Disconnect', disabled=True),
            MenuItem('Exit', menu_action='app.exit'),
            name='File',
            id='file_menu',
        )
        yield Menu(
            MenuItem('Transactions', disabled=True),
            MenuItem('Accounts', disabled=True),
            MenuItem('Labels', disabled=True),
            name='Edit',
            id='edit_menu',
        )
        yield Menu(
            MenuItem('Statistics', menu_action='app.statistics', id='statistics_menu_item'),
            MenuItem('Cached Quotes', menu_action='app.cached_quotes'),
            name='View',
            id='view_menu',
        )
        yield Menu(
            MenuItem('Fetch Quotes', menu_action='app.fetch_quotes'),
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

    def __init__(self):
        super().__init__()
        self._db_path: Path | None = None
        self._db_conn: Connection | None = None
        self._status_text = 'not connected'
        self._log_history: list = []

    def log_write(self, message) -> None:
        self._log_history.append(message)
        try:
            self.screen.query_one('#log', RichLog).write(message)
        except NoMatches:
            pass

    def database_connect(self, db_path: Path) -> None:
        self._db_path = db_path

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


def run() -> None:
    app = CluecoinsApp()
    app.run()


if __name__ == '__main__':
    run()
