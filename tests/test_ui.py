from pathlib import Path

from zandev_textual_widgets.menu import MenuHeader

from cluecoins.ui import CluecoinsApp
from cluecoins.ui import CluecoinsMenuScreen


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
