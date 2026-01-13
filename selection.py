import time
import json
import requests
import telebot
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from base64 import b64encode, b64decode
import urllib3
import traceback

urllib3.disable_warnings()

# ================= HARD CODED =================
BOT_TOKEN = "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo"
UT_EMAIL = "7891745633"
UT_PASSWORD = "Sitar@123"

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

# ================= CRYPTO =================
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

def api_post(path, payload):
    try:
        r = requests.post(API_URL + path, headers=HEADERS, data=encrypt(payload), timeout=20)
        dec = decrypt(r.text)
        return json.loads(dec) if dec else {}
    except Exception:
        return {}

# ================= LOGIN =================
session = None

def utkarsh_login():
    global session
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
        js = res.json()

        if not isinstance(js, dict) or "response" not in js:
            return False, f"Login failed: {js}"

        session = s
        return True, "Login OK"

    except Exception as e:
        return False, str(e)

# ================= BOT =================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

@bot.message_handler(commands=["start"])
def start(m):
    bot.reply_to(m, "✅ Bot running\nUse /extract <batch_id>")

@bot.message_handler(commands=["ping"])
def ping(m):
    bot.reply_to(m, "🏓 Alive")

# ================= EXTRACT =================
@bot.message_handler(commands=["extract"])
def extract(m):
    try:
        parts = m.text.split()
        if len(parts) != 2:
            bot.reply_to(m, "❌ Usage:\n/extract <batch_id>")
            return

        batch_id = parts[1]
        bot.reply_to(m, f"⏳ Extracting batch `{batch_id}` …")

        ok, msg = utkarsh_login()
        if not ok:
            bot.reply_to(m, f"❌ Login failed:\n{msg}")
            return

        # STEP 1: batch tiles
        payload = {
            "course_id": batch_id,
            "parent_id": 0,
            "layer": 1,
            "tile_id": "15330",
            "type": "course_combo",
            "revert_api": "1#0#0#1"
        }

        data = api_post("/course/get_course_tiles", payload)
        items = data.get("data", [])

        if not items:
            bot.reply_to(m, "❌ No data found for this batch")
            return

        sent = 0

        for item in items:
            title = item.get("title", "Untitled")
            cid = item.get("id")

            meta = api_post(
                "/meta_distributer/on_request_meta_source",
                {
                    "course_id": cid,
                    "type": "video",
                    "download_click": "0",
                    "device_id": "x",
                    "device_name": "x",
                    "name": f"{cid}_0_0"
                }
            )

            urls = meta.get("data", {}).get("bitrate_urls", [])

            for u in urls:
                link = u.get("url")
                if link:
                    clean = link.split("?Expires=")[0]
                    bot.send_message(m.chat.id, f"<b>{title}</b>\n{clean}")
                    sent += 1
                    time.sleep(0.3)

        bot.reply_to(m, f"✅ Extraction done\nLinks sent: {sent}")

    except Exception as e:
        traceback.print_exc()
        bot.reply_to(m, f"❌ Error:\n{e}")

# ================= MAIN =================
if __name__ == "__main__":
    print("🚀 Bot starting (extract enabled)")

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print("Polling crash:", e)
            time.sleep(5)
