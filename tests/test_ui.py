from pathlib import Path

from cluecoins.ui import CluecoinsApp


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

        # Exit via action
        app.action_exit()
