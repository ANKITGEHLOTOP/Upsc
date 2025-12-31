import requests
import logging
import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo")
PORT = int(os.environ.get("PORT", "8000"))

# --- THE ONLY API ---
CLASSES_API = "https://backend.multistreaming.site/api/courses/{course_id}/classes?populate=full"

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- WEB SERVER (Keep Alive) ---
async def health_check(request):
    return web.Response(text="Bot is alive!", status=200)

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"🕸️ Web server started on port {PORT}")

# --- BOT LOGIC ---
class SelectionWayBot:
    def __init__(self):
        self.base_headers = {
            "sec-ch-ua-platform": "\"Windows\"",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "content-type": "application/json",
            "origin": "https://www.selectionway.com",
            "referer": "https://www.selectionway.com/"
        }
        self.user_sessions = {}

    def clean_url(self, url):
        if not url: return ""
        return url.strip().replace(" ", "%20")

    async def login_user(self, email, password, user_id):
        """Kept only for generating tokens for private courses"""
        url = "https://selectionway.hranker.com/admin/api/user-login"
        headers = {"host": "selectionway.hranker.com", **self.base_headers}
        payload = {
            "email": email, "password": password, "mobile": "", 
            "otp": "", "logged_in_via": "web", "customer_id": 561
        }
        
        try:
            session = requests.Session()
            resp = session.post(url, headers=headers, json=payload)
            data = resp.json()
            
            if data.get("state") == 200:
                self.user_sessions[user_id] = {
                    'user_id': data["data"]["user_id"],
                    'token': data["data"]["token_id"],
                    'session': session
                }
                return True, "✅ Login successful! Now send me a Course ID."
            return False, "❌ Login failed."
        except Exception as e:
            return False, f"❌ Login error: {str(e)}"

    async def extract_course_data(self, user_id, course_id):
        try:
            # Determine session (User or Guest)
            session = requests.Session()
            if user_id in self.user_sessions:
                session = self.user_sessions[user_id]['session']

            headers = {"host": "backend.multistreaming.site", **self.base_headers}
            
            # THE ONLY API CALL
            url = CLASSES_API.format(course_id=course_id)
            resp = session.get(url, headers=headers)
            
            # Check for JSON validity
            try:
                data = resp.json()
            except:
                return False, "API did not return JSON. Invalid ID?"

            if data.get("state") == 200:
                return True, data.get("data", {})
            else:
                return False, f"API Error: {data.get('message', 'Unknown error')}"

        except Exception as e:
            logger.error(e)
            return False, f"Error: {str(e)}"

    def process_content(self, data):
        video_links = []
        pdf_links = []
        
        # Go through classes
        if data and "classes" in data:
            for topic in data["classes"]:
                for cls in topic.get("classes", []):
                    title = cls.get("title", "Unknown Class")
                    
                    # 1. Extract VIDEO
                    best_video_url = cls.get("class_link", "")
                    quality_tag = "Link"
                    
                    recordings = cls.get("mp4Recordings", [])
                    for q in ["720p", "480p", "360p"]:
                        for rec in recordings:
                            if rec.get("quality") == q:
                                best_video_url = rec.get("url")
                                quality_tag = q
                                break
                        if best_video_url and quality_tag == q: break
                    
                    if best_video_url:
                        video_links.append(f"{title} ({quality_tag}): {self.clean_url(best_video_url)}")

                    # 2. Extract PDF (Smart Scan)
                    found_pdf = None
                    
                    # Scan all string keys for ".pdf" or "/pdfs/"
                    for key, val in cls.items():
                        if isinstance(val, str) and val.startswith("http"):
                            if val.lower().endswith(".pdf") or "/pdfs/" in val:
                                found_pdf = val
                                break
                    
                    # Check attachments array
                    if not found_pdf and "attachments" in cls:
                        for att in cls["attachments"]:
                            url = att.get("url", "")
                            if url and (url.endswith(".pdf") or "/pdfs/" in url): 
                                found_pdf = url
                                break

                    if found_pdf:
                        pdf_links.append(f"📝 {title} (Notes): {self.clean_url(found_pdf)}")
                        
        return video_links, pdf_links

bot_logic = SelectionWayBot()

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Simple Course Extractor*\n\n"
        "1. Send me a **Course ID** to extract.\n"
        "2. To login (for paid courses), send: `/login email password`",
        parse_mode='Markdown'
    )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Usage: `/login email password`")
        return
    
    email, password = args
    msg = await update.message.reply_text("🔄 Logging in...")
    success, text = await bot_logic.login_user(email, password, user_id)
    await msg.edit_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Assume any text sent is a Course ID
    if len(text) < 5:
        await update.message.reply_text("❌ ID seems too short.")
        return

    status_msg = await update.message.reply_text(f"🔄 Checking ID: `{text}`...", parse_mode='Markdown')
    
    success, data = await bot_logic.extract_course_data(user_id, text)
    
    if success:
        v_links, p_links = bot_logic.process_content(data)
        
        # Use ID as filename since we might not get a clean course name easily
        filename = f"Course_{text}.txt"
        
        content = f"🎯 Course ID: {text}\n\n"
        if p_links: content += "📄 PDFS & MATERIALS:\n" + "\n".join(p_links) + "\n\n"
        if v_links: content += "🎥 VIDEOS:\n" + "\n".join(v_links)
        
        if not v_links and not p_links:
            content += "❌ No content found! (Check if ID is correct or if you need to /login)"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
            
        caption = (f"✅ *Extraction Complete*\n"
                   f"🆔 `{text}`\n"
                   f"📹 Videos: {len(v_links)} | 📄 PDFs: {len(p_links)}")
                   
        with open(filename, "rb") as f:
            await update.message.reply_document(document=f, caption=caption, parse_mode='Markdown')
            
        await status_msg.delete()
        os.remove(filename)
    else:
        await status_msg.edit_text(f"❌ Failed: {data}")

if __name__ == "__main__":
    if not BOT_TOKEN or "YOUR_BOT_TOKEN_HERE" in BOT_TOKEN:
        print("⚠️ Warning: BOT_TOKEN is missing.")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(run_web_server())

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)
    
