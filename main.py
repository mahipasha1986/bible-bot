from flask import Flask, request, jsonify, Response
import requests
import os
import re
import random
import time

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SHEET_ID = "1m6dqGbvS-CHQO1eAO6l6A_2vSkxSIWdhlS5WnNl4zA0"
BASE = f"https://opensheet.elk.sh/{SHEET_ID}"
API_BASE = "https://square-silence-9274.mahi-pasha1986.workers.dev"
TG = f"https://api.telegram.org/bot{BOT_TOKEN}/"
CHANNEL_URL = "https://t.me/persian_bible"
WEBAPP_URL = "https://bible-bot-4eo2.onrender.com/webapp"
WRITER_URL = "https://script.google.com/macros/s/AKfycbwEQknEZsWHgdAyg8BI1tm0R-UDjUiD1gQFcifqa3sSuAWUPT1GmqJ0eSSSmVdNpXVV/exec"

ADMIN_CHAT_ID = "987273459"

SONG_CATEGORIES = [
    {"button": "✝️ سرودهای عید قیام", "value": "عید قیام"},
    {"button": "🎄 سرودهای تولد مسیح", "value": "تولد مسیح"},
    {"button": "🩸 سرودهای جمعه صلیب", "value": "جمعه صلیب"},
]

SONGS_PER_PAGE = 20
CACHE = {}
CACHE_TIME = 300

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


def sheet(name, use_cache=True):
    now = time.time()
    if use_cache and name in CACHE and now - CACHE[name]["time"] < CACHE_TIME:
        return CACHE[name]["data"]

    try:
        data = requests.get(f"{BASE}/{name}", timeout=15).json()
        CACHE[name] = {"time": now, "data": data}
        return data
    except Exception as e:
        print("Sheet error:", name, e)
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
    except Exception as e:
        print("Writer error:", e)
        return {"ok": False}


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
    send_msg(chat_id, """⚠️ راهنمای ربات

به ربات «کلمه‌یاب و سرودیاب» خوش آمدید 🕊️

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
    return [
        r for r in sheet("Songs", use_cache=False)
        if value(r, "اسم سرود") and value(r, "فایل")
    ]


def get_category_songs():
    return [
        r for r in sheet("CategorySongs", use_cache=False)
        if value(r, "اسم سرود") and value(r, "فایل")
    ]


def get_library_books():
    return [
        r for r in sheet("Library", use_cache=False)
        if value(r, "اسم کتاب") and value(r, "فایل")
    ]


def random_song(chat_id):
    songs = get_all_songs()

    if not songs:
        send_msg(chat_id, "🎵 هنوز سرودی ثبت نشده است.")
        return

    s = random.choice(songs)
    send_audio(chat_id, value(s, "فایل"), "🎶 این سرود تقدیم به شما\n\n🎵 " + value(s, "اسم سرود"))


@app.route("/api/songs", methods=["GET"])
def api_songs():
    rows = get_all_songs()
    songs = []

    for i, r in enumerate(rows):
        songs.append({
            "index": i,
            "name": value(r, "اسم سرود")
        })

    return jsonify({"ok": True, "songs": songs})


@app.route("/api/category/<int:cat_index>", methods=["GET"])
def api_category(cat_index):
    if cat_index < 0 or cat_index >= len(SONG_CATEGORIES):
        return jsonify({"ok": False, "songs": []})

    cat_value = SONG_CATEGORIES[cat_index]["value"]
    rows = get_category_songs()
    songs = []

    for i, r in enumerate(rows):
        if norm(value(r, "مناسبت")) == norm(cat_value):
            songs.append({
                "index": i,
                "name": value(r, "اسم سرود")
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
        value(s, "فایل"),
        "🎶 این سرود تقدیم به شما\n\n🎵 " + value(s, "اسم سرود")
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

    file_id = value(rows[index], "فایل")

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
        value(s, "فایل"),
        "🎶 این سرود تقدیم به شما\n\n🎵 " + value(s, "اسم سرود")
    )

    return jsonify({"ok": True})


@app.route("/api/books", methods=["GET"])
def api_books():
    rows = get_library_books()
    books = []

    for i, r in enumerate(rows):
        books.append({
            "index": i,
            "name": value(r, "اسم کتاب")
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
        value(b, "فایل"),
        "📚 " + value(b, "اسم کتاب")
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
<title>سرودها و کتابخانه</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
body{
  margin:0;
  font-family:Arial, sans-serif;
  background:radial-gradient(circle at top,#5d347d,#1b102b 65%);
  color:white;
  padding:18px;
  text-align:center;
}
.card{
  background:rgba(255,255,255,0.13);
  border:1px solid rgba(255,255,255,0.2);
  border-radius:28px;
  padding:20px;
  margin-bottom:16px;
  box-shadow:0 12px 40px rgba(0,0,0,0.35);
}
h1{font-size:25px;margin:5px 0 12px;}
p{line-height:1.9;font-size:15px;opacity:.94;}
button{
  width:100%;
  padding:15px;
  margin-top:11px;
  border:none;
  border-radius:18px;
  font-size:16px;
  font-weight:bold;
  color:white;
  cursor:pointer;
  box-shadow:0 8px 22px rgba(0,0,0,.28);
}
.red{background:linear-gradient(135deg,#ff416c,#ff4b2b);}
.blue{background:linear-gradient(135deg,#36d1dc,#5b86e5);}
.green{background:linear-gradient(135deg,#56ab2f,#a8e063);color:#102000;}
.gold{background:linear-gradient(135deg,#f7971e,#ffd200);color:#2b1900;}
.purple{background:linear-gradient(135deg,#8e2de2,#4a00e0);}
input{
  width:100%;
  box-sizing:border-box;
  padding:15px;
  border-radius:18px;
  border:1px solid rgba(255,255,255,.25);
  background:rgba(255,255,255,.12);
  color:white;
  margin-top:12px;
  font-size:16px;
  text-align:right;
  outline:none;
}
input::placeholder{color:rgba(255,255,255,.7);}
.song-item, .book-item{
  background:rgba(255,255,255,0.12);
  border:1px solid rgba(255,255,255,.14);
  padding:13px;
  border-radius:16px;
  margin-top:10px;
  cursor:pointer;
  text-align:right;
}
.small{
  font-size:13px;
  opacity:.82;
  margin-top:10px;
  line-height:1.7;
}
.player-card{
  display:none;
  background:rgba(255,255,255,0.13);
  border:1px solid rgba(255,255,255,.18);
  border-radius:22px;
  padding:16px;
  margin-top:16px;
  text-align:right;
}
.player-title{
  font-size:16px;
  font-weight:bold;
  margin-bottom:12px;
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
}
.tab-buttons button{
  flex:1;
  font-size:14px;
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
  <button class="purple" onclick="showSection('songsSection')">🎼 سرودها</button>
  <button class="green" onclick="showSection('librarySection')">📚 کتابخانه</button>
</div>

<div id="songsSection" class="section active">

<div class="card">
  <h1>🎼 سرودهای پرستشی</h1>
  <p>
به بخش سرودیاب خوش آمدید.<br>
از گزینه‌های زیر می‌توانید سرودهای مناسبتی یا لیست کامل سرودها را انتخاب کنید.
</p>

  <button class="gold" onclick="loadCategory(0)">✝️ سرودهای عید قیام</button>
  <button class="blue" onclick="loadCategory(1)">🎄 سرودهای تولد مسیح</button>
  <button class="red" onclick="loadCategory(2)">🩸 سرودهای جمعه صلیب</button>
  <button class="green" onclick="loadSongs()">🎼 لیست کامل سرودها</button>
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

<script>
Telegram.WebApp.ready();
Telegram.WebApp.expand();

let allSongs = [];
let currentSource = "songs";
let currentPage = 0;
const songsPerPage = 30;
let selectedSong = null;

let allBooks = [];

function showSection(sectionId){
  document.getElementById("songsSection").classList.remove("active");
  document.getElementById("librarySection").classList.remove("active");
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


def library(chat_id):
    books = get_library_books()

    if not books:
        send_msg(chat_id, "📚 هنوز کتابی در کتابخانه ثبت نشده است.")
        return

    buttons = [
        [{"text": "📖 " + value(b, "اسم کتاب"), "callback_data": f"book|{i}"}]
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

    pending_id = str(int(time.time() * 1000))
    PENDING_PRAYERS[pending_id] = {
        "user_chat_id": chat_id,
        "display_name": display_name,
        "public_text": public_text,
        "original_text": text
    }

    PRAYER_STATES.pop(str(chat_id), None)

    send_msg(chat_id, "🙏 درخواست دعای شما دریافت شد و پس از تایید خادمین در بخش دعا نمایش داده می‌شود.")

    admin_text = (
        "🙏 درخواست دعای جدید برای تایید\n\n"
        f"👤 نمایش برای دیگران: {display_name}\n\n"
        f"📝 متن دعا:\n{text}"
    )

    send_msg(
        ADMIN_CHAT_ID,
        admin_text,
        {"inline_keyboard": [
            [{"text": "✅ تایید", "callback_data": f"approve_prayer|{pending_id}"}],
            [{"text": "❌ رد", "callback_data": f"reject_prayer|{pending_id}"}],
        ]}
    )


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
            send_doc(chat_id, value(b, "فایل"), "📚 " + value(b, "اسم کتاب"))

        elif cb.startswith("cat|"):
            cat_index = int(cb.split("|", 1)[1])
            cat_value = SONG_CATEGORIES[cat_index]["value"]
            cat_button = SONG_CATEGORIES[cat_index]["button"]

            all_category_songs = get_category_songs()

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

            buttons.append([{"text": "➡️ برگشت", "callback_data": "songs_menu"}])
            send_msg(chat_id, f"🎵 {cat_button}:", {"inline_keyboard": buttons})

        elif cb == "songs_menu":
            songs_menu(chat_id)

        elif cb.startswith("catsong|"):
            index = int(cb.split("|", 1)[1])
            all_category_songs = get_category_songs()

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

        elif cb == "promise_next":
            promise(chat_id)

        elif cb == "fact_next":
            fact(chat_id)

        elif cb == "back_main":
            send_msg(chat_id, "🏠 از منوی پایین، بخش مورد نظر را انتخاب کنید.", main_keyboard())

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

            result = writer({"type": "prayer", "text": prayer["public_text"]})

            if result.get("ok"):
                clear_cache("Prayers")
                send_msg(chat_id, "✅ دعا تایید و در بخش دعا ثبت شد.")
                send_msg(prayer["user_chat_id"], "🙏 درخواست دعای شما تایید شد و در بخش دعا قرار گرفت.")
            else:
                send_msg(chat_id, "❌ ثبت دعا در شیت انجام نشد. دوباره تلاش کنید.")

        elif cb.startswith("reject_prayer|"):
            pending_id = cb.split("|", 1)[1]
            prayer = PENDING_PRAYERS.pop(pending_id, None)

            if prayer:
                send_msg(chat_id, "❌ درخواست دعا رد شد.")
                send_msg(prayer["user_chat_id"], "درخواست دعای شما توسط خادمین تایید نشد.")
            else:
                send_msg(chat_id, "این درخواست دعا پیدا نشد یا قبلاً بررسی شده است.")

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
