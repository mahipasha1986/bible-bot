from flask import Flask, request, jsonify, Response
import requests
import os
import re
import random

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_BASE = "https://square-silence-9274.mahi-pasha1986.workers.dev"
TG = f"https://api.telegram.org/bot{BOT_TOKEN}/"
CHANNEL_URL = "https://t.me/persian_bible"
WEBAPP_URL = "https://bible-bot-4eo2.onrender.com/webapp"

ADMIN_CHAT_ID = "987273459"

SONG_CATEGORIES = [
    {"button": "سرودهای عید قیام", "value": "عید قیام", "category_id": 1},
    {"button": "سرودهای تولد مسیح", "value": "تولد مسیح", "category_id": 2},
    {"button": "سرودهای جمعه صلیب", "value": "جمعه صلیب", "category_id": 3},
]

SONGS_PER_PAGE = 20
CACHE = {}

PRAYER_STATES = {}
PENDING_PRAYERS = {}


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


def get_user_name(user):
    first = (user.get("first_name") or "").strip()
    last = (user.get("last_name") or "").strip()
    username = (user.get("username") or "").strip()

    full_name = (first + " " + last).strip()
    if full_name:
        return full_name
    if username:
        return "@" + username
    return "کاربر"


def main_keyboard():
    return {
        "keyboard": [
            [{"text": "🌍 پلتفرم کلام حیات"}],
            [{"text": "🎵 یک سرود برام انتخاب کن"}],
            [{"text": "📩 وعده‌های خدا"}, {"text": "💡 دانستنی‌های جالب"}],
            [{"text": "📣 کانال"}, {"text": "⚠️ راهنما"}],
        ],
        "resize_keyboard": True
    }


def welcome(chat_id):
    text = "✨ شالوم بر شما فرزندان نور\nبه ربات «کلام حیات» خوش آمدید 🕊️"
    send_msg(chat_id, text, main_keyboard())


def guide(chat_id):
    send_msg(chat_id, """⚠️ راهنمای ربات

به ربات «کلام حیات» خوش آمدید 🕊️

برای ورود به App سرودها و کتابخانه، از منوی اصلی روی دکمه «🕊️ بخش سرودها و کتابخانه» بزنید.
در این بخش می‌توانید:
🎵 سرودهای پرستشی را بر اساس دسته‌بندی مشاهده کنید
🔍 نام سرود را جستجو کنید
▶️ سرود را داخل App پخش کنید
📩 سرود را در تلگرام دریافت کنید
📚 کتاب‌های موجود را مشاهده و دریافت کنید

📖 از منوی اصلی روی «📖 کلمات کتاب مقدس» بزنید.
سپس نام کلمه، مکان یا شخصیت مورد نظر را ارسال کنید.

🙏 دعا:
برای ثبت درخواست دعا، متن خود را بعد از «دعا:» بنویسید.
مثال:
دعا: برای آرامش خانواده‌ام

⚠️ در برخی مواقع ممکن است اولین پاسخ چند لحظه زمان ببرد. سپاس از شکیبایی شما.""")


def channel(chat_id):
    send_msg(chat_id, "عضویت در کانال رسمی برای دسترسی به آرشیو بزرگ مسیحی:",
             {"inline_keyboard": [[{"text": "📣 ورود به کانال", "url": CHANNEL_URL}]]})


def songs_menu(chat_id):
    send_msg(
        chat_id,
        "برای ورود به پلتفرم کلام حیات روی دکمه زیر کلیک کنید",
        {"inline_keyboard": [[
            {"text": "🌍 ورود به پلتفرم کلام حیات",
             "web_app": {"url": WEBAPP_URL}}
        ]]}
    )


def word_instruction(chat_id):
    send_msg(chat_id, "نام کلمه مورد نظر را بنویسید.")


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


def get_all_songs():
    try:
        rows = requests.get(f"{API_BASE}/hymns", timeout=10).json()
    except Exception:
        rows = []

    return [
        r for r in rows
        if r.get("title") and r.get("audio_file_id") and r.get("is_active", True)
    ]


def get_category_songs():
    try:
        rows = requests.get(f"{API_BASE}/hymns", timeout=10).json()
    except Exception:
        rows = []

    return [
        r for r in rows
        if r.get("title") and r.get("audio_file_id") and r.get("is_active", True)
    ]


def get_library_books():
    try:
        rows = requests.get(f"{API_BASE}/books", timeout=10).json()
    except Exception:
        rows = []

    return [
        r for r in rows
        if r.get("title") and r.get("file_id") and r.get("is_active", True)
    ]


def random_song(chat_id):
    songs = get_all_songs()

    if not songs:
        send_msg(chat_id, "🎵 هنوز سرودی ثبت نشده است.")
        return

    s = random.choice(songs)
    send_audio(chat_id, s.get("audio_file_id"), "🎶\n\nاین سرود تقدیم به شما\n🎶 " + s.get("title", ""))


@app.route("/api/songs", methods=["GET"])
def api_songs():
    rows = get_all_songs()
    songs = []

    for i, r in enumerate(rows):
        songs.append({
            "index": i,
            "name": r.get("title", "")
        })

    return jsonify({"ok": True, "songs": songs})


@app.route("/api/category/<int:cat_index>", methods=["GET"])
def api_category(cat_index):
    if cat_index < 0 or cat_index >= len(SONG_CATEGORIES):
        return jsonify({"ok": False, "songs": []})

    rows = get_category_songs()
    songs = []

    for i, r in enumerate(rows):
        if r.get("category_id") == SONG_CATEGORIES[cat_index]["category_id"]:
            songs.append({
                "index": i,
                "name": r.get("title", "")
            })

    return jsonify({
        "ok": True,
        "title": SONG_CATEGORIES[cat_index]["button"],
        "songs": songs
    })


@app.route("/api/send_song", methods=["POST"])
def api_send_song():
    data = request.get_json() or {}

    chat_id = data.get("chat_id")
    index = data.get("index")
    source = data.get("source", "songs")

    if not chat_id or index is None:
        return jsonify({"ok": False})

    try:
        index = int(index)
    except:
        return jsonify({"ok": False})

    rows = get_category_songs() if source == "category" else get_all_songs()

    if index < 0 or index >= len(rows):
        return jsonify({"ok": False})

    s = rows[index]

    send_audio(
        chat_id,
        s.get("audio_file_id"),
        "🎶 این سرود تقدیم به شما\n\n🎵 " + s.get("title", "")
    )

    return jsonify({"ok": True})


@app.route("/api/audio", methods=["GET"])
def api_audio():
    source = request.args.get("source", "songs")
    index = request.args.get("index")

    if index is None:
        return Response("missing index", status=400)

    try:
        index = int(index)
    except:
        return Response("bad index", status=400)

    rows = get_category_songs() if source == "category" else get_all_songs()

    if index < 0 or index >= len(rows):
        return Response("not found", status=404)

    file_id = rows[index].get("audio_file_id")

    if not file_id:
        return Response("file not found", status=404)

    try:
        file_info = requests.get(TG + "getFile", params={"file_id": file_id}, timeout=15).json()

        if not file_info.get("ok"):
            return Response("telegram getFile failed", status=502)

        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        range_header = request.headers.get("Range")
        headers = {}

        if range_header:
            headers["Range"] = range_header

        telegram_response = requests.get(
            file_url,
            headers=headers,
            stream=True,
            timeout=30
        )

        content_type = telegram_response.headers.get("Content-Type", "audio/mpeg")

        response_headers = {
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600"
        }

        if telegram_response.headers.get("Content-Length"):
            response_headers["Content-Length"] = telegram_response.headers.get("Content-Length")

        if telegram_response.headers.get("Content-Range"):
            response_headers["Content-Range"] = telegram_response.headers.get("Content-Range")

        status_code = 206 if telegram_response.status_code == 206 else 200

        return Response(
            telegram_response.iter_content(chunk_size=32768),
            status=status_code,
            headers=response_headers
        )

    except Exception as e:
        print("Audio stream error:", e)
        return Response("audio stream error", status=500)


@app.route("/api/random_song", methods=["POST"])
def api_random_song():
    data = request.get_json() or {}
    chat_id = data.get("chat_id")

    if not chat_id:
        return jsonify({"ok": False})

    songs = get_all_songs()

    if not songs:
        return jsonify({"ok": False})

    s = random.choice(songs)

    send_audio(
        chat_id,
        s.get("audio_file_id"),
        "🎶 این سرود تقدیم به شما\n\n🎵 " + s.get("title", "")
    )

    return jsonify({"ok": True})


@app.route("/api/books", methods=["GET"])
def api_books():
    rows = get_library_books()
    books = []

    for i, r in enumerate(rows):
        books.append({
            "index": i,
            "name": r.get("title", ""),
            "author": r.get("author", ""),
            "description": r.get("description", ""),
            "cover_url": r.get("cover_url", "")
        })

    return jsonify({"ok": True, "books": books})


@app.route("/api/send_book", methods=["POST"])
def api_send_book():
    data = request.get_json() or {}

    chat_id = data.get("chat_id")
    index = data.get("index")

    if not chat_id or index is None:
        return jsonify({"ok": False})

    try:
        index = int(index)
    except:
        return jsonify({"ok": False})

    books = get_library_books()

    if index < 0 or index >= len(books):
        return jsonify({"ok": False})

    b = books[index]

    send_doc(
        chat_id,
        b.get("file_id"),
        "📚 " + b.get("title", "")
    )

    return jsonify({"ok": True})


@app.route("/webapp", methods=["GET"])
def webapp():
    return """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>کلام حیات</title>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lalezar&family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
body{
    margin:0;
    font-family:'Vazirmatn',sans-serif;
    background:#f7f9fc;
    color:#222;
    padding:18px;
    text-align:center;
}
.card{
    background:#ffffff;
    border:1px solid #e8edf3;
    border-radius:26px;
    padding:12px 14px;
    margin-bottom:8px;
    box-shadow:0 8px 24px rgba(31,78,121,0.08);
}
.home-hero{
    background:
        linear-gradient(135deg, rgba(31,78,121,0.95), rgba(17,24,39,0.92)),
        radial-gradient(circle at top left, rgba(255,255,255,0.22), transparent 35%);
    color:white;
    border-radius:30px;
    padding:34px 22px;
    margin-bottom:18px;
    box-shadow:0 18px 45px rgba(31,78,121,0.25);
}

.home-hero h1{
    color:white;
    font-size:46px;
    margin-bottom:8px;
}

.home-hero p,
.home-hero .small{
    color:rgba(255,255,255,0.86);
}

.quick-grid{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:12px;
    margin-top:18px;
}

.quick-card{
    background:rgba(255,255,255,0.14);
    border:1px solid rgba(255,255,255,0.22);
    border-radius:22px;
    padding:16px 10px;
    color:white;
    font-weight:800;
}
.hero-card{
    background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%);
    padding:40px 24px;
    border:none;
    box-shadow:0 12px 40px rgba(0,0,0,0.08);
    margin-bottom:20px;
}
h1{
    font-family:'Lalezar','Vazirmatn',sans-serif;
    font-size:42px;
    font-weight:400;
    color:#111827;
    line-height:1.4;
    margin:8px 0 16px;
}

h2{
    font-family:'Lalezar','Vazirmatn',sans-serif;
    font-size:34px;
    font-weight:400;
    color:#111827;
    line-height:1.5;
    margin:8px 0 18px;
}

p{
    line-height:2;
    font-size:18px;
    color:#4b5563;
}
button{
    width:100%;
    padding:13px;
    margin-top:10px;
    border:none;
    border-radius:18px;
    font-size:18px;
    font-weight:700;
    cursor:pointer;

    box-shadow:
    0 6px 18px rgba(0,0,0,0.08);

    transition:all .25s ease;
}
.red{background:linear-gradient(135deg,#ff416c,#ff4b2b);}
.blue{
    background:linear-gradient(
        135deg,
        #1f4e79,
        #3b82c4
    );
    color:white;
}
.green{
    background:linear-gradient(135deg,#1f4e79,#3d7fc0);
    color:white;
    box-shadow:0 6px 18px rgba(31,78,121,0.25);
}
.gold{
    background:linear-gradient(135deg,#1f4e79,#2d6aa0);
    color:white;
    border:none;
    border-radius:18px;
    padding:16px 22px;
    box-shadow:0 8px 24px rgba(31,78,121,0.25);
    transition:all 0.25s ease;
}

.gold:hover{
    transform:translateY(-2px);
    box-shadow:0 12px 32px rgba(31,78,121,0.35);
}
.secondary{
    background:white;
    color:#1f4e79;
    border:2px solid #1f4e79;
    box-shadow:0 4px 12px rgba(0,0,0,0.08);
}
.ency-btn{
    background:#ffffff;
    color:#1f4e79;
    border:2px solid #1f4e79;
    border-radius:18px;
    padding:15px;
    margin-top:10px;
    font-size:18px;
    font-weight:800;
    box-shadow:0 4px 14px rgba(31,78,121,0.08);
}

.ency-result{
    background:#f8fafc;
    border-radius:20px;
    padding:20px;
    margin-top:16px;
    text-align:center;
    line-height:2.2;
    color:#374151;
}
.purple{background:linear-gradient(135deg,#8e2de2,#4a00e0);}
input{
  width:100%;
  box-sizing:border-box;
  padding:15px;
  border-radius:18px;
  border:1px solid #dedee6;
  background:#ffffff;
  color:#222;
  margin-top:12px;
  font-size:16px;
  text-align:right;
  outline:none;
}
input::placeholder{color:#999;}
.song-item, .book-item{
    background:#ffffff;
    border:1px solid #e7e7ec;
    padding:16px;
    border-radius:18px;
    margin-top:12px;
    cursor:pointer;
    text-align:right;
    color:#333;
    box-shadow:0 4px 12px rgba(0,0,0,0.05);
}
.song-item:hover,
.book-item:hover{
    background:#fafafa;
    border-color:#d4d4dc;
    transform:translateY(-1px);
    transition:all .2s ease;
}
.small{
    font-size:16px;
    color:#6b7280;
    line-height:2;
}
.player-card{
  display:none;
  background:#ffffff;
  border:1px solid #e7e7ec;
  border-radius:22px;
  padding:16px;
  margin-top:16px;
  text-align:right;
  box-shadow:0 4px 12px rgba(0,0,0,0.05);
}
.player-title{
  font-size:16px;
  font-weight:bold;
  margin-bottom:12px;
  color:#2c2c2c;
}
audio{
  width:100%;
  margin-top:10px;
}
.player-actions{
  display:flex;
  gap:10px;
  margin-top:10px;
}
.player-actions button{
  flex:1;
  font-size:14px;
  padding:13px;
}
.tab-buttons{
    display:flex;
    gap:8px;
    margin-bottom:14px;
    overflow-x:auto;
    padding:8px;
    background:rgba(255,255,255,0.85);
    border:1px solid #e8edf3;
    border-radius:22px;
    box-shadow:0 8px 24px rgba(31,78,121,0.08);
}

.tab-buttons button{
    flex:none;
    min-width:140px;
    font-size:14px;
    white-space:nowrap;
}
.top-home-btn{
    width:auto !important;
    min-width:auto;
    padding:8px;
    border-radius:0;
    background:transparent;
    color:#1f4e79;
    border:none;
    font-size:15px;
    font-weight:800;
    box-shadow:none;
}
.compact-btn{
    width:auto !important;
    display:inline-block;
    padding:10px 24px;
    border-radius:999px;
    font-size:15px;
    font-weight:800;
    margin:8px 6px;
}
.home-menu-grid{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:12px;
    margin-top:18px;
}

.home-menu-btn{
    width:100%;
    min-height:74px;
    background:white;
    color:#1f4e79;
    border:2px solid #dbe7f3;
    border-radius:22px;
    padding:14px 10px;
    font-size:15px;
    font-weight:900;
    box-shadow:0 10px 26px rgba(31,78,121,.08);
    display:flex;
    align-items:center;
    justify-content:center;
    text-align:center;
    line-height:1.7;
}

.home-menu-btn:hover{
    border-color:#1f4e79;
    transform:translateY(-2px);
    box-shadow:0 14px 32px rgba(31,78,121,.16);
}
.daily-verse-card{
    background:
        linear-gradient(rgba(0,0,0,.45), rgba(0,0,0,.45)),
        url('https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1200');
    background-size:cover;
    background-position:center;
    border-radius:28px;
    padding:35px 25px;
    text-align:center;
    color:white;
    box-shadow:0 12px 30px rgba(31,78,121,.25);
}

.daily-verse-card *{
    color:white !important;
}
.encyclopedia-btn{
    width:auto !important;
    display:inline-block;
    padding:12px 28px;
    border-radius:999px;
    font-size:15px;
    font-weight:700;
}
.encyclopedia-card{
    background:linear-gradient(135deg,#ffffff,#f7fafc);
    border:1px solid #e6edf5;
    padding:24px 25px;
    text-align:center;
}

.encyclopedia-card h2{
    font-size:28px;
    margin-bottom:12px;
}

.encyclopedia-card p{
    color:#667085;
    line-height:2;
    max-width:700px;
    margin:0 auto 14px;
}
.verse-actions{
    display:flex;
    justify-content:center;
    gap:34px;
    margin-top:26px;
}

.verse-actions button{
    width:auto !important;
    background:transparent;
    box-shadow:none;
    border:none;
    color:white;
    font-size:30px;
    padding:0;
    margin:0;
}

.verse-actions span{
    display:block;
    font-size:13px;
    margin-top:4px;
    font-weight:500;
    opacity:.9;
}
.verse-actions svg{
    width:28px;
    height:28px;
    display:block;
    margin:0 auto 6px;
    fill:none;
    stroke:white;
    stroke-width:2;
    stroke-linecap:round;
    stroke-linejoin:round;
}

.verse-actions button:hover{
    transform:translateY(-2px);
    opacity:.9;
}
.section{
  display:none;
}
.section.active{
  display:block;
}
</style>
</head>
<body>

<div class="tab-buttons">

    <button class="top-home-btn" onclick="location.reload()">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 10.5L12 3l9 7.5"></path>
            <path d="M5 9.5V21h14V9.5"></path>
        </svg>
    </button>

</div>

<div id="homeSection" class="section active">

<div class="card hero-card">

<h1>کلام حیات</h1>

<p>
هر روز یک قدم نزدیکتر به خدا
</p>

<div class="small">
مسیر روزانه‌ای برای رشد ایمان، پرستش و شناخت عمیق‌تر خدا
</div>

<div onclick="showSection('bibleSection')" style="
display:flex;
align-items:center;
justify-content:space-between;
padding:11px 0;
cursor:pointer;
border-bottom:1px solid #ececec;
direction:rtl;
">

<div style="display:flex;align-items:center;gap:12px;">

<svg width="20" height="20" viewBox="0 0 24 24" fill="none"
stroke="#1f4e79" stroke-width="2"
stroke-linecap="round"
stroke-linejoin="round">
<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
<path d="M6.5 2H20v15H6.5A2.5 2.5 0 0 0 4 19.5V4.5A2.5 2.5 0 0 1 6.5 2z"/>
</svg>

<span style="
font-size:17px;
font-weight:600;
color:#222;
">
مطالعه کتاب مقدس
</span>

</div>

<span style="
font-size:22px;
color:#999;
">
›
</span>

</div>

</div>

<div class="card daily-verse-card">
  <h2>آیه روز</h2>
  <div id="homeDailyVerse" class="small">
    در انتظار دریافت آیه روز...
  </div>
</div>

<div class="card encyclopedia-card">
  <h2>دانشنامه کتاب مقدس</h2>
  <p>
    جستجو در میان شخصیت‌ها، مکان‌ها،
    واژه‌ها و مفاهیم کتاب مقدس 
  </p>
  <button class="gold encyclopedia-btn" onclick="showBibleEncyclopedia()">
    ورود به دانشنامه
  </button>
  
  </div>

 <div class="home-menu-grid">

     <button class="home-menu-btn" onclick="showSection('songsSection'); loadSongs();">
        سرودهای پرستشی
    </button>

    <button class="home-menu-btn" onclick="showSection('librarySection')">
        کتابخانه مسیحی
    </button>

    <button class="home-menu-btn" onclick="alert('کتاب مقدس صوتی به‌زودی اضافه می‌شود')">
        کتاب مقدس صوتی
    </button>

    <button class="home-menu-btn" onclick="alert('بازی‌ها و آزمون‌های کتاب مقدس به‌زودی اضافه می‌شود')">
        بازی‌ها و آزمون‌های کتاب مقدس
    </button>
    
</div>

</div>

<div id="songsSection" class="section">

<div
    style="
    background:
    linear-gradient(rgba(0,0,0,.45), rgba(0,0,0,.45)),
    url('https://images.unsplash.com/photo-1514119412350-e174d90d280e?w=1200');
    background-size:cover;
    background-position:center;
    border-radius:24px;
    padding:60px 24px;
    color:white;
    text-align:center;
    margin-bottom:20px;
">

    <h1 style="color:white;margin-bottom:14px;">
        سرودهای پرستشی
    </h1>

    <div style="
        font-size:18px;
        line-height:1.9;
        opacity:.95;
    ">
        مجموعه‌ای از سرودهای پرستشی
    </div>

</div>

    <button onclick="loadCategory(0)" style="background:#1f4e79;color:white;border:none;border-radius:999px;padding:12px
    22px;font-size:15px;font-weight:bold;cursor:pointer;width:auto;display:inline-block;margin:6px;box-shadow:0 8px 18px
    rgba(31,78,121,.18);">
         سرودهای عید قیام
    </button>

    <button onclick="loadCategory(1)" style="background:#1f4e79;color:white;border:none;border-radius:999px;padding:12px
    22px;font-size:15px;font-weight:bold;cursor:pointer;width:auto;display:inline-block;margin:6px;box-shadow:0 8px 18px
    rgba(31,78,121,.18);">
         سرودهای تولد مسیح
    </button>

    <button onclick="loadCategory(2)" style="background:#1f4e79;color:white;border:none;border-radius:999px;padding:12px
    22px;font-size:15px;font-weight:bold;cursor:pointer;width:auto;display:inline-block;margin:6px;box-shadow:0 8px 18px
    rgba(31,78,121,.18);">
         سرودهای جمعه صلیب
    </button>

    <button onclick="loadSongs()" style="background:#1f4e79;color:white;border:none;border-radius:999px;padding:12px
    22px;font-size:15px;font-weight:bold;cursor:pointer;width:auto;display:inline-block;margin:6px;box-shadow:0 8px 18px
    rgba(31,78,121,.18);">
        آرشیو سرودهای پرستشی
    </button>

<div class="card">
  <input id="search" placeholder="جستجوی نام سرود..." oninput="filterSongs()">
  <div id="status" class="small"></div>

  <div id="playerCard" class="player-card">
    <div id="playerTitle" class="player-title">نام سرود</div>
    <audio id="audioPlayer" controls></audio>
    <div class="player-actions">
      <button class="green" onclick="sendSelectedSong()">📩 ارسال در تلگرام</button>
      <button class="red" onclick="closePlayer()">بستن</button>
    </div>
  </div>

  <div id="songs"></div>
</div>

</div>

<div id="librarySection" class="section">

<div
    style="
    background:
    linear-gradient(rgba(0,0,0,.45), rgba(0,0,0,.45)),
    url('https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=1200');
    background-size:cover;
    background-position:center;
    border-radius:24px;
    padding:60px 24px;
    color:white;
    text-align:center;
">

    <h1 style="color:white;margin-bottom:14px;">
        کتابخانه مسیحی
    </h1>

    <div style="
        font-size:18px;
        line-height:1.9;
        margin-bottom:24px;
        opacity:.95;
    ">
        کتاب‌هایی برای رشد ایمان،
        شاگردی و شناخت عمیق‌تر خدا
    </div>

    <button
        onclick="loadBooks()"
        style="
            background:#1f4e79;
            color:white;
            border:none;
            border-radius:30px;
            padding:12px 28px;
            font-size:16px;
            font-weight:bold;
            cursor:pointer;
            width:auto;
            display:inline-block;
            margin-top:10px;
        ">
         مشاهده کتاب‌ها
    </button>

</div>

<div class="card">
  <input id="bookSearch" placeholder="جستجوی نام کتاب..." oninput="filterBooks()">
  <div id="bookStatus" class="small"></div>
  <div id="books"></div>
</div>

</div>

<div id="bibleSection" class="section">

    <div id="bibleHero" class="card hero-card" style="
    background:
    linear-gradient(rgba(8,20,40,.65),rgba(8,20,40,.65)),
    url('https://images.unsplash.com/photo-1504052434569-70ad5836ab65?w=1200');
    background-size:cover;
    background-position:center;
    color:white;
    text-align:center;
    padding:60px 24px;
    ">

        <h1 style="color:white;margin-bottom:14px;">
            مطالعه کتاب مقدس
        </h1>

        <div style="
        font-size:18px;
        line-height:1.9;
        max-width:700px;
        margin:auto;
        ">
            کلام تو برای پاهای من چراغ است
            <br>
            و برای راه من نور
        </div>

        <div style="
        margin-top:20px;
        font-size:14px;
        opacity:.85;
        ">
            مزمور ۱۱۹:۱۰۵
        </div>

    </div>

    <div id="bibleTestamentCards" class="card" style="padding:14px 18px;">

        <div style="display:flex; gap:8px; margin-bottom:12px;">
            <input
                id="bibleSearchInput"
                type="text"
                placeholder="جستجو در کتاب مقدس..."
                onkeydown="if(event.key==='Enter') searchBibleVerse()"
                style="flex:1; padding:11px 12px; border-radius:14px; border:1px solid #dbe7f3; direction:rtl; font-size:14px"
            >
            
        </div>

        <div onclick="loadBibleBooks('old')" style="
            display:flex;
            align-items:center;
            justify-content:space-between;
            padding:13px 0;
            cursor:pointer;
            direction:rtl;
            border-bottom:1px solid #eee;
        ">
            <div style="display:flex; align-items:center; gap:10px;">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                     stroke="#1f4e79" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                    <path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15z"></path>
                </svg>
                <span style="font-size:17px; font-weight:700; color:#222;">
                    عهد عتیق
                </span>
            </div>
            
            <span style="font-size:22px; color:#999;">›</span>
        </div>

        <div onclick="loadBibleBooks('new')" style="
            display:flex;
            align-items:center;
            justify-content:space-between;
            padding:13px 0;
            cursor:pointer;
            direction:rtl;
        ">
            <div style="display:flex; align-items:center; gap:10px;">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                     stroke="#1f4e79" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 6h6a4 4 0 0 1 4 4v12a4 4 0 0 0-4-4H2V6z"></path>
                    <path d="M22 6h-6a4 4 0 0 0-4 4v12a4 4 0 0 1 4-4h6V6z"></path>
                </svg>
                <span style="font-size:17px; font-weight:700; color:#222;">
                    عهد جدید
                </span>
            </div>
            
            <span style="font-size:22px; color:#999;">›</span>
        </div>

    </div>

    <div id="bibleTools" style="display:none;"></div>

    <div class="card">
        <div id="bibleContent">
        </div>
    </div>

</div>

<script>
Telegram.WebApp.ready();
Telegram.WebApp.expand();

let allSongs = [];
let currentSource = "songs";
let currentPage = 0;
const songsPerPage = 30;
let selectedSong = null;

let allBooks = [];

let currentBibleTestament = "old";

async function searchBibleVerse(){

    const input = document.getElementById("bibleSearchInput");
    const bibleContent = document.getElementById("bibleContent");

    const q = input.value.trim();

    if(!q){
        bibleContent.innerHTML = "لطفاً عبارت جستجو را وارد کنید";
        return;
    }

    bibleContent.innerHTML = "⏳ در حال جستجو...";

    try{

        const res = await fetch(
            "https://square-silence-9274.mahi-pasha1986.workers.dev/bible/search?q=" + encodeURIComponent(q)
        );

        const results = await res.json();

        bibleContent.innerHTML = `

            ${results.map(v => `
                <div style="
                    border-right:3px solid #111;
                    padding:0 16px 24px 0;
                    margin:0 0 24px 0;
                    text-align:right;
                    direction:rtl;
                ">
                   <div style="
                       font-size:18px;
                       line-height:2.3;
                       color:#222;
                       margin-bottom:12px;
                   ">
                       ${v.verse_text}
                   </div>

                   <div style="
                       font-size:16px;
                       font-weight:700;
                       color:#333;
                   ">
                       ${v.bible_books?.name_fa || ""} ${v.chapter_number}:${v.verse_number}
                   </div>
               </div>
            `).join("")}
        `;

    }catch(err){
        bibleContent.innerHTML = "❌ خطا در جستجو";
    }
}

async function addBookmark(verseId){

    const userId = Telegram.WebApp.initDataUnsafe.user?.id;

    if(!userId){
        alert("کاربر شناسایی نشد");
        return;
    }

    try{

        const res = await fetch(
            `https://square-silence-9274.mahi-pasha1986.workers.dev/bible/bookmarks/add?user_id=${userId}&verse_id=${verseId}`
        );

        const data = await res.json();

        alert("✅ آیه ذخیره شد");

    }catch(err){

        alert("❌ خطا در ذخیره آیه");

    }
}

async function loadDailyVerse(){

    const homeDailyVerse = document.getElementById("homeDailyVerse");

    if(!homeDailyVerse){
        return;
    }

    homeDailyVerse.innerHTML = "در حال دریافت آیه روز...";

    try{

        const res = await fetch(
            "https://square-silence-9274.mahi-pasha1986.workers.dev/bible/daily-verse"
        );

        const data = await res.json();
        const verse = data[0];

        window.currentDailyVerseId = verse.id;

        homeDailyVerse.innerHTML = `
       <div style="line-height:2.2; text-align:center;">

          <div style="display:inline-block; padding:8px 18px; border-radius:999px; background:rgba(255,255,255,.16); font-size:20px; font-weight:700; margin-bottom:20px;">
              ${verse.bible_books?.name_fa || ""} ${verse.chapter_number}:${verse.verse_number}
          </div>

          <div style="font-size:20px; max-width:700px; margin:auto;">
              ${verse.verse_text}
          </div>

          <div class="verse-actions">
              <button onclick="likeDailyVerse()">
                  <svg viewBox="0 0 24 24">
                      <path d="M20.8 4.6c-1.8-1.7-4.6-1.6-6.3.2L12 7.3 9.5 4.8C7.8 3 5 2.9 3.2 4.6c-2 1.9-2.1 5-.2 7l9 8.8 9-8.8c1.9-2 1.8-5.1-.2-7z"/>
                  </svg>
                  <span>پسندیدن</span>
                  <span id="dailyVerseLikeCount">0 نفر</span>
              </button>

          </div>

      </div>
      `;

      await loadDailyVerseLikes(verse.id);

    }catch(err){
        homeDailyVerse.innerHTML = "خطا در دریافت آیه روز";
    }
}

async function likeDailyVerse(){

    const userId = Telegram.WebApp.initDataUnsafe.user?.id;

    if(!userId){
        return;
    }

    const verseId = window.currentDailyVerseId;

    const res = await fetch(
        `https://square-silence-9274.mahi-pasha1986.workers.dev/bible/daily-verse/like?user_id=${userId}&verse_id=${verseId}`
    );

    const data = await res.json();

    document.getElementById("dailyVerseLikeCount").innerText =
        ((data.likes ?? data.length) || 0) + " نفر";
}

async function loadDailyVerseLikes(verseId){

    const res = await fetch(
        `https://square-silence-9274.mahi-pasha1986.workers.dev/bible/daily-verse/likes?verse_id=${verseId}`
    );

    const data = await res.json();

    const count = Array.isArray(data)
        ? data.length
        : Number(data.likes || 0);

    document.getElementById("dailyVerseLikeCount").innerText =
        count + " نفر";
}

async function loadBookmarks(){

    const userId = Telegram.WebApp.initDataUnsafe.user?.id;
    const bibleContent = document.getElementById("bibleContent");

    if(!userId){
        bibleContent.innerHTML = "کاربر شناسایی نشد";
        return;
    }

    bibleContent.innerHTML = "⏳ در حال دریافت آیات ذخیره‌شده...";

    try{

        const res = await fetch(
            `https://square-silence-9274.mahi-pasha1986.workers.dev/bible/bookmarked-verses?user_id=${userId}`
        );

        const verses = await res.json();

        if(!verses.length){
            bibleContent.innerHTML = "هنوز آیه‌ای ذخیره نکرده‌اید.";
            return;
        }

        bibleContent.innerHTML = `
            <div class="small">آیات ذخیره‌شده</div>

            ${verses.map(v => `
                <div style="margin-bottom:14px; line-height:2;">
                    <span style="font-weight:bold;color:#1f4e79;">
                        ${v.chapter_number}:${v.verse_number}
                    </span>
                    ${v.verse_text}
                    <button class="gold" onclick="deleteBookmark(${v.id})" style="margin-top:8px;">
                        🗑 حذف از ذخیره‌ها
                    </button>
                </div>
            `).join("")}
        `;

    }catch(err){
        bibleContent.innerHTML = "❌ خطا در دریافت آیات ذخیره‌شده";
    }
}

async function deleteBookmark(verseId){

    const userId = Telegram.WebApp.initDataUnsafe.user?.id;

    if(!userId){
        alert("کاربر شناسایی نشد");
        return;
    }

    try{
        await fetch(
            `https://square-silence-9274.mahi-pasha1986.workers.dev/bible/bookmarks/delete?user_id=${userId}&verse_id=${verseId}`
        );

        alert("🗑 آیه حذف شد");
        loadBookmarks();

    }catch(err){
        alert("❌ خطا در حذف آیه");
    }
}

async function loadBibleBooks(testament){

    currentBibleTestament = testament;

    const bibleContent = document.getElementById("bibleContent");

    document.getElementById("bibleHero").style.display = "none";
    document.getElementById("bibleTestamentCards").style.display = "none";
    document.getElementById("bibleTools").style.display = "none";

    bibleContent.innerHTML = "⏳ در حال دریافت کتاب‌ها...";

    try{

        const res = await fetch(
            "https://square-silence-9274.mahi-pasha1986.workers.dev/bible/books"
        );

        const books = await res.json();
        console.log("Bible books data:", books);

        let bookList = Array.isArray(books) ? books : (books.books || books.data || []);

        let filtered = bookList;

        if(testament === "old"){
            filtered = bookList.filter(b => b.testament === "OT");
        }

        if(testament === "new"){
            filtered = bookList.filter(b => b.testament === "NT");
        }

        bibleContent.innerHTML = `
            <div style="text-align:right; direction:rtl;">
                ${filtered.map(book => `
                    <div onclick="loadBibleChapters(${book.id}, '${book.name_fa || book.name}')"
                         style="
                            padding:12px 4px;
                            font-size:25px;
                            font-weight:400;
                            color:#111;
                            cursor:pointer;
                         ">
                        ${book.name_fa || book.book_name_fa || book.name || book.title}
                    </div>
                `).join("")}
            </div>
       `;

    }catch(err){

        bibleContent.innerHTML =
            "❌ خطا در دریافت کتاب‌های کتاب مقدس";

    }
}

async function loadBibleChapters(bookId, bookName){

    const bibleContent = document.getElementById("bibleContent");

    document.getElementById("bibleHero").style.display = "none";
    document.getElementById("bibleTestamentCards").style.display = "none";
    document.getElementById("bibleTools").style.display = "none";

    bibleContent.innerHTML = "⏳ در حال دریافت باب‌های " + bookName + "...";

    try{

        const res = await fetch(
            "https://square-silence-9274.mahi-pasha1986.workers.dev/bible/chapters?book_id=" + bookId
        );

        const chapters = await res.json();

        bibleContent.innerHTML = `
        <div style="
            text-align:right;
            font-family:Vazirmatn,sans-serif;
            font-size:22px;
            font-weight:600;
            color:#444;
            margin-bottom:18px;
        ">
            ${bookName}
        </div>

        <div style="
            display:grid;
            grid-template-columns:repeat(5,1fr);
            gap:8px;
        ">

            ${chapters.map(chapter => `
                <div
                    onclick="loadBibleVerses(${bookId}, ${chapter.chapter_number}, '${bookName}', ${chapters.length})"
                    style="
                        background:#efefef;
                        border-radius:12px;
                        height:46px;
                        display:flex;
                        justify-content:center;
                        align-items:center;
                        font-size:18px;
                        font-weight:700;
                        cursor:pointer;
                    ">
                    ${chapter.chapter_number}
                </div>
            `).join("")}

        </div>

        <div
            class="book-item"
            style="margin-top:20px"
            onclick="loadBibleBooks(currentBibleTestament)">
            ← بازگشت به کتاب‌ها
        </div>
        `;

    }catch(err){

        bibleContent.innerHTML = "❌ خطا در دریافت باب‌ها";

    }
}

async function loadBibleVerses(bookId, chapterNumber, bookName, totalChapters){

    const bibleContent = document.getElementById("bibleContent");

    document.getElementById("bibleHero").style.display = "none";
    document.getElementById("bibleTestamentCards").style.display = "none";
    document.getElementById("bibleTools").style.display = "none";

    bibleContent.innerHTML =
        "⌛ در حال دریافت آیات...";

    try{

        const res = await fetch(
            "https://square-silence-9274.mahi-pasha1986.workers.dev/bible/verses?book_id="
            + bookId +
            "&chapter_number=" +
            chapterNumber
        );

        const verses = await res.json();

        bibleContent.innerHTML = `
            <div style="text-align:center; direction:rtl; margin-bottom:34px;">
                <div style="
                    font-family:Vazirmatn,sans-serif;
                    font-size:15px;
                    font-weight:500;
                    color:#8a8a8a;
                    letter-spacing:0.5px;
                    margin-bottom:6px;
                ">
                    ${bookName}
                </div>

                <div style="
                    font-family:Vazirmatn,sans-serif;
                    font-size:76px;
                    font-weight:800;
                    color:#111;
                    line-height:0.9;
                    letter-spacing:-2px;
                    margin-bottom:34px;
                ">
                    ${chapterNumber}
                </div>
            </div>

            <div style="
                text-align:right;
                direction:rtl;
                font-family:Vazirmatn,sans-serif;
                font-size:17px;
                line-height:2.45;
                font-weight:400;
                color:#2b2b2b;
                padding:0 22px;
                text-align:right;
                letter-spacing:0;;
            ">
                ${verses.map(v => `
                    <span style="
                        font-size:11px;
                        color:#777;
                        font-weight:600;
                        vertical-align:super;
                        margin-left:5px;
                    ">
                        ${v.verse_number}
                    </span>
                    ${v.verse_text}
                `).join(" ")}
            </div>

            <div style="
                width:220px;
                margin:30px auto 0;
                padding-top:10px;
                border-top:1px solid #eee;
                display:flex;
                align-items:center;
                justify-content:space-between;
                direction:ltr;
            ">
                <div
                    onclick="loadBibleVerses(${bookId}, ${chapterNumber + 1}, '${bookName}', ${totalChapters})"
                    style="
                        font-size:28px;
                        cursor:pointer;
                        visibility:${chapterNumber < totalChapters ? 'visible' : 'hidden'};
                    ">
                    ‹
                </div>

                <div
                    onclick="loadBibleChapters(${bookId}, '${bookName}')"
                    style="
                        font-size:18px;
                        font-weight:700;
                        color:#1f4e79;
                        cursor:pointer;
                    ">
                    ${bookName}
                </div>

                <div
                    onclick="loadBibleVerses(${bookId}, ${chapterNumber - 1}, '${bookName}', ${totalChapters})"
                    style="
                        font-size:28px;
                        cursor:pointer;
                        visibility:${chapterNumber > 1 ? 'visible' : 'hidden'};
                    ">
                    ›
                </div>
                
            </div>
      `;

      bibleContent.scrollIntoView({
          behavior: "smooth",
          block: "start"
      });

    }catch(err){

        bibleContent.innerHTML =
            "❌ خطا در دریافت آیات";

    }
}

function openEncyclopediaEntry(word){

    showBibleEncyclopedia();

    setTimeout(() => {

        const input = document.getElementById("encyclopediaSearchInput");

        if(input){
            input.value = word;
            searchBibleEncyclopedia();
        }

    }, 300);

}

function showBibleEncyclopedia(){

    const homeSection = document.getElementById("homeSection");

    homeSection.innerHTML = `
        <div class="card">
            <h1>دانشنامه کتاب مقدس</h1>
            <p>
                واژه‌ها، شخصیت‌ها، مکان‌ها و مفاهیم مهم کتاب مقدس را در این بخش جستجو و مطالعه کنید.
            </p>
        </div>

        <div class="card">
            <input id="encyclopediaSearchInput"
                   type="text"
                   placeholder="جستجوی واژه، شخصیت یا مکان...">

            <button class="gold compact-btn" onclick="searchBibleEncyclopedia()">
                جستجو در دانشنامه
            </button>

            <div id="encyclopediaContent" class="small">
                این بخش در حال آماده‌سازی است.
            </div>
        </div>

        <button class="secondary compact-btn" onclick="location.reload()">
            بازگشت به خانه
        </button>
    `;

    window.scrollTo({top:0, behavior:"smooth"});
}

async function searchBibleEncyclopedia(){

    const input = document.getElementById("encyclopediaSearchInput");
    const content = document.getElementById("encyclopediaContent");

    const q = input.value.trim();

    if(!q){
        content.innerHTML = "لطفاً یک واژه، شخصیت یا مکان را وارد کنید.";
        return;
    }

    content.innerHTML = "در حال جستجو...";

    try{
        const res = await fetch(
            "https://square-silence-9274.mahi-pasha1986.workers.dev/bible-words"
        );

        const rows = await res.json();

        const results = rows.filter(item =>
            (item.word || "").includes(q) ||
            (item.meaning || "").includes(q) ||
            (item.related_verse || "").includes(q)
        );

        if(!results.length){
            content.innerHTML = "موردی پیدا نشد.";
            return;
        }

        content.innerHTML = results.map((item, index) => `
            <div class="card">

                <h3>${item.word || ""}</h3>

                <button class="ency-btn" onclick="showEncyclopediaPart(${index}, 'meaning')">
                    معنی
                </button>

                <button class="ency-btn" onclick="showEncyclopediaPart(${index}, 'root')">
                    ریشه ${item.root_language || ""}
                </button>

                <button class="ency-btn" onclick="showEncyclopediaPart(${index}, 'verse')">
                    آیه مرتبط
                </button>

                <div id="encyclopediaResult-${index}" class="small">
            یکی از بخش‌های بالا را انتخاب کنید.
        </div>

    </div>
`).join("");

window.encyclopediaResults = results;

    }catch(err){
        content.innerHTML = "خطا در دریافت اطلاعات دانشنامه.";
    }
}

function showEncyclopediaPart(index, type){

    const item = window.encyclopediaResults[index];
    const target = document.getElementById(`encyclopediaResult-${index}`);

    if(!item || !target){
        return;
    }

    if(type === "meaning"){
        target.innerHTML = `
            <div class="ency-result">
                <h4>معنی</h4>
                <p>${item.meaning || "-"}</p>
            </div>
        `;
        return;
    }

    if(type === "root"){
        target.innerHTML = `
            <div class="ency-result">
                <h4>ریشه ${item.root_language || ""}</h4>
                <p>${item.root_text || "-"}</p>
            </div>
        `;
        return;
    }

    if(type === "verse"){

        target.innerHTML = `
            <div class="ency-result">
                <h4>آیه مرتبط</h4>
                <p>در حال دریافت متن آیه...</p>
            </div>
        `;

        fetch("https://square-silence-9274.mahi-pasha1986.workers.dev/bible/search?q=" + encodeURIComponent(item.related_verse || ""))
            .then(res => res.json())
            .then(verses => {

                if(!verses || !verses.length){
                    target.innerHTML = `
                        <div class="ency-result">
                            <h4>آیه مرتبط</h4>
                            <p>${item.related_verse || "-"}</p>
                        </div>
                    `;
                    return;
                }

                target.innerHTML = verses.map(v => `
                    <div class="ency-result">
                        <h4>آیه مرتبط</h4>
                        <p>
                            <strong>${v.chapter_number}:${v.verse_number}</strong>
                            ${v.verse_text || ""}
                        </p>
                    </div>
                `).join("");
            })
            .catch(() => {
                target.innerHTML = `
                    <div class="ency-result">
                        <h4>آیه مرتبط</h4>
                        <p>${item.related_verse || "-"}</p>
                    </div>
                `;
            });

        return;
    }
}
    
function showSection(sectionId){

    document.querySelectorAll(".section").forEach(sec => {
        sec.classList.remove("active");
        sec.style.display = "none";
    });

    const target = document.getElementById(sectionId);
    if(target){
        target.classList.add("active");
        target.style.display = "block";
    }

    window.scrollTo({
        top:0,
        behavior:"smooth"
    });
}

function getChatId(){
  const user = Telegram.WebApp.initDataUnsafe && Telegram.WebApp.initDataUnsafe.user;
  return user ? user.id : null;
}

function setStatus(text){
  document.getElementById("status").innerText = text || "";
}

async function loadSongs(){
  currentSource = "songs";
  closePlayer();
  setStatus("⏳ در حال دریافت لیست سرودها...");

  const res = await fetch("/api/songs");
  const data = await res.json();

  allSongs = data.songs || [];
  currentPage = 0;

  document.getElementById("search").value = "";
  renderPage();

  setStatus("لیست کامل سرودها");
}

async function loadCategory(index){
  currentSource = "category";
  closePlayer();
  setStatus("⏳ در حال دریافت سرودهای مناسبتی...");

  const res = await fetch("/api/category/" + index);
  const data = await res.json();

  allSongs = data.songs || [];
  currentPage = 0;

  document.getElementById("search").value = "";
  renderPage();

  setStatus(data.title || "سرودهای مناسبتی");
}

function renderPage(){
  const start = currentPage * songsPerPage;
  const end = start + songsPerPage;
  const songs = allSongs.slice(start, end);

  renderSongs(songs, true);
}

function renderSongs(songs, showPagination){
  const container = document.getElementById("songs");
  container.innerHTML = "";

  if(!songs.length){
    container.innerHTML = "<div class='small'>موردی پیدا نشد.</div>";
    return;
  }

  songs.forEach(song => {
    const div = document.createElement("div");
    div.className = "song-item";
    div.innerText = "🎵 " + song.name;
    div.onclick = () => openPlayer(song);
    container.appendChild(div);
  });

  if(showPagination){
    renderPagination(container);
  }
}

function renderPagination(container){
  const totalPages = Math.ceil(allSongs.length / songsPerPage);

  if(totalPages <= 1) return;

  const pageInfo = document.createElement("div");
  pageInfo.className = "small";
  pageInfo.innerText = "صفحه " + (currentPage + 1) + " از " + totalPages;
  container.appendChild(pageInfo);

  const nav = document.createElement("div");
  nav.style.marginTop = "12px";
  nav.style.display = "flex";
  nav.style.gap = "10px";

  const prev = document.createElement("button");
  prev.innerText = "➡️ صفحه قبل";
  prev.className = "blue";
  prev.style.flex = "1";
  prev.disabled = currentPage === 0;
  prev.style.opacity = currentPage === 0 ? "0.45" : "1";
  prev.onclick = () => {
    if(currentPage > 0){
      currentPage--;
      closePlayer();
      renderPage();
      window.scrollTo({top: 0, behavior: "smooth"});
    }
  };

  const next = document.createElement("button");
  next.innerText = "صفحه بعد ⬅️";
  next.className = "purple";
  next.style.flex = "1";
  next.disabled = currentPage >= totalPages - 1;
  next.style.opacity = currentPage >= totalPages - 1 ? "0.45" : "1";
  next.onclick = () => {
    if(currentPage < totalPages - 1){
      currentPage++;
      closePlayer();
      renderPage();
      window.scrollTo({top: 0, behavior: "smooth"});
    }
  };

  nav.appendChild(prev);
  nav.appendChild(next);
  container.appendChild(nav);
}

function filterSongs(){
  const q = document.getElementById("search").value.toLowerCase().trim();

  if(!q){
    closePlayer();
    renderPage();
    return;
  }

  const filtered = allSongs.filter(s => (s.name || "").toLowerCase().includes(q));
  renderSongs(filtered.slice(0, 100), false);

  if(filtered.length > 100){
    setStatus("🔍 بیش از ۱۰۰ نتیجه پیدا شد؛ لطفاً دقیق‌تر جستجو کنید.");
  }else{
    setStatus("🔍 نتیجه جستجو: " + filtered.length + " مورد");
  }
}

function openPlayer(song){
  selectedSong = song;

  const playerCard = document.getElementById("playerCard");
  const playerTitle = document.getElementById("playerTitle");
  const audioPlayer = document.getElementById("audioPlayer");

  playerTitle.innerText = "🎵 " + song.name;
  audioPlayer.src = "/api/audio?source=" + currentSource + "&index=" + song.index;

  playerCard.style.display = "block";
  setStatus("🎧 برای پخش، دکمه Play را بزنید.");

  playerCard.scrollIntoView({behavior:"smooth", block:"start"});
}

function closePlayer(){
  const playerCard = document.getElementById("playerCard");
  const audioPlayer = document.getElementById("audioPlayer");

  audioPlayer.pause();
  audioPlayer.removeAttribute("src");
  audioPlayer.load();

  playerCard.style.display = "none";
  selectedSong = null;
}

async function sendSelectedSong(){
  if(!selectedSong){
    setStatus("ابتدا یک سرود را انتخاب کنید.");
    return;
  }

  await sendSong(selectedSong.index);
}

async function sendSong(index){
  const chatId = getChatId();

  if(!chatId){
    alert("لطفاً این صفحه را از داخل تلگرام باز کنید.");
    return;
  }

  setStatus("⏳ در حال ارسال سرود...");

  const res = await fetch("/api/send_song", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      chat_id:chatId,
      index:index,
      source:currentSource
    })
  });

  const data = await res.json();

  if(data.ok){
    setStatus("✅ سرود در تلگرام برای شما ارسال شد.");
  }else{
    setStatus("❌ ارسال سرود انجام نشد.");
  }
}

async function loadBooks(){
  document.getElementById("bookStatus").innerText = "⏳ در حال دریافت کتاب‌ها...";

  const res = await fetch("/api/books");
  const data = await res.json();

  allBooks = data.books || [];

  document.getElementById("bookSearch").value = "";
  renderBooks(allBooks);

  document.getElementById("bookStatus").innerText = "کتابخانه";
}

function renderBooks(books){
  const container = document.getElementById("books");
  container.innerHTML = "";

  if(!books.length){
    container.innerHTML = "<div class='small'>کتابی پیدا نشد.</div>";
    return;
  }

books.forEach(book => {

    const div = document.createElement("div");

    div.className = "book-item";

    div.innerHTML = `
        <div style="
            display:flex;
            gap:12px;
            align-items:center;
            text-align:right;
        ">

            <img
                src="${book.cover_url || 'https://via.placeholder.com/80x120'}"
                style="
                    width:80px;
                    height:120px;
                    object-fit:cover;
                    border-radius:12px;
                    border:1px solid #ddd;
                "
            >

            <div style="flex:1">

                <div style="
                    font-size:18px;
                    font-weight:bold;
                    margin-bottom:6px;
                ">
                    ${book.name}
                </div>

                <div style="
                    color:#666;
                    font-size:14px;
                    margin-bottom:8px;
                ">
                    ${book.author || ""}
                </div>

                <div style="
                    color:#888;
                    font-size:13px;
                    line-height:1.7;
                ">
                    ${book.description || ""}
                </div>

            </div>

        </div>
    `;

    div.onclick = () => showBookDetails(book.index);

    container.appendChild(div);

});
}

function showBookDetails(index){

    const book = allBooks.find(b => b.index === index);
    const container = document.getElementById("books");

    if(!book){
        return;
    }

    container.innerHTML = `
        <div class="card" style="
        background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%);
        border:1px solid #dbe7f3;
        box-shadow:0 18px 45px rgba(31,78,121,0.12);
        ">

            <img
                src="${book.cover_url || 'https://via.placeholder.com/160x220'}"
                style="
                    width:160px;
                    height:220px;
                    object-fit:cover;
                    border-radius:18px;
                    margin-bottom:18px;
                    border:1px solid #ddd;
                "
            >

            <h2>${book.name || ""}</h2>

            <div class="small" style="margin-bottom:18px;">
                ${book.author ? "نویسنده: " + book.author : ""}
            </div>

            <p style="line-height:2; color:#555;">
                ${book.description || ""}
            </p>

            <button class="gold compact-btn" onclick="sendBook(${book.index})">
                دریافت کتاب
            </button>

            <button class="secondary compact-btn" onclick="renderBooks(allBooks)">
                بازگشت به کتابخانه
            </button>

        </div>
    `;
}

function filterBooks(){
  const q = document.getElementById("bookSearch").value.toLowerCase().trim();

  if(!q){
    renderBooks(allBooks);
    return;
  }

  const filtered = allBooks.filter(b => (b.name || "").toLowerCase().includes(q));
  renderBooks(filtered);
}

async function sendBook(index){
  const chatId = getChatId();

  if(!chatId){
    alert("لطفاً این صفحه را از داخل تلگرام باز کنید.");
    return;
  }

  document.getElementById("bookStatus").innerText = "⏳ در حال ارسال کتاب...";

  const res = await fetch("/api/send_book", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      chat_id:chatId,
      index:index
    })
  });

  const data = await res.json();

  if(data.ok){
    document.getElementById("bookStatus").innerText = "✅ کتاب در تلگرام برای شما ارسال شد.";
  }else{
    document.getElementById("bookStatus").innerText = "❌ ارسال کتاب انجام نشد.";
  }
}

loadDailyVerse();

</script>

</body>
</html>
"""


def find_word(text):
    exact = None
    partial = []

    try:
        rows = requests.get(f"{API_BASE}/bible-words", timeout=10).json()
    except Exception:
        rows = []

    for r in rows:
        word = r.get("word") or ""
        normalized = r.get("normalized_word") or word

        if not word:
            continue

        mapped = {
            "کلمه": word,
            "معنی": r.get("meaning") or "",
            "ریشه": r.get("root_text") or "",
            "آیه مرتبط": r.get("related_verse") or "",
            "عهد": "NT" if r.get("root_language") == "یونانی" else "OT",
        }

        if norm(word) == norm(text) or norm(normalized) == norm(text):
            exact = mapped
            break

        if norm(text) in norm(word) or norm(word) in norm(text):
            partial.append(mapped)

    return exact, partial


def word_result(chat_id, text):
    exact, partial = find_word(text)

    if exact:
        w = exact
        root = "💡 ریشه یونانی" if value(w, "عهد") == "NT" else "💡 ریشه عبری"

        send_msg(chat_id, f"🔍 اطلاعات کلمه «{value(w, 'کلمه')}» یافت شد:",
                 {"inline_keyboard": [
                     [{"text": "آیه مرتبط", "callback_data": f"wverse|{value(w, 'کلمه')}"}],
                     [{"text": "معنی", "callback_data": f"wmean|{value(w, 'کلمه')}"}],
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


def search_song(chat_id, text):
    query = norm(text.replace("سرود", "", 1))

    if not query:
        send_msg(chat_id, "🎵 لطفاً بعد از کلمه «سرود» اسم سرود را بنویسید.")
        return

    exact = None
    partial = []

    for s in get_all_songs():
        song_name = s.get("title", "")
        file_id = s.get("audio_file_id", "")

        if not song_name or not file_id:
            continue

        clean_name = norm(song_name + " " + s.get("search_title", ""))


        if query in clean_name:
            partial.append(s)

    results = partial[:20]

    if results:
        buttons = []
        all_songs = get_all_songs()

        for r in results:
            buttons.append([{
                "text": "🎵 " + r.get("title", ""),
                "callback_data": f"allsong|{all_songs.index(r)}"
            }])

        send_msg(
            chat_id,
            f"🎵 نتایج جستجو برای «{query}»:\n\nلطفا سرود مورد نظر را انتخاب کنید:",
            {"inline_keyboard": buttons}
        )
        return

    not_found(chat_id)


def library(chat_id):
    books = get_library_books()

    if not books:
        send_msg(chat_id, "هنوز کتابی در کتابخانه ثبت نشده است.")
        return

    buttons = [
        [{"text": "📖 " + b.get("title", ""), "callback_data": f"book|{i}"}]
        for i, b in enumerate(books)
    ]

    send_msg(chat_id, "کتاب مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})


def song_list(chat_id, page=0):
    songs = get_all_songs()

    if not songs:
        send_msg(chat_id, "هنوز سرودی در لیست ثبت نشده است.")
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
        song_name = songs[i].get("title", "")
        buttons.append([{
            "text": f"🎵 {song_name}",
            "callback_data": f"allsong|{i}"
        }])

    nav = []
    if page > 0:
        nav.append({"text": "صفحه قبل ➡️", "callback_data": f"songpage|{page - 1}"})
    if page < total_pages - 1:
        nav.append({"text": "⬅️ صفحه بعد", "callback_data": f"songpage|{page + 1}"})

    if nav:
        buttons.append(nav)

    buttons.append([{"text": "برگشت ➡️", "callback_data": "songs_menu"}])

    send_msg(
        chat_id,
        f"لیست سرودها — صفحه {page + 1} از {total_pages}\n\nبرای دریافت، روی نام سرود بزنید:",
        {"inline_keyboard": buttons}
    )


def promise(chat_id):
    try:
        rows = requests.get(f"{API_BASE}/promises", timeout=10).json()
    except Exception:
        rows = []

    if not rows:
        send_msg(chat_id, "📩 هنوز وعده‌ای ثبت نشده است.")
        return

    r = random.choice(rows)
    send_msg(
        chat_id,
        f"📩 وعده امروز خداوند برای شما :\n\n✨ {r.get('promise_text','')}\n\n📖 {r.get('verse_reference','')}",
        {"inline_keyboard": [[{"text": "📩 وعده بعدی", "callback_data": "promise_next"}]]}
    )


def fact(chat_id):
    try:
        rows = requests.get(f"{API_BASE}/facts", timeout=10).json()
    except Exception:
        rows = []

    if not rows:
        send_msg(chat_id, "💡 هنوز دانستنی ثبت نشده است.")
        return

    r = random.choice(rows)

    fact_text = r.get("fact_text", "") or r.get("text", "")
    source = r.get("source", "")

    msg = f"💡 آیا می‌دانستید؟\n\n{fact_text}"

    if source:
        msg += f"\n\n📍 منبع: {source}"

    send_msg(
        chat_id,
        msg,
        {"inline_keyboard": [[{"text": "💡 دانستنی بعدی", "callback_data": "fact_next"}]]}
    )
def bible_menu(chat_id):
    send_msg(
        chat_id,
        "بخش کتاب مقدس\n\nیکی از گزینه‌ها را انتخاب کنید:",
        {"inline_keyboard": [
            [{"text": "عهد عتیق", "callback_data": "bible_testament|OT"}],
            [{"text": "عهد جدید", "callback_data": "bible_testament|NT"}],
        ]}
    )


def bible_books(chat_id, testament):
    try:
        rows = requests.get(f"{API_BASE}/bible/books", timeout=10).json()
    except Exception:
        rows = []

    books = [b for b in rows if b.get("testament") == testament]

    if not books:
        send_msg(chat_id, "هنوز کتابی برای این بخش ثبت نشده است.")
        return

    buttons = []
    for b in books:
        buttons.append([{
            "text": b.get("name_fa", ""),
            "callback_data": f"bible_book|{b.get('id')}"
        }])

    send_msg(chat_id, "کتاب مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})


def bible_chapters(chat_id, book_id):
    try:
        rows = requests.get(f"{API_BASE}/bible/chapters?book_id={book_id}", timeout=10).json()
    except Exception:
        rows = []

    if not rows:
        send_msg(chat_id, "هنوز فصلی برای این کتاب ثبت نشده است.")
        return

    buttons = []
    row = []

    for ch in rows:
        row.append({
            "text": str(ch.get("chapter_number")),
            "callback_data": f"bible_chapter|{book_id}|{ch.get('chapter_number')}"
        })

        if len(row) == 5:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    send_msg(chat_id, "باب مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})


def bible_verses(chat_id, book_id, chapter_number):
    try:
        rows = requests.get(
            f"{API_BASE}/bible/verses?book_id={book_id}&chapter_number={chapter_number}",
            timeout=10
        ).json()
    except Exception:
        rows = []

    if not rows:
        send_msg(
            chat_id,
            "آیات این باب به‌زودی اضافه می‌شود.\n\nاین بخش در حال تکمیل است."
        )
        return

    text = f"باب {chapter_number}\n\n"
    for v in rows:
        text += f"{v.get('verse_number')}. {v.get('verse_text')}\n\n"

    send_msg(chat_id, text)

def prayer_menu(chat_id):
    send_msg(chat_id, "یکی از گزینه‌ها را انتخاب کنید 👇",
             {"inline_keyboard": [
                 [{"text": "✍️ درخواست دعا", "callback_data": "prayer_request"}],
                 [{"text": "🙌 دعا برای یکدیگر", "callback_data": "prayer_random"}],
             ]})


def ask_prayer_visibility(chat_id):
    send_msg(
        chat_id,
        "ایمانداران گرامی ، مایل هستید دعای شما به چه صورتی برای دیگران نمایش داده شود؟",
        {"inline_keyboard": [
            [{"text": "🕵 با نام خودم", "callback_data": "prayer_visibility|name"}],
            [{"text": "👤 بصورت ناشناس", "callback_data": "prayer_visibility|anon"}],
        ]}
    )


def receive_prayer_text(chat_id, text, user):
    state = PRAYER_STATES.get(str(chat_id), {})
    visibility = state.get("visibility", "anon")
    user_name = state.get("name", get_user_name(user))

    if visibility == "name":
        display_name = user_name
        public_text = f"از طرف {display_name}: {text}"
    else:
        display_name = "ناشناس"
        public_text = text

    PRAYER_STATES.pop(str(chat_id), None)

    try:
        requests.post(
            f"{API_BASE}/prayers/submit",
            json={
                "prayer_text": public_text,
                "user_name": display_name,
                "is_anonymous": visibility != "name"
            },
            timeout=10
        )
        send_msg(chat_id, "🙏 درخواست دعای شما ثبت شد.")
    except Exception:
        send_msg(chat_id, "متأسفانه ثبت دعا انجام نشد. لطفاً دوباره تلاش کنید.")


def save_prayer(chat_id, text):
    prayer = text.replace("دعا:", "", 1).strip()

    if not prayer:
        send_msg(chat_id, "🙏 لطفاً بعد از «دعا:» متن درخواست دعای خود را بنویسید.")
        return

    try:
        result = requests.post(
            f"{API_BASE}/prayers/submit",
            json={
                "prayer_text": prayer,
                "user_name": "ناشناس",
                "is_anonymous": True
            },
            timeout=10
        ).json()
    except Exception:
        result = {}

    if result:
        send_msg(chat_id, "🙏 درخواست دعای شما ثبت شد و پس از تایید خادمین نمایش داده می‌شود.")
    else:
        send_msg(chat_id, "متأسفانه ثبت دعا انجام نشد. لطفاً دوباره تلاش کنید.")


def random_prayer(chat_id):
    try:
        rows = requests.get(f"{API_BASE}/prayers", timeout=10).json()
    except Exception:
        rows = []

    if not rows:
        send_msg(chat_id, "🙏 هنوز درخواست دعایی ثبت نشده است.")
        return

    r = random.choice(rows)

    prayer_id = r.get("id")
    prayer_text = r.get("prayer_text", "")
    count = r.get("prayer_count", 0)

    send_msg(
        chat_id,
        f"🙏 درخواست دعا:\n\n{prayer_text}\n\n⭕ تا الان {count} نفر برای این دعا، دعا کردند.",
        {"inline_keyboard": [
            [{"text": "🙌 من هم دعا کردم", "callback_data": f"praydone_{prayer_id}"}],
            [{"text": "✍️ ثبت درخواست دعا", "callback_data": "prayer_request"}]
        ]}
    )


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
        user = msg.get("from", {})

        if handle_file(msg):
            return "ok"

        text = msg.get("text", "").strip()

        if str(chat_id) in PRAYER_STATES and PRAYER_STATES[str(chat_id)].get("step") == "awaiting_text":
            receive_prayer_text(chat_id, text, user)
            return "ok"

        if text == "/start":
            welcome(chat_id)
        elif text == "⚠️ راهنما" or text == "🕊️ راهنمای ربات":
            guide(chat_id)
        elif text == "📣 کانال" or text == "📣 کانال تلگرام":
            channel(chat_id)
        elif "🌍 پلتفرم کلام حیات" in text:
            songs_menu(chat_id)
        elif text == "📚 کتابخانه":
            library(chat_id)
        elif text == "🙏 دعا" or text == "🙏 دعا کنیم":
            prayer_menu(chat_id)
        elif text == "📩 وعده‌های خدا":
            promise(chat_id)
        elif text == "💡 دانستنی‌های جالب":
            fact(chat_id)
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
        user = q.get("from", {})
        cb = q["data"]

        requests.post(TG + "answerCallbackQuery", json={"callback_query_id": q["id"]})

        if cb.startswith("book|"):
            books = get_library_books()
            b = books[int(cb.split("|")[1])]

            send_doc(
                chat_id,
                b.get("file_id"),
                "📚 " + b.get("title", "")
            )

        elif cb.startswith("cat|"):
            cat_index = int(cb.split("|", 1)[1])
            category = SONG_CATEGORIES[cat_index]
            category_id = category["category_id"]
            cat_button = category["button"]

            try:
                songs = requests.get(f"{API_BASE}/hymns?category_id={category_id}", timeout=10).json()
            except Exception:
                songs = []

            songs = [
                s for s in songs
                if s.get("title") and s.get("audio_file_id") and s.get("is_active", True)
            ]

            if not songs:
                send_msg(chat_id, f"🎵\n\nهنوز سرودی برای این مناسبت ثبت نشده است:\n\n{cat_button}")
                return "ok"

            buttons = [
                [{
                    "text": "🎵 " + s.get("title", ""),
                    "callback_data": f"catsong|{s.get('id')}"
                }]
                for s in songs
            ]

            buttons.append([{"text": "➡️ برگشت", "callback_data": "songs_menu"}])
            send_msg(chat_id, f"🎵 {cat_button}:", {"inline_keyboard": buttons})

        elif cb == "songs_menu":
            songs_menu(chat_id)

        elif cb.startswith("catsong|"):
            song_id = int(cb.split("|", 1)[1])

            try:
                rows = requests.get(
                    f"{API_BASE}/hymns/{song_id}",
                    timeout=10
                ).json()
            except Exception:
                rows = []

            if rows:
                s = rows[0]
                send_audio(
                    chat_id,
                    s.get("audio_file_id"),
                    "🎶\n\nاین سرود تقدیم به شما\n🎶 "
                    + s.get("title", "")
                )

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
                send_audio(
                    chat_id,
                    s.get("audio_file_id"),
                    "🎶\n\nاین سرود تقدیم به شما\n🎶 "
                + s.get("title", "")
                )

        elif cb == "promise_next":
            promise(chat_id)

        elif cb == "fact_next":
            fact(chat_id)

        elif cb == "back_main":
            send_msg(chat_id, "🏠 از منوی پایین، بخش مورد نظر را انتخاب کنید.", main_keyboard())

        elif cb.startswith("bible_testament|"):
            testament = cb.split("|", 1)[1]
            bible_books(chat_id, testament)

        elif cb.startswith("bible_book|"):
            book_id = cb.split("|", 1)[1]
            bible_chapters(chat_id, book_id)

        elif cb.startswith("bible_chapter|"):
            parts = cb.split("|")
            book_id = parts[1]
            chapter_number = parts[2]
            bible_verses(chat_id, book_id, chapter_number)

        elif cb == "prayer_request":
            ask_prayer_visibility(chat_id)

        elif cb.startswith("prayer_visibility|"):
            mode = cb.split("|", 1)[1]
            name = get_user_name(user)

            PRAYER_STATES[str(chat_id)] = {
                "step": "awaiting_text",
                "visibility": "name" if mode == "name" else "anon",
                "name": name
            }

            send_msg(chat_id, "🙏 لطفاً درخواست دعای خود را ارسال کنید.")

        elif cb == "prayer_random":
            random_prayer(chat_id)

        elif cb.startswith("approve_prayer|"):
            pending_id = cb.split("|", 1)[1]
            prayer = PENDING_PRAYERS.pop(pending_id, None)

            if not prayer:
                send_msg(chat_id, "این درخواست دعا پیدا نشد یا قبلاً بررسی شده است.")
                return "ok"

            result = requests.post(
            f"{API_BASE}/prayers/submit",
            json={
                "prayer_text": prayer["public_text"],
                "user_name": prayer.get("display_name", ""),
                "is_anonymous": prayer.get("visibility") == "anon"
            },
            timeout=10
        ).json()

            if result.get("id"):
                clear_cache("Prayers")
                send_msg(chat_id, "✅ دعا تایید و در بخش دعا ثبت شد.")
                send_msg(prayer["user_chat_id"], "🙏 درخواست دعای شما تایید شد و در بخش دعا قرار گرفت.")
            else:
                send_msg(chat_id, "❌ ثبت دعا انجام نشد. دوباره تلاش کنید.")

        elif cb.startswith("reject_prayer|"):
            pending_id = cb.split("|", 1)[1]
            prayer = PENDING_PRAYERS.pop(pending_id, None)

            if prayer:
                send_msg(chat_id, "❌ درخواست دعا رد شد.")
                send_msg(prayer["user_chat_id"], "درخواست دعای شما توسط خادمین تایید نشد.")
            else:
                send_msg(chat_id, "این درخواست دعا پیدا نشد یا قبلاً بررسی شده است.")

        elif cb.startswith("praydone_"):
            prayer_id = cb.split("_", 1)[1]
            result = requests.post(f"{API_BASE}/prayers/prayed", json={"prayer_id": int(prayer_id)}, timeout=10).json()
            if isinstance(result, list) and result:
                count = result[0].get("prayer_count", "")
            elif isinstance(result, dict):
                count = result.get("prayer_count", "")
            else:
                count = ""

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
                    send_msg(chat_id, "آیه مرتبط:\n\n" + value(w, "آیه مرتبط"))
                elif action == "wmean":
                    send_msg(chat_id, "معنی:\n\n" + value(w, "معنی"))
                elif action == "wroot":
                    title = "💡 ریشه یونانی" if value(w, "عهد") == "NT" else "💡 ریشه عبری"
                    send_msg(chat_id, title + ":\n\n" + value(w, "ریشه"))

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
