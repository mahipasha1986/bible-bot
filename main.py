from flask import Flask, request
import requests, os, re, random

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SHEET_ID = "1m6dqGbvS-CHQO1eAO6l6A_2vSkxSIWdhlS5WnNl4zA0"
BASE = f"https://opensheet.elk.sh/{SHEET_ID}"
TG = f"https://api.telegram.org/bot{BOT_TOKEN}/"
CHANNEL_URL = "https://t.me/persian_bible"

SONG_CATEGORIES = [
    "✝️ سرودهای عید قیام",
    "🎄 سرودهای تولد مسیح",
    "🩸 سرودهای جمعه صلیب"
]

def sheet(name):
    try:
        return requests.get(f"{BASE}/{name}", timeout=10).json()
    except:
        return []

def value(row, key):
    for k, v in row.items():
        if str(k).strip() == key:
            return str(v).strip()
    return ""

def norm(t):
    t = str(t).strip().lower()
    t = t.replace("ي","ی").replace("ك","ک").replace("آ","ا").replace("أ","ا").replace("إ","ا")
    t = re.sub(r"[ًٌٍَُِّْ]", "", t)
    t = re.sub(r"[.,،؛:!؟?()«»\"']", "", t)
    return re.sub(r"\s+", " ", t)

def send_msg(chat_id, text, markup=None):
    data = {"chat_id": chat_id, "text": text}
    if markup:
        data["reply_markup"] = markup
    requests.post(TG + "sendMessage", json=data)

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

def main_keyboard():
    return {
        "keyboard": [
            [{"text":"🕊️ راهنمای ربات"}, {"text":"📣 کانال تلگرام"}],
            [{"text":"📚 کتابخانه"}, {"text":"📁 دسته‌بندی سرودها"}],
            [{"text":"🎵 یک سرود برام انتخاب کن"}],
            [{"text":"📩 وعده‌های خدا"}, {"text":"💡 دانستنی‌های جالب"}],
        ],
        "resize_keyboard": True
    }

def welcome(chat_id):
    send_msg(chat_id, "✨ شالوم بر شما فرزندان نور\nبه ربات «کلمه‌یاب و سرودیاب» خوش آمدید 🕊️", main_keyboard())

def guide(chat_id):
    send_msg(chat_id, """🕊️ راهنمای ربات:
عزیزان و همراهان در مسیح، برای بنای بیشتر از این خدمت، به نکات زیر توجه کنید:

🌱 بذر کلام: کافیست نام کلمه‌ای (مثلاً: ابا) را بفرستید تا ریشه و معنای آن در کتاب‌مقدس برایتان آشکار شود.
🎶 پرستش: نوشتن کلمه «سرود» پیش از نام آن.
🙌 اتحاد در دعا: بارهای خود را با نوشتن «دعا:» با ما سهیم شوید.

⚠️ در برخی مواقع ممکن است اولین پاسخ چند لحظه زمان ببرد. سپاس از شکیبایی شما 🙏""")

def channel(chat_id):
    send_msg(chat_id, "عضویت در کانال رسمی برای دسترسی به آرشیو بزرگ مسیحی:",
        {"inline_keyboard":[[{"text":"📣 ورود به کانال","url":CHANNEL_URL}]]})

def handle_file(msg):
    chat_id = msg["chat"]["id"]
    for kind, icon in [("document","📄"),("audio","🎵"),("voice","🎙")]:
        if kind in msg:
            file_id = msg[kind]["file_id"]
            name = msg[kind].get("file_name","بدون نام")
            send_msg(chat_id, f"{icon} کد فایل دریافت شد:\n\nfile_id:\n{file_id}\n\nنام فایل:\n{name}")
            return True
    return False

def find_word(text):
    for r in sheet("Word"):
        if norm(value(r, "کلمه")) == norm(text):
            return r
    return None

def word_result(chat_id, text):
    w = find_word(text)
    if not w:
        send_msg(chat_id, "🔍 کلمه مورد نظر یافت نشد. خادمین شما در حال گسترش آرشیو هستند.")
        return

    testament = value(w, "عهد")
    root = "💡 ریشه یونانی" if testament == "NT" else "💡 ریشه عبری"

    send_msg(chat_id, f"🔍 اطلاعات کلمه «{value(w, 'کلمه')}» یافت شد:",
        {"inline_keyboard":[
            [{"text":"📜 آیه مرتبط","callback_data":f"wverse|{text}"}],
            [{"text":"📖 معنی","callback_data":f"wmean|{text}"}],
            [{"text":root,"callback_data":f"wroot|{text}"}],
        ]})

def library(chat_id):
    books = [r for r in sheet("Library") if value(r, "اسم کتاب") and value(r, "فایل")]
    if not books:
        send_msg(chat_id, "📚 هنوز کتابی در کتابخانه ثبت نشده است.")
        return

    buttons = [[{"text":"📖 " + value(b, "اسم کتاب"), "callback_data":f"book|{i}"}] for i,b in enumerate(books)]
    send_msg(chat_id, "📚 کتاب مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})

def categories(chat_id):
    buttons = [[{"text": c, "callback_data": f"cat|{c}"}] for c in SONG_CATEGORIES]
    send_msg(chat_id, "🎵 مناسبت مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})

def random_song(chat_id):
    songs = [r for r in sheet("Songs") if value(r, "اسم سرود") and value(r, "فایل")]
    if not songs:
        send_msg(chat_id, "🎵 هنوز سرودی ثبت نشده است.")
        return

    s = random.choice(songs)
    send_audio(chat_id, value(s, "فایل"), "🎵 " + value(s, "اسم سرود"))

def search_song(chat_id, text):
    name = norm(text.replace("سرود", "", 1))
    for s in sheet("Songs"):
        if norm(value(s, "اسم سرود")) == name:
            send_audio(chat_id, value(s, "فایل"), "🎵 " + value(s, "اسم سرود"))
            return
    send_msg(chat_id, "🎵 سرود مورد نظر یافت نشد.")

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

        text = msg.get("text","").strip()

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
                r for r in sheet("Songs")
                if value(r, "مناسبت") == cat and value(r, "اسم سرود") and value(r, "فایل")
            ]

            if not songs:
                send_msg(chat_id, f"🎵 هنوز سرودی برای این مناسبت ثبت نشده است:\n\n{cat}")
                return "ok"

            buttons = [[{"text":"🎵 " + value(s, "اسم سرود"), "callback_data":f"song|{i}|{cat}"}] for i,s in enumerate(songs)]
            send_msg(chat_id, f"🎵 سرودهای {cat}:", {"inline_keyboard": buttons})

        elif cb.startswith("song|"):
            parts = cb.split("|")
            index = int(parts[1])
            cat = parts[2]

            songs = [
                r for r in sheet("Songs")
                if value(r, "مناسبت") == cat and value(r, "اسم سرود") and value(r, "فایل")
            ]

            s = songs[index]
            send_audio(chat_id, value(s, "فایل"), "🎵 " + value(s, "اسم سرود"))

        elif cb.startswith("w"):
            action, word_text = cb.split("|",1)
            w = find_word(word_text)

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
