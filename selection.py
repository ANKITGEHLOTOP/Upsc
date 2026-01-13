import os
import json
import asyncio
import requests
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from base64 import b64decode, b64encode
import base64
import urllib3
import io

urllib3.disable_warnings()

# ===== BOT TOKEN =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo")

# ===== CONSTANTS =====
API_URL = "https://application.utkarshapp.com/index.php/data_model"
COMMON_KEY = b"%!^F&^$)&^$&*$^&"
COMMON_IV = b"#*v$JvywJvyJDyvJ"
key_chars = "%!F*&^$)_*%3f&B+"
iv_chars = "#*$DJvyw2w%!_-$@"
BASE_HEADERS = {
    "Authorization": "Bearer 152#svf346t45ybrer34yredk76t",
    "Content-Type": "text/plain; charset=UTF-8",
    "devicetype": "1",
    "host": "application.utkarshapp.com",
    "lang": "1",
    "user-agent": "okhttp/4.9.0",
    "userid": "0",
    "version": "152"
}

# Conversation states
LOGIN_EMAIL, LOGIN_PASSWORD, BATCH_ID = range(3)

# User sessions storage
user_sessions = {}

# ===== CRYPTO FUNCTIONS =====
def enc(d, key, iv, c=False):
    ck, ci = (COMMON_KEY, COMMON_IV) if c else (key, iv)
    return b64encode(AES.new(ck, AES.MODE_CBC, ci).encrypt(pad(json.dumps(d, separators=(",", ":")).encode(), 16))).decode() + ":"

def dec(d, key, iv, c=False):
    ck, ci = (COMMON_KEY, COMMON_IV) if c else (key, iv)
    try:
        return unpad(AES.new(ck, AES.MODE_CBC, ci).decrypt(b64decode(d.split(":")[0])), 16).decode()
    except:
        return None

def api(p, d, headers, key, iv, c=False):
    try:
        r = requests.post(f"{API_URL}{p}", headers=headers, data=enc(d, key, iv, c), verify=False, timeout=30)
        x = dec(r.text, key, iv, c)
        return json.loads(x) if x else {}
    except:
        return {}

def ds(e):
    try:
        d = AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').decrypt(b64decode(e))
        try:
            p = unpad(d, 16).decode()
        except:
            p = d.decode(errors='ignore')
        for x in range(len(p), 0, -1):
            try:
                return json.loads(p[:x])
            except:
                continue
    except:
        pass
    return None

def es(d):
    try:
        return b64encode(AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').encrypt(pad(d.encode(), 16))).decode()
    except:
        return None

# ===== EXTRACTION FUNCTIONS =====
def get_link(ji, jti, fi, headers, key, iv):
    try:
        r = api("/meta_distributer/on_request_meta_source", {
            "course_id": fi, "device_id": "x", "device_name": "x",
            "download_click": "0", "name": f"{ji}_0_0", "tile_id": jti, "type": "video"
        }, headers, key, iv)
        d = r.get("data", {})
        if not d:
            return None
        q = d.get("bitrate_urls", [])
        if q:
            for i in [3, 2, 1, 0]:
                if len(q) > i and q[i].get("url"):
                    return q[i]["url"].split("?Expires=")[0]
        l = d.get("link", "") or d.get("url", "")
        if l:
            if "http" in l or ".m3u8" in l or ".pdf" in l:
                return l.split("?Expires=")[0]
            return f"https://www.youtube.com/embed/{l}"
    except:
        pass
    return None

def extract_layer3(s, h, cs, fi, sfi, ti, tn, headers, key, iv, results):
    pg = 1
    while True:
        try:
            d = {"course_id": fi, "parent_id": fi, "layer": 3, "page": pg,
                 "revert_api": "1#0#0#1", "subject_id": sfi, "tile_id": 0, "topic_id": ti, "type": "content"}
            r = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data",
                       headers=h, data={'layer_two_input_data': base64.b64encode(json.dumps(d).encode()).decode(),
                                        'csrf_name': cs}, verify=False, timeout=30).json()
            dr = ds(r.get("response"))
            if not dr or "data" not in dr:
                break
            items = dr["data"].get("list", [])
            if not items:
                break
            for i in items:
                ji, jt, p = i.get("id"), i.get("title", "?"), i.get("payload", {})
                jti = p.get("tile_id")
                if i.get("has_child") == 1:
                    extract_layer4(s, h, cs, fi, sfi, ji, f"{tn}/{jt}", headers, key, iv, results)
                elif ji and jti:
                    lk = get_link(ji, jti, fi, headers, key, iv)
                    if lk:
                        results.append(f"{tn}/{jt}:{lk}")
            if pg >= dr["data"].get("total_page", 1):
                break
            pg += 1
        except:
            break

def extract_layer4(s, h, cs, fi, sfi, ti, tn, headers, key, iv, results):
    pg = 1
    while True:
        try:
            d = {"course_id": fi, "parent_id": fi, "layer": 4, "page": pg,
                 "revert_api": "1#0#0#1", "subject_id": sfi, "tile_id": 0, "topic_id": ti, "type": "content"}
            r = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data",
                       headers=h, data={'layer_two_input_data': base64.b64encode(json.dumps(d).encode()).decode(),
                                        'csrf_name': cs}, verify=False, timeout=30).json()
            dr = ds(r.get("response"))
            if not dr or "data" not in dr:
                break
            items = dr["data"].get("list", [])
            if not items:
                break
            for i in items:
                ji, jt, p = i.get("id"), i.get("title", "?"), i.get("payload", {})
                jti = p.get("tile_id")
                if ji and jti:
                    lk = get_link(ji, jti, fi, headers, key, iv)
                    if lk:
                        results.append(f"{tn}/{jt}:{lk}")
            if pg >= dr["data"].get("total_page", 1):
                break
            pg += 1
        except:
            break

def full_extraction(session_data, batch_id):
    """Main extraction function"""
    s = session_data['session']
    h = session_data['web_headers']
    cs = session_data['csrf']
    headers = session_data['api_headers']
    key = session_data['key']
    iv = session_data['iv']
    
    results = []
    results.append(f"⚡ UTKARSH EXTRACTOR - Batch {batch_id}")
    results.append("=" * 40)
    
    # Get course
    d3 = {"course_id": batch_id, "revert_api": "1#0#0#1", "parent_id": 0, "tile_id": "15330", "layer": 1, "type": "course_combo"}
    r = s.post("https://online.utkarsh.com/web/Course/tiles_data",
               headers=h, data={'tile_input': es(json.dumps(d3)), 'csrf_name': cs}, verify=False, timeout=30).json()
    dr3 = ds(r.get("response"))
    
    if not dr3:
        return None, "❌ Course not found or access denied!"
    
    courses = dr3.get("data", [])
    if isinstance(courses, dict):
        courses = [courses]
    
    count = 0
    for c in courses:
        fi, tn = c.get("id"), c.get("title", "Course")
        results.append(f"\n📂 {tn}")
        
        pg = 1
        while True:
            d5 = {"course_id": fi, "layer": 1, "page": pg, "parent_id": fi,
                  "revert_api": "1#1#0#1", "tile_id": "0", "type": "content"}
            r = s.post("https://online.utkarsh.com/web/Course/tiles_data",
                       headers=h, data={'tile_input': es(json.dumps(d5)), 'csrf_name': cs}, verify=False, timeout=30).json()
            dr = ds(r.get("response"))
            if not dr:
                break
            subs = dr.get("data", {}).get("list", [])
            if not subs:
                break
            
            for sub in subs:
                sfi, sfn = sub.get("id"), sub.get("title", "Subject")
                results.append(f"\n  📖 {sfn}")
                
                pg2 = 1
                while True:
                    d7 = {"course_id": fi, "parent_id": fi, "layer": 2, "page": pg2,
                          "revert_api": "1#0#0#1", "subject_id": sfi, "tile_id": 0, "topic_id": sfi, "type": "content"}
                    r = s.post("https://online.utkarsh.com/web/Course/get_layer_two_data",
                               headers=h, data={'layer_two_input_data': base64.b64encode(json.dumps(d7).encode()).decode(),
                                                'csrf_name': cs}, verify=False, timeout=30).json()
                    dr = ds(r.get("response"))
                    if not dr:
                        break
                    tops = dr.get("data", {}).get("list", [])
                    if not tops:
                        break
                    
                    for t in tops:
                        ti, tt = t.get("id"), t.get("title", "Topic")
                        p = t.get("payload", {})
                        jti = p.get("tile_id")
                        
                        if t.get("has_child") == 1:
                            extract_layer3(s, h, cs, fi, sfi, ti, f"{sfn}/{tt}", headers, key, iv, results)
                        elif ti and jti:
                            lk = get_link(ti, jti, fi, headers, key, iv)
                            if lk:
                                results.append(f"{sfn}/{tt}:{lk}")
                                count += 1
                    
                    if pg2 >= dr.get("data", {}).get("total_page", 1):
                        break
                    pg2 += 1
            
            if pg >= dr.get("data", {}).get("total_page", 1):
                break
            pg += 1
    
    results.append(f"\n{'=' * 40}")
    results.append(f"✅ TOTAL: {count} links extracted")
    
    return results, count

# ===== BOT HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = """
🎓 **UTKARSH EXTRACTOR BOT** 🎓

Welcome! This bot extracts video links from Utkarsh courses.

**Commands:**
/login - Login to your Utkarsh account
/extract - Extract links from a batch
/logout - Logout from current session
/status - Check login status
/help - Show this message

**How to use:**
1️⃣ Use /login to authenticate
2️⃣ Use /extract and provide Batch ID
3️⃣ Wait for extraction to complete
4️⃣ Download the text file with links

⚠️ *Use responsibly and respect copyright!*
    """
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        await update.message.reply_text("✅ You're already logged in!\n\nUse /logout first to login with different account.")
        return ConversationHandler.END
    
    await update.message.reply_text("📱 Enter your **Mobile Number/Email**:", parse_mode='Markdown')
    return LOGIN_EMAIL

async def login_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['email'] = update.message.text.strip()
    await update.message.reply_text("🔑 Enter your **Password**:", parse_mode='Markdown')
    return LOGIN_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    email = context.user_data.get('email')
    password = update.message.text.strip()
    
    await update.message.reply_text("⏳ Logging in, please wait...")
    
    try:
        # Create session
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
        s.mount('https://', adapter)
        
        # Get CSRF
        csrf_resp = s.get("https://online.utkarsh.com/", verify=False, timeout=15)
        cs = csrf_resp.cookies.get('csrf_name')
        
        if not cs:
            await update.message.reply_text("❌ Failed to get CSRF token. Try again later.")
            return ConversationHandler.END
        
        # Web headers
        h = {
            'Host': 'online.utkarsh.com',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 Chrome/119.0.0.0'
        }
        
        # Login
        login_data = {
            'csrf_name': cs,
            'mobile': email,
            'url': '0',
            'password': password,
            'submit': 'LogIn',
            'device_token': 'null'
        }
        
        r = s.post("https://online.utkarsh.com/web/Auth/login", data=login_data, headers=h, verify=False, timeout=15).json()
        dr = ds(r.get("response"))
        
        if not dr or dr.get("status") != 200:
            await update.message.reply_text("❌ Login failed! Check your credentials.")
            return ConversationHandler.END
        
        h["token"] = dr.get("token")
        h["jwt"] = dr["data"]["jwt"]
        
        # API headers
        api_headers = BASE_HEADERS.copy()
        api_headers["jwt"] = h["jwt"]
        
        # Get profile
        p = api("/users/get_my_profile", {}, api_headers, None, None, True)
        
        if not p.get("data"):
            await update.message.reply_text("❌ Failed to get profile!")
            return ConversationHandler.END
        
        uid = p["data"]["id"]
        api_headers["userid"] = uid
        
        # Generate keys
        key = "".join(key_chars[int(i)] for i in (uid + "1524567456436545")[:16]).encode()
        iv = "".join(iv_chars[int(i)] for i in (uid + "1524567456436545")[:16]).encode()
        
        # Store session
        user_sessions[user_id] = {
            'session': s,
            'web_headers': h,
            'api_headers': api_headers,
            'csrf': cs,
            'key': key,
            'iv': iv,
            'uid': uid,
            'email': email
        }
        
        await update.message.reply_text(
            f"✅ **Login Successful!**\n\n"
            f"👤 User ID: `{uid}`\n\n"
            f"Use /extract to extract batch links.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("✅ Logged out successfully!")
    else:
        await update.message.reply_text("ℹ️ You're not logged in.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        session = user_sessions[user_id]
        await update.message.reply_text(
            f"✅ **Logged In**\n\n"
            f"📧 Email: {session.get('email', 'N/A')}\n"
            f"🆔 User ID: {session.get('uid', 'N/A')}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Not logged in. Use /login")

async def extract_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Please /login first!")
        return ConversationHandler.END
    
    await update.message.reply_text("📚 Enter the **Batch ID** to extract:", parse_mode='Markdown')
    return BATCH_ID

async def extract_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    batch_id = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Session expired! Please /login again.")
        return ConversationHandler.END
    
    status_msg = await update.message.reply_text(
        f"⏳ **Extracting Batch {batch_id}...**\n\n"
        f"This may take several minutes. Please wait!",
        parse_mode='Markdown'
    )
    
    try:
        # Run extraction in executor to avoid blocking
        loop = asyncio.get_event_loop()
        results, count = await loop.run_in_executor(
            None,
            full_extraction,
            user_sessions[user_id],
            batch_id
        )
        
        if results is None:
            await status_msg.edit_text(f"❌ {count}")  # count contains error message
            return ConversationHandler.END
        
        # Create file
        file_content = "\n".join(results)
        file_buffer = io.BytesIO(file_content.encode('utf-8'))
        file_buffer.name = f"Utkarsh_{batch_id}.txt"
        
        await status_msg.edit_text(f"✅ Extraction complete! Sending file...")
        
        # Send file
        await update.message.reply_document(
            document=InputFile(file_buffer, filename=f"Utkarsh_{batch_id}.txt"),
            caption=f"✅ **Extraction Complete!**\n\n📊 Total Links: {count}\n📂 Batch: {batch_id}",
            parse_mode='Markdown'
        )
        
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error during extraction: {str(e)}")
    
    return ConversationHandler.END

# ===== MAIN =====
def main():
    print("🚀 Starting Utkarsh Extractor Bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Login conversation handler
    login_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login_start)],
        states={
            LOGIN_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_email)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Extract conversation handler
    extract_handler = ConversationHandler(
        entry_points=[CommandHandler('extract', extract_start)],
        states={
            BATCH_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_batch)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Add handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(login_handler)
    app.add_handler(extract_handler)
    app.add_handler(CommandHandler('logout', logout))
    app.add_handler(CommandHandler('status', status))
    
    print("✅ Bot is running!")
    
    # Run bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
