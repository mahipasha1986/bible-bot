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
TG = f"https://api.telegram.org/bot{BOT_TOKEN}/"
CHANNEL_URL = "https://t.me/persian_bible"
WEBAPP_URL = "https://bible-bot-4eo2.onrender.com/webapp"
WRITER_URL = "https://script.google.com/macros/s/AKfycbwEQknEZsWHgdAyg8BI1tm0R-UDjUiD1gQFcifqa3sSuAWUPT1GmqJ0eSSSmVdNpXVV/exec"

ADMIN_CHAT_ID = "987273459"

SONG_CATEGORIES = [
    {"button": "âœï¸ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ø¹ÛŒØ¯ Ù‚ÛŒØ§Ù…", "value": "Ø¹ÛŒØ¯ Ù‚ÛŒØ§Ù…"},
    {"button": "ðŸŽ„ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ ØªÙˆÙ„Ø¯ Ù…Ø³ÛŒØ­", "value": "ØªÙˆÙ„Ø¯ Ù…Ø³ÛŒØ­"},
    {"button": "ðŸ©¸ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ø¬Ù…Ø¹Ù‡ ØµÙ„ÛŒØ¨", "value": "Ø¬Ù…Ø¹Ù‡ ØµÙ„ÛŒØ¨"},
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
    t = t.replace("ÙŠ", "ÛŒ").replace("Ùƒ", "Ú©")
    t = t.replace("Ø¢", "Ø§").replace("Ø£", "Ø§").replace("Ø¥", "Ø§")
    t = re.sub(r"[ÙŽÙ‹ÙÙŒÙÙÙ’Ù‘]", "", t)
    t = re.sub(r"[.,ØŒØ›:!ØŸ?()Â«Â»\"']", "", t)
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
    return "Ú©Ø§Ø±Ø¨Ø±"


def main_keyboard():
    return {
        "keyboard": [
            [{"text": "âœ¨ ÙˆØ±ÙˆØ¯ Ø¨Ù‡ Ø§Ù¾Ù„ÛŒÚ©ÛŒØ´Ù†"}],
            [{"text": "ðŸŽµ ÛŒÚ© Ø³Ø±ÙˆØ¯ Ø¨Ø±Ø§Ù… Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†"}],
            [{"text": "ðŸ™ Ø¯Ø¹Ø§ Ø¨Ø±Ø§ÛŒ ÛŒÚ©Ø¯ÛŒÚ¯Ø±"}],
            [{"text": "ðŸ“© ÙˆØ¹Ø¯Ù‡â€ŒÙ‡Ø§ÛŒ Ø®Ø¯Ø§"}, {"text": "ðŸ’¡ Ø¯Ø§Ù†Ø³ØªÙ†ÛŒâ€ŒÙ‡Ø§ÛŒ Ø¬Ø§Ù„Ø¨"}],
            [{"text": "ðŸ“£ Ú©Ø§Ù†Ø§Ù„"}, {"text": "âš ï¸ Ø±Ø§Ù‡Ù†Ù…Ø§"}],
        ],
        "resize_keyboard": True
    }


def welcome(chat_id):
    result = writer({"type": "user", "chat_id": chat_id})

    if result.get("exists"):
        text = "âœ¨ Ø®ÙˆØ´Ø­Ø§Ù„ÛŒÙ… Ø¯ÙˆØ¨Ø§Ø±Ù‡ Ù…ÛŒâ€ŒØ¨ÛŒÙ†ÛŒÙ…Øª.\nØ¨Ù‡ Ø±Ø¨Ø§Øª Â«Ú©Ù„Ù…Ù‡â€ŒÛŒØ§Ø¨ Ùˆ Ø³Ø±ÙˆØ¯ÛŒØ§Ø¨Â» Ø®ÙˆØ´ Ø¢Ù…Ø¯ÛŒØ¯ ðŸ•Šï¸"
    else:
        text = "âœ¨ Ø´Ø§Ù„ÙˆÙ… Ø¨Ø± Ø´Ù…Ø§ ÙØ±Ø²Ù†Ø¯Ø§Ù† Ù†ÙˆØ±\nØ¨Ù‡ Ø±Ø¨Ø§Øª Â«Ú©Ù„Ù…Ù‡â€ŒÛŒØ§Ø¨ Ùˆ Ø³Ø±ÙˆØ¯ÛŒØ§Ø¨Â» Ø®ÙˆØ´ Ø¢Ù…Ø¯ÛŒØ¯ ðŸ•Šï¸"

    send_msg(chat_id, text, main_keyboard())


def guide(chat_id):
    send_msg(chat_id, """âš ï¸ Ø±Ø§Ù‡Ù†Ù…Ø§ÛŒ Ø±Ø¨Ø§Øª

Ø¨Ù‡ Ø±Ø¨Ø§Øª Â«Ú©Ù„Ù…Ù‡â€ŒÛŒØ§Ø¨ Ùˆ Ø³Ø±ÙˆØ¯ÛŒØ§Ø¨Â» Ø®ÙˆØ´ Ø¢Ù…Ø¯ÛŒØ¯ ðŸ•Šï¸

âœ¨ Ø¨Ø±Ø§ÛŒ Ø§Ø³ØªÙØ§Ø¯Ù‡ Ø§Ø² Ø¨Ø®Ø´ Ø­Ø±ÙÙ‡â€ŒØ§ÛŒ Ø±Ø¨Ø§Øª:
Ø±ÙˆÛŒ Ø¯Ú©Ù…Ù‡ Â«âœ¨ ÙˆØ±ÙˆØ¯ Ø¨Ù‡ Ø§Ù¾Ù„ÛŒÚ©ÛŒØ´Ù†Â» Ø¨Ø²Ù†ÛŒØ¯.

Ø¯Ø± Ø§Ù¾Ù„ÛŒÚ©ÛŒØ´Ù† Ù…ÛŒâ€ŒØªÙˆØ§Ù†ÛŒØ¯:

ðŸŽ¼ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ù¾Ø±Ø³ØªØ´ÛŒ Ø±Ø§ Ø¬Ø³ØªØ¬ÙˆØŒ Ù¾Ø®Ø´ Ùˆ Ø¯Ø±ÛŒØ§ÙØª Ú©Ù†ÛŒØ¯

ðŸ“š Ú©ØªØ§Ø¨â€ŒÙ‡Ø§ÛŒ Ù…ÙˆØ¬ÙˆØ¯ Ø±Ø§ Ù…Ø´Ø§Ù‡Ø¯Ù‡ Ùˆ Ø¯Ø§Ù†Ù„ÙˆØ¯ Ú©Ù†ÛŒØ¯

ðŸ“– Ú©Ù„Ù…Ø§ØªØŒ Ù…Ú©Ø§Ù†â€ŒÙ‡Ø§ Ùˆ Ø´Ø®ØµÛŒØªâ€ŒÙ‡Ø§ÛŒ Ú©ØªØ§Ø¨â€ŒÙ…Ù‚Ø¯Ø³ Ø±Ø§ Ø¬Ø³ØªØ¬Ùˆ Ú©Ù†ÛŒØ¯ Ùˆ Ù…Ø¹Ù†ÛŒØŒ Ø±ÛŒØ´Ù‡ Ùˆ Ø¢ÛŒÙ‡ Ù…Ø±ØªØ¨Ø· Ø±Ø§ Ø¨Ø¨ÛŒÙ†ÛŒØ¯

ðŸŽµ Ø¨Ø±Ø§ÛŒ Ø¯Ø±ÛŒØ§ÙØª ÛŒÚ© Ø³Ø±ÙˆØ¯ Ù¾ÛŒØ´Ù†Ù‡Ø§Ø¯ÛŒ:
Ø§Ø² Ù…Ù†ÙˆÛŒ Ø§ØµÙ„ÛŒ Ø±ÙˆÛŒ Â«ðŸŽµ ÛŒÚ© Ø³Ø±ÙˆØ¯ Ø¨Ø±Ø§Ù… Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†Â» Ø¨Ø²Ù†ÛŒØ¯.

ðŸ™ Ø¨Ø±Ø§ÛŒ Ø«Ø¨Øª Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§:
Ø§Ø² Ù…Ù†ÙˆÛŒ Ø§ØµÙ„ÛŒ Ø±ÙˆÛŒ Â«ðŸ™ Ø¯Ø¹Ø§ Ø¨Ø±Ø§ÛŒ ÛŒÚ©Ø¯ÛŒÚ¯Ø±Â» Ø¨Ø²Ù†ÛŒØ¯.

Ø¨Ø±Ø§ÛŒ Ø«Ø¨Øª Ø¯Ø¹Ø§ØŒ Ù…ØªÙ† Ø®ÙˆØ¯ Ø±Ø§ Ø¨Ø¹Ø¯ Ø§Ø² Â«Ø¯Ø¹Ø§:Â» Ø¨Ù†ÙˆÛŒØ³ÛŒØ¯.

Ù…Ø«Ø§Ù„:
Ø¯Ø¹Ø§: Ø¨Ø±Ø§ÛŒ Ø¢Ø±Ø§Ù…Ø´ Ø®Ø§Ù†ÙˆØ§Ø¯Ù‡â€ŒØ§Ù…

Ø¯Ø±Ø®ÙˆØ§Ø³Øªâ€ŒÙ‡Ø§ÛŒ Ø¯Ø¹Ø§ Ù¾Ø³ Ø§Ø² ØªØ§ÛŒÛŒØ¯ Ø®Ø§Ø¯Ù…ÛŒÙ† Ù†Ù…Ø§ÛŒØ´ Ø¯Ø§Ø¯Ù‡ Ù…ÛŒâ€ŒØ´ÙˆÙ†Ø¯.

âš ï¸ Ù…Ù…Ú©Ù† Ø§Ø³Øª Ø§ÙˆÙ„ÛŒÙ† Ù¾Ø§Ø³Ø® Ø±Ø¨Ø§Øª Ú†Ù†Ø¯ Ù„Ø­Ø¸Ù‡ Ø²Ù…Ø§Ù† Ø¨Ø¨Ø±Ø¯.
Ø³Ù¾Ø§Ø³ Ø§Ø² Ø´Ú©ÛŒØ¨Ø§ÛŒÛŒ Ø´Ù…Ø§ ðŸ™""")


def channel(chat_id):
    send_msg(chat_id, "Ø¹Ø¶ÙˆÛŒØª Ø¯Ø± Ú©Ø§Ù†Ø§Ù„ Ø±Ø³Ù…ÛŒ Ø¨Ø±Ø§ÛŒ Ø¯Ø³ØªØ±Ø³ÛŒ Ø¨Ù‡ Ø¢Ø±Ø´ÛŒÙˆ Ø¨Ø²Ø±Ú¯ Ù…Ø³ÛŒØ­ÛŒ:",
             {"inline_keyboard": [[{"text": "ðŸ“£ ÙˆØ±ÙˆØ¯ Ø¨Ù‡ Ú©Ø§Ù†Ø§Ù„", "url": CHANNEL_URL}]]})


def songs_menu(chat_id):
    send_msg(
        chat_id,
        "âœ¨ Ø¨Ø±Ø§ÛŒ ÙˆØ±ÙˆØ¯ Ø¨Ù‡ Ø§Ù¾Ù„ÛŒÚ©ÛŒØ´Ù† Ú©Ù„Ù…Ù‡â€ŒÛŒØ§Ø¨ Ùˆ Ø³Ø±ÙˆØ¯ÛŒØ§Ø¨ Ø±ÙˆÛŒ Ø¯Ú©Ù…Ù‡ Ø²ÛŒØ± Ø¨Ø²Ù†ÛŒØ¯:",
        {"inline_keyboard": [[
            {"text": "âœ¨ ÙˆØ±ÙˆØ¯ Ø¨Ù‡ Ø§Ù¾Ù„ÛŒÚ©ÛŒØ´Ù†", "web_app": {"url": WEBAPP_URL}}
        ]]}
    )


def word_instruction(chat_id):
    send_msg(chat_id, "ðŸ“– Ù†Ø§Ù… Ú©Ù„Ù…Ù‡ Ù…ÙˆØ±Ø¯ Ù†Ø¸Ø± Ø±Ø§ Ø¨Ù†ÙˆÛŒØ³ÛŒØ¯.")


def handle_file(msg):
    chat_id = msg["chat"]["id"]

    for kind, icon in [("document", "ðŸ“„"), ("audio", "ðŸŽµ"), ("voice", "ðŸŽ™")]:
        if kind in msg:
            file_id = msg[kind]["file_id"]
            name = msg[kind].get("file_name", "Ø¨Ø¯ÙˆÙ† Ù†Ø§Ù…")
            send_msg(chat_id, f"{icon} Ú©Ø¯ ÙØ§ÛŒÙ„ Ø¯Ø±ÛŒØ§ÙØª Ø´Ø¯:\n\nfile_id:\n{file_id}\n\nÙ†Ø§Ù… ÙØ§ÛŒÙ„:\n{name}")
            return True

    return False


def not_found(chat_id):
    send_msg(chat_id, "ðŸ” Ø§ÛŒÙ† Ù…ÙˆØ±Ø¯ Ù‡Ù†ÙˆØ² Ø¯Ø± Ø¢Ø±Ø´ÛŒÙˆ Ù…Ø§ Ù†ÛŒØ³Øª\nØ®Ø§Ø¯Ù…ÛŒÙ† Ø¯Ø± Ø­Ø§Ù„ Ú¯Ø³ØªØ±Ø´ Ø¢Ø±Ø´ÛŒÙˆ Ù‡Ø³ØªÙ†Ø¯.")


def get_all_songs():
    return [
        r for r in sheet("Songs", use_cache=False)
        if value(r, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯") and value(r, "ÙØ§ÛŒÙ„")
    ]


def get_category_songs():
    return [
        r for r in sheet("CategorySongs", use_cache=False)
        if value(r, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯") and value(r, "ÙØ§ÛŒÙ„")
    ]


def get_library_books():
    return [
        r for r in sheet("Library", use_cache=False)
        if value(r, "Ø§Ø³Ù… Ú©ØªØ§Ø¨") and value(r, "ÙØ§ÛŒÙ„")
    ]


def random_song(chat_id):
    songs = get_all_songs()

    if not songs:
        send_msg(chat_id, "ðŸŽµ Ù‡Ù†ÙˆØ² Ø³Ø±ÙˆØ¯ÛŒ Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª.")
        return

    s = random.choice(songs)
    send_audio(chat_id, value(s, "ÙØ§ÛŒÙ„"), "ðŸŽ¶ Ø§ÛŒÙ† Ø³Ø±ÙˆØ¯ ØªÙ‚Ø¯ÛŒÙ… Ø¨Ù‡ Ø´Ù…Ø§\n\nðŸŽµ " + value(s, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯"))


@app.route("/api/songs", methods=["GET"])
def api_songs():
    rows = get_all_songs()
    songs = []

    for i, r in enumerate(rows):
        songs.append({
            "index": i,
            "name": value(r, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯")
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
        if norm(value(r, "Ù…Ù†Ø§Ø³Ø¨Øª")) == norm(cat_value):
            songs.append({
                "index": i,
                "name": value(r, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯")
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
        value(s, "ÙØ§ÛŒÙ„"),
        "ðŸŽ¶ Ø§ÛŒÙ† Ø³Ø±ÙˆØ¯ ØªÙ‚Ø¯ÛŒÙ… Ø¨Ù‡ Ø´Ù…Ø§\n\nðŸŽµ " + value(s, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯")
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

    file_id = value(rows[index], "ÙØ§ÛŒÙ„")

    if not file_id:
        return Response("file not found", status=404)

    try:
        file_info = requests.get(TG + "getFile", params={"file_id": file_id}, timeout=15).json()

        if not file_info.get("ok"):
            return Response("telegram getFile failed", status=502)

        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        telegram_response = requests.get(file_url, stream=True, timeout=30)

        content_type = telegram_response.headers.get("Content-Type", "audio/mpeg")

        return Response(
            telegram_response.iter_content(chunk_size=8192),
            content_type=content_type
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
        value(s, "ÙØ§ÛŒÙ„"),
        "ðŸŽ¶ Ø§ÛŒÙ† Ø³Ø±ÙˆØ¯ ØªÙ‚Ø¯ÛŒÙ… Ø¨Ù‡ Ø´Ù…Ø§\n\nðŸŽµ " + value(s, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯")
    )

    return jsonify({"ok": True})



@app.route("/api/books", methods=["GET"])
def api_books():
    rows = get_library_books()
    books = []

    for i, r in enumerate(rows):
        books.append({
            "index": i,
            "name": value(r, "Ø§Ø³Ù… Ú©ØªØ§Ø¨")
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

    rows = get_library_books()

    if index < 0 or index >= len(rows):
        return jsonify({"ok": False})

    b = rows[index]
    send_doc(chat_id, value(b, "ÙØ§ÛŒÙ„"), "ðŸ“š " + value(b, "Ø§Ø³Ù… Ú©ØªØ§Ø¨"))

    return jsonify({"ok": True})


@app.route("/api/word", methods=["GET"])
def api_word():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify({"ok": False, "error": "empty"})

    exact, partial = find_word(q)

    if exact:
        root_title = "ðŸ’¡ Ø±ÛŒØ´Ù‡ ÛŒÙˆÙ†Ø§Ù†ÛŒ" if value(exact, "Ø¹Ù‡Ø¯") == "NT" else "ðŸ’¡ Ø±ÛŒØ´Ù‡ Ø¹Ø¨Ø±ÛŒ"
        return jsonify({
            "ok": True,
            "found": True,
            "type": "exact",
            "word": value(exact, "Ú©Ù„Ù…Ù‡"),
            "meaning": value(exact, "Ù…Ø¹Ù†ÛŒ"),
            "root": value(exact, "Ø±ÛŒØ´Ù‡"),
            "root_title": root_title,
            "verse": value(exact, "Ø¢ÛŒÙ‡ Ù…Ø±ØªØ¨Ø·")
        })

    suggestions = []
    for w in partial[:20]:
        suggestions.append(value(w, "Ú©Ù„Ù…Ù‡"))

    return jsonify({
        "ok": True,
        "found": False,
        "suggestions": suggestions
    })


@app.route("/webapp", methods=["GET"])
def webapp():
    return """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ú©Ù„Ù…Ù‡â€ŒÛŒØ§Ø¨ Ùˆ Ø³Ø±ÙˆØ¯ÛŒØ§Ø¨</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:radial-gradient(circle at top,#5d347d,#1b102b 65%);color:white;padding:16px;padding-bottom:88px;text-align:center;}
.card{background:rgba(255,255,255,0.13);border:1px solid rgba(255,255,255,0.2);border-radius:28px;padding:20px;margin-bottom:16px;box-shadow:0 12px 40px rgba(0,0,0,0.35);backdrop-filter:blur(12px);}
h1{font-size:25px;margin:5px 0 12px;} h2{font-size:21px;margin:4px 0 12px;} p{line-height:1.9;font-size:15px;opacity:.94;}
button{width:100%;padding:15px;margin-top:11px;border:none;border-radius:18px;font-size:16px;font-weight:bold;color:white;cursor:pointer;box-shadow:0 8px 22px rgba(0,0,0,.28);}
.red{background:linear-gradient(135deg,#ff416c,#ff4b2b);} .blue{background:linear-gradient(135deg,#36d1dc,#5b86e5);} .green{background:linear-gradient(135deg,#56ab2f,#a8e063);color:#102000;} .gold{background:linear-gradient(135deg,#f7971e,#ffd200);color:#2b1900;} .purple{background:linear-gradient(135deg,#8e2de2,#4a00e0);} .darkbtn{background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.18);}
input{width:100%;box-sizing:border-box;padding:15px;border-radius:18px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.12);color:white;margin-top:12px;font-size:16px;text-align:right;outline:none;} input::placeholder{color:rgba(255,255,255,.7);}
.item{background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,.14);padding:13px;border-radius:16px;margin-top:10px;cursor:pointer;text-align:right;}
.small{font-size:13px;opacity:.82;margin-top:10px;line-height:1.7;}
.player-card{display:none;background:rgba(255,255,255,0.13);border:1px solid rgba(255,255,255,.18);border-radius:22px;padding:16px;margin-top:16px;text-align:right;}
.player-title{font-size:16px;font-weight:bold;margin-bottom:12px;} audio{width:100%;margin-top:10px;} .player-actions{display:flex;gap:10px;margin-top:10px;} .player-actions button{flex:1;font-size:14px;padding:13px;}
.tab-page{display:none;} .tab-page.active{display:block;}
.result-box{display:none;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);border-radius:20px;padding:16px;margin-top:15px;text-align:right;line-height:2;white-space:pre-wrap;}
.word-buttons{display:none;gap:10px;margin-top:12px;} .word-buttons button{font-size:14px;padding:12px;}
.bottom-nav{position:fixed;bottom:0;left:0;right:0;background:rgba(20,13,35,.92);backdrop-filter:blur(18px);border-top:1px solid rgba(255,255,255,.18);display:flex;justify-content:space-around;padding:9px 6px 12px;z-index:10;}
.nav-item{flex:1;color:rgba(255,255,255,.72);font-size:12px;padding:7px 2px;border-radius:14px;} .nav-item.active{color:white;background:rgba(255,255,255,.13);} .nav-icon{font-size:20px;display:block;margin-bottom:3px;}
</style>
</head>
<body>

<div id="songsPage" class="tab-page active">
  <div class="card">
    <h1>ðŸŽ¼ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ù¾Ø±Ø³ØªØ´ÛŒ</h1>
    <p>Ø¨Ù‡ Ø¨Ø®Ø´ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ø±Ø¨Ø§Øª Â«Ú©Ù„Ù…Ù‡â€ŒÛŒØ§Ø¨ Ùˆ Ø³Ø±ÙˆØ¯ÛŒØ§Ø¨Â» Ø®ÙˆØ´ Ø¢Ù…Ø¯ÛŒØ¯.<br>Ø§Ø² Ú¯Ø²ÛŒÙ†Ù‡â€ŒÙ‡Ø§ÛŒ Ø²ÛŒØ± Ù…ÛŒâ€ŒØªÙˆØ§Ù†ÛŒØ¯ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ù…Ù†Ø§Ø³Ø¨ØªÛŒ ÛŒØ§ Ù„ÛŒØ³Øª Ú©Ø§Ù…Ù„ Ø³Ø±ÙˆØ¯Ù‡Ø§ Ø±Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†ÛŒØ¯.</p>
    <button class="gold" onclick="loadCategory(0)">âœï¸ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ø¹ÛŒØ¯ Ù‚ÛŒØ§Ù…</button>
    <button class="blue" onclick="loadCategory(1)">ðŸŽ„ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ ØªÙˆÙ„Ø¯ Ù…Ø³ÛŒØ­</button>
    <button class="red" onclick="loadCategory(2)">ðŸ©¸ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ø¬Ù…Ø¹Ù‡ ØµÙ„ÛŒØ¨</button>
    <button class="green" onclick="loadSongs()">ðŸŽ¼ Ù„ÛŒØ³Øª Ú©Ø§Ù…Ù„ Ø³Ø±ÙˆØ¯Ù‡Ø§</button>
  </div>
  <div class="card">
    <input id="songSearch" placeholder="ðŸ” Ø¬Ø³ØªØ¬ÙˆÛŒ Ù†Ø§Ù… Ø³Ø±ÙˆØ¯..." oninput="filterSongs()">
    <div class="small">Ø¨Ø±Ø§ÛŒ Ù¾Ø®Ø´ Ø³Ø±ÙˆØ¯ØŒ Ø±ÙˆÛŒ Ù†Ø§Ù… Ø¢Ù† Ø¨Ø²Ù†ÛŒØ¯.</div>
    <div id="songStatus" class="small"></div>
    <div id="playerCard" class="player-card">
      <div id="playerTitle" class="player-title">ðŸŽµ Ù†Ø§Ù… Ø³Ø±ÙˆØ¯</div>
      <audio id="audioPlayer" controls></audio>
      <div class="player-actions">
        <button class="green" onclick="sendSelectedSong()">ðŸ“© Ø§Ø±Ø³Ø§Ù„ Ø¯Ø± ØªÙ„Ú¯Ø±Ø§Ù…</button>
        <button class="red" onclick="closePlayer()">Ø¨Ø³ØªÙ†</button>
      </div>
    </div>
    <div id="songs"></div>
  </div>
</div>

<div id="booksPage" class="tab-page">
  <div class="card">
    <h1>ðŸ“š Ú©ØªØ§Ø¨Ø®Ø§Ù†Ù‡</h1>
    <p>Ú©ØªØ§Ø¨ Ù…ÙˆØ±Ø¯ Ù†Ø¸Ø± Ø®ÙˆØ¯ Ø±Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†ÛŒØ¯ ØªØ§ ÙØ§ÛŒÙ„ Ø¢Ù† Ø¯Ø± ØªÙ„Ú¯Ø±Ø§Ù… Ø¨Ø±Ø§ÛŒ Ø´Ù…Ø§ Ø§Ø±Ø³Ø§Ù„ Ø´ÙˆØ¯.</p>
    <button class="green" onclick="loadBooks()">ðŸ“š Ù†Ù…Ø§ÛŒØ´ Ú©ØªØ§Ø¨â€ŒÙ‡Ø§</button>
  </div>
  <div class="card">
    <input id="bookSearch" placeholder="ðŸ” Ø¬Ø³ØªØ¬ÙˆÛŒ Ù†Ø§Ù… Ú©ØªØ§Ø¨..." oninput="filterBooks()">
    <div id="bookStatus" class="small"></div>
    <div id="books"></div>
  </div>
</div>

<div id="wordsPage" class="tab-page">
  <div class="card">
    <h1>ðŸ“– Ú©Ù„Ù…Ø§Øª Ú©ØªØ§Ø¨â€ŒÙ…Ù‚Ø¯Ø³</h1>
    <p>Ù†Ø§Ù… Ú©Ù„Ù…Ù‡ØŒ Ù…Ú©Ø§Ù† ÛŒØ§ Ø´Ø®ØµÛŒØª Ú©ØªØ§Ø¨â€ŒÙ…Ù‚Ø¯Ø³ Ø±Ø§ Ø¬Ø³ØªØ¬Ùˆ Ú©Ù†ÛŒØ¯.</p>
    <input id="wordSearch" placeholder="Ù…Ø«Ø§Ù„: Ø§Ø¨Ø§" onkeydown="if(event.key==='Enter') searchWord()">
    <button class="purple" onclick="searchWord()">ðŸ” Ø¬Ø³ØªØ¬Ùˆ</button>
    <div id="wordStatus" class="small"></div>
    <div id="wordButtons" class="word-buttons">
      <button class="green" onclick="showWordPart('meaning')">ðŸ“– Ù…Ø¹Ù†ÛŒ</button>
      <button class="gold" onclick="showWordPart('root')">ðŸ’¡ Ø±ÛŒØ´Ù‡</button>
      <button class="blue" onclick="showWordPart('verse')">ðŸ“œ Ø¢ÛŒÙ‡ Ù…Ø±ØªØ¨Ø·</button>
    </div>
    <div id="wordResult" class="result-box"></div>
    <div id="wordSuggestions"></div>
  </div>
</div>

<div class="bottom-nav">
  <div id="navSongs" class="nav-item active" onclick="showTab('songs')"><span class="nav-icon">ðŸŽ¼</span>Ø³Ø±ÙˆØ¯Ù‡Ø§</div>
  <div id="navBooks" class="nav-item" onclick="showTab('books')"><span class="nav-icon">ðŸ“š</span>Ú©ØªØ§Ø¨Ø®Ø§Ù†Ù‡</div>
  <div id="navWords" class="nav-item" onclick="showTab('words')"><span class="nav-icon">ðŸ“–</span>Ú©Ù„Ù…Ø§Øª</div>
</div>

<script>
Telegram.WebApp.ready(); Telegram.WebApp.expand();
let allSongs=[]; let currentSource="songs"; let currentPage=0; const songsPerPage=30; let selectedSong=null; let allBooks=[]; let currentWordData=null;
function getChatId(){const user=Telegram.WebApp.initDataUnsafe&&Telegram.WebApp.initDataUnsafe.user;return user?user.id:null;}
function showTab(tab){document.querySelectorAll(".tab-page").forEach(p=>p.classList.remove("active"));document.querySelectorAll(".nav-item").forEach(n=>n.classList.remove("active")); if(tab==="songs"){songsPage.classList.add("active");navSongs.classList.add("active");} if(tab==="books"){booksPage.classList.add("active");navBooks.classList.add("active");} if(tab==="words"){wordsPage.classList.add("active");navWords.classList.add("active");}}
function setSongStatus(t){songStatus.innerText=t||"";}
async function loadSongs(){currentSource="songs";closePlayer();setSongStatus("â³ Ø¯Ø± Ø­Ø§Ù„ Ø¯Ø±ÛŒØ§ÙØª Ù„ÛŒØ³Øª Ø³Ø±ÙˆØ¯Ù‡Ø§...");const res=await fetch("/api/songs");const data=await res.json();allSongs=data.songs||[];currentPage=0;songSearch.value="";renderSongPage();setSongStatus("ðŸŽ¼ Ù„ÛŒØ³Øª Ú©Ø§Ù…Ù„ Ø³Ø±ÙˆØ¯Ù‡Ø§");}
async function loadCategory(index){currentSource="category";closePlayer();setSongStatus("â³ Ø¯Ø± Ø­Ø§Ù„ Ø¯Ø±ÛŒØ§ÙØª Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ù…Ù†Ø§Ø³Ø¨ØªÛŒ...");const res=await fetch("/api/category/"+index);const data=await res.json();allSongs=data.songs||[];currentPage=0;songSearch.value="";renderSongPage();setSongStatus(data.title||"ðŸŽµ Ø³Ø±ÙˆØ¯Ù‡Ø§ÛŒ Ù…Ù†Ø§Ø³Ø¨ØªÛŒ");}
function renderSongPage(){const start=currentPage*songsPerPage;const end=start+songsPerPage;renderSongs(allSongs.slice(start,end),true);}
function renderSongs(songs,showPagination){songsDiv=document.getElementById("songs");songsDiv.innerHTML=""; if(!songs.length){songsDiv.innerHTML="<div class='small'>Ù…ÙˆØ±Ø¯ÛŒ Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯.</div>";return;} songs.forEach(song=>{const div=document.createElement("div");div.className="item";div.innerText="ðŸŽµ "+song.name;div.onclick=()=>openPlayer(song);songsDiv.appendChild(div);}); if(showPagination) renderSongPagination(songsDiv);}
function renderSongPagination(container){const totalPages=Math.ceil(allSongs.length/songsPerPage); if(totalPages<=1)return; const pageInfo=document.createElement("div");pageInfo.className="small";pageInfo.innerText="ØµÙØ­Ù‡ "+(currentPage+1)+" Ø§Ø² "+totalPages;container.appendChild(pageInfo); const nav=document.createElement("div");nav.style.marginTop="12px";nav.style.display="flex";nav.style.gap="10px"; const prev=document.createElement("button");prev.innerText="â¬…ï¸ ØµÙØ­Ù‡ Ù‚Ø¨Ù„";prev.className="blue";prev.style.flex="1";prev.disabled=currentPage===0;prev.style.opacity=currentPage===0?"0.45":"1";prev.onclick=()=>{if(currentPage>0){currentPage--;closePlayer();renderSongPage();window.scrollTo({top:0,behavior:"smooth"});}}; const next=document.createElement("button");next.innerText="ØµÙØ­Ù‡ Ø¨Ø¹Ø¯ âž¡ï¸";next.className="purple";next.style.flex="1";next.disabled=currentPage>=totalPages-1;next.style.opacity=currentPage>=totalPages-1?"0.45":"1";next.onclick=()=>{if(currentPage<totalPages-1){currentPage++;closePlayer();renderSongPage();window.scrollTo({top:0,behavior:"smooth"});}}; nav.appendChild(prev);nav.appendChild(next);container.appendChild(nav);}
function filterSongs(){const q=songSearch.value.toLowerCase().trim(); if(!q){renderSongPage();return;} const filtered=allSongs.filter(s=>(s.name||"").toLowerCase().includes(q));renderSongs(filtered.slice(0,100),false);setSongStatus(filtered.length>100?"ðŸ” Ø¨ÛŒØ´ Ø§Ø² Û±Û°Û° Ù†ØªÛŒØ¬Ù‡ Ù¾ÛŒØ¯Ø§ Ø´Ø¯Ø› Ù„Ø·ÙØ§Ù‹ Ø¯Ù‚ÛŒÙ‚â€ŒØªØ± Ø¬Ø³ØªØ¬Ùˆ Ú©Ù†ÛŒØ¯.":"ðŸ” Ù†ØªÛŒØ¬Ù‡ Ø¬Ø³ØªØ¬Ùˆ: "+filtered.length+" Ù…ÙˆØ±Ø¯");}
function openPlayer(song){selectedSong=song;playerTitle.innerText="ðŸŽµ "+song.name;audioPlayer.src="/api/audio?source="+currentSource+"&index="+song.index;playerCard.style.display="block";setSongStatus("ðŸŽ§ Ø¨Ø±Ø§ÛŒ Ù¾Ø®Ø´ØŒ Ø¯Ú©Ù…Ù‡ Play Ø±Ø§ Ø¨Ø²Ù†ÛŒØ¯.");playerCard.scrollIntoView({behavior:"smooth",block:"start"});}
function closePlayer(){audioPlayer.pause();audioPlayer.removeAttribute("src");audioPlayer.load();playerCard.style.display="none";selectedSong=null;}
async function sendSelectedSong(){if(!selectedSong){setSongStatus("Ø§Ø¨ØªØ¯Ø§ ÛŒÚ© Ø³Ø±ÙˆØ¯ Ø±Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†ÛŒØ¯.");return;} await sendSong(selectedSong.index);}
async function sendSong(index){const chatId=getChatId(); if(!chatId){alert("Ù„Ø·ÙØ§Ù‹ Ø§ÛŒÙ† ØµÙØ­Ù‡ Ø±Ø§ Ø§Ø² Ø¯Ø§Ø®Ù„ ØªÙ„Ú¯Ø±Ø§Ù… Ø¨Ø§Ø² Ú©Ù†ÛŒØ¯.");return;} setSongStatus("â³ Ø¯Ø± Ø­Ø§Ù„ Ø§Ø±Ø³Ø§Ù„ Ø³Ø±ÙˆØ¯...");const res=await fetch("/api/send_song",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({chat_id:chatId,index:index,source:currentSource})});const data=await res.json();setSongStatus(data.ok?"âœ… Ø³Ø±ÙˆØ¯ Ø¯Ø± ØªÙ„Ú¯Ø±Ø§Ù… Ø¨Ø±Ø§ÛŒ Ø´Ù…Ø§ Ø§Ø±Ø³Ø§Ù„ Ø´Ø¯.":"âŒ Ø§Ø±Ø³Ø§Ù„ Ø³Ø±ÙˆØ¯ Ø§Ù†Ø¬Ø§Ù… Ù†Ø´Ø¯.");}
async function loadBooks(){bookStatus.innerText="â³ Ø¯Ø± Ø­Ø§Ù„ Ø¯Ø±ÛŒØ§ÙØª Ú©ØªØ§Ø¨â€ŒÙ‡Ø§...";const res=await fetch("/api/books");const data=await res.json();allBooks=data.books||[];bookSearch.value="";renderBooks(allBooks);bookStatus.innerText="ðŸ“š Ú©ØªØ§Ø¨Ø®Ø§Ù†Ù‡";}
function renderBooks(books){booksDiv=document.getElementById("books");booksDiv.innerHTML=""; if(!books.length){booksDiv.innerHTML="<div class='small'>Ú©ØªØ§Ø¨ÛŒ Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯.</div>";return;} books.forEach(book=>{const div=document.createElement("div");div.className="item";div.innerText="ðŸ“– "+book.name;div.onclick=()=>sendBook(book.index);booksDiv.appendChild(div);});}
function filterBooks(){const q=bookSearch.value.toLowerCase().trim(); if(!q){renderBooks(allBooks);return;} const filtered=allBooks.filter(b=>(b.name||"").toLowerCase().includes(q));renderBooks(filtered);}
async function sendBook(index){const chatId=getChatId(); if(!chatId){alert("Ù„Ø·ÙØ§Ù‹ Ø§ÛŒÙ† ØµÙØ­Ù‡ Ø±Ø§ Ø§Ø² Ø¯Ø§Ø®Ù„ ØªÙ„Ú¯Ø±Ø§Ù… Ø¨Ø§Ø² Ú©Ù†ÛŒØ¯.");return;} bookStatus.innerText="â³ Ø¯Ø± Ø­Ø§Ù„ Ø§Ø±Ø³Ø§Ù„ Ú©ØªØ§Ø¨...";const res=await fetch("/api/send_book",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({chat_id:chatId,index:index})});const data=await res.json();bookStatus.innerText=data.ok?"âœ… Ú©ØªØ§Ø¨ Ø¯Ø± ØªÙ„Ú¯Ø±Ø§Ù… Ø¨Ø±Ø§ÛŒ Ø´Ù…Ø§ Ø§Ø±Ø³Ø§Ù„ Ø´Ø¯.":"âŒ Ø§Ø±Ø³Ø§Ù„ Ú©ØªØ§Ø¨ Ø§Ù†Ø¬Ø§Ù… Ù†Ø´Ø¯.";}
async function searchWord(){const q=wordSearch.value.trim(); if(!q){wordStatus.innerText="Ù„Ø·ÙØ§Ù‹ ÛŒÚ© Ú©Ù„Ù…Ù‡ ÙˆØ§Ø±Ø¯ Ú©Ù†ÛŒØ¯.";return;} wordStatus.innerText="â³ Ø¯Ø± Ø­Ø§Ù„ Ø¬Ø³ØªØ¬Ùˆ...";wordResult.style.display="none";wordButtons.style.display="none";wordSuggestions.innerHTML=""; const res=await fetch("/api/word?q="+encodeURIComponent(q)); const data=await res.json(); if(data.found){currentWordData=data;wordStatus.innerText="ðŸ” Ø§Ø·Ù„Ø§Ø¹Ø§Øª Â«"+data.word+"Â» ÛŒØ§ÙØª Ø´Ø¯.";wordButtons.style.display="flex";wordButtons.style.flexDirection="column";}else{currentWordData=null;wordStatus.innerText="Ù…ÙˆØ±Ø¯ Ø¯Ù‚ÛŒÙ‚ Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯."; if(data.suggestions&&data.suggestions.length){wordSuggestions.innerHTML="<div class='small'>Ù…ÙˆØ§Ø±Ø¯ Ù†Ø²Ø¯ÛŒÚ©:</div>";data.suggestions.forEach(w=>{const div=document.createElement("div");div.className="item";div.innerText="ðŸ” "+w;div.onclick=()=>{wordSearch.value=w;searchWord();};wordSuggestions.appendChild(div);});}}}
function showWordPart(part){if(!currentWordData)return; wordResult.style.display="block"; if(part==="meaning") wordResult.innerText="ðŸ“– Ù…Ø¹Ù†ÛŒ:\n\n"+(currentWordData.meaning||"Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª."); if(part==="root") wordResult.innerText=(currentWordData.root_title||"ðŸ’¡ Ø±ÛŒØ´Ù‡")+":\n\n"+(currentWordData.root||"Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª."); if(part==="verse") wordResult.innerText="ðŸ“œ Ø¢ÛŒÙ‡ Ù…Ø±ØªØ¨Ø·:\n\n"+(currentWordData.verse||"Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª."); wordResult.scrollIntoView({behavior:"smooth",block:"start"});}
</script>
</body>
</html>
"""


# Rest of bot functions below
def find_word(text):
    exact = None
    partial = []

    for r in sheet("Word"):
        word = value(r, "Ú©Ù„Ù…Ù‡")
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
        root = "ðŸ’¡ Ø±ÛŒØ´Ù‡ ÛŒÙˆÙ†Ø§Ù†ÛŒ" if value(w, "Ø¹Ù‡Ø¯") == "NT" else "ðŸ’¡ Ø±ÛŒØ´Ù‡ Ø¹Ø¨Ø±ÛŒ"

        send_msg(chat_id, f"ðŸ” Ø§Ø·Ù„Ø§Ø¹Ø§Øª Ú©Ù„Ù…Ù‡ Â«{value(w, 'Ú©Ù„Ù…Ù‡')}Â» ÛŒØ§ÙØª Ø´Ø¯:",
                 {"inline_keyboard": [
                     [{"text": "ðŸ“œ Ø¢ÛŒÙ‡ Ù…Ø±ØªØ¨Ø·", "callback_data": f"wverse|{value(w, 'Ú©Ù„Ù…Ù‡')}"}],
                     [{"text": "ðŸ“– Ù…Ø¹Ù†ÛŒ", "callback_data": f"wmean|{value(w, 'Ú©Ù„Ù…Ù‡')}"}],
                     [{"text": root, "callback_data": f"wroot|{value(w, 'Ú©Ù„Ù…Ù‡')}"}],
                 ]})
        return

    if partial:
        buttons = [
            [{"text": "ðŸ” " + value(w, "Ú©Ù„Ù…Ù‡"), "callback_data": f"wordchoose|{value(w, 'Ú©Ù„Ù…Ù‡')}"}]
            for w in partial[:10]
        ]
        send_msg(chat_id, "ðŸ” Ú†Ù†Ø¯ Ù…ÙˆØ±Ø¯ Ù†Ø²Ø¯ÛŒÚ© Ù¾ÛŒØ¯Ø§ Ø´Ø¯:", {"inline_keyboard": buttons})
        return

    not_found(chat_id)


def search_song(chat_id, text):
    query = norm(text.replace("Ø³Ø±ÙˆØ¯", "", 1))

    if not query:
        send_msg(chat_id, "ðŸŽµ Ù„Ø·ÙØ§Ù‹ Ø¨Ø¹Ø¯ Ø§Ø² Ú©Ù„Ù…Ù‡ Â«Ø³Ø±ÙˆØ¯Â» Ø§Ø³Ù… Ø³Ø±ÙˆØ¯ Ø±Ø§ Ø¨Ù†ÙˆÛŒØ³ÛŒØ¯.")
        return

    exact = None
    partial = []

    for s in sheet("Songs", use_cache=False):
        song_name = value(s, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯")
        file_id = value(s, "ÙØ§ÛŒÙ„")

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
        send_audio(chat_id, value(chosen, "ÙØ§ÛŒÙ„"), "ðŸŽ¶ Ø§ÛŒÙ† Ø³Ø±ÙˆØ¯ ØªÙ‚Ø¯ÛŒÙ… Ø¨Ù‡ Ø´Ù…Ø§\n\nðŸŽµ " + value(chosen, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯"))
        return

    not_found(chat_id)


def library(chat_id):
    books = get_library_books()

    if not books:
        send_msg(chat_id, "ðŸ“š Ù‡Ù†ÙˆØ² Ú©ØªØ§Ø¨ÛŒ Ø¯Ø± Ú©ØªØ§Ø¨Ø®Ø§Ù†Ù‡ Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª.")
        return

    buttons = [
        [{"text": "ðŸ“– " + value(b, "Ø§Ø³Ù… Ú©ØªØ§Ø¨"), "callback_data": f"book|{i}"}]
        for i, b in enumerate(books)
    ]

    send_msg(chat_id, "ðŸ“š Ú©ØªØ§Ø¨ Ù…ÙˆØ±Ø¯ Ù†Ø¸Ø± Ø±Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†ÛŒØ¯:", {"inline_keyboard": buttons})


def song_list(chat_id, page=0):
    songs = get_all_songs()

    if not songs:
        send_msg(chat_id, "ðŸŽ¼ Ù‡Ù†ÙˆØ² Ø³Ø±ÙˆØ¯ÛŒ Ø¯Ø± Ù„ÛŒØ³Øª Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª.")
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
        song_name = value(songs[i], "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯")
        buttons.append([{
            "text": f"ðŸŽµ {song_name}",
            "callback_data": f"allsong|{i}"
        }])

    nav = []
    if page > 0:
        nav.append({"text": "â¬…ï¸ ØµÙØ­Ù‡ Ù‚Ø¨Ù„", "callback_data": f"songpage|{page - 1}"})
    if page < total_pages - 1:
        nav.append({"text": "ØµÙØ­Ù‡ Ø¨Ø¹Ø¯ âž¡ï¸", "callback_data": f"songpage|{page + 1}"})

    if nav:
        buttons.append(nav)

    buttons.append([{"text": "â¬…ï¸ Ø¨Ø±Ú¯Ø´Øª", "callback_data": "songs_menu"}])

    send_msg(
        chat_id,
        f"ðŸŽ¼ Ù„ÛŒØ³Øª Ø³Ø±ÙˆØ¯Ù‡Ø§ â€” ØµÙØ­Ù‡ {page + 1} Ø§Ø² {total_pages}\n\nØ¨Ø±Ø§ÛŒ Ø¯Ø±ÛŒØ§ÙØªØŒ Ø±ÙˆÛŒ Ù†Ø§Ù… Ø³Ø±ÙˆØ¯ Ø¨Ø²Ù†ÛŒØ¯:",
        {"inline_keyboard": buttons}
    )


def promise(chat_id):
    rows = [r for r in sheet("Promises") if value(r, "Ù…ØªÙ† ÙˆØ¹Ø¯Ù‡")]

    if not rows:
        send_msg(chat_id, "ðŸ“© Ù‡Ù†ÙˆØ² ÙˆØ¹Ø¯Ù‡â€ŒØ§ÛŒ Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª.")
        return

    r = random.choice(rows)
    send_msg(
        chat_id,
        f"ðŸ“© ÙˆØ¹Ø¯Ù‡â€Œ Ø§Ù…Ø±ÙˆØ² Ø®Ø¯Ø§ÙˆÙ†Ø¯ Ø¨Ø±Ø§ÛŒ Ø´Ù…Ø§ :\n\nâœ¨ {value(r, 'Ù…ØªÙ† ÙˆØ¹Ø¯Ù‡')}\n\nðŸ“– {value(r, 'Ø¢ÛŒÙ‡')}",
        {"inline_keyboard": [[{"text": "ðŸ“© ÙˆØ¹Ø¯Ù‡ Ø¨Ø¹Ø¯ÛŒ", "callback_data": "promise_next"}]]}
    )


def fact(chat_id):
    rows = [r for r in sheet("Facts") if value(r, "Ù…ØªÙ† Ø¯Ø§Ù†Ø³ØªÙ†ÛŒ")]

    if not rows:
        send_msg(chat_id, "ðŸ’¡ Ù‡Ù†ÙˆØ² Ø¯Ø§Ù†Ø³ØªÙ†ÛŒ Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª.")
        return

    r = random.choice(rows)
    send_msg(
        chat_id,
        f"ðŸ’¡ Ø¢ÛŒØ§ Ù…ÛŒØ¯Ø§Ù†Ø³ØªÛŒØ¯:\n\nâ–«ï¸ {value(r, 'Ù…ØªÙ† Ø¯Ø§Ù†Ø³ØªÙ†ÛŒ')}\n\nðŸ“ {value(r, 'Ù…Ù†Ø¨Ø¹')}",
        {"inline_keyboard": [[{"text": "ðŸ’¡ Ø¯Ø§Ù†Ø³ØªÙ†ÛŒ Ø¨Ø¹Ø¯ÛŒ", "callback_data": "fact_next"}]]}
    )


def prayer_menu(chat_id):
    send_msg(chat_id, "ÛŒÚ©ÛŒ Ø§Ø² Ú¯Ø²ÛŒÙ†Ù‡â€ŒÙ‡Ø§ Ø±Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†ÛŒØ¯ ðŸ‘‡",
             {"inline_keyboard": [
                 [{"text": "âœï¸ Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§", "callback_data": "prayer_request"}],
                 [{"text": "ðŸ™Œ Ø¯Ø¹Ø§ Ø¨Ø±Ø§ÛŒ ÛŒÚ©Ø¯ÛŒÚ¯Ø±", "callback_data": "prayer_random"}],
             ]})


def ask_prayer_visibility(chat_id):
    send_msg(
        chat_id,
        "Ø§ÛŒÙ…Ø§Ù†Ø¯Ø§Ø±Ø§Ù† Ú¯Ø±Ø§Ù…ÛŒ ØŒ Ù…Ø§ÛŒÙ„ Ù‡Ø³ØªÛŒØ¯ Ø¯Ø¹Ø§ÛŒ Ø´Ù…Ø§ Ø¨Ù‡ Ú†Ù‡ ØµÙˆØ±ØªÛŒ Ø¨Ø±Ø§ÛŒ Ø¯ÛŒÚ¯Ø±Ø§Ù† Ù†Ù…Ø§ÛŒØ´ Ø¯Ø§Ø¯Ù‡ Ø´ÙˆØ¯ØŸ",
        {"inline_keyboard": [
            [{"text": "ðŸ•µ Ø¨Ø§ Ù†Ø§Ù… Ø®ÙˆØ¯Ù…", "callback_data": "prayer_visibility|name"}],
            [{"text": "ðŸ‘¤ Ø¨ØµÙˆØ±Øª Ù†Ø§Ø´Ù†Ø§Ø³", "callback_data": "prayer_visibility|anon"}],
        ]}
    )


def receive_prayer_text(chat_id, text, user):
    state = PRAYER_STATES.get(str(chat_id), {})
    visibility = state.get("visibility", "anon")
    user_name = state.get("name", get_user_name(user))

    if visibility == "name":
        display_name = user_name
        public_text = f"Ø§Ø² Ø·Ø±Ù {display_name}: {text}"
    else:
        display_name = "Ù†Ø§Ø´Ù†Ø§Ø³"
        public_text = text

    pending_id = str(int(time.time() * 1000))
    PENDING_PRAYERS[pending_id] = {
        "user_chat_id": chat_id,
        "display_name": display_name,
        "public_text": public_text,
        "original_text": text
    }

    PRAYER_STATES.pop(str(chat_id), None)

    send_msg(chat_id, "ðŸ™ Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ÛŒ Ø´Ù…Ø§ Ø¯Ø±ÛŒØ§ÙØª Ø´Ø¯ Ùˆ Ù¾Ø³ Ø§Ø² ØªØ§ÛŒÛŒØ¯ Ø®Ø§Ø¯Ù…ÛŒÙ† Ø¯Ø± Ø¨Ø®Ø´ Ø¯Ø¹Ø§ Ù†Ù…Ø§ÛŒØ´ Ø¯Ø§Ø¯Ù‡ Ù…ÛŒâ€ŒØ´ÙˆØ¯.")

    admin_text = (
        "ðŸ™ Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ÛŒ Ø¬Ø¯ÛŒØ¯ Ø¨Ø±Ø§ÛŒ ØªØ§ÛŒÛŒØ¯\n\n"
        f"ðŸ‘¤ Ù†Ù…Ø§ÛŒØ´ Ø¨Ø±Ø§ÛŒ Ø¯ÛŒÚ¯Ø±Ø§Ù†: {display_name}\n\n"
        f"ðŸ“ Ù…ØªÙ† Ø¯Ø¹Ø§:\n{text}"
    )

    send_msg(
        ADMIN_CHAT_ID,
        admin_text,
        {"inline_keyboard": [
            [{"text": "âœ… ØªØ§ÛŒÛŒØ¯", "callback_data": f"approve_prayer|{pending_id}"}],
            [{"text": "âŒ Ø±Ø¯", "callback_data": f"reject_prayer|{pending_id}"}],
        ]}
    )


def save_prayer(chat_id, text):
    prayer = text.replace("Ø¯Ø¹Ø§:", "", 1).strip()

    if not prayer:
        send_msg(chat_id, "ðŸ™ Ù„Ø·ÙØ§Ù‹ Ø¨Ø¹Ø¯ Ø§Ø² Â«Ø¯Ø¹Ø§:Â» Ù…ØªÙ† Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ÛŒ Ø®ÙˆØ¯ Ø±Ø§ Ø¨Ù†ÙˆÛŒØ³ÛŒØ¯.")
        return

    result = writer({"type": "prayer", "text": prayer})

    if result.get("ok"):
        clear_cache("Prayers")
        send_msg(chat_id, "ðŸ™ Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ÛŒ Ø´Ù…Ø§ Ø¨Ù‡ ØµÙˆØ±Øª Ù†Ø§Ø´Ù†Ø§Ø³ Ø«Ø¨Øª Ø´Ø¯.\nØ®Ø§Ø¯Ù…ÛŒÙ† Ø¨Ø±Ø§ÛŒ Ø´Ù…Ø§ Ø¯Ø¹Ø§ Ø®ÙˆØ§Ù‡Ù†Ø¯ Ú©Ø±Ø¯ ðŸ™")
    else:
        send_msg(chat_id, "Ù…ØªØ£Ø³ÙØ§Ù†Ù‡ Ø«Ø¨Øª Ø¯Ø¹Ø§ Ø§Ù†Ø¬Ø§Ù… Ù†Ø´Ø¯. Ù„Ø·ÙØ§Ù‹ Ø¯ÙˆØ¨Ø§Ø±Ù‡ ØªÙ„Ø§Ø´ Ú©Ù†ÛŒØ¯.")


def random_prayer(chat_id):
    rows = sheet("Prayers", use_cache=False)
    valid = []

    for i, r in enumerate(rows, start=2):
        if value(r, "Ù…ØªÙ† Ø¯Ø¹Ø§"):
            valid.append((i, r))

    if not valid:
        send_msg(chat_id, "ðŸ™ Ù‡Ù†ÙˆØ² Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ÛŒÛŒ Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª.")
        return

    row_number, r = random.choice(valid)
    count = value(r, "ØªØ¹Ø¯Ø§Ø¯ Ø¯Ø¹Ø§") or "0"

    send_msg(chat_id,
             f"ðŸ™ Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§: {value(r, 'Ù…ØªÙ† Ø¯Ø¹Ø§')}\n\nâ­•ï¸ {count} Ù†ÙØ± Ø¨Ø±Ø§ÛŒ Ø§ÛŒÙ† Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ Ú©Ø±Ø¯Ù†Ø¯",
             {"inline_keyboard": [
                 [{"text": "ðŸ™Œ Ù…Ù† Ù‡Ù… Ø¯Ø¹Ø§ Ú©Ø±Ø¯Ù…", "callback_data": f"praydone|{row_number}"}],
                 [{"text": "âœï¸ Ø«Ø¨Øª Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§", "callback_data": "prayer_request"}],
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

        if text != "/start":
            send_msg(chat_id, "â³ Ø¯Ø± Ø­Ø§Ù„ Ø¢Ù…Ø§Ø¯Ù‡â€ŒØ³Ø§Ø²ÛŒ...")

        if str(chat_id) in PRAYER_STATES and PRAYER_STATES[str(chat_id)].get("step") == "awaiting_text":
            receive_prayer_text(chat_id, text, user)
            return "ok"

        if text == "/start":
            welcome(chat_id)
        elif text == "âš ï¸ Ø±Ø§Ù‡Ù†Ù…Ø§" or text == "ðŸ•Šï¸ Ø±Ø§Ù‡Ù†Ù…Ø§ÛŒ Ø±Ø¨Ø§Øª":
            guide(chat_id)
        elif text == "ðŸ“£ Ú©Ø§Ù†Ø§Ù„" or text == "ðŸ“£ Ú©Ø§Ù†Ø§Ù„ ØªÙ„Ú¯Ø±Ø§Ù…":
            channel(chat_id)
        elif text == "âœ¨ ÙˆØ±ÙˆØ¯ Ø¨Ù‡ Ø§Ù¾Ù„ÛŒÚ©ÛŒØ´Ù†":
            songs_menu(chat_id)
        elif text == "ðŸŽ¼ Ø³Ø±ÙˆØ¯Ù‡Ø§":
            songs_menu(chat_id)
        elif text == "ðŸ“š Ú©ØªØ§Ø¨Ø®Ø§Ù†Ù‡":
            library(chat_id)
        elif text == "ðŸ™ Ø¯Ø¹Ø§ Ø¨Ø±Ø§ÛŒ ÛŒÚ©Ø¯ÛŒÚ¯Ø±" or text == "ðŸ™ Ø¯Ø¹Ø§" or text == "ðŸ™ Ø¯Ø¹Ø§ Ú©Ù†ÛŒÙ…":
            prayer_menu(chat_id)
        elif text == "ðŸ“– Ú©Ù„Ù…Ø§Øª Ú©ØªØ§Ø¨ Ù…Ù‚Ø¯Ø³":
            word_instruction(chat_id)
        elif text == "ðŸ“© ÙˆØ¹Ø¯Ù‡â€ŒÙ‡Ø§ÛŒ Ø®Ø¯Ø§":
            promise(chat_id)
        elif text == "ðŸ’¡ Ø¯Ø§Ù†Ø³ØªÙ†ÛŒâ€ŒÙ‡Ø§ÛŒ Ø¬Ø§Ù„Ø¨":
            fact(chat_id)
        elif text == "ðŸŽ¼ Ù„ÛŒØ³Øª Ø³Ø±ÙˆØ¯Ù‡Ø§":
            song_list(chat_id, 0)
        elif text == "ðŸŽµ ÛŒÚ© Ø³Ø±ÙˆØ¯ Ø¨Ø±Ø§Ù… Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†":
            random_song(chat_id)
        elif text.startswith("Ø¯Ø¹Ø§:"):
            save_prayer(chat_id, text)
        elif norm(text).startswith("Ø³Ø±ÙˆØ¯ "):
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
            send_doc(chat_id, value(b, "ÙØ§ÛŒÙ„"), "ðŸ“š " + value(b, "Ø§Ø³Ù… Ú©ØªØ§Ø¨"))

        elif cb.startswith("cat|"):
            cat_index = int(cb.split("|", 1)[1])
            cat_value = SONG_CATEGORIES[cat_index]["value"]
            cat_button = SONG_CATEGORIES[cat_index]["button"]

            all_category_songs = get_category_songs()

            songs = [
                {"index": i, "row": r}
                for i, r in enumerate(all_category_songs)
                if norm(value(r, "Ù…Ù†Ø§Ø³Ø¨Øª")) == norm(cat_value)
            ]

            if not songs:
                send_msg(chat_id, f"ðŸŽµ Ù‡Ù†ÙˆØ² Ø³Ø±ÙˆØ¯ÛŒ Ø¨Ø±Ø§ÛŒ Ø§ÛŒÙ† Ù…Ù†Ø§Ø³Ø¨Øª Ø«Ø¨Øª Ù†Ø´Ø¯Ù‡ Ø§Ø³Øª:\n\n{cat_value}")
                return "ok"

            buttons = [
                [{
                    "text": "ðŸŽµ " + value(item["row"], "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯"),
                    "callback_data": f"catsong|{item['index']}"
                }]
                for item in songs
            ]

            buttons.append([{"text": "â¬…ï¸ Ø¨Ø±Ú¯Ø´Øª", "callback_data": "songs_menu"}])
            send_msg(chat_id, f"ðŸŽµ {cat_button}:", {"inline_keyboard": buttons})

        elif cb == "songs_menu":
            songs_menu(chat_id)

        elif cb.startswith("catsong|"):
            index = int(cb.split("|", 1)[1])
            all_category_songs = get_category_songs()

            if 0 <= index < len(all_category_songs):
                s = all_category_songs[index]
                send_audio(chat_id, value(s, "ÙØ§ÛŒÙ„"), "ðŸŽ¶ Ø§ÛŒÙ† Ø³Ø±ÙˆØ¯ ØªÙ‚Ø¯ÛŒÙ… Ø¨Ù‡ Ø´Ù…Ø§\n\nðŸŽµ " + value(s, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯"))

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
                send_audio(chat_id, value(s, "ÙØ§ÛŒÙ„"), "ðŸŽ¶ Ø§ÛŒÙ† Ø³Ø±ÙˆØ¯ ØªÙ‚Ø¯ÛŒÙ… Ø¨Ù‡ Ø´Ù…Ø§\n\nðŸŽµ " + value(s, "Ø§Ø³Ù… Ø³Ø±ÙˆØ¯"))

        elif cb == "promise_next":
            promise(chat_id)

        elif cb == "fact_next":
            fact(chat_id)

        elif cb == "back_main":
            send_msg(chat_id, "ðŸ  Ø§Ø² Ù…Ù†ÙˆÛŒ Ù¾Ø§ÛŒÛŒÙ†ØŒ Ø¨Ø®Ø´ Ù…ÙˆØ±Ø¯ Ù†Ø¸Ø± Ø±Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ù†ÛŒØ¯.", main_keyboard())

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

            send_msg(chat_id, "ðŸ™ Ù„Ø·ÙØ§Ù‹ Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ÛŒ Ø®ÙˆØ¯ Ø±Ø§ Ø§Ø±Ø³Ø§Ù„ Ú©Ù†ÛŒØ¯.")

        elif cb == "prayer_random":
            random_prayer(chat_id)

        elif cb.startswith("approve_prayer|"):
            pending_id = cb.split("|", 1)[1]
            prayer = PENDING_PRAYERS.pop(pending_id, None)

            if not prayer:
                send_msg(chat_id, "Ø§ÛŒÙ† Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯ ÛŒØ§ Ù‚Ø¨Ù„Ø§Ù‹ Ø¨Ø±Ø±Ø³ÛŒ Ø´Ø¯Ù‡ Ø§Ø³Øª.")
                return "ok"

            result = writer({"type": "prayer", "text": prayer["public_text"]})

            if result.get("ok"):
                clear_cache("Prayers")
                send_msg(chat_id, "âœ… Ø¯Ø¹Ø§ ØªØ§ÛŒÛŒØ¯ Ùˆ Ø¯Ø± Ø¨Ø®Ø´ Ø¯Ø¹Ø§ Ø«Ø¨Øª Ø´Ø¯.")
                send_msg(prayer["user_chat_id"], "ðŸ™ Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ÛŒ Ø´Ù…Ø§ ØªØ§ÛŒÛŒØ¯ Ø´Ø¯ Ùˆ Ø¯Ø± Ø¨Ø®Ø´ Ø¯Ø¹Ø§ Ù‚Ø±Ø§Ø± Ú¯Ø±ÙØª.")
            else:
                send_msg(chat_id, "âŒ Ø«Ø¨Øª Ø¯Ø¹Ø§ Ø¯Ø± Ø´ÛŒØª Ø§Ù†Ø¬Ø§Ù… Ù†Ø´Ø¯. Ø¯ÙˆØ¨Ø§Ø±Ù‡ ØªÙ„Ø§Ø´ Ú©Ù†ÛŒØ¯.")

        elif cb.startswith("reject_prayer|"):
            pending_id = cb.split("|", 1)[1]
            prayer = PENDING_PRAYERS.pop(pending_id, None)

            if prayer:
                send_msg(chat_id, "âŒ Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ Ø±Ø¯ Ø´Ø¯.")
                send_msg(prayer["user_chat_id"], "Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ÛŒ Ø´Ù…Ø§ ØªÙˆØ³Ø· Ø®Ø§Ø¯Ù…ÛŒÙ† ØªØ§ÛŒÛŒØ¯ Ù†Ø´Ø¯.")
            else:
                send_msg(chat_id, "Ø§ÛŒÙ† Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯ ÛŒØ§ Ù‚Ø¨Ù„Ø§Ù‹ Ø¨Ø±Ø±Ø³ÛŒ Ø´Ø¯Ù‡ Ø§Ø³Øª.")

        elif cb.startswith("praydone|"):
            row_number = cb.split("|", 1)[1]
            result = writer({"type": "prayer_count", "row": row_number})
            count = result.get("count", "")

            clear_cache("Prayers")

            if count != "":
                send_msg(chat_id, f"ðŸ¤ Ù…Ù…Ù†ÙˆÙ† Ø§Ø² Ù‡Ù…Ø±Ø§Ù‡ÛŒ Ø´Ù…Ø§\n\nâ­•ï¸ {count} Ù†ÙØ± Ø¨Ø±Ø§ÛŒ Ø§ÛŒÙ† Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø¯Ø¹Ø§ Ú©Ø±Ø¯Ù†Ø¯")
            else:
                send_msg(chat_id, "ðŸ™ Ù…Ù…Ù†ÙˆÙ† Ø§Ø² Ø§ÛŒÙ†Ú©Ù‡ Ø¯Ø± Ø¯Ø¹Ø§ Ù‡Ù…Ø±Ø§Ù‡ Ø´Ø¯ÛŒØ¯.\nØ®Ø¯Ø§ÙˆÙ†Ø¯ Ø¨Ø±Ú©ØªØªØ§Ù† Ø¯Ù‡Ø¯ ðŸ¤")

        elif cb.startswith("wordchoose|"):
            word_text = cb.split("|", 1)[1]
            word_result(chat_id, word_text)

        elif cb.startswith("w"):
            action, word_text = cb.split("|", 1)
            exact, _ = find_word(word_text)
            w = exact

            if w:
                if action == "wverse":
                    send_msg(chat_id, "ðŸ“œ Ø¢ÛŒÙ‡ Ù…Ø±ØªØ¨Ø·:\n\n" + value(w, "Ø¢ÛŒÙ‡ Ù…Ø±ØªØ¨Ø·"))
                elif action == "wmean":
                    send_msg(chat_id, "ðŸ“– Ù…Ø¹Ù†ÛŒ:\n\n" + value(w, "Ù…Ø¹Ù†ÛŒ"))
                elif action == "wroot":
                    title = "ðŸ’¡ Ø±ÛŒØ´Ù‡ ÛŒÙˆÙ†Ø§Ù†ÛŒ" if value(w, "Ø¹Ù‡Ø¯") == "NT" else "ðŸ’¡ Ø±ÛŒØ´Ù‡ Ø¹Ø¨Ø±ÛŒ"
                    send_msg(chat_id, title + ":\n\n" + value(w, "Ø±ÛŒØ´Ù‡"))

    return "ok"


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=10000)
