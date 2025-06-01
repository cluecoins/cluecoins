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
LOG.styles.height = 20


class MenuButton(Button):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.add_class('menu_button')


class MainScreen(Static):
    def compose(self) -> ComposeResult:
        yield Static('')


class FetchQuotesScreen(Static):
    app: 'CluecoinsApp'

    def __init__(self):
        super().__init__()
        self._log = RichLog()

    def compose(self) -> ComposeResult:
        yield Static('fetch quotes')
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
        self.parent.watch_current('fetch_quotes_screen', 'main_screen')


class QuotesScreen(Static):
    app: 'CluecoinsApp'

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
        yield Static('quotes\n')
        yield self._log


class OpenFileScreen(Static):
    app: 'CluecoinsApp'

    def __init__(self):
        super().__init__()
        self._tree = None
        self._selected = None

    def compose(self) -> ComposeResult:
        if not self._tree:
            self._tree = DirectoryTree('./')

        yield Static('open file')
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
        self.parent.watch_current('open_file_screen', 'main_screen')

    @on(Button.Pressed, '#open-file-open')
    async def on_open_pressed(self, event):
        if not self._selected:
            return
        if not self._selected.name.endswith('.fydb'):
            LOG.write('Please select a fydb file')
            return

        self.app.set_db_path(self._selected)
        self.parent.watch_current('open_file_screen', 'main_screen')


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

    # def set_status(self, status: str) -> None:
    #     db_name = self._db_path.name if self._db_path else 'not connected'
    #     self._status_bar.update(f'{db_name} | {status}')

    def set_db_path(self, db_path: Path) -> None:
        self._db_path = db_path
        LOG.write(f'connected to `{db_path}`')
        self._status_bar.update(f'connected to {db_path.name}')

    def compose(self):
        yield Container(
            MenuButton('File', id='file_menu_button'),
            MenuButton('Edit', id='edit_menu_button'),
            MenuButton('View', id='view_menu_button'),
            MenuButton('Help', id='help_menu_button'),
            id='menu_bar',
        )
        yield Container(
            MenuButton('Open File', id='open_file_button'),
            MenuButton('Open Device', id='open_device_button', disabled=True),
            MenuButton('Disconnect', disabled=True),
            MenuButton('Exit', id='exit'),
            id='file_menu',
            classes='menu_column hidden',
        )
        yield Container(
            MenuButton('Fetch Quotes', id='fetch_quotes_button'),
            MenuButton('Change Currency', id='change_currency_button', disabled=True),
            id='edit_menu',
            classes='menu_column hidden',
        )
        yield Container(
            MenuButton('Accounts', disabled=True),
            MenuButton('Cached Quotes', id='cached_quotes_button'),
            id='view_menu',
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

    def hide_menu_bar(self):
        self.query_one('#file_menu').add_class('hidden')
        self.query_one('#edit_menu').add_class('hidden')
        self.query_one('#view_menu').add_class('hidden')
        self.query_one('#help_menu').add_class('hidden')

    @on(Button.Pressed, '#file_menu_button')
    def show_file_menu(self, event):
        is_hidden = self.query_one('#file_menu').has_class('hidden')
        self.hide_menu_bar()

        if is_hidden:
            self.query_one('#file_menu').remove_class('hidden')
            self.query_one('#file_menu').styles.offset = (0, 1)

    @on(Button.Pressed, '#edit_menu_button')
    def show_edit_menu(self, event):
        is_hidden = self.query_one('#edit_menu').has_class('hidden')
        self.hide_menu_bar()

        if is_hidden:
            self.query_one('#edit_menu').remove_class('hidden')
            self.query_one('#edit_menu').styles.offset = (22, 1)

    @on(Button.Pressed, '#view_menu_button')
    def show_view_menu(self, event):
        is_hidden = self.query_one('#view_menu').has_class('hidden')
        self.hide_menu_bar()

        if is_hidden:
            self.query_one('#view_menu').remove_class('hidden')
            self.query_one('#view_menu').styles.offset = (44, 1)

    @on(Button.Pressed, '#help_menu_button')
    def show_help_menu(self, event):
        is_hidden = self.query_one('#help_menu').has_class('hidden')
        self.hide_menu_bar()

        if is_hidden:
            self.query_one('#help_menu').remove_class('hidden')
            self.query_one('#help_menu').styles.offset = (66, 1)

    @on(Button.Pressed, '#exit')
    async def on_exit_pressed(self, event):
        sys.exit(0)

    @on(Button.Pressed, '#open_file_button')
    async def on_open_file_pressed(self, event):
        self.hide_menu_bar()
        try:
            self._content.watch_current(self._content.visible_content.id, 'open_file_screen')
        except Exception:
            self._content.add_content(
                OpenFileScreen(),
                id='open_file_screen',
                set_current=True,
            )

    @on(Button.Pressed, '#cached_quotes_button')
    async def on_cached_quotes_pressed(self, event):
        self.hide_menu_bar()
        try:
            self._content.watch_current(self._content.visible_content.id, 'quotes_screen')
        except Exception:
            self._content.add_content(
                QuotesScreen(),
                id='quotes_screen',
                set_current=True,
            )

    @on(Button.Pressed, '#fetch_quotes_button')
    async def on_fetch_quotes_pressed(self, event):
        self.hide_menu_bar()
        try:
            self._content.watch_current(self._content.visible_content.id, 'fetch_quotes_screen')
        except Exception:
            self._content.add_content(
                FetchQuotesScreen(),
                id='fetch_quotes_screen',
                set_current=True,
            )

    def on_mount(self) -> None:
        self._content.add_content(
            MainScreen(),
            id='main_screen',
            set_current=True,
        )
        LOG.write('Welcome to Cluecoins!')


def run() -> None:

    # sync = SyncManager()

    # def get_db() -> str:
    #     if not db_path:
    #         return sync.prepare_local_db()
    #     return db_path

    app = CluecoinsApp()
    app.run()

    # def create_currency_window(manager: WindowManager) -> Window:
    #     '''Create the window to choose a currency and start convert.'''

    #     window = Window()

    #     def _start(base_currency: str) -> None:
    #         tmp_window = Window().center() + Label('Please wait...')
    #         manager.add(tmp_window)
    #         start_convert(base_currency)
    #         manager.remove(tmp_window)

    #     currency_field = InputField(prompt='Currency: ', value='USD')
    #     currency_window = (
    #         window
    #         + ""
    #         + currency_field
    #         + ""
    #         + Button('Convert', lambda *_: _start(currency_field.value))
    #         + ""
    #         + Button('Back', lambda *_: manager.remove(window))
    #     ).center()

    #     return currency_window

    # def create_account_archive_window(manager: WindowManager) -> Window:
    #     """Create the window to choose an account by name and start archive.

    #     Create an accounts info table.
    #     """

    #     con = lite.connect(get_db())

    #     accounts_table = Container()

    #     for account in get_accounts_list(con):
    #         account_name = account[0]
    #         acc = Button(
    #             account_name,
    #             partial(start_archive_account, account_name=account_name),
    #         )
    #         accounts_table += acc

    #     window = Window(box="HEAVY")

    #     archive_window = (
    #         window + "" + accounts_table + "" + Button('Back', lambda *_: manager.remove(window))
    #     ).center()

    #     return archive_window

    # def create_account_unarchive_window(manager: WindowManager) -> Window:
    #     """Create the window to choose an account by name and start unarchive.

    #     Create an accounts info table.
    #     """

    #     con = lite.connect(get_db())

    #     unarchive_accounts_table = Container()

    #     for account in get_archived_accounts(con):
    #         account_name = account[0]
    #         acc = Button(
    #             label=account_name,
    #             onclick=partial(start_unarchive_account, account_name=account_name),
    #         )
    #         unarchive_accounts_table += acc

    #     window = Window(box="HEAVY")

    #     unarchive_window = (
    #         window + "" + unarchive_accounts_table + "" + Button('Back', lambda *_: manager.remove(window))
    #     ).center()

    #     return unarchive_window

    # def start_convert(base_currency: str) -> None:

    #     cli._convert(base_currency, get_db())

    # def start_archive_account(button: Button, account_name: str) -> None:

    #     cli._archive(account_name, get_db())

    # def start_unarchive_account(button: Button | None, account_name: str) -> None:

    #     cli._unarchive(account_name, get_db())

    # def close_session() -> None:
    #     """Run app activity:
    #             default: opening an app on the phone

    #     Close terminal interface.
    #     """

    #     if sync.device is not None:
    #         # FIXME: hardcode
    #         sync.push_changes_to_app('.ui.activities.main.MainActivity')
    #     sys.exit(0)

    # with YamlLoader() as loader:
    #     loader.load(PYTERMGUI_CONFIG)

    # manager = WindowManager()

    # # Create a layout
    # layout = ptg.Layout()
    # top_bar_slot = layout.add_slot('top_bar', height=1, width=1.0)
    # top_bar_slot.content = ptg.Container(
    #     ptg.Label("File"),
    #     ptg.Label("Edit"),
    #     ptg.Label("View"),
    #     ptg.Label("Help"),
    # )

    # main_slot = layout.add_slot('main_screen', height=25, width=25)
    # main_slot.content = (
    #     Window(width=60, box="DOUBLE")
    #         + ""
    #         + Label(
    #             "A CLI tool to manage the database of Bluecoins,\nan awesome budget planner for Android.",
    #         )
    #         + ""
    #         + ptg.Container(
    #             "In development:",
    #             Label("- archive"),
    #             box="EMPTY_VERTICAL",
    #         )
    #         + ""
    #         + Button('Convert', lambda *_: manager.add(create_currency_window(manager)))
    #         + ""
    #         + Button('Archive', lambda *_: manager.add(create_account_archive_window(manager)))
    #         + ""
    #         + Button('Unarchive', lambda *_: manager.add(create_account_unarchive_window(manager)))
    #         + ""
    #         + Button('Exit programm', lambda *_: close_session())
    #         + ""
    #     ).set_title("[210 bold]Cluecoins").center()

    # layout.apply()

    # manager.add(main_slot.content)
    # manager.add(top_bar_slot.content)
    # manager.run()


if __name__ == '__main__':
    run()
