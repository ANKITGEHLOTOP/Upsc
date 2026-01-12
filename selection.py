# UTKARSH EXTRACTOR BOT - FULLY WORKING JANUARY 2025
# Just change BOT_TOKEN and deploy on Koyeb → DONE!

import json
import base64
import requests
import urllib3
from io import BytesIO

from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

urllib3.disable_warnings()

# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
BOT_TOKEN = "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo"  # ← YOUR TOKEN HERE
# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

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
    except: return None

def api(path, data, common=False):
    try:
        r = requests.post(API_URL + path, headers=HEADERS, data=enc(data, common), verify=False, timeout=30)
        x = dec(r.text, common)
        return json.loads(x) if x else {}
    except: return {}

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

async def extract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mobile = context.user_data["mobile"]
    pwd = context.user_data["pwd"]
    batch = context.user_data["batch"]

    s = requests.Session()
    s.mount('https://', requests.adapters.HTTPAdapter(pool_maxsize=200))

    status_msg = await update.message.reply_text("🔄 Logging in...")

    try:
        csrf = s.get("https://online.utkarsh.com/", verify=False, timeout=20).cookies.get('csrf_name')
        if not csrf:
            await status_msg.edit_text("❌ Failed to get login token")
            return

        login_res = s.post("https://online.utkarsh.com/web/Auth/login", data={
            "mobile": mobile, "password": pwd, "csrf_name": csrf,
            "url": "0", "submit": "LogIn", "device_token": "null"
        }, verify=False, timeout=20).json()

        login_data = ds(login_res.get("response", {}))
        if not login_data or login_data.get("status") != 1:
            await status_msg.edit_text("❌ Wrong Mobile/Email or Password!")
            return

        HEADERS["jwt"] = login_data["data"]["jwt"]
        profile = api("/users/get_my_profile", {}, True)
        uid = profile["data"]["id"]
        HEADERS["userid"] = uid
        global key, iv
        key = "".join(key_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()
        iv = "".join(iv_chars[int(c)] for c in (uid + "1524567456436545")[:16]).encode()

        await status_msg.edit_text("🔥 Extracting all videos... (3-8 minutes)")

        result = BytesIO()
        result.write(f"UTKARSH BATCH {batch} - ALL VIDEO LINKS\n{'='*60}\n\n".encode())
        total_links = 0

        course_res = s.post("https://online.utkarsh.com/web/Course/tiles_data", data={
            "tile_input": es(json.dumps({"course_id": batch, "parent_id": 0, "tile_id": "15330", "layer": 1, "type": "course_combo", "revert_api": "1#0#0#1"})),
            "csrf_name": csrf
        }, verify=False).json()
        courses = ds(course_res.get("response", {}) ).get("data", [])
        if isinstance(courses, dict): courses = [courses]

        for course in courses:
            cid = course["id"]
            cname = course.get("title", "Unknown Course")
            result.write(f"\n📂 COURSE: {cname}\n".encode())

            page = 1
            while True:
                sub_res = s.post("https://online.utkarsh.com/web/Course/tiles_data", data={
                    "tile_input": es(json.dumps({"course_id": cid, "parent_id": cid, "layer": 1, "page": page, "tile_id": "0", "type": "content", "revert_api": "1#1#0#1"})),
                    "csrf_name": csrf
                }, verify=False).json()
                sub_data = ds(sub_res.get("response", {}))
                if not sub_data or "list" not in sub_data.get("data", {}): break

                for subject in sub_data["data"]["list"]:
                    sid = subject["id"]
                    sname = subject.get("title", "Subject")
                    result.write(f"\n   📖 {sname}\n".encode())

                    page2 = 1
                    while True:
                        topic_res = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data", data={
                            "layer_two_input_data": base64.b64encode(json.dumps({
                                "course_id": cid, "parent_id": cid, "subject_id": sid, "topic_id": sid,
                                "layer": 2, "page": page2, "tile_id": 0, "type": "content", "revert_api": "1#0#0#1"
                            }).encode()).decode(),
                            "csrf_name": csrf
                        }, verify=False).json()

                        topic_data = ds(topic_res.get("response", {}))
                        if not topic_data or "list" not in topic_data.get("data", {}): break

                        for topic in topic_data["data"]["list"]:
                            tid = topic["id"]
                            tname = topic.get("title", "Video")
                            tile_id = topic.get("payload", {}).get("tile_id")
                            if tile_id:
                                link = get_link(tid, tile_id, cid)
                                if link:
                                    result.write(f"    🎥 {tname}: {link}\n".encode())
                                    total_links += 1

                        if page2 >= topic_data["data"].get("total_page", 1): break
                        page2 += 1

                if page >= sub_data["data"].get("total_page", 1): break
                page += 1

        result.write(f"\n{'='*60}\nTOTAL LINKS EXTRACTED: {total_links}\n".encode())
        result.seek(0)

        await status_msg.delete()
        await update.message.reply_document(
            document=("Utkarsh_Batch_" + batch + ".txt", result),
            caption=f"✅ Batch {batch} Done!\n📊 Total Links: {total_links}\n🔥 Free Bot by @YourChannel"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

# ================= BOT HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ *UTKARSH FULL EXTRACTOR BOT* ⚡\n\n"
        "Send /extract → Mobile → Password → Batch ID\n"
        "Get ALL videos + PDFs in .txt file!\n\n"
        "Working 100% - January 2025 🔥",
        parse_mode="Markdown"
    )

async def extract_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 Send Mobile Number or Email:",
        reply_markup=ForceReply(force_reply=True, selective=True)
    )
    context.user_data["step"] = "mobile"

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "step" not in context.user_data:
        return

    text = update.message.text.strip()
    step = context.user_data["step"]

    if step == "mobile":
        context.user_data["mobile"] = text
        await update.message.reply_text("🔑 Send Password:", reply_markup=ForceReply(force_reply=True, selective=True))
        context.user_data["step"] = "pwd"

    elif step == "pwd":
        context.user_data["pwd"] = text
        await update.message.reply_text("📚 Send Batch ID:", reply_markup=ForceReply(force_reply=True, selective=True))
        context.user_data["step"] = "batch"

    elif step == "batch":
        context.user_data["batch"] = text
        await update.message.reply_text("🚀 Starting extraction...\nPlease wait 3-8 minutes ⏳")
        await extract(update, context)
        context.user_data.clear()

# ================= RUN BOT =================
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("extract", extract_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("UTKARSH BOT IS LIVE & READY!")
    app.run_polling(drop_pending_updates=True)
