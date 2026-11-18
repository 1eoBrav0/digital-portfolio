"""Один процесс long polling для собственного Telegram-бота."""

import json
import os
import time
from contextlib import closing
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bot import handle_update, open_store


class TemporaryFailure(Exception):
    def __init__(self, seconds=3):
        self.seconds = seconds


def call_api(token, method, payload):
    request = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=45) as response:
            body = json.load(response)
    except HTTPError as error:
        if error.code == 429:
            retry_after = json.load(error).get("parameters", {}).get("retry_after", 3)
            raise TemporaryFailure(retry_after) from None
        if error.code >= 500:
            raise TemporaryFailure() from None
        raise SystemExit(f"Telegram отклонил {method} (HTTP {error.code}).") from None
    except (URLError, TimeoutError, HTTPException, json.JSONDecodeError):
        raise TemporaryFailure() from None
    if not body.get("ok"):
        raise SystemExit(f"Telegram отклонил {method} (код {body.get('error_code')}).")
    return body["result"]


def poll(db, token):
    while True:
        try:
            last = db.execute("SELECT * FROM delivery WHERE slot = 1").fetchone()
            if last and not last["sent"]:
                call_api(token, "sendMessage", json.loads(last["reply_json"]))
                with db:
                    db.execute("UPDATE delivery SET sent = 1 WHERE slot = 1")

            # Telegram хранит необработанные обновления не дольше суток.
            recent = db.execute(
                "SELECT update_id FROM delivery WHERE received_utc >= datetime('now', '-1 day')"
            ).fetchone()
            options = {"timeout": 25, "limit": 1, "allowed_updates": ["message"]}
            if recent:
                options["offset"] = recent["update_id"] + 1
            for update in call_api(token, "getUpdates", options):
                handle_update(db, update)
        except TemporaryFailure as error:
            time.sleep(error.seconds)


if __name__ == "__main__":
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Для подключения задайте TELEGRAM_BOT_TOKEN. Локальное демо: python bot.py")
    try:
        with closing(open_store(os.environ.get("BOT_DB", "requests.sqlite"))) as store:
            poll(store, token)
    except KeyboardInterrupt:
        pass
