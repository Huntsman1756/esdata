# Alertmanager Telegram Secrets

Create this file on the VPS before enabling the `prod` Compose profile:

- `telegram_bot_token`: Telegram bot token from BotFather.

It is mounted read-only into Alertmanager at:

- `/etc/alertmanager/secrets/telegram_bot_token`

Set `TELEGRAM_CHAT_ID` in `/etc/esdata/esdata.env`. Alertmanager v0.28.1
supports `bot_token_file`, but not `chat_id_file`, so the Compose service
renders the chat id into a temporary config before starting Alertmanager.

Do not commit real secret values.
