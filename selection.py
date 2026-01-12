# TERA ORIGINAL CODE KA BOT - AB MOBILE & PASSWORD DIRECT DAAL SAKTA HAI (LINE 132 STYLE)

import json
import base64
import requests
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

requests.packages.urllib3.disable_warnings()

# ============ YE 3 LINE ME APNA DATA DAAL DE BHAI ============
BOT_TOKEN   = "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo"   # ← Apna Bot Token
MOBILE      = "7891745633"                                      # ← Apna Mobile/Email yahan daal
PASSWORD    = "Sitar@123"                                       # ← Apna Password yahan daal
# ==============================================================

# Baaki sab kuch 100% tera original code hi hai - kuch nahi badla

API_URL = "https://application.utkarshapp.com/index.php/data_model"
COMMON_KEY = b"%!^F&^$)&^$&*$^&"
COMMON_IV = b"#*v$JvywJvyJDyvJ"
key_chars = "%!F*&^$)_*%3f&B+"
iv_chars = "#*$DJvyw2w%!_-$@"

HEADERS = {
    "Authorization": "Bearer 152#svf346t45ybrer34yredk76t",
    "Content-Type": "text/plain; charset=UTF-8",
    "devicetype": "1", "host": "application.utkarshapp.com",
    "lang": "1", "user-agent": "okhttp/4.9.0",
    "userid": "0", "version": "152"
}

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Tere original functions bilkul same
def encrypt(data, use_common_key, key=None, iv=None):
    ck, ci = (COMMON_KEY, COMMON_IV) if use_common_key else (key, iv)
    return base64.b64encode(AES.new(ck, AES.MODE_CBC, ci).encrypt(pad(json.dumps(data, separators=(",",":")).encode(), 16))).decode() + ":"

def decrypt(data, use_common_key, key=None, iv=None):
    ck, ci = (COMMON_KEY, COMMON_IV) if use_common_key else (key, iv)
    try:
        return unpad(AES.new(ck, AES.MODE_CBC, ci).decrypt(base64.b64decode(data.split(":")[0])), 16).decode()
    except: return None

def post_request(path, data=None, use_common_key=False, key=None, iv=None):
    if not data: return {}
    enc_data = encrypt(data, use_common_key, key, iv)
    r = requests.post(API_URL + path, headers=HEADERS, data=enc_data, verify=False, timeout=40)
    dec_data = decrypt(r.text, use_common_key, key, iv)
    return json.loads(dec_data) if dec_data else {}

def decrypt_stream(enc):
    try:
        d = AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').decrypt(base64.b64decode(enc))
        p = unpad(d, 16).decode(errors='ignore')
        for i in range(len(p), 0, -1):
            try: return json.loads(p[:i])
            except: continue
    except: pass
    return {}

def encrypt_stream(txt):
    return base64.b64encode(AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').encrypt(pad(txt.encode(), 16))).decode()

async def extract_batch(update: Update, context: ContextTypes.DEFAULT_TYPE, batch_id: str):
    session = requests.Session()
    status = await update.message.reply_text("🔄 Login kar raha hu...")

    try:
        r1 = session.get("https://online.utkarsh.com/", verify=False)
        csrf = r1.cookies.get('csrf_name')

        h = {'Host': 'online.utkarsh.com', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest'}

        login_res = session.post("https://online.utkarsh.com/web/Auth/login", data={
            'csrf_name': csrf, 'mobile': MOBILE, 'password': PASSWORD, 'url': '0', 'submit': 'LogIn', 'device_token': 'null'
        }, headers=h, verify=False).json()

        login_data = decrypt_stream(login_res.get("response", {}))
        if not login_data or login_data.get("status") != 1:
            await status.edit_text("❌ Galat mobile ya password bhai!")
            return

        HEADERS["jwt"] = login_data["data"]["jwt"]
        profile = post_request("/users/get_my_profile", use_common_key=True)
        uid = str(profile["data"]["id"])
        HEADERS["userid"] = uid
        key = "".join(key_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()
        iv = "".join(iv_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()

        await status.edit_text(f"🔥 Batch {batch_id} nikal raha hu... 4-8 min lagega ⏳")

        output = BytesIO()
        count = 0

        # Tera original course fetch
        tile_input = encrypt_stream(json.dumps({"course_id": batch_id, "revert_api": "1#0#0#1", "parent_id": 0, "tile_id": "15330", "layer": 1, "type": "course_combo"}))
        res = session.post("https://online.utkarsh.com/web/Course/tiles_data", data={'tile_input': tile_input, 'csrf_name': csrf}, headers=h, verify=False).json()
        courses = decrypt_stream(res.get("response", {})).get("data", [])
        if isinstance(courses, dict): courses = [courses]

        for course in courses:
            fi = course.get("id")
            tn = course.get("title", "Course")
            output.write(f"\n{fi} ♧ {tn}\n\n".encode())

            pg = 1
            while True:
                payload = {"course_id": fi, "layer": 1, "page": pg, "parent_id": fi, "revert_api": "1#1#0#1", "tile_id": "0", "type": "content"}
                res2 = session.post("https://online.utkarsh.com/web/Course/tiles_data", data={'tile_input': encrypt_stream(json.dumps(payload)), 'csrf_name': csrf}, headers=h, verify=False).json()
                data2 = decrypt_stream(res2.get("response", {}))
                if not data2 or "list" not in data2.get("data", {}): break

                for subj in data2["data"]["list"]:
                    sfi = subj.get("id")
                    d7 = {"course_id": fi, "parent_id": fi, "layer": 2, "page": 1, "revert_api": "1#0#0#1", "subject_id": sfi, "tile_id": 0, "topic_id": sfi, "type": "content"}
                    res3 = session.post("https://online.utkarsh.com/web/Course/get_layer_two_data", data={'layer_two_input_data': base64.b64encode(json.dumps(d7).encode()).decode(), 'csrf_name': csrf}, headers=h, verify=False).json()
                    data3 = decrypt_stream(res3.get("response", {}))

                    if data3 and "list" in data3.get("data", {}):
                        for topic in data3["data"]["list"]:
                            ji = topic.get("id")
                            jt = topic.get("title")
                            jti = topic.get("payload", {}).get("tile_id")
                            if jti:
                                link_data = post_request("/meta_distributer/on_request_meta_source", {"course_id": fi, "tile_id": jti, "name": f"{ji}_0_0", "type": "video"}, key=key, iv=iv)
                                urls = link_data.get("data", {}).get("bitrate_urls", [])
                                if urls and len(urls) > 3:
                                    link = urls[3].get("url", "") or urls[2].get("url", "") or urls[1].get("url", "") or urls[0].get("url", "")
                                    if link:
                                        output.write(f"{jt}:{link.split('?Expires=')[0]}\n".encode())
                                        count += 1

                if pg >= data2["data"].get("total_page", 1): break
                pg += 1

        output.write(f"\nTOTAL LINKS: {count}\n".encode())
        output.seek(0)

        await status.delete()
        await update.message.reply_document(document=("Utkarsh_Batch_" + batch_id + ".txt", output), caption=f"Batch {batch_id} Nikal diya bhai ✅\nTotal Links: {count}")

    except Exception as e:
        await status.edit_text(f"Error: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Extract Batch", callback_data="extract")]]
    await update.message.reply_text("⚡ Tera Original Utkarsh Bot Live Hai Bhai ⚡\n\nNiche button daba aur batch ID daal!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "extract":
        await query.edit_message_text("Batch ID daal bhai (jaise 18399, 21753):")
        context.user_data["waiting_batch"] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_batch"):
        batch_id = update.message.text.strip()
        await update.message.reply_text(f"Thik hai bhai, Batch {batch_id} nikal raha hu... 5-8 minute me file aa jayegi 🔥")
        context.user_data["waiting_batch"] = False
        await extract_batch(update, context, batch_id)

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(None, handle_message))

print("BOT LIVE HAI BHAI - AB SIRF BATCH ID DAAL!")
app.run_polling(drop_pending_updates=True)
