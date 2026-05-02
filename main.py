from flask import Flask, request
import requests
import os
import re
import random
import time

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SHEET_ID = "1m6dqGbvS-CHQO1eAO6l6A_2vSkxSIWdhlS5WnNl4zA0"
BASE = f"https://opensheet.elk.sh/{SHEET_ID}"
TG = f"https://api.telegram.org/bot{BOT_TOKEN}/"
CHANNEL_URL = "https://t.me/persian_bible"
WRITER_URL = "https://script.google.com/macros/s/AKfycbwEQknEZsWHgdAyg8BI1tm0R-UDjUiD1gQFcifqa3sSuAWUPT1GmqJ0eSSSmVdNpXVV/exec"

SONG_CATEGORIES = [
    {"button": "✝️ سرودهای عید قیام", "value": "عید قیام"},
    {"button": "🎄 سرودهای تولد مسیح", "value": "تولد مسیح"},
    {"button": "🩸 سرودهای جمعه صلیب", "value": "جمعه صلیب"},
]

CACHE = {}
CACHE_TIME = 300


def norm(t):
    t = str(t).strip().lower()
    t = t.replace("ي", "ی").replace("ك", "ک")
    t = t.replace("آ", "ا").replace("أ", "ا").replace("إ", "ا")
    t = re.sub(r"[ًٌٍَُِّْ]", "", t)
    t = re.sub(r"[.,،؛:!؟?()«»\"']", "", t)
    return re.sub(r"\s+", " ", t)


def clear_cache(name=None):
    if name:
        CACHE.pop(name, None)
    else:
        CACHE.clear()


def sheet(name, use_cache=True):
    now = time.time()
    if use_cache and name in CACHE and now - CACHE[name]["time"] < CACHE_TIME:
        return CACHE[name]["data"]

    try:
        data = requests.get(f"{BASE}/{name}", timeout=10).json()
        CACHE[name] = {"time": now, "data": data}
        return data
    except:
        return []


def value(row, key):
    for k, v in row.items():
        if str(k).strip() == key:
            return str(v).strip()
    return ""


def send_msg(chat_id, text, markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if markup:
        payload["reply_markup"] = markup
    requests.post(TG + "sendMessage", json=payload)


def send_audio(chat_id, file_id, caption=""):
    requests.post(TG + "sendAudio", json={
        "chat_id": chat_id,
        "audio": file_id,
        "caption": caption
    })


def send_doc(chat_id, file_id, caption=""):
    requests.post(TG + "sendDocument", json={
        "chat_id": chat_id,
        "document": file_id,
        "caption": caption
    })


def writer(payload):
    try:
        return requests.post(WRITER_URL, json=payload, timeout=10).json()
    except:
        return {"ok": False}


def main_keyboard():
    return {
        "keyboard": [
            [{"text": "🕊️ راهنمای ربات"}, {"text": "📣 کانال تلگرام"}],
            [{"text": "📚 کتابخانه"}, {"text": "📁 دسته‌بندی سرودها"}],
            [{"text": "🎵 یک سرود برام انتخاب کن"}],
            [{"text": "📩 وعده‌های خدا"}, {"text": "💡 دانستنی‌های جالب"}],
            [{"text": "🙏 دعا کنیم"}],
        ],
        "resize_keyboard": True
    }


def welcome(chat_id):
    result = writer({"type": "user", "chat_id": chat_id})

    if result.get("exists"):
        text = "✨ خوشحالیم دوباره می‌بینیمت.\nبه ربات «کلمه‌یاب و سرودیاب» خوش آمدید 🕊️"
    else:
        text = "✨ شالوم بر شما فرزندان نور\nبه ربات «کلمه‌یاب و سرودیاب» خوش آمدید 🕊️"

    send_msg(chat_id, text, main_keyboard())


def guide(chat_id):
    send_msg(chat_id, """🕊️ راهنمای ربات:
عزیزان و همراهان در مسیح، برای بنای بیشتر از این خدمت، به نکات زیر توجه کنید:

🌱 بذر کلام: کافیست نام کلمه‌ای (مثلاً: ابا) را بفرستید تا ریشه و معنای آن در کتاب‌مقدس برایتان آشکار شود.
🎶 پرستش: نوشتن کلمه «سرود» پیش از نام آن.
🙌 اتحاد در دعا: بارهای خود را با نوشتن «دعا:» با ما سهیم شوید.

⚠️ در برخی مواقع ممکن است اولین پاسخ چند لحظه زمان ببرد. سپاس از شکیبایی شما 🙏""")


def channel(chat_id):
    send_msg(chat_id, "عضویت در کانال رسمی برای دسترسی به آرشیو بزرگ مسیحی:",
             {"inline_keyboard": [[{"text": "📣 ورود به کانال", "url": CHANNEL_URL}]]})


def handle_file(msg):
    chat_id = msg["chat"]["id"]

    for kind, icon in [("document", "📄"), ("audio", "🎵"), ("voice", "🎙")]:
        if kind in msg:
            file_id = msg[kind]["file_id"]
            name = msg[kind].get("file_name", "بدون نام")
            send_msg(chat_id, f"{icon} کد فایل دریافت شد:\n\nfile_id:\n{file_id}\n\nنام فایل:\n{name}")
            return True

    return False


def not_found(chat_id):
    send_msg(chat_id, "🔍 این مورد هنوز در آرشیو ما نیست\nخادمین در حال گسترش آرشیو هستند.")


def find_word(text):
    exact = None
    partial = []

    for r in sheet("Word"):
        word = value(r, "کلمه")
        if not word:
            continue

        if norm(word) == norm(text):
            exact = r
            break

        if norm(text) in norm(word) or norm(word) in norm(text):
            partial.append(r)

    return exact, partial


def word_result(chat_id, text):
    exact, partial = find_word(text)

    if exact:
        w = exact
        root = "💡 ریشه یونانی" if value(w, "عهد") == "NT" else "💡 ریشه عبری"

        send_msg(chat_id, f"🔍 اطلاعات کلمه «{value(w, 'کلمه')}» یافت شد:",
                 {"inline_keyboard": [
                     [{"text": "📜 آیه مرتبط", "callback_data": f"wverse|{value(w, 'کلمه')}"}],
                     [{"text": "📖 معنی", "callback_data": f"wmean|{value(w, 'کلمه')}"}],
                     [{"text": root, "callback_data": f"wroot|{value(w, 'کلمه')}"}],
                 ]})
        return

    if partial:
        buttons = [
            [{"text": "🔍 " + value(w, "کلمه"), "callback_data": f"wordchoose|{value(w, 'کلمه')}"}]
            for w in partial[:10]
        ]
        send_msg(chat_id, "🔍 چند مورد نزدیک پیدا شد:", {"inline_keyboard": buttons})
        return

    not_found(chat_id)


def library(chat_id):
    books = [r for r in sheet("Library") if value(r, "اسم کتاب") and value(r, "فایل")]

    if not books:
        send_msg(chat_id, "📚 هنوز کتابی در کتابخانه ثبت نشده است.")
        return

    buttons = [
        [{"text": "📖 " + value(b, "اسم کتاب"), "callback_data": f"book|{i}"}]
        for i, b in enumerate(books)
    ]

    send_msg(chat_id, "📚 کتاب مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})


def categories(chat_id):
    buttons = [
        [{"text": c["button"], "callback_data": f"cat|{c['value']}"}]
        for c in SONG_CATEGORIES
    ]

    send_msg(chat_id, "🎵 مناسبت مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})


def random_song(chat_id):
    songs = [
        r for r in sheet("Songs", use_cache=False)
        if value(r, "اسم سرود") and value(r, "فایل")
    ]

    if not songs:
        send_msg(chat_id, "🎵 هنوز سرودی ثبت نشده است.")
        return

    s = random.choice(songs)
    send_audio(chat_id, value(s, "فایل"), "🎶 این سرود تقدیم به شما\n\n🎵 " + value(s, "اسم سرود"))


def search_song(chat_id, text):
    name = norm(text.replace("سرود", "", 1))
    exact = None
    partial = []

    for s in sheet("Songs", use_cache=False):
        song_name = value(s, "اسم سرود")

        if not song_name:
            continue

        if norm(song_name) == name:
            exact = s
            break

        if name in norm(song_name) or norm(song_name) in name:
            partial.append(s)

    if exact:
        send_audio(chat_id, value(exact, "فایل"), "🎶 این سرود تقدیم به شما\n\n🎵 " + value(exact, "اسم سرود"))
        return

    if partial:
        buttons = [
            [{"text": "🎵 " + value(s, "اسم سرود"), "callback_data": f"songname|{value(s, 'اسم سرود')}"}]
            for s in partial[:10]
        ]
        send_msg(chat_id, "🎵 چند سرود نزدیک پیدا شد:", {"inline_keyboard": buttons})
        return

    not_found(chat_id)


def promise(chat_id):
    rows = [r for r in sheet("Promises") if value(r, "متن وعده")]

    if not rows:
        send_msg(chat_id, "📩 هنوز وعده‌ای ثبت نشده است.")
        return

    r = random.choice(rows)
    send_msg(chat_id, f"📩 وعده‌ای از خداوند برای امروز:\n\n✨ {value(r, 'متن وعده')}\n\n📖 {value(r, 'آیه')}")


def fact(chat_id):
    rows = [r for r in sheet("Facts") if value(r, "متن دانستنی")]

    if not rows:
        send_msg(chat_id, "💡 هنوز دانستنی ثبت نشده است.")
        return

    r = random.choice(rows)
    send_msg(chat_id, f"💡 آیا می‌دانستید؟\n\n▫️ {value(r, 'متن دانستنی')}\n\n📍 {value(r, 'منبع')}")


def prayer_menu(chat_id):
    send_msg(chat_id, "🙏 بخش دعا\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
             {"inline_keyboard": [
                 [{"text": "✍️ درخواست دعا", "callback_data": "prayer_request"}],
                 [{"text": "🙌 دعا برای یکدیگر", "callback_data": "prayer_random"}],
             ]})


def save_prayer(chat_id, text):
    prayer = text.replace("دعا:", "", 1).strip()

    if not prayer:
        send_msg(chat_id, "🙏 لطفاً بعد از «دعا:» متن درخواست دعای خود را بنویسید.")
        return

    result = writer({"type": "prayer", "text": prayer})

    if result.get("ok"):
        clear_cache("Prayers")
        send_msg(chat_id, "🙏 درخواست دعای شما به صورت ناشناس ثبت شد.\nخادمین برای شما دعا خواهند کرد 🙏")
    else:
        send_msg(chat_id, "متأسفانه ثبت دعا انجام نشد. لطفاً دوباره تلاش کنید.")


def random_prayer(chat_id):
    rows = sheet("Prayers", use_cache=False)
    valid = []

    for i, r in enumerate(rows, start=2):
        if value(r, "متن دعا"):
            valid.append((i, r))

    if not valid:
        send_msg(chat_id, "🙏 هنوز درخواست دعایی ثبت نشده است.")
        return

    row_number, r = random.choice(valid)
    count = value(r, "تعداد دعا") or "0"

    send_msg(chat_id,
             f"🙏 درخواست دعا: {value(r, 'متن دعا')}\n\n⭕️ {count} نفر برای این درخواست دعا کردند",
             {"inline_keyboard": [
                 [{"text": "🙌 من هم دعا کردم", "callback_data": f"praydone|{row_number}"}],
                 [{"text": "✍️ ثبت درخواست دعا", "callback_data": "prayer_request"}],
             ]})


@app.route("/", methods=["GET"])
def home():
    return "Bot is running"


@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return "ok"

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]

        if handle_file(msg):
            return "ok"

        text = msg.get("text", "").strip()

        if text != "/start":
            send_msg(chat_id, "⏳ در حال آماده‌سازی...")

        if text == "/start":
            welcome(chat_id)
        elif text == "🕊️ راهنمای ربات":
            guide(chat_id)
        elif text == "📣 کانال تلگرام":
            channel(chat_id)
        elif text == "📚 کتابخانه":
            library(chat_id)
        elif text == "📁 دسته‌بندی سرودها":
            categories(chat_id)
        elif text == "🎵 یک سرود برام انتخاب کن":
            random_song(chat_id)
        elif text == "📩 وعده‌های خدا":
            promise(chat_id)
        elif text == "💡 دانستنی‌های جالب":
            fact(chat_id)
        elif text == "🙏 دعا کنیم":
            prayer_menu(chat_id)
        elif text.startswith("دعا:"):
            save_prayer(chat_id, text)
        elif norm(text).startswith("سرود "):
            search_song(chat_id, text)
        else:
            word_result(chat_id, text)

    if "callback_query" in data:
        q = data["callback_query"]
        chat_id = q["message"]["chat"]["id"]
        cb = q["data"]

        requests.post(TG + "answerCallbackQuery", json={"callback_query_id": q["id"]})

        if cb.startswith("book|"):
            books = [r for r in sheet("Library") if value(r, "اسم کتاب") and value(r, "فایل")]
            b = books[int(cb.split("|")[1])]
            send_doc(chat_id, value(b, "فایل"), "📚 " + value(b, "اسم کتاب"))

        elif cb.startswith("cat|"):
            cat = cb.split("|", 1)[1]

            songs = [
                r for r in sheet("Songs", use_cache=False)
                if norm(value(r, "مناسبت")) == norm(cat)
                and value(r, "اسم سرود")
                and value(r, "فایل")
            ]

            if not songs:
                send_msg(chat_id, f"🎵 هنوز سرودی برای این مناسبت ثبت نشده است:\n\n{cat}")
                return "ok"

            buttons = [
                [{"text": "🎵 " + value(s, "اسم سرود"), "callback_data": f"catsong|{cat}|{value(s, 'اسم سرود')}"}]
                for s in songs
            ]

            buttons.append([{"text": "⬅️ برگشت", "callback_data": "back_categories"}])
            send_msg(chat_id, f"🎵 سرودهای {cat}:", {"inline_keyboard": buttons})

        elif cb == "back_categories":
            categories(chat_id)

        elif cb.startswith("catsong|"):
            _, cat, song_name = cb.split("|", 2)

            for s in sheet("Songs", use_cache=False):
                if norm(value(s, "مناسبت")) == norm(cat) and norm(value(s, "اسم سرود")) == norm(song_name):
                    send_audio(chat_id, value(s, "فایل"), "🎶 این سرود تقدیم به شما\n\n🎵 " + value(s, "اسم سرود"))
                    break

        elif cb.startswith("songname|"):
            song_name = cb.split("|", 1)[1]

            for s in sheet("Songs", use_cache=False):
                if norm(value(s, "اسم سرود")) == norm(song_name):
                    send_audio(chat_id, value(s, "فایل"), "🎶 این سرود تقدیم به شما\n\n🎵 " + value(s, "اسم سرود"))
                    break

        elif cb == "prayer_request":
            send_msg(chat_id, "🙏 درخواست دعای خود را بنویسید:\n\nمثال:\nدعا: برای آرامش خانواده‌ام\n\nخادمین برای شما دعا خواهند کرد 🙏")

        elif cb == "prayer_random":
            random_prayer(chat_id)

        elif cb.startswith("praydone|"):
            row_number = cb.split("|", 1)[1]
            result = writer({"type": "prayer_count", "row": row_number})
            count = result.get("count", "")

            clear_cache("Prayers")

            if count != "":
                send_msg(chat_id, f"🤍 ممنون از همراهی شما\n\n⭕️ {count} نفر برای این درخواست دعا کردند")
            else:
                send_msg(chat_id, "🙏 ممنون از اینکه در دعا همراه شدید.\nخداوند برکتتان دهد 🤍")

        elif cb.startswith("wordchoose|"):
            word_text = cb.split("|", 1)[1]
            word_result(chat_id, word_text)

        elif cb.startswith("w"):
            action, word_text = cb.split("|", 1)
            exact, _ = find_word(word_text)
            w = exact

            if w:
                if action == "wverse":
                    send_msg(chat_id, "📜 آیه مرتبط:\n\n" + value(w, "آیه مرتبط"))
                elif action == "wmean":
                    send_msg(chat_id, "📖 معنی:\n\n" + value(w, "معنی"))
                elif action == "wroot":
                    title = "💡 ریشه یونانی" if value(w, "عهد") == "NT" else "💡 ریشه عبری"
                    send_msg(chat_id, title + ":\n\n" + value(w, "ریشه"))

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
