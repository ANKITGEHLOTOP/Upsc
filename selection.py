import os
import json
import requests
import telebot
from telebot import types
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from base64 import b64decode, b64encode
import base64
import urllib3
import io
import threading

urllib3.disable_warnings()

# ===== BOT TOKEN =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo")

bot = telebot.TeleBot(BOT_TOKEN)

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

# User sessions and states storage
user_sessions = {}
user_states = {}

# States
STATE_NONE = 0
STATE_LOGIN_EMAIL = 1
STATE_LOGIN_PASSWORD = 2
STATE_BATCH_ID = 3

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

def api_call(p, d, headers, key, iv, c=False):
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
        r = api_call("/meta_distributer/on_request_meta_source", {
            "course_id": fi, "device_id": "x", "device_name": "x",
            "download_click": "0", "name": f"{ji}_0_0", "tile_id": jti, "type": "video"
        }, headers, key, iv, False)
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

def extract_layer3(s, h, cs, fi, sfi, ti, tn, headers, key, iv, results, count_ref):
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
                    extract_layer4(s, h, cs, fi, sfi, ji, f"{tn}/{jt}", headers, key, iv, results, count_ref)
                elif ji and jti:
                    lk = get_link(ji, jti, fi, headers, key, iv)
                    if lk:
                        results.append(f"{tn}/{jt}:{lk}")
                        count_ref[0] += 1
            if pg >= dr["data"].get("total_page", 1):
                break
            pg += 1
        except:
            break

def extract_layer4(s, h, cs, fi, sfi, ti, tn, headers, key, iv, results, count_ref):
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
                        count_ref[0] += 1
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
    count_ref = [0]
    results.append(f"⚡ UTKARSH EXTRACTOR - Batch {batch_id}")
    results.append("=" * 40)
    
    try:
        d3 = {"course_id": batch_id, "revert_api": "1#0#0#1", "parent_id": 0, "tile_id": "15330", "layer": 1, "type": "course_combo"}
        r = s.post("https://online.utkarsh.com/web/Course/tiles_data",
                   headers=h, data={'tile_input': es(json.dumps(d3)), 'csrf_name': cs}, verify=False, timeout=30).json()
        dr3 = ds(r.get("response"))
        
        if not dr3:
            return None, "❌ Course not found or access denied!"
        
        courses = dr3.get("data", [])
        if isinstance(courses, dict):
            courses = [courses]
        
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
                                extract_layer3(s, h, cs, fi, sfi, ti, f"{sfn}/{tt}", headers, key, iv, results, count_ref)
                            elif ti and jti:
                                lk = get_link(ti, jti, fi, headers, key, iv)
                                if lk:
                                    results.append(f"{sfn}/{tt}:{lk}")
                                    count_ref[0] += 1
                        
                        if pg2 >= dr.get("data", {}).get("total_page", 1):
                            break
                        pg2 += 1
                
                if pg >= dr.get("data", {}).get("total_page", 1):
                    break
                pg += 1
        
        results.append(f"\n{'=' * 40}")
        results.append(f"✅ TOTAL: {count_ref[0]} links extracted")
        
        return results, count_ref[0]
    
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

# ===== BOT HANDLERS =====

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_msg = """
🎓 *UTKARSH EXTRACTOR BOT* 🎓

Welcome! This bot extracts video links from Utkarsh courses.

*Commands:*
/login - Login to your Utkarsh account
/extract - Extract links from a batch
/logout - Logout from current session
/status - Check login status
/cancel - Cancel current operation

*How to use:*
1️⃣ Use /login to authenticate
2️⃣ Use /extract and provide Batch ID
3️⃣ Wait for extraction to complete
4️⃣ Download the text file with links

⚠️ _Use responsibly!_
    """
    bot.reply_to(message, welcome_msg, parse_mode='Markdown')

@bot.message_handler(commands=['cancel'])
def cancel_operation(message):
    user_id = message.from_user.id
    user_states[user_id] = STATE_NONE
    bot.reply_to(message, "❌ Operation cancelled.")

@bot.message_handler(commands=['login'])
def login_start(message):
    user_id = message.from_user.id
    
    if user_id in user_sessions:
        bot.reply_to(message, "✅ You're already logged in!\n\nUse /logout first to login with different account.")
        return
    
    user_states[user_id] = STATE_LOGIN_EMAIL
    bot.reply_to(message, "📱 Enter your *Mobile Number/Email*:", parse_mode='Markdown')

@bot.message_handler(commands=['logout'])
def logout(message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        bot.reply_to(message, "✅ Logged out successfully!")
    else:
        bot.reply_to(message, "ℹ️ You're not logged in.")

@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        session = user_sessions[user_id]
        bot.reply_to(message, 
            f"✅ *Logged In*\n\n"
            f"📧 Email: {session.get('email', 'N/A')}\n"
            f"🆔 User ID: {session.get('uid', 'N/A')}",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "❌ Not logged in. Use /login")

@bot.message_handler(commands=['extract'])
def extract_start(message):
    user_id = message.from_user.id
    
    if user_id not in user_sessions:
        bot.reply_to(message, "❌ Please /login first!")
        return
    
    user_states[user_id] = STATE_BATCH_ID
    bot.reply_to(message, "📚 Enter the *Batch ID* to extract:", parse_mode='Markdown')

def do_login(message, email, password):
    user_id = message.from_user.id
    
    status_msg = bot.reply_to(message, "⏳ Logging in, please wait...")
    
    try:
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
        s.mount('https://', adapter)
        
        csrf_resp = s.get("https://online.utkarsh.com/", verify=False, timeout=15)
        cs = csrf_resp.cookies.get('csrf_name')
        
        if not cs:
            bot.edit_message_text("❌ Failed to get CSRF token. Try again later.", 
                                  message.chat.id, status_msg.message_id)
            return
        
        h = {
            'Host': 'online.utkarsh.com',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 Chrome/119.0.0.0'
        }
        
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
            bot.edit_message_text("❌ Login failed! Check your credentials.", 
                                  message.chat.id, status_msg.message_id)
            return
        
        h["token"] = dr.get("token")
        h["jwt"] = dr["data"]["jwt"]
        
        api_headers = BASE_HEADERS.copy()
        api_headers["jwt"] = h["jwt"]
        
        p = api_call("/users/get_my_profile", {}, api_headers, None, None, True)
        
        if not p.get("data"):
            bot.edit_message_text("❌ Failed to get profile!", 
                                  message.chat.id, status_msg.message_id)
            return
        
        uid = str(p["data"]["id"])
        api_headers["userid"] = uid
        
        key = "".join(key_chars[int(i)] for i in (uid + "1524567456436545")[:16]).encode()
        iv = "".join(iv_chars[int(i)] for i in (uid + "1524567456436545")[:16]).encode()
        
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
        
        bot.edit_message_text(
            f"✅ *Login Successful!*\n\n"
            f"👤 User ID: `{uid}`\n\n"
            f"Use /extract to extract batch links.",
            message.chat.id, status_msg.message_id,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", 
                              message.chat.id, status_msg.message_id)

def do_extract(message, batch_id):
    user_id = message.from_user.id
    
    if user_id not in user_sessions:
        bot.reply_to(message, "❌ Session expired! Please /login again.")
        return
    
    status_msg = bot.reply_to(message, 
        f"⏳ *Extracting Batch {batch_id}...*\n\n"
        f"This may take several minutes. Please wait!",
        parse_mode='Markdown'
    )
    
    try:
        results, count = full_extraction(user_sessions[user_id], batch_id)
        
        if results is None:
            bot.edit_message_text(f"❌ {count}", message.chat.id, status_msg.message_id)
            return
        
        file_content = "\n".join(results)
        file_buffer = io.BytesIO(file_content.encode('utf-8'))
        file_buffer.name = f"Utkarsh_{batch_id}.txt"
        file_buffer.seek(0)
        
        bot.edit_message_text("✅ Extraction complete! Sending file...", 
                              message.chat.id, status_msg.message_id)
        
        bot.send_document(
            message.chat.id,
            file_buffer,
            caption=f"✅ *Extraction Complete!*\n\n📊 Total Links: {count}\n📂 Batch: {batch_id}",
            parse_mode='Markdown'
        )
        
        bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ Error during extraction: {str(e)}", 
                              message.chat.id, status_msg.message_id)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, STATE_NONE)
    text = message.text.strip()
    
    if state == STATE_LOGIN_EMAIL:
        user_states[user_id] = STATE_LOGIN_PASSWORD
        user_sessions[user_id + 1000000000] = {'temp_email': text}  # Temp storage
        bot.reply_to(message, "🔑 Enter your *Password*:", parse_mode='Markdown')
    
    elif state == STATE_LOGIN_PASSWORD:
        user_states[user_id] = STATE_NONE
        temp_data = user_sessions.pop(user_id + 1000000000, {})
        email = temp_data.get('temp_email', '')
        
        # Run login in thread to avoid blocking
        thread = threading.Thread(target=do_login, args=(message, email, text))
        thread.start()
    
    elif state == STATE_BATCH_ID:
        user_states[user_id] = STATE_NONE
        
        # Run extraction in thread to avoid blocking
        thread = threading.Thread(target=do_extract, args=(message, text))
        thread.start()
    
    else:
        bot.reply_to(message, "❓ Unknown command. Use /help to see available commands.")

# ===== MAIN =====
if __name__ == "__main__":
    print("🚀 Starting Utkarsh Extractor Bot...")
    print("✅ Bot is running!")
    
    # Remove webhook if any
    bot.remove_webhook()
    
    # Start polling
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
