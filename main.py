from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return "no data"

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            send_message(
                chat_id,
                "✨ شالوم بر شما فرزندان نور\n"
                "به ربات «کلمه‌یاب و سرودیاب» خوش آمدید 🕊️\n\n"
                "⚠️ در برخی مواقع ممکن است اولین پاسخ چند لحظه زمان ببرد. سپاس از شکیبایی شما 🙏"
            )
        else:
            send_message(chat_id, f"شما نوشتید: {text}")

    return "ok"

def send_message(chat_id, text):
    requests.post(URL + "sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
