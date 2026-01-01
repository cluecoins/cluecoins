import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

from textual import on
from textual.app import App
from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import NoMatches
from textual.widgets import Button
from textual.widgets import ContentSwitcher
from textual.widgets import DataTable
from textual.widgets import DirectoryTree
from textual.widgets import RichLog
from textual.widgets import Static
from zandev_textual_widgets import MenuScreen
from cluecoins.ui import menu

from cluecoins.storage import LocalStorage

if TYPE_CHECKING:
    from aiosqlite import Connection

LOG = RichLog()
LOG.styles.height = 10


WELCOME_TEXT = """
Welcome to Cluecoins!

To get started, select "Open File" from the File menu to open a database file.
"""


class BaseScreen(Static):
    """Base screen class with common navigation functionality."""

    app: 'CluecoinsApp'

    def __init__(self):
        super().__init__(classes='screen')

    def navigate_back_to_main(self):
        """Navigate back to the main screen."""
        ...
        # (self.app.navigate_to_screen('menu', menu.MenuScreen),)
        # self.app.navigate_to_screen('main_screen', MainScreen)


class MainScreen(BaseScreen):
    def compose(self) -> ComposeResult:
        yield Static(WELCOME_TEXT, id='welcome_text')


class FetchQuotesScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self._log = RichLog()

    def compose(self) -> ComposeResult:
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

        self.app.get_widget_by_id('status_bar').update('fetching quotes...')
        self.app.get_widget_by_id('ok').disabled = True
        self.app.get_widget_by_id('back').disabled = True

        await convert('USD', str(self.app._db_path), LOG.write)

        self.app.get_widget_by_id('status_bar').update('quotes fetched')
        self.app.get_widget_by_id('ok').disabled = False
        self.app.get_widget_by_id('back').disabled = False

    @on(Button.Pressed, '#back')
    async def on_back_pressed(self, event):
        self.navigate_back_to_main()


class QuotesScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self._data = DataTable()

    async def on_mount(self):
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

    def compose(self) -> ComposeResult:
        yield Static('Quotes fetched from CurrencyBeacon API\n')
        yield self._data


class StatisticsScreen(BaseScreen):
    async def on_mount(self): ...

    def compose(self) -> ComposeResult:
        yield Static('')


class OpenFileScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self._tree = None
        self._selected = None

    def compose(self) -> ComposeResult:
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
        self.navigate_back_to_main()

    @on(Button.Pressed, '#open-file-open')
    async def on_open_pressed(self, event):
        if not self._selected:
            return
        if not self._selected.name.endswith('.fydb'):
            LOG.write('Please select a fydb file')
            return

        self.app.database_connect(self._selected)
        self.navigate_back_to_main()


class CluecoinsMenuScreen(MenuScreen):
    """Custom MenuScreen that mounts all the menus defined in menu.py"""
    
    async def on_mount(self):
        # Mount all the menus from menu.py
        self.mount(menu.file_menu)
        self.mount(menu.edit_menu)  
        self.mount(menu.view_menu)
        self.mount(menu.tools_menu)
        self.mount(menu.help_menu)
        
        await super().on_mount()


class CluecoinsApp(App):
    """A Textual app to manage Cluecoinses."""

    BINDINGS: ClassVar = [
        ('q', 'quit', 'Quit the app'),
    ]
    CSS_PATH = 'style.tcss'
    SCREENS = {  # noqa: RUF012
        'menu': CluecoinsMenuScreen,
        'open_file_screen': OpenFileScreen,
    }

    def __init__(self):
        super().__init__()
        self._content = ContentSwitcher(id='content')
        self._status_bar = Static(
            'not connected',
            id='status_bar',
        )
        self._db_path: Path | None = None
        self._db_conn: Connection | None = None

    def database_connect(self, db_path: Path) -> None:
        self._db_path = db_path

        res = subprocess.run(
            ('file', str(db_path)),
            capture_output=True,
            text=True,
            check=True,
        )
        LOG.write(f'connected to `{db_path}`')
        LOG.write(res.stdout.split(':')[1].strip())
        self._status_bar.update(f'connected to `{db_path.name}`')
        self.app.query_one('#welcome_text').update(  # type: ignore[attr-defined]
            f'Connected to `{db_path.name}.\n\nSelect command from the menu bar.'
        )

    def navigate_to_screen(self, screen_id: str, screen_class):
        """Navigate to a screen, creating it if it doesn't exist."""
        # self.hide_all_menus()

        self.app.query('.screen').set(display=False)

        if self._content.current:
            self._content.watch_current(self._content.visible_content.id, None)

        try:
            self._content.watch_current(None, screen_id)
        except NoMatches:
            self._content.add_content(
                screen_class(),
                id=screen_id,
                set_current=True,
            )

    def compose(self):

        yield menu.bar
        yield Container(
            self._content,
            classes='window',
        )
        yield LOG
        yield self._status_bar

    def on_mount(self) -> None:
        self.navigate_to_screen('main_screen', MainScreen)

    # Menu action handlers
    def action_exit(self):
        self.exit()

    def action_open_file(self):
        self.navigate_to_screen('open_file_screen', OpenFileScreen)

    def action_cached_quotes(self):
        self.navigate_to_screen('quotes_screen', QuotesScreen)

    def action_statistics(self):
        self.navigate_to_screen('statistics_screen', StatisticsScreen)

    def action_fetch_quotes(self):
        self.navigate_to_screen('fetch_quotes_screen', FetchQuotesScreen)


def run() -> None:
    app = CluecoinsApp()
    app.run()


if __name__ == '__main__':
    run()
