"""Демонстрация приёма заявок. Для запуска достаточно Python и SQLite."""

import json
import sqlite3
from contextlib import closing


SERVICES = ("Telegram-бот", "Автоматизация")
CONFIRM = ("Отправить", "Отменить")


def open_store(path=":memory:"):
    db = sqlite3.connect(path, isolation_level="IMMEDIATE")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS drafts (
            chat INTEGER PRIMARY KEY,
            service TEXT,
            brief TEXT
        );
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY,
            chat INTEGER NOT NULL,
            service TEXT NOT NULL,
            brief TEXT NOT NULL,
            created_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS delivery (
            slot INTEGER PRIMARY KEY CHECK (slot = 1),
            update_id INTEGER NOT NULL,
            reply_json TEXT,
            sent INTEGER NOT NULL,
            received_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    return db


def dialogue(db, chat, message):
    text = message.strip()
    if text == "/start":
        db.execute("INSERT OR REPLACE INTO drafts(chat) VALUES (?)", (chat,))
        return "Выберите услугу.", SERVICES
    if text == "/cancel":
        db.execute("DELETE FROM drafts WHERE chat = ?", (chat,))
        return "Заполнение отменено. Новая заявка — /start.", ()

    draft = db.execute("SELECT * FROM drafts WHERE chat = ?", (chat,)).fetchone()
    if draft is None:
        return "Чтобы оформить заявку, отправьте /start.", ()
    if draft["service"] is None:
        if text not in SERVICES:
            return "Выберите услугу.", SERVICES
        db.execute("UPDATE drafts SET service = ? WHERE chat = ?", (text, chat))
        return "Коротко опишите задачу.", ()
    if draft["brief"] is None:
        if not 5 <= len(text) <= 500:
            return "Введите от 5 до 500 символов.", ()
        db.execute("UPDATE drafts SET brief = ? WHERE chat = ?", (text, chat))
        return f"Проверьте заявку.\nУслуга: {draft['service']}\nЗадача: {text}", CONFIRM
    if text == "Отменить":
        db.execute("DELETE FROM drafts WHERE chat = ?", (chat,))
        return "Заявка отменена.", ()
    if text != "Отправить":
        return "Отправить заявку?", CONFIRM

    request = db.execute(
        "INSERT INTO requests(chat, service, brief) VALUES (?, ?, ?)",
        (chat, draft["service"], draft["brief"]),
    )
    db.execute("DELETE FROM drafts WHERE chat = ?", (chat,))
    return f"Заявка №{request.lastrowid} принята.", ()


def handle_update(db, update):
    """Сохранить изменение диалога и ответ в одной транзакции."""
    update_id = update["update_id"]
    with db:
        db.execute("BEGIN IMMEDIATE")
        last = db.execute("SELECT * FROM delivery WHERE slot = 1").fetchone()
        if last and last["update_id"] == update_id:
            return json.loads(last["reply_json"]) if last["reply_json"] else None

        message = update.get("message", {})
        chat = message.get("chat", {})
        reply = None
        if chat.get("type") == "private":
            if isinstance(message.get("text"), str):
                text, buttons = dialogue(db, chat["id"], message["text"])
                markup = {"keyboard": [list(buttons)], "resize_keyboard": True,
                          "one_time_keyboard": True} if buttons else {"remove_keyboard": True}
                reply = {"chat_id": chat["id"], "text": text, "reply_markup": markup}
            else:
                reply = {"chat_id": chat["id"], "text": "Пришлите текстовое сообщение."}

        db.execute(
            "INSERT OR REPLACE INTO delivery(slot, update_id, reply_json, sent) VALUES (1, ?, ?, ?)",
            (update_id, json.dumps(reply, ensure_ascii=False) if reply else None, int(reply is None)),
        )
    return reply


def demo():
    with closing(open_store()) as db:
        for update_id, text in enumerate(("/start", SERVICES[0], "Записать гостя на мастер-класс", "Отправить"), 1):
            message = {"chat": {"id": 1, "type": "private"}, "text": text}
            reply = handle_update(db, {"update_id": update_id, "message": message})
            print(f"> {text}\n{reply['text']}\n")


if __name__ == "__main__":
    demo()
