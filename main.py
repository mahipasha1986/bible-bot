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
    {"button": "✝️ سرودهای عید قیام", "value": "عید قیام", "category_id": 1},
    {"button": "🎄 سرودهای تولد مسیح", "value": "تولد مسیح", "category_id": 2},
    {"button": "🩸 سرودهای جمعه صلیب", "value": "جمعه صلیب", "category_id": 3},
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
            [{"text": "🕊️ بخش سرودها و کتابخانه"}],
            [{"text": "🎵 یک سرود برام انتخاب کن"}],
            [{"text": "🙏 دعا"}, {"text": "📖 کلمات کتاب مقدس"}],
            [{"text": "📖 کتاب مقدس"}],
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
        "برای ورود به بخش سرودها و کتابخانه روی دکمه زیر کلیک کنید",
        {"inline_keyboard": [[
            {"text": "🕊️ ورود به بخش سرودها و کتابخانه", "web_app": {"url": WEBAPP_URL}}
        ]]}
    )


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
            "name": r.get("title", "")
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
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
body{
    margin:0;
    font-family:Tahoma,sans-serif;
    background:#f7f9fc;
    color:#222;
    padding:18px;
    text-align:center;
}
.card{
    background:#ffffff;
    border:1px solid #e8edf3;
    border-radius:26px;
    padding:22px 18px;
    margin-bottom:14px;
    box-shadow:0 8px 24px rgba(31,78,121,0.08);
}
h1{
    font-size:30px;
    font-weight:700;
    color:#2c2c2c;
    margin:8px 0 16px;
}

h2{
    font-size:28px;
    font-weight:800;
    color:#2c2c2c;
    margin:8px 0 18px;
}

p{
    line-height:2;
    font-size:16px;
    color:#555;
}
button{
    width:100%;
    padding:16px;
    margin-top:12px;
    border:none;
    border-radius:20px;
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
    background:white;
    color:#1f4e79;
    border:2px solid #1f4e79;
    box-shadow:0 4px 12px rgba(0,0,0,0.08);
}
.secondary{
    background:white;
    color:#1f4e79;
    border:2px solid #1f4e79;
    box-shadow:0 4px 12px rgba(0,0,0,0.08);
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
    font-size:14px;
    color:#777;
    margin-top:10px;
    line-height:1.8;
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
    gap:10px;
    margin-bottom:16px;
    overflow-x:auto;
    padding-bottom:5px;
}

.tab-buttons button{
    flex:none;
    min-width:140px;
    font-size:14px;
    white-space:nowrap;
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

    <button class="gold"
        onclick="showSection('homeSection')">
        🏠 خانه
    </button>

    <button class="gold" onclick="alert('Bible clicked'); showSection('bibleSection')">
    📖 کتاب مقدس
</button>

    <button class="gold"
        onclick="alert('🔍 دانشنامه کتاب مقدس در حال تکمیل است')">
        🔍 دانشنامه کتاب مقدس
    </button>

</div>

<div id="homeSection" class="section active">

<div class="card">

<h1>📖 کلام حیات</h1>

<p>
مطالعه، پرستش و رشد در کلام خدا
</p>

<div class="small">
کشف حقیقت، رشد ایمان و زندگی با کلام خدا
</div>

</div>

<div class="card">
  <h2>🌟 آیه روز</h2>
  <div id="homeDailyVerse" class="small">
    در حال دریافت آیه روز...
  </div>
</div>

<div class="card">
  <h1>🔍 دانشنامه کتاب مقدس</h1>
  <p>
    واژه‌ها • شخصیت‌ها • مکان‌ها • آیات مرتبط
  </p>
  <button class="gold" onclick="showBibleEncyclopedia()">
    ورود به دانشنامه
  </button>
</div>

<div class="card">
  <button class="gold" onclick="showSection('bibleSection')">
      📖 کتاب مقدس
  </button>

  <button class="secondary" onclick="showSection('songsSection'); loadSongs();">
      🎵 سرودها
  </button>

  <button class="secondary" onclick="showSection('librarySection')">
    📚 کتابخانه
  </button>

  <button class="secondary" onclick="alert('🎧 کتاب مقدس صوتی به‌زودی اضافه می‌شود')">
    🎧 کتاب مقدس صوتی
  </button>

  <button class="secondary" onclick="alert('🎮 بازی‌ها و آزمون‌های کتاب مقدس به‌زودی اضافه می‌شود')">
    🎮 بازی‌ها و آزمون‌ها
  </button>
</div>

<div id="songsSection" class="section">

<div class="card">

    <h1>سرودها 🎵</h1>

    <p>دسته‌بندی سرودهای مناسبتی</p>

    <button class="gold" onclick="loadCategory(0)">
        ✝️ سرودهای عید قیام
    </button>

    <button class="gold" onclick="loadCategory(1)">
        🎄 سرودهای تولد مسیح
    </button>

    <button class="gold" onclick="loadCategory(2)">
        🩸 سرودهای جمعه صلیب
    </button>

    <button class="gold" onclick="loadSongs()">
        🎼 همه سرودها
    </button>

</div>

<div class="card">
  <input id="search" placeholder="🔍 جستجوی نام سرود..." oninput="filterSongs()">
  <div class="small">برای دریافت سرود، روی نام آن بزنید.</div>
  <div id="status" class="small"></div>

  <div id="playerCard" class="player-card">
    <div id="playerTitle" class="player-title">🎵 نام سرود</div>
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

<div class="card">
  <h1>📚 کتابخانه</h1>
  <p>
    به بخش کتابخانه خوش آمدید<br>
    کتاب‌های موجود را مشاهده کنید و برای دریافت فایل، روی نام کتاب بزنید.
  </p>
  <button class="green" onclick="loadBooks()">📚 نمایش کتاب‌ها</button>
</div>

<div class="card">
  <input id="bookSearch" placeholder="🔍 جستجوی نام کتاب..." oninput="filterBooks()">
  <div id="bookStatus" class="small"></div>
  <div id="books"></div>
</div>

</div>

<div id="bibleSection" class="section">

    <div class="card">
        <h1>📖 کتاب مقدس</h1>

        <p>
            به بخش کتاب مقدس خوش آمدید.<br>
            از این قسمت می‌توانید عهد عتیق و عهد جدید را مطالعه کنید.
        </p>
    </div>

    <div class="card">
        <button class="gold" onclick="loadBibleBooks('old')">
            📜 عهد عتیق
        </button>

        <button class="gold" onclick="loadBibleBooks('new')">
            ✨ عهد جدید
        </button>
    </div>

    <div class="card">

        <input
            id="bibleSearchInput"
            type="text"
            placeholder="🔍 جستجوی آیه..."
            style="width:100%; padding:12px; border-radius:12px; margin-bottom:10px;">

        <button class="gold" onclick="searchBibleVerse()">
            🔍 جستجو
        </button>

        <button class="gold" onclick="loadDailyVerse()">
            🌟 آیه روز
        </button>

        <button class="gold" onclick="loadBookmarks()">
            🔖 آیات ذخیره‌شده
        </button>

    </div>

    <div class="card">
        <div id="bibleContent">
            انتخاب یکی از بخش‌های بالا...
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
            <div class="small">
                🔍 نتیجه جستجو برای: ${q}
            </div>

            ${results.map(v => `
                <div style="margin-bottom:12px; line-height:2;">
                    <span style="font-weight:bold;color:#1f4e79;">
                        ${v.chapter_number}:${v.verse_number}
                    </span>
                    ${v.verse_text}

                    <button class="gold" onclick="addBookmark(${v.id})" style="margin-top:8px;">
                        🔖 ذخیره آیه
                    </button>
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

    const bibleContent = document.getElementById("bibleContent");

    bibleContent.innerHTML = "⏳ در حال دریافت آیه روز...";

    try{

        const res = await fetch(
            "https://square-silence-9274.mahi-pasha1986.workers.dev/bible/daily-verse"
        );

        const data = await res.json();
        const verse = data[0];

        bibleContent.innerHTML = `
            <div class="small">
                🌟 آیه روز
            </div>

            <div style="margin-bottom:12px; line-height:2; font-size:17px; text-align:right;">
                <span style="font-weight:bold; color:#1f4e79;">
                    ${verse.chapter_number}:${verse.verse_number}
                </span>
                ${verse.verse_text}
            </div>
        `;

    }catch(err){
        bibleContent.innerHTML = "❌ " + err.message;
    }
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
            <div class="small">🔖 آیات ذخیره‌شده</div>

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

        bibleContent.innerHTML = filtered.map(book => `
            <div class="book-item" onclick="loadBibleChapters(${book.id}, '${book.name_fa || book.name}')">
                 📖 ${book.name_fa || book.book_name_fa || book.name || book.title}
            </div>
        `).join("");

    }catch(err){

        bibleContent.innerHTML =
            "❌ خطا در دریافت کتاب‌های کتاب مقدس";

    }
}

async function loadBibleChapters(bookId, bookName){

    const bibleContent = document.getElementById("bibleContent");

    bibleContent.innerHTML = "⏳ در حال دریافت باب‌های " + bookName + "...";

    try{

        const res = await fetch(
            "https://square-silence-9274.mahi-pasha1986.workers.dev/bible/chapters?book_id=" + bookId
        );

        const chapters = await res.json();

        bibleContent.innerHTML = `
            <div class="book-item"
                 onclick="loadBibleBooks(currentBibleTestament)">
                 ⬅️ بازگشت به کتاب‌ها
            </div>

            <div class="small">📖 ${bookName}</div>

            ${chapters.map(chapter => `
                <div class="book-item"
                     onclick="loadBibleVerses(${bookId}, ${chapter.chapter_number}, '${bookName}', ${chapters.length})">
                     باب ${chapter.chapter_number}
                </div>
            `).join("")}
        `;

    }catch(err){

        bibleContent.innerHTML = "❌ خطا در دریافت باب‌ها";

    }
}

async function loadBibleVerses(bookId, chapterNumber, bookName, totalChapters){

    const bibleContent = document.getElementById("bibleContent");

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
            <div class="book-item"
                 onclick="loadBibleChapters(${bookId}, '${bookName}')">
                 ⬅️ بازگشت به باب‌ها
            </div>

            <div class="book-item"
                 onclick="loadBibleBooks(currentBibleTestament)">
                 ⬅️ بازگشت به کتاب‌ها
            </div>

            <div class="small">
                📖 ${bookName} - باب ${chapterNumber}
            </div>

            ${verses.map(v => `
                <div style="margin-bottom:10px; line-height:2; font-size:17px;
            text-align:right;">
                    <span style="font-weight:bold; color:#1f4e79;">
                        ${v.verse_number}
                    </span>
                    ${v.verse_text}
                </div>
            `).join("")}

            <div style="display:flex; gap:10px; margin-top:25px;">
                <div class="book-item"
                     onclick="loadBibleVerses(${bookId}, ${chapterNumber - 1}, '${bookName}', ${totalChapters})"
                     style="flex:1; display:${chapterNumber > 1 ? 'block' : 'none'};">
                     باب قبل
                </div>

                <div class="book-item"
                     onclick="loadBibleVerses(${bookId}, ${chapterNumber + 1}, '${bookName}', ${totalChapters})"
                     style="flex:1; display:${chapterNumber < totalChapters ? 'block' : 'none'};">
                     باب بعد
                </div>
            </div>
            
            `;

    }catch(err){

        bibleContent.innerHTML =
            "❌ خطا در دریافت آیات";

    }
}

function showSection(sectionId){

    document.getElementById("songsSection").classList.remove("active");
    document.getElementById("librarySection").classList.remove("active");
    document.getElementById("bibleSection").classList.remove("active");

    document.getElementById(sectionId).classList.add("active");
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

  setStatus("🎼 لیست کامل سرودها");
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

  setStatus(data.title || "🎵 سرودهای مناسبتی");
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

  document.getElementById("bookStatus").innerText = "📚 کتابخانه";
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
    div.innerText = "📖 " + book.name;
    div.onclick = () => sendBook(book.index);
    container.appendChild(div);
  });
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
        send_msg(chat_id, "📚 هنوز کتابی در کتابخانه ثبت نشده است.")
        return

    buttons = [
        [{"text": "📖 " + b.get("title", ""), "callback_data": f"book|{i}"}]
        for i, b in enumerate(books)
    ]

    send_msg(chat_id, "📚 کتاب مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})


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
        f"🎼 لیست سرودها — صفحه {page + 1} از {total_pages}\n\nبرای دریافت، روی نام سرود بزنید:",
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
        "📖 بخش کتاب مقدس\n\nیکی از گزینه‌ها را انتخاب کنید:",
        {"inline_keyboard": [
            [{"text": "📜 عهد عتیق", "callback_data": "bible_testament|OT"}],
            [{"text": "📘 عهد جدید", "callback_data": "bible_testament|NT"}],
        ]}
    )


def bible_books(chat_id, testament):
    try:
        rows = requests.get(f"{API_BASE}/bible/books", timeout=10).json()
    except Exception:
        rows = []

    books = [b for b in rows if b.get("testament") == testament]

    if not books:
        send_msg(chat_id, "📖 هنوز کتابی برای این بخش ثبت نشده است.")
        return

    buttons = []
    for b in books:
        buttons.append([{
            "text": "📖 " + b.get("name_fa", ""),
            "callback_data": f"bible_book|{b.get('id')}"
        }])

    send_msg(chat_id, "📖 کتاب مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})


def bible_chapters(chat_id, book_id):
    try:
        rows = requests.get(f"{API_BASE}/bible/chapters?book_id={book_id}", timeout=10).json()
    except Exception:
        rows = []

    if not rows:
        send_msg(chat_id, "📖 هنوز فصلی برای این کتاب ثبت نشده است.")
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

    send_msg(chat_id, "📖 باب مورد نظر را انتخاب کنید:", {"inline_keyboard": buttons})


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
            "📖 آیات این باب به‌زودی اضافه می‌شود.\n\nاین بخش در حال تکمیل است."
        )
        return

    text = f"📖 باب {chapter_number}\n\n"
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
        elif text == "🕊️ بخش سرودها و کتابخانه" or text == "🎼 سرودها و کتابخانه" or text == "🎼 سرودها":
            songs_menu(chat_id)
        elif text == "📚 کتابخانه":
            library(chat_id)
        elif text == "🙏 دعا" or text == "🙏 دعا کنیم":
            prayer_menu(chat_id)
        elif text == "📖 کلمات کتاب مقدس":
            word_instruction(chat_id)
        elif text == "📖 کتاب مقدس":
            bible_menu(chat_id)
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
                    send_msg(chat_id, "📜 آیه مرتبط:\n\n" + value(w, "آیه مرتبط"))
                elif action == "wmean":
                    send_msg(chat_id, "📖 معنی:\n\n" + value(w, "معنی"))
                elif action == "wroot":
                    title = "💡 ریشه یونانی" if value(w, "عهد") == "NT" else "💡 ریشه عبری"
                    send_msg(chat_id, title + ":\n\n" + value(w, "ریشه"))

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
