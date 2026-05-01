from flask import Flask, request
import requests
import os
import re

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SHEET_URL = "https://opensheet.elk.sh/1m6dqGbvS-CHQO1eAO6l6A_2vSkxSIWdhlS5WnNl4zA0/Word"
CHANNEL_URL = "https://t.me/persian_bible"

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"


def normalize(text):
    text = str(text).strip().lower()
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = re.sub(r"[ًٌٍَُِّْ]", "", text)
    text = re.sub(r"[.,،؛:!؟?()«»\"']", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def get_words():
    try:
        response = requests.get(SHEET_URL, timeout=10)
        return response.json()
    except:
        return []


def find_word(user_text):
    normal_user_text = normalize(user_text)
    words = get_words()

    for item in words:
        word = item.get("کلمه", "")
        if normalize(word) == normal_user_text:
            return item

    return None


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(TELEGRAM_URL + "sendMessage", json=payload)


def answer_callback(callback_query_id):
    requests.post(TELEGRAM_URL + "answerCallbackQuery", json={
        "callback_query_id": callback_query_id
    })


def send_welcome(chat_id):
    text = (
        "✨ شالوم بر شما فرزندان نور\n"
        "به ربات «کلمه‌یاب و سرودیاب» خوش آمدید 🕊️"
    )

    keyboard = {
        "keyboard": [
            [{"text": "🕊️ راهنمای ربات"}],
            [{"text": "📣 کانال تلگرام"}]
        ],
        "resize_keyboard": True
    }

    send_message(chat_id, text, keyboard)


def send_guide(chat_id):
    text = (
        "🕊️ راهنمای ربات:\n"
        "عزیزان و همراهان در مسیح، برای بنای بیشتر از این خدمت، به نکات زیر توجه کنید:\n\n"
        "🌱 بذر کلام: کافیست نام کلمه‌ای (مثلاً: ابا) را بفرستید تا ریشه و معنای آن در کتاب‌مقدس برایتان آشکار شود.\n"
        "🎶 پرستش: نوشتن کلمه «سرود» پیش از نام آن.\n"
        "🙌 اتحاد در دعا: بارهای خود را با نوشتن «دعا:» با ما سهیم شوید.\n\n"
        "⚠️ در برخی مواقع ممکن است اولین پاسخ چند لحظه زمان ببرد. سپاس از شکیبایی شما 🙏"
    )

    send_message(chat_id, text)


def send_channel(chat_id):
    text = "عضویت در کانال رسمی برای دسترسی به آرشیو بزرگ مسیحی:"

    keyboard = {
        "inline_keyboard": [
            [{"text": "📣 ورود به کانال", "url": CHANNEL_URL}]
        ]
    }

    send_message(chat_id, text, keyboard)


def handle_file(message):
    chat_id = message["chat"]["id"]

    if "document" in message:
        file_id = message["document"]["file_id"]
        file_name = message["document"].get("file_name", "بدون نام")
        send_message(
            chat_id,
            f"📄 کد فایل دریافت شد:\n\nfile_id:\n{file_id}\n\nنام فایل:\n{file_name}"
        )
        return True

    if "audio" in message:
        file_id = message["audio"]["file_id"]
        file_name = message["audio"].get("file_name", "بدون نام")
        send_message(
            chat_id,
            f"🎵 کد فایل صوتی دریافت شد:\n\nfile_id:\n{file_id}\n\nنام فایل:\n{file_name}"
        )
        return True

    if "voice" in message:
        file_id = message["voice"]["file_id"]
        send_message(
            chat_id,
            f"🎙 کد ویس دریافت شد:\n\nfile_id:\n{file_id}"
        )
        return True

    return False


@app.route("/", methods=["GET"])
def home():
    return "Bot is running"


@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return "no data"

    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]

        if handle_file(message):
            return "ok"

        text = message.get("text", "").strip()

        if text == "/start":
            send_welcome(chat_id)
            return "ok"

        if text == "🕊️ راهنمای ربات" or "راهنمای ربات" in text:
            send_guide(chat_id)
            return "ok"

        if text == "📣 کانال تلگرام" or "کانال تلگرام" in text:
            send_channel(chat_id)
            return "ok"

        word = find_word(text)

        if not word:
            send_message(chat_id, "🔍 کلمه مورد نظر یافت نشد. خادمین شما در حال گسترش آرشیو هستند.")
            return "ok"

        testament = word.get("عهد", "")
        root_button = "💡 ریشه یونانی" if testament == "NT" else "💡 ریشه عبری"

        keyboard = {
            "inline_keyboard": [
                [{"text": "📜 آیه مرتبط", "callback_data": f"verse|{text}"}],
                [{"text": "📖 معنی", "callback_data": f"meaning|{text}"}],
                [{"text": root_button, "callback_data": f"root|{text}"}]
            ]
        }

        send_message(chat_id, f"🔍 اطلاعات کلمه «{word.get('کلمه', text)}» یافت شد:", keyboard)

    if "callback_query" in data:
        query = data["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        callback_data = query["data"]

        answer_callback(query["id"])

        action, searched_word = callback_data.split("|", 1)
        word = find_word(searched_word)

        if not word:
            send_message(chat_id, "❌ اطلاعات این کلمه پیدا نشد. دوباره جستجو کن.")
            return "ok"

        if action == "verse":
            send_message(chat_id, "📜 آیه مرتبط:\n\n" + word.get("آیه مرتبط", ""))

        elif action == "meaning":
            send_message(chat_id, "📖 معنی:\n\n" + word.get("معنی", ""))

        elif action == "root":
            title = "💡 ریشه یونانی" if word.get("عهد", "") == "NT" else "💡 ریشه عبری"
            send_message(chat_id, title + ":\n\n" + word.get("ریشه", ""))

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
