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

SONGS_PER_PAGE = 20
CACHE = {}
CACHE_TIME = 300


def norm(t):
    t = str(t or "").strip().lower()
    t = t.replace("\u200c", "").replace("\u200f", "").replace("\ufeff", "")
    t = t.replace("\xa0", " ")
    t = t.replace("ي", "ی").replace("ك", "ک")
    t = t.replace("آ", "ا").replace("أ", "ا").replace("إ", "ا")
    t = re.sub(r"[ًٌٍَُِّْ]", "", t)
    t = re.sub(r"[.,،؛:!؟?()«»\"']", "", t)
    return re.sub(r"\s+", " ", t).strip()


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
        data = requests.get(f"{BASE}/{name}", timeout=15).json()
        CACHE[name] = {"time": now, "data": data}
        return data
    except:
        return []


def value(row, key):
    wanted = norm(key)
    for k, v in row.items():
        if norm(k) == wanted:
            return str(v or "").strip()
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
            [{"text": "🎼 سرودها"}, {"text": "📚 کتابخانه"}],
            [{"text": "🙏 دعا"}, {"text": "📖 کلمات کتاب مقدس"}],
            [{"text": "📩 وعده‌های خدا"}, {"text": "💡 دانستنی‌های جالب"}],
            [{"text": "📣 کانال"}, {"text": "⚠️ راهنما"}],
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
🎶 پرستش: برای دریافت سرود، اول کلمه «سرود» و بعد اسم آن را بنویسید.
مثال: سرود نترس

🙌 اتحاد در دعا: بارهای خود را با نوشتن «دعا:» با ما سهیم شوید.

⚠️ در برخی مواقع ممکن است اولین پاسخ چند لحظه زمان ببرد. سپاس از شکیبایی شما 🙏""")


def channel(chat_id):
    send_msg(chat_id, "عضویت در کانال رسمی برای دسترسی به آرشیو بزرگ مسیحی:",
             {"inline_keyboard": [[{"text": "📣 ورود به کانال", "url": CHANNEL_URL}]]})


def songs_menu(chat_id):
    buttons = [
        [{"text": "✝️ سرودهای عید قیام", "callback_data": "cat|0"}],
        [{"text": "🎄 سرودهای تولد مسیح", "callback_data": "cat|1"}],
        [{"text": "🩸 سرودهای جمعه صلیب", "callback_data": "cat|2"}],
        [{"text": "🎼 لیست کامل سرودها", "callback_data": "songpage|0"}],
        [{"text": "🎵 یک سرود برام انتخاب کن", "callback_data": "random_song"}],
        [{"text": "⬅️ بازگشت", "callback_data": "back_main"}],
    ]

    send_msg(chat_id, "🎼 بخش سرودها\n\nیکی از گزینه‌های زیر را انتخاب کنید 👇", {"inline_keyboard": buttons})


def word_instruction(chat_id):
    send_msg(chat_id, "📖 نام کلمه مورد نظر را بنویسید.")


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
        [{"text": c["button"], "callback_data": f"cat|{i}"}]
        for i, c in enumerate(SONG_CATEGORIES)
    ]

    send_msg(chat_id, "🎵 مناسبت مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})


def get_all_songs():
    return [
        r for r in sheet("Songs", use_cache=False)
        if value(r, "اسم سرود") and value(r, "فایل")
    ]


def random_song(chat_id):
    songs = get_all_songs()

    if not songs:
        send_msg(chat_id, "🎵 هنوز سرودی ثبت نشده است.")
        return

    s = random.choice(songs)
    send_audio(chat_id, value(s, "فایل"), "🎶 این سرود تقدیم به شما\n\n🎵 " + value(s, "اسم سرود"))


def song_list(chat_id, page=0):
    songs = get_all_songs()

    if not songs:
        send_msg(chat_id, "🎼 هنوز سرودی در لیست ثبت نشده است.")
        return

    total = len(songs)
    total_pages = (total + SONGS_PER_PAGE - 1) // SONGS_PER_PAGE

    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    start = page * SONGS_PER_PAGE
    end = min(start + SONGS_PER_PAGE, total)

    buttons = []

    for i in range(start, end):
        song_name = value(songs[i], "اسم سرود")
        buttons.append([{
            "text": f"🎵 {song_name}",
            "callback_data": f"allsong|{i}"
        }])

    nav = []
    if page > 0:
        nav.append({"text": "⬅️ صفحه قبل", "callback_data": f"songpage|{page - 1}"})
    if page < total_pages - 1:
        nav.append({"text": "صفحه بعد ➡️", "callback_data": f"songpage|{page + 1}"})

    if nav:
        buttons.append(nav)

    buttons.append([{"text": "⬅️ برگشت", "callback_data": "songs_menu"}])

    send_msg(
        chat_id,
        f"🎼 لیست سرودها — صفحه {page + 1} از {total_pages}\n\nبرای دریافت، روی نام سرود بزنید:",
        {"inline_keyboard": buttons}
    )


def search_song(chat_id, text):
    query = norm(text.replace("سرود", "", 1))

    if not query:
        send_msg(chat_id, "🎵 لطفاً بعد از کلمه «سرود» اسم سرود را بنویسید.")
        return

    exact = None
    partial = []

    for s in sheet("Songs", use_cache=False):
        song_name = value(s, "اسم سرود")
        file_id = value(s, "فایل")

        if not song_name or not file_id:
            continue

        clean_name = norm(song_name)

        if clean_name == query:
            exact = s
            break

        if query in clean_name:
            partial.append(s)

    chosen = exact or (partial[0] if partial else None)

    if chosen:
        send_audio(chat_id, value(chosen, "فایل"), "🎶 این سرود تقدیم به شما\n\n🎵 " + value(chosen, "اسم سرود"))
        return

    not_found(chat_id)


def promise(chat_id):
    rows = [r for r in sheet("Promises") if value(r, "متن وعده")]

    if not rows:
        send_msg(chat_id, "📩 هنوز وعده‌ای ثبت نشده است.")
        return

    r = random.choice(rows)
    send_msg(
        chat_id,
        f"📩 وعده‌ امروز خداوند برای شما :\n\n✨ {value(r, 'متن وعده')}\n\n📖 {value(r, 'آیه')}",
        {"inline_keyboard": [[{"text": "📩 وعده بعدی", "callback_data": "promise_next"}]]}
    )


def fact(chat_id):
    rows = [r for r in sheet("Facts") if value(r, "متن دانستنی")]

    if not rows:
        send_msg(chat_id, "💡 هنوز دانستنی ثبت نشده است.")
        return

    r = random.choice(rows)
    send_msg(
        chat_id,
        f"💡 آیا میدانستید:\n\n▫️ {value(r, 'متن دانستنی')}\n\n📍 {value(r, 'منبع')}",
        {"inline_keyboard": [[{"text": "💡 دانستنی بعدی", "callback_data": "fact_next"}]]}
    )


def prayer_menu(chat_id):
    send_msg(chat_id, "یکی از گزینه‌ها را انتخاب کنید 👇",
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
        elif text == "⚠️ راهنما" or text == "🕊️ راهنمای ربات":
            guide(chat_id)
        elif text == "📣 کانال" or text == "📣 کانال تلگرام":
            channel(chat_id)
        elif text == "🎼 سرودها":
            songs_menu(chat_id)
        elif text == "📚 کتابخانه":
            library(chat_id)
        elif text == "🙏 دعا" or text == "🙏 دعا کنیم":
            prayer_menu(chat_id)
        elif text == "📖 کلمات کتاب مقدس":
            word_instruction(chat_id)
        elif text == "📩 وعده‌های خدا":
            promise(chat_id)
        elif text == "💡 دانستنی‌های جالب":
            fact(chat_id)
        elif text == "📁 دسته‌بندی سرودها":
            categories(chat_id)
        elif text == "🎼 لیست سرودها":
            song_list(chat_id, 0)
        elif text == "🎵 یک سرود برام انتخاب کن":
            random_song(chat_id)
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
            cat_index = int(cb.split("|", 1)[1])
            cat_value = SONG_CATEGORIES[cat_index]["value"]
            cat_button = SONG_CATEGORIES[cat_index]["button"]

            all_category_songs = [
                r for r in sheet("CategorySongs", use_cache=False)
                if value(r, "اسم سرود") and value(r, "فایل")
            ]

            songs = [
                {"index": i, "row": r}
                for i, r in enumerate(all_category_songs)
                if norm(value(r, "مناسبت")) == norm(cat_value)
            ]

            if not songs:
                send_msg(chat_id, f"🎵 هنوز سرودی برای این مناسبت ثبت نشده است:\n\n{cat_value}")
                return "ok"

            buttons = [
                [{
                    "text": "🎵 " + value(item["row"], "اسم سرود"),
                    "callback_data": f"catsong|{item['index']}"
                }]
                for item in songs
            ]

            buttons.append([{"text": "⬅️ برگشت", "callback_data": "songs_menu"}])
            send_msg(chat_id, f"🎵 {cat_button}:", {"inline_keyboard": buttons})

        elif cb == "songs_menu":
            songs_menu(chat_id)

        elif cb == "back_categories":
            categories(chat_id)

        elif cb.startswith("catsong|"):
            index = int(cb.split("|", 1)[1])
            all_category_songs = [
                r for r in sheet("CategorySongs", use_cache=False)
                if value(r, "اسم سرود") and value(r, "فایل")
            ]

            if 0 <= index < len(all_category_songs):
                s = all_category_songs[index]
                send_audio(chat_id, value(s, "فایل"), "🎶 این سرود تقدیم به شما\n\n🎵 " + value(s, "اسم سرود"))

        elif cb == "random_song":
            random_song(chat_id)

        elif cb.startswith("songpage|"):
            page = int(cb.split("|", 1)[1])
            song_list(chat_id, page)

        elif cb.startswith("allsong|"):
            index = int(cb.split("|", 1)[1])
            songs = get_all_songs()

            if 0 <= index < len(songs):
                s = songs[index]
                send_audio(chat_id, value(s, "فایل"), "🎶 این سرود تقدیم به شما\n\n🎵 " + value(s, "اسم سرود"))

        elif cb == "back_main":
            send_msg(chat_id, "🏠 از منوی پایین، بخش مورد نظر را انتخاب کنید.", main_keyboard())

        elif cb == "promise_next":
            promise(chat_id)

        elif cb == "fact_next":
            fact(chat_id)

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
