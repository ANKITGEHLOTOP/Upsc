import os
import json
import requests
import telebot
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from base64 import b64decode, b64encode
import base64
import urllib3
import io
import threading
import traceback

urllib3.disable_warnings()

# ===== BOT TOKEN =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo")

# ===== AUTO LOGIN CREDENTIALS =====
AUTO_MOBILE = "7891745633"
AUTO_PASSWORD = "Sitar@123"

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

# Global session storage
global_session = None

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
    except Exception as ex:
        print(f"ds() error: {ex}")
    return None

def es(d):
    try:
        return b64encode(AES.new(b'%!$!%_$&!%F)&^!^', AES.MODE_CBC, b'#*y*#2yJ*#$wJv*v').encrypt(pad(d.encode(), 16))).decode()
    except:
        return None

# ===== LOGIN FUNCTION WITH DEBUG =====
def do_login():
    global global_session
    
    print("\n" + "="*50)
    print("🔐 STARTING LOGIN PROCESS...")
    print("="*50)
    
    try:
        # Step 1: Create session
        print("\n[1] Creating session...")
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
        s.mount('https://', adapter)
        print("✓ Session created")
        
        # Step 2: Get CSRF
        print("\n[2] Getting CSRF token...")
        csrf_resp = s.get("https://online.utkarsh.com/", verify=False, timeout=15)
        print(f"   Status Code: {csrf_resp.status_code}")
        print(f"   Cookies: {dict(csrf_resp.cookies)}")
        
        cs = csrf_resp.cookies.get('csrf_name')
        if not cs:
            print("❌ CSRF token not found in cookies!")
            return False, "CSRF Failed - No token in cookies"
        print(f"✓ CSRF Token: {cs[:20]}...")
        
        # Step 3: Prepare headers
        print("\n[3] Preparing headers...")
        h = {
            'Host': 'online.utkarsh.com',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Origin': 'https://online.utkarsh.com',
            'Referer': 'https://online.utkarsh.com/'
        }
        print("✓ Headers prepared")
        
        # Step 4: Login request
        print("\n[4] Sending login request...")
        print(f"   Mobile: {AUTO_MOBILE}")
        print(f"   Password: {'*' * len(AUTO_PASSWORD)}")
        
        login_data = {
            'csrf_name': cs,
            'mobile': AUTO_MOBILE,
            'url': '0',
            'password': AUTO_PASSWORD,
            'submit': 'LogIn',
            'device_token': 'null'
        }
        
        r = s.post("https://online.utkarsh.com/web/Auth/login", 
                   data=login_data, 
                   headers=h, 
                   verify=False, 
                   timeout=15)
        
        print(f"   Response Status: {r.status_code}")
        print(f"   Response Length: {len(r.text)} chars")
        print(f"   Response Preview: {r.text[:200]}...")
        
        # Step 5: Parse response
        print("\n[5] Parsing response...")
        try:
            r_json = r.json()
            print(f"   JSON Keys: {list(r_json.keys())}")
        except Exception as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"   Raw Response: {r.text[:500]}")
            return False, f"JSON Parse Failed: {e}"
        
        # Step 6: Decrypt response
        print("\n[6] Decrypting response...")
        response_data = r_json.get("response")
        if not response_data:
            print(f"❌ No 'response' field in JSON!")
            print(f"   Full JSON: {r_json}")
            return False, "No response field"
        
        print(f"   Encrypted data length: {len(response_data)}")
        
        dr = ds(response_data)
        if not dr:
            print("❌ Decryption failed!")
            print(f"   Encrypted data: {response_data[:100]}...")
            return False, "Decryption Failed"
        
        print(f"✓ Decrypted! Keys: {list(dr.keys())}")
        print(f"   Status: {dr.get('status')}")
        print(f"   Message: {dr.get('message', dr.get('msg', 'N/A'))}")
        
        # Step 7: Check status
        print("\n[7] Checking login status...")
        status_code = dr.get("status")
        if status_code != 200:
            print(f"❌ Login failed with status: {status_code}")
            print(f"   Full response: {json.dumps(dr, indent=2)[:500]}")
            return False, f"Status {status_code}: {dr.get('message', dr.get('msg', 'Unknown error'))}"
        
        # Step 8: Extract tokens
        print("\n[8] Extracting tokens...")
        if "data" not in dr:
            print("❌ No 'data' field in response!")
            print(f"   Response: {dr}")
            return False, "No data in response"
        
        token = dr.get("token")
        jwt = dr["data"].get("jwt")
        
        if not jwt:
            print("❌ No JWT token!")
            print(f"   Data: {dr['data']}")
            return False, "No JWT token"
        
        print(f"✓ Token: {token[:20] if token else 'None'}...")
        print(f"✓ JWT: {jwt[:30]}...")
        
        h["token"] = token
        h["jwt"] = jwt
        
        # Step 9: Get profile
        print("\n[9] Getting user profile...")
        api_headers = BASE_HEADERS.copy()
        api_headers["jwt"] = jwt
        
        p = api_call("/users/get_my_profile", {}, api_headers, None, None, True)
        print(f"   Profile response keys: {list(p.keys())}")
        
        if not p.get("data"):
            print("❌ Profile fetch failed!")
            print(f"   Response: {p}")
            return False, "Profile Failed"
        
        uid = str(p["data"]["id"])
        name = p["data"].get("name", "Unknown")
        print(f"✓ User ID: {uid}")
        print(f"✓ Name: {name}")
        
        # Step 10: Generate keys
        print("\n[10] Generating encryption keys...")
        api_headers["userid"] = uid
        
        key = "".join(key_chars[int(i)] for i in (uid + "1524567456436545")[:16]).encode()
        iv = "".join(iv_chars[int(i)] for i in (uid + "1524567456436545")[:16]).encode()
        print(f"✓ Key generated: {key[:10]}...")
        print(f"✓ IV generated: {iv[:10]}...")
        
        # Step 11: Save session
        print("\n[11] Saving session...")
        global_session = {
            'session': s,
            'web_headers': h,
            'api_headers': api_headers,
            'csrf': cs,
            'key': key,
            'iv': iv,
            'uid': uid,
            'name': name
        }
        
        print("\n" + "="*50)
        print("✅ LOGIN SUCCESSFUL!")
        print(f"   User: {name} (ID: {uid})")
        print("="*50 + "\n")
        
        return True, uid
        
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False, str(e)

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

def full_extraction(batch_id):
    global global_session
    
    if not global_session:
        success, msg = do_login()
        if not success:
            return None, f"Login failed: {msg}"
    
    s = global_session['session']
    h = global_session['web_headers']
    cs = global_session['csrf']
    headers = global_session['api_headers']
    key = global_session['key']
    iv = global_session['iv']
    
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
            global_session = None
            success, msg = do_login()
            if not success:
                return None, "❌ Session expired and re-login failed!"
            return full_extraction(batch_id)
        
        courses = dr3.get("data", [])
        if isinstance(courses, dict):
            courses = [courses]
        
        if not courses:
            return None, "❌ Course not found or no access!"
        
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

*Commands:*
/extract `<batch_id>` - Extract links
/login - Force re-login
/status - Check status
/debug - Show debug info

*Example:*
`/extract 12345`
    """
    bot.reply_to(message, welcome_msg, parse_mode='Markdown')

@bot.message_handler(commands=['login'])
def force_login(message):
    global global_session
    global_session = None
    
    status_msg = bot.reply_to(message, "⏳ Logging in...")
    
    success, msg = do_login()
    
    if success:
        bot.edit_message_text(
            f"✅ *Login Successful!*\n\n"
            f"👤 User ID: `{msg}`\n"
            f"📱 Mobile: {AUTO_MOBILE}",
            message.chat.id, status_msg.message_id,
            parse_mode='Markdown'
        )
    else:
        bot.edit_message_text(
            f"❌ *Login Failed!*\n\n"
            f"Error: `{msg}`\n\n"
            f"Check Koyeb logs for details.",
            message.chat.id, status_msg.message_id,
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['debug'])
def debug_info(message):
    global global_session
    
    info = f"""
🔧 *Debug Info*

*Session:* {'Active' if global_session else 'None'}
*Mobile:* {AUTO_MOBILE}
*Password:* {'*' * len(AUTO_PASSWORD)}

*Session Details:*
"""
    if global_session:
        info += f"""
- UID: `{global_session.get('uid', 'N/A')}`
- Name: {global_session.get('name', 'N/A')}
- CSRF: `{global_session.get('csrf', 'N/A')[:20]}...`
"""
    else:
        info += "\nNo active session. Use /login"
    
    bot.reply_to(message, info, parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def status(message):
    global global_session
    if global_session:
        bot.reply_to(message, 
            f"✅ *Logged In*\n\n"
            f"📱 Mobile: {AUTO_MOBILE}\n"
            f"🆔 User ID: {global_session.get('uid', 'N/A')}\n"
            f"👤 Name: {global_session.get('name', 'N/A')}",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "❌ Not logged in. Use /login")

@bot.message_handler(commands=['extract'])
def extract_cmd(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage: /extract <batch_id>\n\nExample: `/extract 12345`", parse_mode='Markdown')
        return
    
    batch_id = args[1].strip()
    thread = threading.Thread(target=do_extract, args=(message, batch_id))
    thread.start()

def do_extract(message, batch_id):
    status_msg = bot.reply_to(message, 
        f"⏳ *Extracting Batch {batch_id}...*\n\nThis may take several minutes!",
        parse_mode='Markdown'
    )
    
    try:
        results, count = full_extraction(batch_id)
        
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
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, status_msg.message_id)

@bot.message_handler(func=lambda message: message.text and message.text.isdigit())
def handle_batch_id(message):
    batch_id = message.text.strip()
    thread = threading.Thread(target=do_extract, args=(message, batch_id))
    thread.start()

@bot.message_handler(func=lambda message: True)
def handle_other(message):
    bot.reply_to(message, "❓ Send a Batch ID or use /extract <batch_id>")

# ===== MAIN =====
if __name__ == "__main__":
    print("🚀 Starting Utkarsh Extractor Bot...")
    print(f"📱 Credentials: {AUTO_MOBILE}")
    print("-" * 50)
    
    # Try login at startup
    success, msg = do_login()
    if success:
        print(f"\n✅ Ready! Logged in as: {msg}")
    else:
        print(f"\n⚠️ Initial login failed: {msg}")
        print("Will retry on first request...")
    
    print("\n" + "="*50)
    print("🤖 Bot is running! Waiting for messages...")
    print("="*50 + "\n")
    
    bot.remove_webhook()
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
