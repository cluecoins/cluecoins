from pathlib import Path

from zandev_textual_widgets.menu import MenuHeader
from zandev_textual_widgets.menu import MenuItem

from cluecoins.ui import CluecoinsApp
from cluecoins.ui import CluecoinsMenuScreen
from cluecoins.ui import MainScreen
from cluecoins.ui import StatisticsScreen
from cluecoins.ui import TableRowsScreen


async def test_menu_opens_and_action_fires() -> None:
    """MenuHeader click → CluecoinsMenuScreen pushed → action routes to app."""
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        # Click the File MenuHeader (mouse_down triggers open_menu)
        file_header = next(h for h in app.screen.query(MenuHeader) if h.menu_id == 'file_menu')
        await pilot.mouse_down(file_header)
        await pilot.pause()

        # CluecoinsMenuScreen should now be the active screen
        assert isinstance(app.screen, CluecoinsMenuScreen)

        # Dismiss the menu and verify we're back on the main screen
        await pilot.press('escape')
        await pilot.pause()
        assert not isinstance(app.screen, CluecoinsMenuScreen)


async def test_open_file_and_exit(fydb_file: Path) -> None:
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        # Navigate to open file screen via action
        app.action_open_file()
        await pilot.pause()

        # Bypass DirectoryTree: inject the selected path directly
        pilot.app.screen._selected = fydb_file  # type: ignore[attr-defined]

        # Click Open
        await pilot.click('#open-file-open')
        await pilot.pause()

        # Verify status bar shows connected
        assert 'connected' in app._status_text

        # Verify log history contains connection message
        assert any('connected' in str(m) for m in app._log_history)


async def test_statistics_screen_no_db() -> None:
    """StatisticsScreen with no DB logs a message and shows empty table."""
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        app.action_statistics()
        await pilot.pause()

        assert isinstance(app.screen, StatisticsScreen)
        assert any('no database' in str(m) for m in app._log_history)


async def test_statistics_screen_with_db(fydb_with_tables: Path) -> None:
    """StatisticsScreen with a DB shows table rows."""
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        app.database_connect(fydb_with_tables)
        app.action_statistics()
        await pilot.pause()

        assert isinstance(app.screen, StatisticsScreen)
        assert app.screen._data.row_count > 0  # type: ignore[attr-defined]


async def test_statistics_back_button() -> None:
    """Back button in StatisticsScreen returns to MainScreen."""
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        app.action_statistics()
        await pilot.pause()
        assert isinstance(app.screen, StatisticsScreen)

        await pilot.click('#statistics-back')
        await pilot.pause()
        assert isinstance(app.screen, MainScreen)


async def test_statistics_esc_returns_to_main() -> None:
    """Esc in StatisticsScreen returns to MainScreen."""
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        app.action_statistics()
        await pilot.pause()
        assert isinstance(app.screen, StatisticsScreen)

        await pilot.press('escape')
        await pilot.pause()
        assert isinstance(app.screen, MainScreen)


async def test_table_rows_back_button(fydb_with_tables: Path) -> None:
    """Back button in TableRowsScreen returns to StatisticsScreen."""
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        app.database_connect(fydb_with_tables)
        app.switch_screen(TableRowsScreen(db_path=fydb_with_tables, table_name='TESTTABLE'))
        await pilot.pause()
        assert isinstance(app.screen, TableRowsScreen)

        await pilot.click('#table-rows-back')
        await pilot.pause()
        assert isinstance(app.screen, StatisticsScreen)


async def test_table_rows_esc(fydb_with_tables: Path) -> None:
    """Esc in TableRowsScreen returns to StatisticsScreen."""
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        app.database_connect(fydb_with_tables)
        app.switch_screen(TableRowsScreen(db_path=fydb_with_tables, table_name='TESTTABLE'))
        await pilot.pause()
        assert isinstance(app.screen, TableRowsScreen)

        await pilot.press('escape')
        await pilot.pause()
        assert isinstance(app.screen, StatisticsScreen)


async def test_statistics_menu_item_greyed_out_no_db() -> None:
    """Statistics menu item is disabled when no DB is connected."""
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        view_header = next(h for h in app.screen.query(MenuHeader) if h.menu_id == 'view_menu')
        await pilot.mouse_down(view_header)
        await pilot.pause()

        assert isinstance(app.screen, CluecoinsMenuScreen)
        stats_item = app.screen.query_one('#statistics_menu_item', MenuItem)
        assert stats_item.disabled


async def test_statistics_menu_item_enabled_with_db(fydb_file: Path) -> None:
    """Statistics menu item is enabled when a DB is connected."""
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        app.database_connect(fydb_file)

        view_header = next(h for h in app.screen.query(MenuHeader) if h.menu_id == 'view_menu')
        await pilot.mouse_down(view_header)
        await pilot.pause()

        assert isinstance(app.screen, CluecoinsMenuScreen)
        stats_item = app.screen.query_one('#statistics_menu_item', MenuItem)
        assert not stats_item.disabled
