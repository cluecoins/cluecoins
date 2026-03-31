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

from cluecoins.storage import LocalStorage

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


class MenuButton(Button):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.add_class('menu_button')


class MenuBar(Container):
    """A menu bar component for the top menu buttons only."""

    def __init__(self):
        super().__init__(id='menu_bar')

    def compose(self) -> ComposeResult:
        yield MenuButton('File', id='file_menu_button')
        yield MenuButton('Edit', id='edit_menu_button')
        yield MenuButton('View', id='view_menu_button')
        yield MenuButton('Tools', id='tools_menu_button')
        yield MenuButton('Help', id='help_menu_button')
        yield MenuButton('▏🏠▕', id='main_menu_button')

    @on(Button.Pressed, '#file_menu_button')
    def show_file_menu(self, event):
        self.screen.show_menu('file_menu', 0)  # type: ignore[attr-defined]

    @on(Button.Pressed, '#edit_menu_button')
    def show_edit_menu(self, event):
        self.screen.show_menu('edit_menu', 22)  # type: ignore[attr-defined]

    @on(Button.Pressed, '#view_menu_button')
    def show_view_menu(self, event):
        self.screen.show_menu('view_menu', 44)  # type: ignore[attr-defined]

    @on(Button.Pressed, '#tools_menu_button')
    def show_tools_menu(self, event):
        self.screen.show_menu('tools_menu', 66)  # type: ignore[attr-defined]

    @on(Button.Pressed, '#help_menu_button')
    def show_help_menu(self, event):
        self.screen.show_menu('help_menu', 88)  # type: ignore[attr-defined]

    @on(Button.Pressed, '#main_menu_button')
    def go_home(self, event):
        self.app.switch_screen(MainScreen())


class BaseScreen(Screen):
    """Base screen with always-visible menubar, log, and status bar."""

    app: 'CluecoinsApp'

    def compose(self) -> ComposeResult:
        yield MenuBar()
        yield Container(
            MenuButton('Open File', id='open_file_button'),
            MenuButton('Open Device', id='open_device_button', disabled=True),
            MenuButton('Disconnect', disabled=True),
            MenuButton('Exit', id='exit'),
            id='file_menu',
            classes='menu_column hidden',
        )
        yield Container(
            MenuButton('Accounts', disabled=True),
            MenuButton('Labels', disabled=True),
            id='edit_menu',
            classes='menu_column hidden',
        )
        yield Container(
            MenuButton('Statistics', id='statistics_button'),
            MenuButton('Cached Quotes', id='cached_quotes_button'),
            id='view_menu',
            classes='menu_column hidden',
        )
        yield Container(
            MenuButton('Fetch Quotes', id='fetch_quotes_button'),
            MenuButton('Change Currency', id='change_currency_button', disabled=True),
            id='tools_menu',
            classes='menu_column hidden',
        )
        yield Container(
            MenuButton('About', disabled=True),
            id='help_menu',
            classes='menu_column hidden',
        )
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

    def hide_all_menus(self) -> None:
        self.query('.menu_column').add_class('hidden')

    def show_menu(self, menu_id: str, x_offset: int) -> None:
        menu = self.query_one(f'#{menu_id}')
        is_hidden = menu.has_class('hidden')
        self.hide_all_menus()
        if is_hidden:
            menu.remove_class('hidden')
            menu.styles.offset = (x_offset, 1)


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

    async def on_data_table_row_selected(self, event: DataTable.RowSelected):
        table_name = str(event.row_key.value)
        db_path = self.app._db_path
        if db_path:
            self.app.switch_screen(TableRowsScreen(db_path=db_path, table_name=table_name))

    async def key_escape(self):
        self.app.switch_screen(StatisticsScreen())


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


class CluecoinsApp(App):
    """A Textual app to manage Cluecoinses."""

    BINDINGS: ClassVar = [
        ('q', 'quit', 'Quit the app'),
    ]
    CSS_PATH = 'style.tcss'

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

    @on(Button.Pressed, '#exit')
    async def on_exit_pressed(self, event):
        self.exit()

    @on(Button.Pressed, '#open_file_button')
    async def on_open_file_pressed(self, event):
        self.switch_screen(OpenFileScreen())

    @on(Button.Pressed, '#cached_quotes_button')
    async def on_cached_quotes_pressed(self, event):
        self.switch_screen(QuotesScreen())

    @on(Button.Pressed, '#statistics_button')
    async def on_statistics_pressed(self, event):
        self.switch_screen(StatisticsScreen())

    @on(Button.Pressed, '#fetch_quotes_button')
    async def on_fetch_quotes_pressed(self, event):
        self.switch_screen(FetchQuotesScreen())

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


def run() -> None:
    app = CluecoinsApp()
    app.run()


if __name__ == '__main__':
    run()
