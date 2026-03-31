from pathlib import Path

from cluecoins.ui import CluecoinsApp


async def test_open_file_and_exit(fydb_file: Path) -> None:
    async with CluecoinsApp().run_test(size=(120, 40)) as pilot:
        # Open File menu
        await pilot.click('#file_menu_button')
        await pilot.pause()

        # Click Open File
        await pilot.click('#open_file_button')
        await pilot.pause()

        # Bypass DirectoryTree: inject the selected path directly
        pilot.app.screen._selected = fydb_file  # type: ignore[attr-defined]

        # Click Open
        await pilot.click('#open-file-open')
        await pilot.pause()

        app: CluecoinsApp = pilot.app  # type: ignore[assignment]

        # Verify status bar shows connected
        assert 'connected' in app._status_text

        # Verify log history contains connection message
        assert any('connected' in str(m) for m in app._log_history)

        # Open File menu and exit
        await pilot.click('#file_menu_button')
        await pilot.pause()
        await pilot.click('#exit')
