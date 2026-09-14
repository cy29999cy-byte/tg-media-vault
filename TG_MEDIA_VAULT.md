# TG Media Vault V1

TG Media Vault is the V1 product layer being built on top of the original Telegram media downloader.

## Current V1 flow

1. Enter Telegram API ID / API Hash once.
2. Sign in with phone number + verification code.
3. Existing Telegram Session is reused on later launches.
4. The app automatically lists joined channels and groups.
5. Select media types: photo / video / GIF / file.
6. Select a time range: all / 7 / 30 / 90 days.
7. Scan first, then archive selected media.
8. SQLite tracks `account_id + chat_id + message_id` to avoid duplicate downloads.
9. Files are organized under:

   `Download Root / Channel / Media Type / <message_id>_<filename>`

## Windows quick start

### First run

Double-click:

`setup_vault_windows.bat`

This creates a local `.venv` and installs the normal + Web UI dependencies.

### Start the app

Double-click:

`run_vault_windows.bat`

Or run manually:

```bash
python vault_ui.py
```

The UI opens on port `8081`.

## Local data

TG Media Vault stores its V1 user data outside the repository under:

`~/.tg-media-vault/`

This includes:

- `settings.yaml`
- `sessions/`
- `vault.sqlite3`

The default media output folder is:

`~/Downloads/TG Media Vault`

## Development branch

Active V1 work happens on:

`dev/v1-mvp`

Draft PR #1 is used for CI validation and should remain unmerged until the MVP passes smoke testing.
