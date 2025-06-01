# cluecoins 🔍

> ⚠️ This project is not related to the Bluecoins team in any way.

Cluecoins is a tool to manage the database of [Bluecoins](https://www.bluecoinsapp.com/) budget planner app. Use at your own risk, and always have a database backup!

You MUST have app version exactly 12.9.5-18451 to use this tool!

## Database backup/restore

1. Open the Bluecoins app. Go to *Settings -> Data Management -> Phone Storage -> Backup to phone storage*.
2. Transfer created `*.fydb` database backup file to the PC.
3. After performing operations on that file transfer it to the smartphone. Go to *Settings -> Data Management -> Phone Storage -> Restore from phone storage*. Choose created file.

## Usage

Run `cluecoins` command in the terminal. Open ".fydb" file with the database.

## Current features

- Update currency exchange rates using [CurrencyBeacon](https://currencybeacon.com/api-documentation) API. Affects transactions and accounts.

Consider registering on the site to get your own API key and set `CB_API_KEY` environment variable. If not set, built-in key will be used, but it has limits; use it only for testing purposes.

## Resources

- `bluecoins.sql` file contains empty database schema. Yours should be identical to it.
- `database.md` file contains some information about the database structure.
