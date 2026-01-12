# Utkarsh Extractor Bot – Koyeb Ready (Jan 2025)
# Uses python-telegram-bot v21+ → No dependency conflict!

import os
import json
import base64
import requests
import urllib3
from io import BytesIO

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

urllib3.disable_warnings()

BOT_TOKEN = os.environ.get("8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo")
if not BOT_TOKEN:
    print("Add BOT_TOKEN in env!")
    exit()

# =================== UTKARSH CORE ===================
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

key = iv = None

def enc(data, common=False):
    k, i = (COMMON_KEY, COMMON_IV) if common else (key, iv)
    encrypted = AES.new(k, AES.MODE_CBC, i).encrypt(pad(json.dumps(data, separators=(",",":")).encode(), 16))
    return base64.b64encode(encrypted).decode() + ":"

def dec(text, common=False):
    k, i = (COMMON_KEY, COMMON_IV) if common else (key, iv)
    try:
        return unpad(AES.new(k, AES.MODE_CBC, i).decrypt(base64.b64decode(text.split(":")[0])), 16).decode()
    except:
        return None

def api(path, data, common=False):
    try:
        r = requests.post(API_URL + path, headers=HEADERS, data=enc(data, common), verify=False, timeout=30)
        x = dec(r.text, common)
        return json.loads(x) if x else {}
    except:
        return {}

def ds(enc_data):
    try:
        raw = AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').decrypt(base64.b64decode(enc_data))
        txt = unpad(raw, 16).decode(errors='ignore')
        for i in range(len(txt), 0, -1):
            try: return json.loads(txt[:i])
            except: continue
    except: pass
    return {}

def es(data): 
    return base64.b64encode(AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').encrypt(pad(data.encode(), 16))).decode()

def get_link(jid, tile_id, course_id):
    res = api("/meta_distributer/on_request_meta_source", {
        "course_id": course_id, "tile_id": tile_id, "name": f"{jid}_0_0",
        "device_id": "x", "device_name": "x", "download_click": "0", "type": "video"
    })
    d = res.get("data", {})
    urls = d.get("bitrate_urls", [])
    if urls:
        for i in [3,2,1,0]:
            if i < len(urls) and urls[i].get("url"):
                return urls[i]["url"].split("?Expires=")[0]
    link = d.get("link") or d.get("url", "")
    if link and ("http" in link or link.endswith(('.m3u8', '.pdf'))):
        return link.split("?Expires=")[0]
    if link:
        return f"https://www.youtube.com/embed/{link}"
    return None

async def extract(update: Update, context: ContextTypes.DEFAULT_TYPE, mobile, pwd, batch):
    global key, iv
    s = requests.Session()
    s.mount('https://', requests.adapters.HTTPAdapter(pool_maxsize=100))

    status = await update.message.reply_text("🔄 Getting token...")
    
    try:
        csrf = s.get("https://online.utkarsh.com/", verify=False, timeout=20).cookies.get('csrf_name')
        if not csrf: raise Exception("CSRF failed")

        await status.edit_text("🔐 Logging in...")
        login_res = s.post("https://online.utkarsh.com/web/Auth/login", data={
            "mobile": mobile, "password": pwd, "csrf_name": csrf,
            "url": "0", "submit": "LogIn", "device_token": "null"
        }, verify=False, timeout=20).json()

        data = ds(login_res.get("response", {}))
        if not data or data.get("status") != 1:
            await status.edit_text("❌ Login Failed – Wrong Mobile/Password")
            return

        jwt = data["data"]["jwt"]
        HEADERS["jwt"] = jwt

        profile = api("/users/get_my_profile", {}, True)
        uid = profile["data"]["id"]
        HEADERS["userid"] = uid
        key = "".join(key_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()
        iv = "".join(iv_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()

        await status.edit_text("📂 Extracting links... (can take 3-10 mins)")

        result = BytesIO()
        result.write(f"UTKARSH BATCH {batch} – EXTRACTED LINKS\n{'='*50}\n\n".encode())
        count = 0

        # Get courses
        courses_res = s.post("https://online.utkarsh.com/web/Course/tiles_data", data={
            "tile_input": es(json.dumps({"course_id": batch, "parent_id": 0, "tile_id": "15330", "layer": 1, "type": "course_combo", "revert_api": "1#0#0#1"})),
            "csrf_name": csrf
        }, verify=False).json()
        courses = ds(courses_res.get("response", {}) ).get("data", [])
        if isinstance(courses, dict): courses = [courses]

        for course in courses:
            cid = course["id"]
            cname = course.get("title", "Unknown")
            result.write(f"\n📂 {cname}\n".encode())

            pg = 1
            while True:
                sub_res = s.post("https://online.utkarsh.com/web/Course/tiles_data", data={
                    "tile_input": es(json.dumps({"course_id": cid, "parent_id": cid, "layer": 1, "page": pg, "tile_id": "0", "type": "content", "revert_api": "1#1#0#1"})),
                    "csrf_name": csrf
                }, verify=False).json()
                sub_data = ds(sub_res.get("response", {}))
                if not sub_data or "list" not in sub_data.get("data", {}): break

                for subject in sub_data["data"]["list"]:
                    sid = subject["id"]
                    sname = subject.get("title", "Subject")
                    result.write(f"\n  📖 {sname}\n".encode())

                    pg2 = 1
                    while True:
                        topic_res = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data", data={
                            "layer_two_input_data": base64.b64encode(json.dumps({
                                "course_id": cid, "parent_id": cid, "subject_id": sid,
                                "topic_id": sid, "layer": 2, "page": pg2, "tile_id": 0,
                                "type": "content", "revert_api": "1#0#0#1"
                            }).encode()).decode(),
                            "csrf_name": csrf
                        }, verify=False).json()

                        topic_data = ds(topic_res.get("response", {}))
                        if not topic_data or "list" not in topic_data.get("data", {}): break

                        for topic in topic_data["data"]["list"]:
                            tid = topic["id"]
                            tname = topic.get("title", "Topic")
                            tile_id = topic.get("payload", {}).get("tile_id")

                            if topic.get("has_child") == 1:
                                # Simple layer 3 & 4 handling (recursive calls removed for speed)
                                link = get_link(tid, tile_id, cid) if tile_id else None
                                if link:
                                    result.write(f"    {tname}:{link}\n".encode())
                                    count += 1
                            elif tile_id:
                                link = get_link(tid, tile_id, cid)
                                if link:
                                    result.write(f"    {tname}:{link}\n".encode())
                                    count += 1

                        if pg2 >= topic_data["data"].get("total_page", 1): break
                        pg2 += 1

                if pg >= sub_data["data"].get("total_page", 1): break
                pg += 1

        result.write(f"\n{'='*50}\nTOTAL LINKS: {count}\n".encode())
        result.seek(0)

        await status.delete()
        await update.message.reply_document(
            document=("Utkarsh_Batch_" + batch + ".txt", result),
            caption=f"Batch {batch} → {count} links extracted ✅\nBot by @YourChannel"
        )

    except Exception as e:
        await status.edit_text(f"Error: {str(e)}")

# =============== BOT HANDLERS ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ *Utkarsh Instant Extractor Bot* ⚡\n\n"
        "Send /extract → Mobile → Password → Batch ID\n"
        "Get all video links in .txt file instantly!\n\n"
        "Working 100% – January 2025 🔥",
        parse_mode="Markdown"
    )

async def extract_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send Mobile/Email:", reply_markup=update.message.reply_markup.force_reply)
    context.user_data["step"] = "mobile"

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if step == "mobile":
        context.user_data["mobile"] = text
        await update.message.reply_text("Send Password:", reply_markup=update.message.reply_markup.force_reply)
        context.user_data["step"] = "pwd"
    elif step == "pwd":
        context.user_data["pwd"] = text
        await update.message.reply_text("Send Batch ID:", reply_markup=update.message.reply_markup.force_reply)
        context.user_data["step"] = "batch"
    elif step == "batch":
        await update.message.reply_text("Starting extraction... Hold on! ⏳")
        await extract(update, context, context.user_data["mobile"], context.user_data["pwd"], text)
        context.user_data.clear()

# =============== RUN ===============
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("extract", extract_cmd))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

print("Utkarsh Bot Started!")
app.run_polling(drop_pending_updates=True)
