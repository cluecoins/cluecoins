# cluecoins 🔍

> ⚠️ This project is not related to the **B**luecoins developers in any way.

**cluecoins** is a tool to manage the database of [Bluecoins](https://www.bluecoinsapp.com/), an awesome budget planner app for Android.

This tool is beta software. Use at your own risk, and always have a database backup!

## Requirements

You **MUST** have Bluecoins app version exactly **12.9.5-18451** to use this tool! The next major version changes the database schema, and this tool will not work with it. Use APKPure or similar service to download the old app version and disable automatic updates for it.

Also, you **MUST** buy a full version of Bluecoins! Support the developer! It's a state-of-art software: offline, without subscription, minimalistic and customizable. I use it daily for 6 (six) years!

Unfortunately, it relies on Google Play Services to check the license, so for no-GAPPS users patched APKs are the only way. As a bonus, patched version won't update and bork the database.

## Installation

You need a Linux machine with `uv` tool installed.

```shell
make install
source .venv/bin/activate
```

## Usage

Run `cluecoins` command in the terminal. Open ".fydb" file with the database. Use mouse to navigate through menus.

## Current features

### Update exchange rates

> ⚠️ This functionality was tested only with **USD** base currency

Updates currency exchange rates using historical data from [CurrencyBeacon API](https://currencybeacon.com/api-documentation). Affects transactions and accounts.

Consider registering on the site to get your own API key and set `CB_API_KEY` environment variable. If not set, built-in key will be used, but it has limits; use it only for testing purposes.

## Roadmap

- [ ] View database statistics. Number of accounts, transactions, etc.
- [ ] Verify database schema.
- [ ] View and edit transaction labels.
- [ ] Find and remove empty transactions, labels.
- [ ] Push/pull database using ADB shell.
- [ ] Backup/restore database.
- [ ] Full keyboard navigation.

### Bugs

- [ ] Menu bar doesn's react to arrow keys.

## Database backup/restore

1. Open the Bluecoins app. Go to *Settings -> Data Management -> Phone Storage -> Backup to phone storage*.
2. Transfer created `*.fydb` database backup file to the PC.
3. After performing operations on that file transfer it to the smartphone. Go to *Settings -> Data Management -> Phone Storage -> Restore from phone storage*. Choose created file.

## Known Bluecoins 12.x issues

<!-- 🤨 Know how to patch these bugs in APK? I would pay someone to fix them! Drop me a message at cluecoins at drsr dot io. -->

### Manual adjustment of foreign currency accounts

- Open non-USD account, modify the current balance.
- "Balance Adjustment" transaction is created, but conversion rate is reversed and direction is "+" instead of "-".
- cluecoins can fix such transactions with "Fetch Quotes" command. To do it manually in Bluecoins, open the transaction, tap "+" button and save.

### Budgeting screen: month resets after opening category

- Open budgeting screen, select previous month.
- Open any category, then go back to budgeting screen.
- Month is reset to the current one, but the data is from the previous month.

This is interface issue, not a database one.

### Y axis in Net Worth widget is not scaled properly

Opinionated, I guess.

- Open Main screen, scroll down to the Net Worth widget.
- Y axis always starts at zero, making the widget useless.

## Resources

See the following files in this repo:

- `tests/bluecoins.sql` file contains empty database schema. Yours should be identical to it.
- `docs/database.md` file contains some information about the database structure.
