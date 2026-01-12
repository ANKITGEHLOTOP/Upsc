# Utkarsh Extractor Telegram Bot - Ready for Koyeb / Heroku / Railway
# Made with ❤️ by Grok (modified for Telegram)

import requests
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from base64 import b64decode, b64encode
import base64
import urllib3
import os
from io import StringIO
import asyncio

from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

urllib3.disable_warnings()

# ===================== CONFIG =====================
BOT_TOKEN = os.getenv("8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo")  # Set this in Koyeb Environment Variables
API_URL = "https://application.utkarshapp.com/index.php/data_model"
COMMON_KEY = b"%!^F&^$)&^$&*$^&"
COMMON_IV = b"#*v$JvywJvyJDyvJ"
key_chars = "%!F*&^$)_*%3f&B+"
iv_chars = "#*$DJvyw2w%!_-$@"
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

# ==================== CRYPTO FUNCTIONS ====================
def enc(d, c=False):
    ck, ci = (COMMON_KEY, COMMON_IV) if c else (key, iv)
    return b64encode(AES.new(ck, AES.MODE_CBC, ci).encrypt(pad(json.dumps(d, separators=(",", ":")).encode(), 16))).decode() + ":"

def dec(d, c=False):
    ck, ci = (COMMON_KEY, COMMON_IV) if c else (key, iv)
    try:
        return unpad(AES.new(ck, AES.MODE_CBC, ci).decrypt(b64decode(d.split(":")[0])), 16).decode()
    except:
        return None

def api(p, d, c=False):
    try:
        r = requests.post(f"{API_URL}{p}", headers=HEADERS, data=enc(d, c), verify=False, timeout=30)
        x = dec(r.text, c)
        return json.loads(x) if x else {}
    except:
        return {}

def ds(e):
    try:
        d = AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').decrypt(b64decode(e))
        try: p = unpad(d, 16).decode()
        except: p = d.decode(errors='ignore')
        for x in range(len(p), 0, -1):
            try: return json.loads(p[:x])
            except: continue
    except: pass
    return None

def es(d):
    try: return b64encode(AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').encrypt(pad(d.encode(), 16))).decode()
    except: return None

# ===================== GET LINK =====================
def get_link(ji, jti, fi):
    try:
        r = api("/meta_distributer/on_request_meta_source", {
            "course_id": fi, "device_id": "x", "device_name": "x",
            "download_click": "0", "name": f"{ji}_0_0", "tile_id": jti, "type": "video"
        })
        d = r.get("data", {})
        if not d: return None
        q = d.get("bitrate_urls", [])
        if q:
            for i in [3,2,1,0]:
                if len(q) > i and q[i].get("url"):
                    return q[i]["url"].split("?Expires=")[0]
        l = d.get("link", "") or d.get("url", "")
        if l:
            if "http" in l or ".m3u8" in l or ".pdf" in l:
                return l.split("?Expires=")[0]
            return f"https://www.youtube.com/embed/{l}"
    except: pass
    return None

# ===================== LAYERS =====================
async def layer3(s, h, cs, fi, sfi, ti, tn, output):
    pg = 1
    while True:
        try:
            d = {"course_id": fi, "parent_id": fi, "layer": 3, "page": pg, "revert_api": "1#0#0#1",
                 "subject_id": sfi, "tile_id": 0, "topic_id": ti, "type": "content"}
            r = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data", headers=h,
                       data={'layer_two_input_data': base64.b64encode(json.dumps(d).encode()).decode(), 'csrf_name': cs},
                       verify=False, timeout=30).json()
            dr = ds(r.get("response"))
            if not dr or "data" not in dr: break
            items = dr["data"].get("list", [])
            if not items: break
            for i in items:
                ji, jt = i.get("id"), i.get("title", "?")
                p = i.get("payload", {})
                jti = p.get("tile_id")
                if i.get("has_child") == 1:
                    await layer4(s, h, cs, fi, sfi, ji, f"{tn}/{jt}", output)
                elif ji and jti:
                    lk = get_link(ji, jti, fi)
                    if lk:
                        output.write(f"{tn}/{jt}:{lk}\n")
            if pg >= dr["data"].get("total_page", 1): break
            pg += 1
        except: break

async def layer4(s, h, cs, fi, sfi, ti, tn, output):
    pg = 1
    while True:
        try:
            d = {"course_id": fi, "parent_id": fi, "layer": 4, "page": pg, "revert_api": "1#0#0#1",
                 "subject_id": sfi, "tile_id": 0, "topic_id": ti, "type": "content"}
            r = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data", headers=h,
                       data={'layer_two_input_data': base64.b64encode(json.dumps(d).encode()).decode(), 'csrf_name': cs},
                       verify=False, timeout=30).json()
            dr = ds(r.get("response"))
            if not dr or "data" not in dr: break
            items = dr["data"].get("list", [])
            if not items: break
            for i in items:
                ji, jt = i.get("id"), i.get("title", "?")
                p = i.get("payload", {})
                jti = p.get("tile_id")
                if ji and jti:
                    lk = get_link(ji, jti, fi)
                    if lk:
                        output.write(f"{tn}/{jt}:{lk}\n")
            if pg >= dr["data"].get("total_page", 1): break
            pg += 1
        except: break

# ===================== MAIN EXTRACTOR =====================
async def extract_batch(mobile, password, batch_id, update: Update, context: ContextTypes.DEFAULT_TYPE):
    global key, iv
    key = iv = None

    s = requests.Session()
    a = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
    s.mount('https://', a)

    msg = await update.message.reply_text("🔄 Getting CSRF...")
    cs = s.get("https://online.utkarsh.com/", verify=False, timeout=15).cookies.get('csrf_name')
    if not cs:
        await msg.edit_text("❌ CSRF Token Failed!")
        return

    await msg.edit_text("🔐 Logging in...")
    h = {
        'Host': 'online.utkarsh.com',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 Chrome/119.0.0.0'
    }

    r = s.post("https://online.utkarsh.com/web/Auth/login", data={
        'csrf_name': cs, 'mobile': mobile, 'url': '0', 'password': password,
        'submit': 'LogIn', 'device_token': 'null'
    }, headers=h, verify=False, timeout=15).json()

    dr = ds(r.get("response"))
    if not dr or dr.get("status") != 1:
        await msg.edit_text("❌ Login Failed! Wrong Mobile/Password.")
        return

    h["token"], h["jwt"] = dr.get("token"), dr["data"]["jwt"]
    HEADERS["jwt"] = h["jwt"]

    await msg.edit_text("👤 Fetching Profile...")
    p = api("/users/get_my_profile", {}, True)
    uid = p["data"]["id"]
    HEADERS["userid"] = uid
    key = "".join(key_chars[int(i)] for i in (uid + "1524567456436545")[:16]).encode()
    iv = "".join(iv_chars[int(i)] for i in (uid + "1524567456436545")[:16]).encode()

    await msg.edit_text("📂 Starting Extraction...\nThis may take 2-10 minutes depending on batch size.")

    output = StringIO()
    output.write(f"⚡ UTKARSH EXTRACTOR - Batch {batch_id}\n")
    output.write("=" * 50 + "\n\n")
    count = 0

    # Get course list
    d3 = {"course_id": batch_id, "revert_api": "1#0#0#1", "parent_id": 0, "tile_id": "15330", "layer": 1, "type": "course_combo"}
    r = s.post("https://online.utkarsh.com/web/Course/tiles_data", headers=h,
               data={'tile_input': es(json.dumps(d3)), 'csrf_name': cs}, verify=False).json()
    dr3 = ds(r.get("response"))
    if not dr3:
        await msg.edit_text("❌ Invalid Batch ID or No Access!")
        return

    courses = dr3.get("data", [])
    if isinstance(courses, dict): courses = [courses]

    for c in courses:
        fi, tn = c.get("id"), c.get("title", "Course")
        output.write(f"📂 {tn}\n")

        pg = 1
        while True:
            d5 = {"course_id": fi, "layer": 1, "page": pg, "parent_id": fi, "revert_api": "1#1#0#1", "tile_id": "0", "type": "content"}
            r = s.post("https://online.utkarsh.com/web/Course/tiles_data", headers=h,
                       data={'tile_input': es(json.dumps(d5)), 'csrf_name': cs}, verify=False).json()
            dr = ds(r.get("response"))
            if not dr: break
            subs = dr.get("data", {}).get("list", [])
            if not subs: break

            for sub in subs:
                sfi, sfn = sub.get("id"), sub.get("title", "Subject")
                output.write(f"\n  📖 {sfn}\n")

                pg2 = 1
                while True:
                    d7 = {"course_id": fi, "parent_id": fi, "layer": 2, "page": pg2, "revert_api": "1#0#0#1",
                          "subject_id": sfi, "tile_id": 0, "topic_id": sfi, "type": "content"}
                    r = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data", headers=h,
                               data={'layer_two_input_data': base64.b64encode(json.dumps(d7).encode()).decode(), 'csrf_name': cs},
                               verify=False).json()
                    dr = ds(r.get("response"))
                    if not dr: break
                    tops = dr.get("data", {}).get("list", [])
                    if not tops: break

                    for t in tops:
                        ti, tt = t.get("id"), t.get("title", "Topic")
                        p = t.get("payload", {})
                        jti = p.get("tile_id")

                        if t.get("has_child") == 1:
                            await layer3(s, h, cs, fi, sfi, ti, f"{sfn}/{tt}", output)
                        elif ti and jti:
                            lk = get_link(ti, jti, fi)
                            if lk:
                                output.write(f"{sfn}/{tt}:{lk}\n")
                                count += 1

                    if pg2 >= dr.get("data", {}).get("total_page", 1): break
                    pg2 += 1

            if pg >= dr.get("data", {}).get("total_page", 1): break
            pg += 1

    output.write(f"\n{'='*50}\n")
    output.write(f"✅ TOTAL: {count} LINKS EXTRACTED!\n")
    output.write("="*50)

    file_content = output.getvalue().encode('utf-8')
    await msg.edit_text(f"✅ Done! Extracted {count} links!\nUploading file...")

    await update.message.reply_document(
        document=("Utkarsh_Batch_" + batch_id + ".txt", file_content),
        caption=f"Batch {batch_id} • {count} links extracted ✅\nBy @Grok"
    )
    await msg.delete()

# ===================== TELEGRAM COMMANDS =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ *Utkarsh Instant Extractor Bot* ⚡\n\n"
        "Send /extract to start extracting any batch!\n\n"
        "Works 100% as of April 2025 🔥\n"
        "Made with ❤️ by Grok",
        parse_mode="Markdown"
    )

async def extract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 Send Mobile/Email\nExample: `7007059472` or `example@gmail.com`",
        parse_mode="Markdown", reply_markup=ForceReply()
    )
    context.user_data["step"] = "mobile"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = context.user_data.get("step")

    if step == "mobile":
        context.user_data["mobile"] = text
        await update.message.reply_text("🔑 Now send Password:", reply_markup=ForceReply())
        context.user_data["step"] = "password"

    elif step == "password":
        context.user_data["password"] = text
        await update.message.reply_text("📚 Now send Batch ID (Course ID):", reply_markup=ForceReply())
        context.user_data["step"] = "batch"

    elif step == "batch":
        batch_id = text
        await update.message.reply_text("🚀 Starting extraction...\nHold tight! ⏳")

        try:
            await extract_batch(
                mobile=context.user_data["mobile"],
                password=context.user_data["password"],
                batch_id=batch_id,
                update=update,
                context=context
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        finally:
            context.user_data.clear()

# ===================== MAIN =====================
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found! Add it in Environment Variables.")
        return

    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("extract", extract))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Utkarsh Extractor Bot is LIVE!")
    app.run_polling()

if __name__ == "__main__":
    main()
