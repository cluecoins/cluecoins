# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**cluecoins** is a Python TUI application (built with [Textual](https://textual.textualize.io/)) for managing the SQLite database of [Bluecoins](https://www.bluecoinsapp.com/), an Android budget planning app. It connects directly to `.fydb` backup files (plain SQLite, version 42).

## Commands

```bash
make install   # Install dependencies via uv
make format    # Format code with ruff
make lint      # Lint + type-check with ruff + mypy
make test      # Run tests with pytest
```

Run a single test:
```bash
uv run pytest tests/test_storage.py::test_name -v
```

Run the app:
```bash
uv run cluecoins
```

## Code Style

- **Ruff**: single quotes, line length 120
- **MyPy**: Python 3.12, non-strict
- **Async-first**: all DB operations use `aiosqlite`; UI is event-driven via Textual

## Architecture

The app is layered:

```
ui/          → Textual TUI (screens, menus, widgets)
cli.py       → Business logic (convert() orchestrates the main workflow)
database.py  → Async DB queries against the .fydb Bluecoins database
storage.py   → Local cache (quotes cached in ~/.cache/cluecoins/cache.sqlite3)
quotes.py    → CurrencyBeacon API client (CB_API_KEY env var; has a built-in fallback key)
```

**Main workflow** (Fetch Quotes):
1. `ui/__init__.py` → user triggers `FetchQuotesScreen`
2. Calls `cli.convert()` which queries `TRANSACTIONSTABLE` / `ACCOUNTSTABLE` for foreign currency entries
3. Fetches rates via `CurrencyBeaconQuoteProvider` (with local SQLite cache)
4. Updates conversion rates in the `.fydb` database

**Storage locations**:
- App data: `~/.local/share/cluecoins/`
- Quote cache: `~/.cache/cluecoins/cache.sqlite3`

## Key Notes

- Several modules (`adb.py`, `sync_manager.py`) and sections of `database.py`/`storage.py` contain commented-out code for future ADB device sync — not yet active.
- The menu system in `ui/__init__.py` uses hidden containers toggled via CSS; it's mouse-driven (keyboard navigation is a roadmap item).
- The `LOG` widget (`RichLog`) in the UI also writes to `cluecoins.log` for debugging.
- The app targets Bluecoins v12.9.5-18451 specifically; schema may differ in other versions.
