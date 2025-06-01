# cluecoins 🔍

> ⚠️ This project is not related to the Bluecoins team in any way.

Cluecoins is a tool to manage the database of [Bluecoins](https://www.bluecoinsapp.com/) budget planner app. Use at your own risk, and always have a database backup!

You MUST have app version exactly **12.9.5-18451** to use this tool! The next major version changes the database schema, and this tool will not work with it. Use APKPure or similar service to download the app version.

## Installation

```shell
make install
source .venv/bin/activate
cluecoins
```

## Usage

Run `cluecoins` command in the terminal. Open ".fydb" file with the database. Use mouse to navigate through menus.

## Current features

- Update currency exchange rates using [CurrencyBeacon](https://currencybeacon.com/api-documentation) API. Affects transactions and accounts.

Consider registering on the site to get your own API key and set `CB_API_KEY` environment variable. If not set, built-in key will be used, but it has limits; use it only for testing purposes.

## Planned features

- [ ] View database statistics: number of accounts, transactions, categories, etc.
- [ ] View and edit transaction labels.
- [ ] Push/pull database using ADB shell.

## Database backup/restore

1. Open the Bluecoins app. Go to *Settings -> Data Management -> Phone Storage -> Backup to phone storage*.
2. Transfer created `*.fydb` database backup file to the PC.
3. After performing operations on that file transfer it to the smartphone. Go to *Settings -> Data Management -> Phone Storage -> Restore from phone storage*. Choose created file.

## Known Bluecoins issues

> 🤨 Know how to patch these bugs in APK? I would pay someone to fix them! Drop me a message at cluecoins at drsr dot io.

### Manual adjustment of foreign currency accounts

- Open non-USD account, modify the current balance.
- "Balance Adjustment" transaction is created, but conversion rate is reversed and direction is "+" instead of "-".
- Cluecoins can fix such transactions with "Fetch Quotes" command.

### Budgeting screen: month resets after opening category

- Open budgeting screen, select previous month.
- Open any category, then go back to budgeting screen.
- Month is reset to the current one, but the data is from the previous month.

This is interface issue, not a database one.

### Y axix in Net Worth widget is not scaled properly

- Open Main screen, scroll down to Net Worth widget.
- Y axis always starts at zero, making the widget useless.

## Resources

- `tests/bluecoins.sql` file contains empty database schema. Yours should be identical to it.
- `docs/database.md` file contains some information about the database structure.
