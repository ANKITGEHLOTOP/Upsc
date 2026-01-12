# UTKARSH BOT - SABSE FINAL VERSION (KOYEB 100% LIVE IN 5 SECONDS)

import json
import base64
import requests
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import asyncio

# ============ SIRF YE 3 LINE CHANGE KAR ============
BOT_TOKEN = "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo"   # ← APNA BOT TOKEN
MOBILE    = "7891745633"                                      # ← APNA MOBILE
PASSWORD  = "Sitar@123"                                       # ← APNA PASSWORD
# ===================================================

requests.packages.urllib3.disable_warnings()

# Baaki sab kuch same hai...

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

def enc(data, common=False, key=None, iv=None):
    k = COMMON_KEY if common else key
    i = COMMON_IV if common else iv
    return base64.b64encode(AES.new(k, AES.MODE_CBC, i).encrypt(pad(json.dumps(data, separators=(",",":")).encode(), 16))).decode() + ":"

def dec(text, common=False, key=None, iv=None):
    k = COMMON_KEY if common else key
    i = COMMON_IV if common else iv
    try:
        return unpad(AES.new(k, AES.MODE_CBC, i).decrypt(base64.b64decode(text.split(":")[0])), 16).decode()
    except: return None

def api(path, data, common=False, key=None, iv=None):
    r = requests.post(API_URL + path, headers=HEADERS, data=enc(data, common, key, iv), verify=False, timeout=40)
    x = dec(r.text, common, key, iv)
    return json.loads(x) if x else {}

def ds(e):
    try:
        d = AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').decrypt(base64.b64decode(e))
        p = unpad(d, 16).decode(errors='ignore')
        for i in range(len(p), 0, -1):
            try: return json.loads(p[:i])
            except: continue
    except: pass
    return {}

def es(txt):
    return base64.b64encode(AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').encrypt(pad(txt.encode(), 16))).decode()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 EXTRACT BATCH", callback_data="extract")]]
    await update.message.reply_text(
        "⚡ UTKARSH EXTRACTOR BOT LIVE HAI BHAI ⚡\n\n"
        "Button daba → Batch ID daal → 5 min me pura batch aa jayega!\n\n"
        "Working 100% - 2025 🔥",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Batch ID daal bhai (18399, 21753 etc):")
    context.user_data["waiting_for_batch"] = True

async def extract_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    batch = update.message.text.strip()
    context.user_data["waiting_for_batch"] = False
    
    status = await update.message.reply_text("🔄 Login + Extracting...")

    try:
        s = requests.Session()
        csrf = s.get("https://online.utkarsh.com/", verify=False).cookies.get('csrf_name')
        
        login = s.post("https://online.utkarsh.com/web/Auth/login", data={
            "mobile": MOBILE, "password": PASSWORD, "csrf_name": csrf, "url": "0", "submit": "LogIn"
        }, verify=False).json()
        
        login_data = ds(login.get("response", {}))
        if not login_data or login_data.get("status") != 1:
            await status.edit_text("❌ Wrong Mobile/Password!")
            return

        HEADERS["jwt"] = login_data["data"]["jwt"]
        profile = api("/users/get_my_profile", {}, True)
        uid = str(profile["data"]["id"])
        HEADERS["userid"] = uid
        key = "".join(key_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()
        iv = "".join(iv_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()

        await status.edit_text(f"🔥 Batch {batch} nikal raha hu... 4-6 min ⏳")

        output = BytesIO()
        count = 0

        # Course list
        res = s.post("https://online.utkarsh.com/web/Course/tiles_data", data={
            "tile_input": es(json.dumps({"course_id": batch, "parent_id": 0, "tile_id": "15330", "layer": 1, "type": "course_combo", "revert_api": "1#0#0#1"})),
            "csrf_name": csrf
        }, verify=False).json()
        courses = ds(res.get("response", {})).get("data", [])
        if isinstance(courses, dict): courses = [courses]

        for course in courses:
            cid = course["id"]
            cname = course.get("title", "Course")
            output.write(f"\n{cid} ♧ {cname}\n\n".encode())

            pg = 1
            while True:
                payload = {"course_id": cid, "layer": 1, "page": pg, "parent_id": cid, "tile_id": "0", "type": "content", "revert_api": "1#1#0#1"}
                res2 = s.post("https://online.utkarsh.com/web/Course/tiles_data", data={"tile_input": es(json.dumps(payload)), "csrf_name": csrf}, verify=False).json()
                data2 = ds(res2.get("response", {}))
                if not data2 or "list" not in data2.get("data", {}): break

                for subj in data2["data"]["list"]:
                    sid = subj["id"]
                    res3 = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data", data={
                        "layer_two_input_data": base64.b64encode(json.dumps({"course_id": cid, "parent_id": cid, "layer": 2, "page": 1, "subject_id": sid, "topic_id": sid, "tile_id": 0, "type": "content", "revert_api": "1#0#0#1"}).encode()).decode(),
                        "csrf_name": csrf
                    }, verify=False).json()
                    data3 = ds(res3.get("response", {}))
                    if data3 and "list" in data3.get("data", {}):
                        for topic in data3["data"]["list"]:
                            tid = topic["id"]
                            tname = topic.get("title", "Lecture")
                            tile_id = topic.get("payload", {}).get("tile_id")
                            if tile_id:
                                link_res = api("/meta_distributer/on_request_meta_source", {"course_id": cid, "tile_id": tile_id, "name": f"{tid}_0_0", "type": "video"}, key=key, iv=iv)
                                urls = link_res.get("data", {}).get("bitrate_urls", [])
                                if urls:
                                    link = urls[min(3, len(urls)-1)].get("url", "")
                                    if link:
                                        output.write(f"{tname}:{link.split('?Expires=')[0]}\n".encode())
                                        count += 1

                if pg >= data2["data"].get("total_page", 1): break
                pg += 1

        output.write(f"\nTOTAL LINKS: {count}\n".encode())
        output.seek(0)
        await status.delete()
        await update.message.reply_document(document=("Utkarsh_Batch_" + batch + ".txt", output), caption=f"Batch {batch} Done ✅ | {count} Links")

    except Exception as e:
        await status.edit_text(f"Error: {str(e)}")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_batch"):
        await extract_batch(update, context)

# FINAL RUN - YE HI DAALNA HAI
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("BOT START HO GAYA BHAI - KOyeb LIVE IN 5 SECONDS!")
app.run_polling(drop_pending_updates=True)
