import os
import json
import requests
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from base64 import b64decode, b64encode
import base64
import asyncio

# ======================= CONFIGURATION =======================
BOT_TOKEN = "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo"
PORT = int(os.environ.get("PORT", 8000))

# API Configuration
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

# Conversation states
WAITING_LOGIN, WAITING_BATCH = range(2)

# User sessions storage
user_sessions = {}

# ======================= FLASK APP FOR HEALTH CHECK =======================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Utkarsh Bot is Running!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# ======================= ENCRYPTION FUNCTIONS =======================
def encrypt(data, use_common_key, key, iv):
    cipher_key, cipher_iv = (COMMON_KEY, COMMON_IV) if use_common_key else (key, iv)
    cipher = AES.new(cipher_key, AES.MODE_CBC, cipher_iv)
    padded_data = pad(json.dumps(data, separators=(",", ":")).encode(), AES.block_size)
    encrypted = cipher.encrypt(padded_data)
    return b64encode(encrypted).decode() + ":"

def decrypt(data, use_common_key, key, iv):
    cipher_key, cipher_iv = (COMMON_KEY, COMMON_IV) if use_common_key else (key, iv)
    cipher = AES.new(cipher_key, AES.MODE_CBC, cipher_iv)
    try:
        encrypted_data = b64decode(data.split(":")[0])
        decrypted_bytes = cipher.decrypt(encrypted_data)
        decrypted = unpad(decrypted_bytes, AES.block_size).decode()
        return decrypted
    except (ValueError, TypeError) as e:
        print(f"Decryption error: {e}")
        return None

def post_request(path, data=None, use_common_key=False, key=None, iv=None, headers=None):
    if headers is None:
        headers = HEADERS.copy()
    encrypted_data = encrypt(data, use_common_key, key, iv) if data else data
    response = requests.post(f"{API_URL}{path}", headers=headers, data=encrypted_data)
    decrypted_data = decrypt(response.text, use_common_key, key, iv)
    if decrypted_data:
        try:
            return json.loads(decrypted_data)
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
    return {}

def decrypt_stream(enc):
    try:
        enc = b64decode(enc)
        key = '%!$!%_$&!%F)&^!^'.encode('utf-8')
        iv = '#*y*#2yJ*#$wJv*v'.encode('utf-8')
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_bytes = cipher.decrypt(enc)
        try:
            plaintext = unpad(decrypted_bytes, AES.block_size).decode('utf-8')
        except Exception:
            plaintext = decrypted_bytes.decode('utf-8', errors='ignore')
        cleaned_json = ''
        for i in range(len(plaintext)):
            try:
                json.loads(plaintext[:i+1])
                cleaned_json = plaintext[:i+1]
            except json.JSONDecodeError:
                continue
        final_brace_index = cleaned_json.rfind('}')
        if final_brace_index != -1:
            cleaned_json = cleaned_json[:final_brace_index + 1]
        return cleaned_json
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def decrypt_and_load_json(enc):
    decrypted_data = decrypt_stream(enc)
    try:
        return json.loads(decrypted_data)
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
        return None

def encrypt_stream(plain_text):
    try:
        key = '%!$!%_$&!%F)&^!^'.encode('utf-8')
        iv = '#*y*#2yJ*#$wJv*v'.encode('utf-8')
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_text = pad(plain_text.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded_text)
        return b64encode(encrypted).decode('utf-8')
    except Exception as e:
        print(f"Encryption error: {e}")
        return None

# ======================= LOGIN FUNCTION =======================
def perform_login(email, password):
    """Perform login and return session data or None"""
    try:
        session = requests.Session()
        base_url = 'https://online.utkarsh.com/'
        login_url = 'https://online.utkarsh.com/web/Auth/login'
        
        # Get CSRF token
        r1 = session.get(base_url)
        csrf_token = r1.cookies.get('csrf_name')
        
        if not csrf_token:
            return None, "Failed to get CSRF token"
        
        # Login
        d1 = {
            'csrf_name': csrf_token,
            'mobile': email,
            'url': '0',
            'password': password,
            'submit': 'LogIn',
            'device_token': 'null'
        }
        h = {
            'Host': 'online.utkarsh.com',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        u2 = session.post(login_url, data=d1, headers=h).json()
        r2 = u2.get("response")
        dr1 = decrypt_and_load_json(r2)
        
        if not dr1:
            return None, "Invalid credentials"
        
        t = dr1.get("token")
        jwt = dr1.get("data", {}).get("jwt")
        
        if not jwt:
            return None, "Could not get JWT token"
        
        h["token"] = t
        h["jwt"] = jwt
        
        # Get user profile
        headers_copy = HEADERS.copy()
        headers_copy["jwt"] = jwt
        
        profile = post_request("/users/get_my_profile", use_common_key=True, headers=headers_copy)
        user_profile_id = profile.get("data", {}).get("id")
        
        if not user_profile_id:
            return None, "Failed to get user profile"
        
        # Generate keys
        key = "".join(key_chars[int(i)] for i in (user_profile_id + "1524567456436545")[:16]).encode()
        iv = "".join(iv_chars[int(i)] for i in (user_profile_id + "1524567456436545")[:16]).encode()
        
        headers_copy["userid"] = user_profile_id
        
        session_data = {
            'logged_in': True,
            'session': session,
            'csrf_token': csrf_token,
            'headers': h,
            'api_headers': headers_copy,
            'key': key,
            'iv': iv,
            'user_profile_id': user_profile_id
        }
        
        return session_data, None
        
    except Exception as e:
        return None, str(e)

# ======================= BOT HANDLERS =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logged_in = user_id in user_sessions and user_sessions[user_id].get('logged_in')
    
    if logged_in:
        keyboard = [
            [InlineKeyboardButton("📚 Extract Course", callback_data="extract")],
            [InlineKeyboardButton("🚪 Logout", callback_data="logout")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        status = "✅ *Status:* Logged In"
    else:
        keyboard = [
            [InlineKeyboardButton("🔐 Login", callback_data="login")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        status = "❌ *Status:* Not Logged In"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_msg = f"""
🎓 *Welcome to Utkarsh Course Extractor Bot!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
{status}
━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 *Commands:*
• /login - Login to account
• /extract - Extract course
• /logout - Logout
• /help - Help

━━━━━━━━━━━━━━━━━━━━━━━━━━
👨‍💻 *Developer:* @MrHacker
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(welcome_msg, parse_mode='Markdown', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 *HOW TO USE THIS BOT*

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 *LOGIN FORMAT:*
━━━━━━━━━━━━━━━━━━━━━━━━━━

Send: `Number*Password`

📝 *Example:*
`9876543210*MyPassword123`

━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 *EXTRACT FORMAT:*
━━━━━━━━━━━━━━━━━━━━━━━━━━

Just send the Batch ID

📝 *Example:*
`12345`

━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 *STEPS:*
━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Use /login command
2️⃣ Send: `Number*Password`
3️⃣ Use /extract command
4️⃣ Send: `BatchID`
5️⃣ Wait for extraction!

━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "login":
        await query.message.reply_text("""
🔐 *LOGIN TO UTKARSH*

━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 *Send your credentials in format:*

`Number*Password`

━━━━━━━━━━━━━━━━━━━━━━━━━━
✏️ *Example:*
`9876543210*MyPassword123`

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Use /cancel to cancel
""", parse_mode='Markdown')
        return WAITING_LOGIN
    
    elif query.data == "extract":
        if user_id not in user_sessions or not user_sessions[user_id].get('logged_in'):
            await query.message.reply_text("❌ Please login first using /login")
            return ConversationHandler.END
        
        await query.message.reply_text("""
📚 *EXTRACT COURSE*

━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 *Send the Batch ID:*

✏️ *Example:* `12345`

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Use /cancel to cancel
""", parse_mode='Markdown')
        return WAITING_BATCH
    
    elif query.data == "logout":
        if user_id in user_sessions:
            del user_sessions[user_id]
            await query.message.reply_text("✅ *Logged out successfully!*", parse_mode='Markdown')
        else:
            await query.message.reply_text("❌ You are not logged in.")
        return ConversationHandler.END
    
    elif query.data == "help":
        help_text = """
📖 *LOGIN FORMAT:*
`Number*Password`

📖 *EXAMPLE:*
`9876543210*MyPassword123`
"""
        await query.message.reply_text(help_text, parse_mode='Markdown')
        return ConversationHandler.END

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔐 *LOGIN TO UTKARSH*

━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 *Send your credentials in format:*

`Number*Password`

━━━━━━━━━━━━━━━━━━━━━━━━━━
✏️ *Example:*
`9876543210*MyPassword123`

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Use /cancel to cancel
""", parse_mode='Markdown')
    return WAITING_LOGIN

async def process_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Check format
    if '*' not in text:
        await update.message.reply_text("""
❌ *Invalid Format!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 *Correct Format:*
`Number*Password`

✏️ *Example:*
`9876543210*MyPassword123`
━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 Try again or /cancel
""", parse_mode='Markdown')
        return WAITING_LOGIN
    
    # Split credentials
    parts = text.split('*', 1)
    if len(parts) != 2:
        await update.message.reply_text("❌ Invalid format! Use: `Number*Password`", parse_mode='Markdown')
        return WAITING_LOGIN
    
    email = parts[0].strip()
    password = parts[1].strip()
    
    if not email or not password:
        await update.message.reply_text("❌ Number and Password cannot be empty!")
        return WAITING_LOGIN
    
    # Delete the message containing password for security
    try:
        await update.message.delete()
    except:
        pass
    
    status_msg = await update.effective_chat.send_message("🔄 *Logging in... Please wait...*", parse_mode='Markdown')
    
    # Perform login
    session_data, error = perform_login(email, password)
    
    if error:
        await status_msg.edit_text(f"""
❌ *Login Failed!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Error: {error}
━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 Try again with /login
""", parse_mode='Markdown')
        return ConversationHandler.END
    
    # Store session
    user_sessions[user_id] = session_data
    
    await status_msg.edit_text(f"""
✅ *Login Successful!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 *User ID:* `{session_data['user_profile_id']}`
📱 *Number:* `{email}`
━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 Now use /extract to extract courses!
""", parse_mode='Markdown')
    
    return ConversationHandler.END

async def extract_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or not user_sessions[user_id].get('logged_in'):
        await update.message.reply_text("""
❌ *Not Logged In!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 Please login first using /login

📝 *Format:* `Number*Password`
━━━━━━━━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown')
        return ConversationHandler.END
    
    await update.message.reply_text("""
📚 *EXTRACT COURSE*

━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 *Send the Batch ID:*

✏️ *Example:* `12345`

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Use /cancel to cancel
""", parse_mode='Markdown')
    return WAITING_BATCH

async def process_extract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    batch_id = update.message.text.strip()
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Session expired! Please /login again.")
        return ConversationHandler.END
    
    session_data = user_sessions[user_id]
    session = session_data['session']
    csrf_token = session_data['csrf_token']
    h = session_data['headers']
    key = session_data['key']
    iv = session_data['iv']
    api_headers = session_data['api_headers']
    
    status_msg = await update.message.reply_text("""
🔄 *Extracting Course Data...*

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ This may take a while...
━━━━━━━━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown')
    
    try:
        tiles_data_url = 'https://online.utkarsh.com/web/Course/tiles_data'
        layer_two_data_url = 'https://online.utkarsh.com/web/Course/get_layer_two_data'
        meta_source_url = '/meta_distributer/on_request_meta_source'
        
        # Get initial course data
        d3 = {
            "course_id": batch_id,
            "revert_api": "1#0#0#1",
            "parent_id": 0,
            "tile_id": "15330",
            "layer": 1,
            "type": "course_combo"
        }
        
        de1 = encrypt_stream(json.dumps(d3))
        d4 = {'tile_input': de1, 'csrf_name': csrf_token}
        u4 = session.post(tiles_data_url, headers=h, data=d4).json()
        r4 = u4.get("response")
        dr3 = decrypt_and_load_json(r4)
        
        if not dr3 or "data" not in dr3:
            await status_msg.edit_text("""
❌ *Extraction Failed!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Invalid Batch ID or No Access
━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 Try again with /extract
""", parse_mode='Markdown')
            return ConversationHandler.END
        
        all_links = []
        course_count = 0
        processed_subjects = 0
        
        for course in dr3.get("data", []):
            fi = course.get("id")
            tn = course.get("title", "Unknown")
            
            await status_msg.edit_text(f"""
🔄 *Extracting...*

━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 *Course:* {tn[:30]}...
📊 *Links Found:* {course_count}
━━━━━━━━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown')
            
            # Get content list
            d5 = {
                "course_id": fi,
                "layer": 1,
                "page": 1,
                "parent_id": fi,
                "revert_api": "1#1#0#1",
                "tile_id": "0",
                "type": "content"
            }
            
            de2 = encrypt_stream(json.dumps(d5))
            d6 = {'tile_input': de2, 'csrf_name': csrf_token}
            u5 = session.post(tiles_data_url, headers=h, data=d6).json()
            r5 = u5.get("response")
            dr4 = decrypt_and_load_json(r5)
            
            if not dr4 or "data" not in dr4:
                continue
            
            for subject in dr4.get("data", {}).get("list", []):
                sfi = subject.get("id")
                sfn = subject.get("title", "Unknown Subject")
                processed_subjects += 1
                
                # Layer 2
                d7 = {
                    "course_id": fi,
                    "parent_id": fi,
                    "layer": 2,
                    "page": 1,
                    "revert_api": "1#0#0#1",
                    "subject_id": sfi,
                    "tile_id": 0,
                    "topic_id": sfi,
                    "type": "content"
                }
                
                b641 = json.dumps(d7)
                de3 = base64.b64encode(b641.encode()).decode()
                d8 = {'layer_two_input_data': de3, 'csrf_name': csrf_token}
                u6 = session.post(layer_two_data_url, headers=h, data=d8).json()
                r6 = u6.get("response")
                dr5 = decrypt_and_load_json(r6)
                
                if not dr5 or "data" not in dr5:
                    continue
                
                for topic in dr5.get("data", {}).get("list", []):
                    ti = topic.get("id")
                    tt = topic.get("title", "Unknown Topic")
                    
                    # Layer 3
                    d9 = {
                        "course_id": fi,
                        "parent_id": fi,
                        "layer": 3,
                        "page": 1,
                        "revert_api": "1#0#0#1",
                        "subject_id": sfi,
                        "tile_id": 0,
                        "topic_id": ti,
                        "type": "content"
                    }
                    
                    b642 = json.dumps(d9)
                    de4 = base64.b64encode(b642.encode()).decode()
                    d10 = {'layer_two_input_data': de4, 'csrf_name': csrf_token}
                    u7 = session.post(layer_two_data_url, headers=h, data=d10).json()
                    r7 = u7.get("response")
                    dr6 = decrypt_and_load_json(r7)
                    
                    if not dr6 or "data" not in dr6:
                        continue
                    
                    for item in dr6.get("data", {}).get("list", []):
                        ji = item.get("id")
                        jt = item.get("title", "Unknown")
                        jti = item.get("payload", {}).get("tile_id")
                        
                        if not jti:
                            continue
                        
                        j4 = {
                            "course_id": fi,
                            "device_id": "server_does_not_validate_it",
                            "device_name": "server_does_not_validate_it",
                            "download_click": "0",
                            "name": f"{ji}_0_0",
                            "tile_id": jti,
                            "type": "video"
                        }
                        
                        j5 = post_request(meta_source_url, j4, key=key, iv=iv, headers=api_headers)
                        cj = j5.get("data", {})
                        
                        if cj:
                            qo = cj.get("bitrate_urls", [])
                            if qo and isinstance(qo, list):
                                vu1 = qo[3].get("url", "") if len(qo) > 3 else ""
                                vu2 = qo[2].get("url", "") if len(qo) > 2 else ""
                                vu3 = qo[1].get("url", "") if len(qo) > 1 else ""
                                vu = qo[0].get("url", "") if len(qo) > 0 else ""
                                selected_vu = vu1 or vu2 or vu3 or vu
                                
                                if selected_vu:
                                    pu = selected_vu.split("?Expires=")[0]
                                    all_links.append(f"{jt}:{pu}")
                                    course_count += 1
                            else:
                                vu = cj.get("link", "")
                                if vu:
                                    if ".m3u8" in vu or ".pdf" in vu:
                                        pu = vu.split("?Expires=")[0]
                                    else:
                                        pu = f"https://www.youtube.com/embed/{vu}"
                                    all_links.append(f"{jt}:{pu}")
                                    course_count += 1
                    
                    # Update progress
                    if course_count % 10 == 0:
                        await status_msg.edit_text(f"""
🔄 *Extracting...*

━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 *Subject:* {sfn[:25]}...
📊 *Links Found:* {course_count}
━━━━━━━━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown')
        
        if all_links:
            # Create and send file
            file_content = "\n".join(all_links)
            file_name = f"Batch_{batch_id}.txt"
            
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            await status_msg.delete()
            
            with open(file_name, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=file_name,
                    caption=f"""
✅ *Extraction Complete!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 *Batch ID:* `{batch_id}`
📊 *Total Links:* {course_count}
📂 *Subjects:* {processed_subjects}
━━━━━━━━━━━━━━━━━━━━━━━━━━

👨‍💻 @MrHacker
""",
                    parse_mode='Markdown'
                )
            
            os.remove(file_name)
        else:
            await status_msg.edit_text("""
❌ *No Content Found!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ No videos/content in this batch
━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 Try another batch with /extract
""", parse_mode='Markdown')
    
    except Exception as e:
        await status_msg.edit_text(f"""
❌ *Error Occurred!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ {str(e)[:100]}
━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 Try again with /extract
""", parse_mode='Markdown')
    
    return ConversationHandler.END

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("""
✅ *Logged Out Successfully!*

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 Use /login to login again
━━━━━━━━━━━━━━━━━━━━━━━━━━
""", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ You are not logged in.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ *Operation Cancelled!*", parse_mode='Markdown')
    return ConversationHandler.END

# ======================= MAIN =======================
def main():
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask server started")
    
    # Create bot application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Login conversation handler
    login_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("login", login_start),
            CallbackQueryHandler(button_callback, pattern="^login$")
        ],
        states={
            WAITING_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_login)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Extract conversation handler
    extract_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("extract", extract_start),
            CallbackQueryHandler(button_callback, pattern="^extract$")
        ],
        states={
            WAITING_BATCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_extract)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(login_conv_handler)
    application.add_handler(extract_conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Run the bot
    print("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
