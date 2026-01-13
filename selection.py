import json
import time
import requests
import telebot
import traceback
import urllib3
from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

urllib3.disable_warnings()

# ================= HARD CODED CREDS =================
BOT_TOKEN = "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo"
UT_EMAIL = "7891745633"
UT_PASSWORD = "Sitar@123"

# ================= SESSION / URLS =================
session = requests.Session()

BASE_URL = "https://online.utkarsh.com/"
LOGIN_URL = BASE_URL + "web/Auth/login"
TILES_DATA_URL = BASE_URL + "web/Course/tiles_data"
LAYER_TWO_DATA_URL = BASE_URL + "web/Course/get_layer_two_data"

# ================= HEADERS =================
h = {
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0"
}

csrf_token = None

# ================= CRYPTO (ORIGINAL) =================
def encrypt_stream(plain):
    key = '%!$!%_$&!%F)&^!^'.encode()
    iv = '#*y*#2yJ*#$wJv*v'.encode()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return b64encode(cipher.encrypt(pad(plain.encode(), 16))).decode()

def decrypt_stream(enc):
    try:
        key = '%!$!%_$&!%F)&^!^'.encode()
        iv = '#*y*#2yJ*#$wJv*v'.encode()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        raw = cipher.decrypt(b64decode(enc))
        dec = raw.decode(errors="ignore")

        # clean garbage till valid JSON
        for i in range(len(dec), 0, -1):
            try:
                return json.loads(dec[:i])
            except:
                pass
    except:
        return None

# ================= LOGIN =================
def utkarsh_login():
    global csrf_token
    try:
        r1 = session.get(BASE_URL, timeout=10)
        csrf_token = r1.cookies.get("csrf_name")
        if not csrf_token:
            return False, "CSRF missing"

        payload = {
            "csrf_name": csrf_token,
            "mobile": UT_EMAIL,
            "password": UT_PASSWORD,
            "url": "0",
            "submit": "LogIn",
            "device_token": "null"
        }

        r2 = session.post(LOGIN_URL, data=payload, headers=h, timeout=15)

        try:
            js = r2.json()
        except:
            return False, "Login response not JSON"

        if not isinstance(js, dict) or "response" not in js:
            return False, f"Login failed: {js}"

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

# ================= EXTRACT (REAL FLOW) =================
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

        # -------- LAYER 1 --------
        d1 = {
            "course_id": batch_id,
            "revert_api": "1#0#0#1",
            "parent_id": 0,
            "tile_id": "15330",
            "layer": 1,
            "type": "course_combo"
        }

        enc1 = encrypt_stream(json.dumps(d1))
        r1 = session.post(
            TILES_DATA_URL,
            headers=h,
            data={"tile_input": enc1, "csrf_name": csrf_token}
        ).json()

        dr1 = decrypt_stream(r1.get("response"))
        if not dr1 or "data" not in dr1:
            bot.reply_to(m, "❌ No data found for this batch")
            return

        sent = 0

        # -------- LAYER 2 --------
        for subj in dr1["data"]:
            sid = subj.get("id")
            sname = subj.get("title")

            d2 = {
                "course_id": batch_id,
                "parent_id": batch_id,
                "layer": 2,
                "page": 1,
                "revert_api": "1#0#0#1",
                "subject_id": sid,
                "tile_id": 0,
                "topic_id": sid,
                "type": "content"
            }

            enc2 = b64encode(json.dumps(d2).encode()).decode()
            r2 = session.post(
                LAYER_TWO_DATA_URL,
                headers=h,
                data={"layer_two_input_data": enc2, "csrf_name": csrf_token}
            ).json()

            dr2 = decrypt_stream(r2.get("response"))
            if not dr2 or "data" not in dr2:
                continue

            # -------- LAYER 3 --------
            for topic in dr2["data"]["list"]:
                tid = topic.get("id")
                tname = topic.get("title")

                bot.send_message(
                    m.chat.id,
                    f"<b>{sname}</b>\n{tname}"
                )
                sent += 1
                time.sleep(0.25)

        bot.reply_to(m, f"✅ Done\nItems found: {sent}")

    except Exception as e:
        traceback.print_exc()
        bot.reply_to(m, f"❌ Error:\n{e}")

# ================= MAIN =================
if __name__ == "__main__":
    print("🚀 Utkarsh bot starting (REAL FLOW)")

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)
