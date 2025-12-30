import requests
import logging
import os
import math
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo")
PORT = int(os.environ.get("PORT", "8000"))  # Required for Koyeb
ITEMS_PER_PAGE = 10  # Number of batches per message

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- WEB SERVER FOR KOYEB (KEEP ALIVE) ---
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

# --- API LOGIC ---
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
        return url.replace(" ", "%")

    async def get_all_batches(self):
        """Get all active batches without login"""
        url = "https://backend.multistreaming.site/api/courses/active?userId=1448640"
        headers = {"host": "backend.multistreaming.site", **self.base_headers}
        try:
            # Using sync requests in async wrapper could block, but fine for low traffic
            resp = requests.get(url, headers=headers)
            data = resp.json()
            if data.get("state") == 200:
                return True, data["data"]
            return False, "Failed to get batches"
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def get_my_batches(self, user_id):
        """Get user's own batches"""
        if user_id not in self.user_sessions:
            return False, "Please login first"
        
        user_data = self.user_sessions[user_id]
        url = "https://backend.multistreaming.site/api/courses/my-courses"
        headers = {"host": "backend.multistreaming.site", **self.base_headers}
        payload = {"userId": str(user_data['user_id'])}
        
        try:
            resp = user_data['session'].post(url, headers=headers, json=payload)
            data = resp.json()
            if str(data.get("state")) == "200":
                # Flatten the structure for "My Batches"
                flat_list = []
                for group in data.get("data", []):
                    flat_list.extend(group.get("liveCourses", []))
                    flat_list.extend(group.get("recordedCourses", []))
                return True, flat_list
            return False, "Failed to get your courses"
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def login_user(self, email, password, user_id):
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
                return True, "✅ Login successful!"
            return False, "❌ Login failed: Invalid credentials"
        except Exception as e:
            return False, f"❌ Login error: {str(e)}"

    async def extract_course_data(self, user_id, course_id, course_name, is_public=True):
        """Unified extraction logic"""
        try:
            session = requests.Session()
            # If private (logged in), use the logged-in session
            if not is_public:
                if user_id in self.user_sessions:
                    session = self.user_sessions[user_id]['session']
                else:
                    return False, "Login expired or required."

            # 1. Get Course Info (PDF)
            # Logic differs slightly for public vs private usually, but trying generic approach first
            pdf_url = ""
            
            # 2. Get Classes
            classes_url = f"https://backend.multistreaming.site/api/courses/{course_id}/classes?populate=full"
            headers = {"host": "backend.multistreaming.site", **self.base_headers}
            
            resp = session.get(classes_url, headers=headers)
            classes_data = resp.json()
            
            if classes_data.get("state") == 200:
                # Try to find PDF from active batch list if public
                if is_public:
                    _, all_batches = await self.get_all_batches()
                    for b in all_batches:
                        if b.get('id') == course_id:
                            pdf_url = b.get('batchInfoPdfUrl', "")
                            break
                
                return True, {
                    "classes_data": classes_data["data"],
                    "pdf_url": self.clean_url(pdf_url),
                    "course_name": course_name
                }
            return False, "Failed to get class data"
        except Exception as e:
            logger.error(e)
            return False, f"Error: {str(e)}"

    def process_content(self, data):
        """Extract links"""
        video_links = []
        pdf_links = []
        
        if data.get("pdf_url"):
            pdf_links.append(f"Batch Info PDF: {data['pdf_url']}")
            
        if data.get("classes_data") and "classes" in data["classes_data"]:
            for topic in data["classes_data"]["classes"]:
                for cls in topic.get("classes", []):
                    title = cls.get("title", "Unknown")
                    # Find best quality video
                    best_url = cls.get("class_link", "")
                    quality_tag = "Link"
                    
                    recordings = cls.get("mp4Recordings", [])
                    for q in ["720p", "480p", "360p"]:
                        for rec in recordings:
                            if rec.get("quality") == q:
                                best_url = rec.get("url")
                                quality_tag = q
                                break
                        if best_url and quality_tag == q: break
                    
                    if best_url:
                        video_links.append(f"{title} ({quality_tag}): {best_url}")
                        
        return video_links, pdf_links

bot_logic = SelectionWayBot()

# --- PAGINATION HELPERS ---
def get_batches_keyboard(current_page, total_pages, list_type):
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("<< Prev", callback_data=f"page|{list_type}|{current_page-1}"))
    
    # Add page counter in middle (non-clickable)
    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Next >>", callback_data=f"page|{list_type}|{current_page+1}"))
    
    return InlineKeyboardMarkup([buttons])

def generate_page_text(batches, page, list_type):
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_batch = batches[start_idx:end_idx]
    
    title = "📚 *All Available Batches*" if list_type == "all" else "🔐 *Your Purchased Batches*"
    msg = f"{title}\n\n"
    
    for i, course in enumerate(current_batch, 1):
        actual_index = start_idx + i
        price = course.get('discountPrice', course.get('price', 'N/A'))
        msg += f"*{actual_index}. {course.get('title')}*\n"
        msg += f"   🆔 `{course.get('id')}` | 💰 ₹{price}\n\n"
    
    if list_type == "my":
        msg += "👉 Reply with *Index Number* (e.g., `1`, `15`) to extract."
    else:
        msg += "👉 Reply with *Batch ID* to extract."
        
    return msg

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔐 Login & My Batches", callback_data="login_menu")],
        [InlineKeyboardButton("📚 Public Batches", callback_data="public_menu")]
    ]
    await update.message.reply_text(
        "🤖 *SelectionWay Downloader*\n\nSelect an option below:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "login_menu":
        context.user_data['awaiting_login'] = True
        await query.edit_message_text(
            "🔐 *Login Required*\nSend details as: `email:password`\nExample: `user@gmail.com:pass123`",
            parse_mode='Markdown'
        )
        
    elif data == "public_menu":
        await query.edit_message_text("🔄 Fetching batches...")
        success, batches = await bot_logic.get_all_batches()
        if success:
            context.user_data['public_batches'] = batches
            context.user_data['mode'] = 'public'
            
            total_pages = math.ceil(len(batches) / ITEMS_PER_PAGE)
            text = generate_page_text(batches, 1, "all")
            kb = get_batches_keyboard(1, total_pages, "all")
            
            await query.edit_message_text(text, reply_markup=kb, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ Error: {batches}")

    # PAGINATION HANDLER
    elif data.startswith("page|"):
        _, list_type, page_num = data.split("|")
        page = int(page_num)
        
        batches = []
        if list_type == "all":
            batches = context.user_data.get('public_batches', [])
        else:
            batches = context.user_data.get('my_batches', [])
            
        if not batches:
            await query.answer("Session expired. Please reload.", show_alert=True)
            return

        total_pages = math.ceil(len(batches) / ITEMS_PER_PAGE)
        text = generate_page_text(batches, page, list_type)
        kb = get_batches_keyboard(page, total_pages, list_type)
        
        try:
            await query.edit_message_text(text, reply_markup=kb, parse_mode='Markdown')
        except Exception:
            pass # Ignore if message is not modified

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # 1. LOGIN LOGIC
    if context.user_data.get('awaiting_login'):
        if ":" in text:
            email, password = text.split(":", 1)
            msg = await update.message.reply_text("🔄 Verifying credentials...")
            success, resp = await bot_logic.login_user(email.strip(), password.strip(), user_id)
            
            if success:
                context.user_data['awaiting_login'] = False
                await msg.edit_text("✅ Login Success! Fetching your batches...")
                
                # Fetch private batches immediately
                ok, batches = await bot_logic.get_my_batches(user_id)
                if ok:
                    context.user_data['my_batches'] = batches
                    context.user_data['mode'] = 'private'
                    
                    total_pages = math.ceil(len(batches) / ITEMS_PER_PAGE)
                    txt = generate_page_text(batches, 1, "my")
                    kb = get_batches_keyboard(1, total_pages, "my")
                    
                    await update.message.reply_text(txt, reply_markup=kb, parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"❌ Login ok, but failed to fetch batches: {batches}")
            else:
                await msg.edit_text(f"{resp}")
        else:
            await update.message.reply_text("❌ Invalid format. Use `email:password`")
            
    # 2. EXTRACTION LOGIC
    else:
        mode = context.user_data.get('mode')
        
        # Handle Private Batch Index Selection
        if mode == 'private' and text.isdigit():
            idx = int(text)
            batches = context.user_data.get('my_batches', [])
            if 1 <= idx <= len(batches):
                course = batches[idx-1]
                await process_extraction(update, user_id, course['id'], course['title'], is_public=False)
            else:
                await update.message.reply_text("❌ Invalid number.")

        # Handle Public Batch ID
        elif mode == 'public':
            # Basic validation for ID length usually around 24 chars for Mongo IDs
            if len(text) > 10: 
                # Find name if possible
                name = "Unknown Course"
                for b in context.user_data.get('public_batches', []):
                    if b['id'] == text:
                        name = b['title']
                        break
                await process_extraction(update, user_id, text, name, is_public=True)
            else:
                await update.message.reply_text("❌ For public batches, please reply with the exact **Batch ID** (long code).", parse_mode='Markdown')
        else:
            # Fallback
            await update.message.reply_text("⚠️ Please select an option from /start first.")

async def process_extraction(update, user_id, course_id, course_name, is_public):
    status_msg = await update.message.reply_text(f"🔄 Extracting *{course_name}*...", parse_mode='Markdown')
    
    success, data = await bot_logic.extract_course_data(user_id, course_id, course_name, is_public)
    
    if success:
        v_links, p_links = bot_logic.process_content(data)
        
        # Create txt file
        safe_name = "".join(c for c in course_name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_name}.txt"
        
        content = f"🎯 {course_name}\n\n"
        if p_links:
            content += "📄 PDFS:\n" + "\n".join(p_links) + "\n\n"
        if v_links:
            content += "🎥 VIDEOS:\n" + "\n".join(v_links)
            
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
            
        caption = (f"✅ *Extraction Complete*\n"
                   f"📁 {course_name}\n"
                   f"📹 Videos: {len(v_links)} | 📄 PDFs: {len(p_links)}")
                   
        with open(filename, "rb") as f:
            await update.message.reply_document(document=f, caption=caption, parse_mode='Markdown')
            
        await status_msg.delete()
        os.remove(filename) # Clean up for Koyeb
    else:
        await status_msg.edit_text(f"❌ Failed: {data}")

# --- MAIN ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN env variable not set.")
        exit(1)

    # 1. Start Web Server for Koyeb
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(run_web_server())

    # 2. Start Bot
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot is running...")
    
    # Using run_polling within the existing loop context
    app.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)
                

