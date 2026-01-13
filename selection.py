import os
import json
import time
import requests
import telebot
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from base64 import b64encode, b64decode
import urllib3
import traceback

urllib3.disable_warnings()

# ================= CONFIG =================
BOT_TOKEN = os.getenv("8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo")
UT_EMAIL = os.getenv("7891745633")
UT_PASSWORD = os.getenv("Sitar@123")

API_URL = "https://application.utkarshapp.com/index.php/data_model"

COMMON_KEY = b"%!^F&^$)&^$&*$^&"
COMMON_IV = b"#*v$JvywJvyJDyvJ"

HEADERS = {
    "Authorization": "Bearer 152#svf346t45ybrer34yredk76t",
    "Content-Type": "text/plain; charset=UTF-8",
    "devicetype": "1",
    "host": "application.utkarshapp.com",
    "lang": "1",
    "user-agent": "okhttp/4.9.0",
    "userid": "0",
    "version": "152"
}

# ================= UTILS =================
def encrypt(data):
    cipher = AES.new(COMMON_KEY, AES.MODE_CBC, COMMON_IV)
    raw = pad(json.dumps(data, separators=(",", ":")).encode(), 16)
    return b64encode(cipher.encrypt(raw)).decode() + ":"

def decrypt(enc):
    try:
        cipher = AES.new(COMMON_KEY, AES.MODE_CBC, COMMON_IV)
        raw = b64decode(enc.split(":")[0])
        return unpad(cipher.decrypt(raw), 16).decode()
    except Exception:
        return None

def safe_post(path, payload):
    try:
        r = requests.post(API_URL + path, headers=HEADERS, data=encrypt(payload), timeout=15)
        dec = decrypt(r.text)
        return json.loads(dec) if dec else {}
    except Exception:
        return {}

# ================= LOGIN =================
def utkarsh_login():
    try:
        s = requests.Session()
        base = "https://online.utkarsh.com/"
        login_url = base + "web/Auth/login"

        r = s.get(base, timeout=10)
        csrf = r.cookies.get("csrf_name")
        if not csrf:
            return False, "CSRF missing"

        payload = {
            "csrf_name": csrf,
            "mobile": UT_EMAIL,
            "password": UT_PASSWORD,
            "url": "0",
            "submit": "LogIn",
            "device_token": "null"
        }

        h = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        res = s.post(login_url, data=payload, headers=h, timeout=15)

        try:
            js = res.json()
        except Exception:
            return False, "Login JSON invalid"

        if not isinstance(js, dict) or "response" not in js:
            return False, f"Unexpected login response: {js}"

        return True, "Login OK"

    except Exception as e:
        return False, str(e)

# ================= BOT =================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

@bot.message_handler(commands=["start"])
def start(m):
    bot.reply_to(
        m,
        "✅ Bot is running\n"
        "⚠️ Scraping runs only on command\n"
        "Use responsibly."
    )

@bot.message_handler(commands=["ping"])
def ping(m):
    bot.reply_to(m, "🏓 Pong! Bot alive.")

# ================= MAIN =================
if __name__ == "__main__":
    print("🚀 Starting Utkarsh Bot (Koyeb Safe Mode)")

    if not BOT_TOKEN or not UT_EMAIL or not UT_PASSWORD:
        print("❌ ENV vars missing")
    else:
        ok, msg = utkarsh_login()
        print("Login:", msg)

    # KEEP APP ALIVE (IMPORTANT FOR KOYEB)
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception:
            traceback.print_exc()
            time.sleep(5)
