import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import ClassVar

import xdg
from textual import on
from textual.app import App
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Button
from textual.widgets import ContentSwitcher
from textual.widgets import DirectoryTree
from textual.widgets import RichLog
from textual.widgets import Static

from cluecoins.storage import Storage

LOG = RichLog()
LOG.styles.height = 10


WELCOME_TEXT = """
Welcome to Cluecoins!

To get started, select "Open File" from the File menu to open a database file.
"""

class BaseScreen(Static):
    """Base screen class with common navigation functionality."""

    app: 'CluecoinsApp'

    def navigate_back_to_main(self):
        """Navigate back to the main screen."""
        self.parent.watch_current(self.id, 'main_screen')


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

    @on(Button.Pressed, '#file_menu_button')
    def show_file_menu(self, event):
        app = self.app
        app.show_menu('file_menu', 0)

    @on(Button.Pressed, '#edit_menu_button')
    def show_edit_menu(self, event):
        app = self.app
        app.show_menu('edit_menu', 22)

    @on(Button.Pressed, '#view_menu_button')
    def show_view_menu(self, event):
        app = self.app
        app.show_menu('view_menu', 44)

    @on(Button.Pressed, '#tools_menu_button')
    def show_tools_menu(self, event):
        app = self.app
        app.show_menu('tools_menu', 66)

    @on(Button.Pressed, '#help_menu_button')
    def show_help_menu(self, event):
        app = self.app
        app.show_menu('help_menu', 88)


class MainScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self._text = Static(WELCOME_TEXT, id='welcome_text')

    def compose(self) -> ComposeResult:
        yield self._text


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
        self._log = RichLog()

    async def on_mount(self):
        storage = Storage(Path(xdg.xdg_data_home()) / 'cluecoins' / 'cluecoins.db')
        quotes = defaultdict(int)
        async with storage.db:
            async for date, base_currency, quote_currency in await storage.db.execute(
                'SELECT date, base_currency, quote_currency FROM quotes ORDER BY base_currency, quote_currency, date'
            ):
                quotes[base_currency + quote_currency + ' ' + date[:4]] += 1
        for group, count in quotes.items():
            self._log.write(f'{group} {count}')

    def compose(self) -> ComposeResult:
        yield Static('Quotes fetched from CurrencyBeacon API\n')
        yield self._log


class StatisticsScreen(BaseScreen):
    async def on_mount(self):
        ...

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

        self.app.set_db_path(self._selected)
        self.navigate_back_to_main()


class CluecoinsApp(App):
    """A Textual app to manage Cluecoinses."""

    BINDINGS: ClassVar = [
        ('q', 'quit', 'Quit the app'),
    ]
    CSS_PATH = 'style.tcss'

    def __init__(self):
        super().__init__()
        self._content = ContentSwitcher(id='content')
        self._status_bar = Static(
            'not connected',
            id='status_bar',
        )
        self._db_path: Path | None = None
        self._db_hint: str = ''
        self._menu_bar = MenuBar()

    def set_db_path(self, db_path: Path) -> None:
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
        self.app.query_one('#welcome_text').update(
            f'Welcome to Cluecoins!\n\n'
            f'Connected to `{db_path.name}`\n\n'
        )

    def navigate_to_screen(self, screen_id: str, screen_class):
        """Navigate to a screen, creating it if it doesn't exist."""
        self.hide_all_menus()
        try:
            self._content.watch_current(self._content.visible_content.id, screen_id)
        except Exception:
            self._content.add_content(
                screen_class(),
                id=screen_id,
                set_current=True,
            )

    def compose(self):
        yield self._menu_bar
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
        yield Container(
            self._content,
            classes='window',
        )
        yield LOG
        yield self._status_bar

    def hide_all_menus(self):
        """Hide all dropdown menus."""
        self.query('.menu_column').add_class('hidden')

    def show_menu(self, menu_id: str, x_offset: int):
        """Show a specific menu at the given x offset."""
        menu = self.query_one(f'#{menu_id}')
        is_hidden = menu.has_class('hidden')
        self.hide_all_menus()

        if is_hidden:
            menu.remove_class('hidden')
            menu.styles.offset = (x_offset, 1)

    @on(Button.Pressed, '#exit')
    async def on_exit_pressed(self, event):
        sys.exit(0)

    @on(Button.Pressed, '#open_file_button')
    async def on_open_file_pressed(self, event):
        self.navigate_to_screen('open_file_screen', OpenFileScreen)

    @on(Button.Pressed, '#cached_quotes_button')
    async def on_cached_quotes_pressed(self, event):
        self.navigate_to_screen('quotes_screen', QuotesScreen)

    @on(Button.Pressed, '#statistics_button')
    async def on_statistics_pressed(self, event):
        self.navigate_to_screen('statistics_screen', StatisticsScreen)


    @on(Button.Pressed, '#fetch_quotes_button')
    async def on_fetch_quotes_pressed(self, event):
        self.navigate_to_screen('fetch_quotes_screen', FetchQuotesScreen)

    def on_mount(self) -> None:
        self._content.add_content(
            MainScreen(),
            id='main_screen',
            set_current=True,
        )


def run() -> None:
    app = CluecoinsApp()
    app.run()


if __name__ == '__main__':
    run()
