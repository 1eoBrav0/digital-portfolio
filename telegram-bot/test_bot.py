import unittest
from unittest.mock import patch

from bot import CONFIRM, SERVICES, handle_update, open_store
from telegram_adapter import TemporaryFailure, poll


class IntakeTest(unittest.TestCase):
    def setUp(self):
        self.db = open_store()
        self.addCleanup(self.db.close)
        self.sequence = 0

    def send(self, text, chat=1):
        self.sequence += 1
        update = {"update_id": self.sequence,
                  "message": {"chat": {"id": chat, "type": "private"}, "text": text}}
        return handle_update(self.db, update)

    def requests(self):
        return [tuple(row) for row in self.db.execute("SELECT id, chat, service, brief FROM requests")]

    def test_review_validation_and_confirmation(self):
        self.assertEqual(self.send("/start")["reply_markup"]["keyboard"][0], list(SERVICES))
        self.assertEqual(self.send("?")["text"], "Выберите услугу.")
        self.send(SERVICES[1])
        self.assertIn("500", self.send("x" * 501)["text"])
        brief = "Собрать учебный отчёт"
        review = self.send(brief)
        self.assertIn(brief, review["text"])
        self.assertEqual(review["reply_markup"]["keyboard"][0], list(CONFIRM))
        self.assertEqual(self.requests(), [])
        self.assertIn("№1", self.send("Отправить")["text"])
        self.assertEqual(self.requests(), [(1, 1, SERVICES[1], brief)])

    def test_cancel_and_separate_chats(self):
        self.send("/start")
        self.send("/start", chat=2)
        self.send(SERVICES[0], chat=2)
        self.send("Записать на показ", chat=2)
        self.send("Отменить", chat=2)
        drafts = self.db.execute("SELECT chat FROM drafts").fetchall()
        self.assertEqual([row["chat"] for row in drafts], [1])
        self.send("/cancel")
        self.assertIn("/start", self.send("Отправить")["text"])
        self.assertEqual(self.requests(), [])

    def test_repeat_update_and_retry_delivery(self):
        for text in ("/start", SERVICES[0], "Уточнить расписание", "Отправить"):
            response = self.send(text)
        repeated = handle_update(self.db, {"update_id": self.sequence})
        self.assertEqual(repeated, response)

        # Имитация обрыва связи при отправке ответа и успешного повтора.
        with patch("telegram_adapter.time.sleep"), patch("telegram_adapter.call_api") as api:
            api.side_effect = [TemporaryFailure(), {}, KeyboardInterrupt()]
            with self.assertRaises(KeyboardInterrupt):
                poll(self.db, "offline-demo")
            self.assertEqual(api.call_args_list[0], api.call_args_list[1])
            self.assertEqual(api.call_args_list[1].args[1:], ("sendMessage", response))
            self.assertEqual(api.call_args_list[2].args[2]["offset"], self.sequence + 1)
        self.assertEqual(len(self.requests()), 1)
        self.assertEqual(self.db.execute("SELECT sent FROM delivery").fetchone()["sent"], 1)


if __name__ == "__main__":
    unittest.main()
