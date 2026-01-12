# UTKARSH BOT - FULLY FIXED - KOyeb 100% WORKING (2025)

import json
import base64
import requests
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

requests.packages.urllib3.disable_warnings()

# ============ SIRF YE 3 LINE CHANGE KAR ============
BOT_TOKEN = "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo"   # ← APNA TOKEN
MOBILE    = "7891745633"                                   # ← APNA MOBILE
PASSWORD  = "Sitar@123"                                    # ← APNA PASSWORD
# ===================================================

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

def encrypt(data, common=False, key=None, iv=None):
    k, i = (COMMON_KEY, COMMON_IV) if common else (key, iv)
    return base64.b64encode(AES.new(k, AES.MODE_CBC, i).encrypt(pad(json.dumps(data, separators=(",",":")).encode(), 16))).decode() + ":"

def decrypt(text, common=False, key=None, iv=None):
    k, i = (COMMON_KEY, COMMON_IV) if common else (key, iv)
    try:
        return unpad(AES.new(k, AES.MODE_CBC, i).decrypt(base64.b64decode(text.split(":")[0])), 16).decode()
    except: return None

def post_request(path, data, common=False, key=None, iv=None):
    r = requests.post(API_URL + path, headers=HEADERS, data=encrypt(data, common, key, iv), verify=False, timeout=40)
    x = decrypt(r.text, common, key, iv)
    return json.loads(x) if x else {}

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
    s = requests.Session()
    msg = await update.message.reply_text("🔄 Login + Extracting...")

    try:
        csrf = s.get("https://online.utkarsh.com/", verify=False).cookies.get('csrf_name')
        h = {'Host': 'online.utkarsh.com', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest'}

        login = s.post("https://online.utkarsh.com/web/Auth/login", data={
            'csrf_name': csrf, 'mobile': MOBILE, 'password': PASSWORD, 'url': '0', 'submit': 'LogIn'
        }, headers=h, verify=False).json()

        data = decrypt_stream(login.get("response", {}))
        if not data or data.get("status") != 1:
            await msg.edit_text("❌ Wrong Mobile/Password!")
            return

        HEADERS["jwt"] = data["data"]["jwt"]
        profile = post_request("/users/get_my_profile", {}, True)
        uid = str(profile["data"]["id"])
        HEADERS["userid"] = uid
        key = "".join(key_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()
        iv = "".join(iv_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()

        await msg.edit_text(f"🔥 Batch {batch_id} nikal raha hu... 4-7 min ⏳")

        output = BytesIO()
        count = 0

        # Course fetch
        res = s.post("https://online.utkarsh.com/web/Course/tiles_data", data={
            'tile_input': encrypt_stream(json.dumps({"course_id": batch_id, "parent_id": 0, "tile_id": "15330", "layer": 1, "type": "course_combo", "revert_api": "1#0#0#1"})),
            'csrf_name': csrf
        }, headers=h, verify=False).json()
        courses = decrypt_stream(res.get("response", {}) ).get("data", [])
        if isinstance(courses, dict): courses = [courses]

        for course in courses:
            fi = course["id"]
            tn = course.get("title", "Course")
            output.write(f"\n{fi} ♧ {tn}\n\n".encode())

            pg = 1
            while True:
                payload = {"course_id": fi, "layer": 1, "page": pg, "parent_id": fi, "revert_api": "1#1#0#1", "tile_id": "0", "type": "content"}
                res2 = s.post("https://online.utkarsh.com/web/Course/tiles_data", data={'tile_input': encrypt_stream(json.dumps(payload)), 'csrf_name': csrf}, headers=h, verify=False).json()
                data2 = decrypt_stream(res2.get("response", {}))
                if not data2 or "list" not in data2.get("data", {}): break

                for subj in data2["data"]["list"]:
                    sfi = subj["id"]
                    res3 = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data", data={
                        'layer_two_input_data': base64.b64encode(json.dumps({"course_id": fi, "parent_id": fi, "layer": 2, "page": 1, "subject_id": sfi, "topic_id": sfi, "tile_id": 0, "type": "content", "revert_api": "1#0#0#1"}).encode()).decode(),
                        'csrf_name': csrf
                    }, headers=h, verify=False).json()
                    data3 = decrypt_stream(res3.get("response", {}))

                    if data3 and "list" in data3.get("data", {}):
                        for topic in data3["data"]["list"]:
                            ji = topic["id"]
                            jt = topic.get("title")
                            jti = topic.get("payload", {}).get("tile_id")
                            if jti:
                                link_data = post_request("/meta_distributer/on_request_meta_source", {"course_id": fi, "tile_id": jti, "name": f"{ji}_0_0", "type": "video"}, key=key, iv=iv)
                                urls = link_data.get("data", {}).get("bitrate_urls", [])
                                if urls:
                                    link = urls[3].get("url") if len(urls)>3 else urls[2].get("url") if len(urls)>2 else urls[1].get("url") if len(urls)>1 else urls[0].get("url", "")
                                    if link:
                                        output.write(f"{jt}:{link.split('?Expires=')[0]}\n".encode())
                                        count += 1

                if pg >= data2["data"].get("total_page", 1): break
                pg += 1

        output.write(f"\nTOTAL LINKS: {count}\n".encode())
        output.seek(0)
        await msg.delete()
        await update.message.reply_document(document=("Utkarsh_" + batch_id + ".txt", output), caption=f"Batch {batch_id} Done ✅ | {count} Links")

    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")

# BOT COMMANDS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = [[InlineKeyboardButton("🚀 Extract Batch", callback_data="go")]]
    await update.message.reply_text("⚡ Bhai Tera Utkarsh Bot Ready Hai!\n\nButton daba aur Batch ID daal → file aa jayegi 🔥", reply_markup=InlineKeyboardMarkup(btn))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Batch ID daal bhai (18399, 21753, 24156 etc):")
    context.user_data["wait"] = True

async def msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("wait"):
        batch = update.message.text.strip()
        await update.message.reply_text(f"Thik hai bhai, {batch} nikal raha hu... 5 minute me file aa jayegi 😈")
        context.user_data["wait"] = False
        await extract_batch(update, context, batch)

# RUN BOT
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))   # ← YE LINE FIX KI HAI

print("BOT LIVE HO GAYA BHAI - AB LOOT LO!")
app.run_polling(drop_pending_updates=True)
