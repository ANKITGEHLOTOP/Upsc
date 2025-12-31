import requests
import logging
import os
import math
import asyncio
import json
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo")
PORT = int(os.environ.get("PORT", "8000"))
ITEMS_PER_PAGE = 10

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- WEB SERVER FOR KOYEB ---
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
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "content-type": "application/json"
        }
        self.user_sessions = {}

    def clean_url(self, url):
        if not url: return ""
        return url.replace(" ", "%")

    async def get_all_batches(self):
        """
        FAIL-SAFE STRATEGY:
        1. Attempt Vercel API.
        2. If Vercel fails (network error OR unknown structure), silently fallback to Backend API.
        """
        # --- SOURCE 1: VERCEL ---
        try:
            url = "https://selection-way.vercel.app/batches"
            resp = requests.get(url, headers=self.base_headers, timeout=5)
            data = resp.json()

            # Handle various potential Vercel structures
            if isinstance(data, list):
                return True, data
            
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    return True, data["data"]
                if "courses" in data and isinstance(data["courses"], list):
                    return True, data["courses"]
            
            # If we reach here, structure is unknown. Log it, but don't return False yet.
            logger.warning(f"⚠️ Vercel structure mismatch. Falling back to backend.")
            
        except Exception as e:
            logger.warning(f"⚠️ Vercel API failed: {e}. Falling back to backend.")

        # --- SOURCE 2: BACKEND FALLBACK (Reliable) ---
        try:
            url = "https://backend.multistreaming.site/api/courses/"
            headers = {
                "host": "backend.multistreaming.site",
                **self.base_headers
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if str(data.get("state")) == "200":
                return True, data["data"]
                
        except Exception as e:
            return False, f"All sources failed. Last Error: {e}"

        return False, "Failed to fetch batches from both Vercel and Backend."

    async def get_my_batches(self, user_id):
        if user_id not in self.user_sessions:
            return False, "Please login first"
        
        user_data = self.user_sessions[user_id]
        url = "https://backend.multistreaming.site/api/courses/my-courses"
        headers = {
            "host": "backend.multistreaming.site",
            "origin": "https://www.selectionway.com",
            "referer": "https://www.selectionway.com/",
            **self.base_headers
        }
        payload = {"userId": str(user_data['user_id'])}
        
        try:
            resp = user_data['session'].post(url, headers=headers, json=payload)
            data = resp.json()
            if str(data.get("state")) == "200":
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
        headers = {
            "host": "selectionway.hranker.com",
            "origin": "https://www.selectionway.com",
            "referer": "https://www.selectionway.com/",
            **self.base_headers
        }
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
            return False, "❌ Login failed"
        except Exception as e:
            return False, f"❌ Login error: {str(e)}"

    async def extract_batch_data(self, batch_id, type="full"):
        """
        Fetches from Vercel: /batch/{id}/full or /batch/{id}/today
        """
        url = f"https://selection-way.vercel.app/batch/{batch_id}/{type}"
        try:
            response = requests.get(url, headers=self.base_headers)
            try:
                json_data = response.json()
            except ValueError:
                return False, f"Server returned HTML/Invalid JSON ({response.status_code})"
            return True, json_data
        except Exception as e:
            return False, f"Connection Error: {str(e)}"

    def process_content(self, data):
        """
        Recursive link extractor to handle any JSON structure
        """
        video_links = []
        pdf_links = []
        
        def find_links_recursive(item, context=""):
            if isinstance(item, dict):
                title = item.get("title", "Untitled")
                
                # Check for direct links
                url = item.get("url") or item.get("class_link") or item.get("materialLink")
                
                if url:
                    clean_link = self.clean_url(url)
                    # Categorize by extension
                    if ".pdf" in str(url).lower():
                        pdf_links.append(f"{context} {title} -> {clean_link}")
                    elif ".mp4" in str(url).lower() or "youtube" in str(url).lower() or "vimeo" in str(url).lower():
                        video_links.append(f"{context} {title} -> {clean_link}")
                    else:
                        # Fallback: assume video if class_link, pdf if materialLink
                        if item.get("materialLink"):
                            pdf_links.append(f"{context} {title} -> {clean_link}")
                        else:
                            video_links.append(f"{context} {title} -> {clean_link}")

                # Check for mp4Recordings list
                if "mp4Recordings" in item and isinstance(item["mp4Recordings"], list):
                    best_url = ""
                    quality_tag = ""
                    for q in ["720p", "480p", "360p"]:
                        for rec in item["mp4Recordings"]:
                            if rec.get("quality") == q:
                                best_url = rec.get("url")
                                quality_tag = q
                                break
                        if best_url: break
                    
                    if best_url:
                        video_links.append(f"{title} ({quality_tag}) -> {self.clean_url(best_url)}")

                # Recurse
                for key, value in item.items():
                    if isinstance(value, (dict, list)):
                        find_links_recursive(value, context)
            
            elif isinstance(item, list):
                for sub_item in item:
                    find_links_recursive(sub_item, context)

        # Handle wrapper
        work_data = data.get("data", data) if isinstance(data, dict) else data
        find_links_recursive(work_data)
        
        # Remove duplicates
        return list(set(video_links)), list(set(pdf_links))

bot_logic = SelectionWayBot()

# --- PAGINATION ---
def get_batches_keyboard(current_page, total_pages, list_type):
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("<< Prev", callback_data=f"page|{list_type}|{current_page-1}"))
    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Next >>", callback_data=f"page|{list_type}|{current_page+1}"))
    return InlineKeyboardMarkup([buttons])

def generate_page_text(batches, page, list_type):
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_batch = batches[start_idx:end_idx]
    
    title = "📚 *Public Batches*" if list_type == "all" else "🔐 *Your Purchased Batches*"
    msg = f"{title}\n\n"
    
    for i, course in enumerate(current_batch, 1):
        actual_index = start_idx + i
        # Handle inconsistent keys (title vs courseName, id vs _id)
        c_title = course.get('title') or course.get('courseName') or "Unknown Course"
        c_id = course.get('id') or course.get('_id') or "N/A"
        msg += f"*{actual_index}. {c_title}*\n   🆔 `{c_id}`\n\n"
    
    msg += "👉 Reply with *Batch ID* (e.g., `68ce...`) for Full Extraction.\n"
    msg += "👉 Type `/today <BatchID>` for Today's Updates."
    return msg

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔐 Login & My Batches", callback_data="login_menu")],
        [InlineKeyboardButton("📚 Public Batches", callback_data="public_menu")]
    ]
    await update.message.reply_text(
        "🤖 *SelectionWay Downloader*\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "login_menu":
        context.user_data['awaiting_login'] = True
        await query.edit_message_text("🔐 *Login Required*\nSend: `email:password`", parse_mode='Markdown')
        
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

    elif data.startswith("page|"):
        _, list_type, page_num = data.split("|")
        page = int(page_num)
        batches = context.user_data.get('public_batches' if list_type == "all" else 'my_batches', [])
        if not batches:
            await query.answer("Session expired. /start again.", show_alert=True)
            return
        total_pages = math.ceil(len(batches) / ITEMS_PER_PAGE)
        text = generate_page_text(batches, page, list_type)
        kb = get_batches_keyboard(page, total_pages, list_type)
        try: await query.edit_message_text(text, reply_markup=kb, parse_mode='Markdown')
        except: pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Login Flow
    if context.user_data.get('awaiting_login'):
        if ":" in text:
            email, password = text.split(":", 1)
            msg = await update.message.reply_text("🔄 Verifying...")
            success, resp = await bot_logic.login_user(email.strip(), password.strip(), user_id)
            if success:
                context.user_data['awaiting_login'] = False
                await msg.edit_text("✅ Success! Fetching My Batches...")
                ok, batches = await bot_logic.get_my_batches(user_id)
                if ok:
                    context.user_data['my_batches'] = batches
                    context.user_data['mode'] = 'private'
                    total_pages = math.ceil(len(batches) / ITEMS_PER_PAGE)
                    txt = generate_page_text(batches, 1, "my")
                    kb = get_batches_keyboard(1, total_pages, "my")
                    await update.message.reply_text(txt, reply_markup=kb, parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"❌ Failed to fetch batches: {batches}")
            else:
                await msg.edit_text(f"{resp}")
        else:
            await update.message.reply_text("❌ Use `email:password`")
            
    # Extraction Flow
    else:
        if text.startswith("/today"):
            parts = text.split()
            if len(parts) > 1:
                batch_id = parts[1]
                await process_extraction(update, batch_id, "Today's Updates", extraction_type="today")
            else:
                await update.message.reply_text("❌ Usage: `/today <BatchID>`")
            return

        mode = context.user_data.get('mode')
        
        # Try to find name in cache
        batch_name = "Unknown Batch"
        
        if mode == 'private' and text.isdigit():
            idx = int(text)
            batches = context.user_data.get('my_batches', [])
            if 1 <= idx <= len(batches):
                b = batches[idx-1]
                await process_extraction(update, b['id'], b.get('title', 'Batch'), extraction_type="full")
            else:
                await update.message.reply_text("❌ Invalid index.")
        
        else:
            # Assume it's a Batch ID
            for b in context.user_data.get('public_batches', []):
                # Check both 'id' and '_id'
                bid = str(b.get('id') or b.get('_id') or "")
                if bid == str(text):
                    batch_name = b.get('title', 'Batch')
                    break
            
            if len(text) > 4: # Simple length check for ID
                await process_extraction(update, text, batch_name, extraction_type="full")
            else:
                await update.message.reply_text("⚠️ Send a valid **Batch ID** (e.g. 68ce...) to extract full content.\nOr use `/today <BatchID>`.")

async def process_extraction(update, batch_id, batch_name, extraction_type="full"):
    type_str = "Full Content" if extraction_type == "full" else "Today's Updates"
    status_msg = await update.message.reply_text(f"🔄 Fetching *{type_str}* for ID: `{batch_id}`...", parse_mode='Markdown')
    
    success, data = await bot_logic.extract_batch_data(batch_id, type=extraction_type)
    
    if success:
        v_links, p_links = bot_logic.process_content(data)
        
        safe_name = "".join(c for c in batch_name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_name}_{extraction_type}.txt"
        
        content = f"🎯 {batch_name}\n"
        content += f"🆔 Batch ID: {batch_id}\n"
        content += f"📅 Type: {type_str}\n"
        content += "="*40 + "\n\n"
        
        if p_links: 
            content += "📄 PDFS:\n" + "-"*30 + "\n" + "\n".join(p_links) + "\n\n"
        
        if v_links: 
            content += "🎥 VIDEOS:\n" + "-"*30 + "\n" + "\n".join(v_links)
            
        if not p_links and not v_links:
            content += "❌ No content found.\n(Empty response from Vercel API)"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
            
        caption = (f"✅ *Extraction Complete*\n"
                   f"📁 {batch_name}\n"
                   f"📹 Videos: {len(v_links)} | 📄 PDFs: {len(p_links)}")
                   
        with open(filename, "rb") as f:
            await update.message.reply_document(document=f, caption=caption, parse_mode='Markdown')
            
        await status_msg.delete()
        os.remove(filename)
    else:
        await status_msg.edit_text(f"❌ Failed: {data}")

if __name__ == "__main__":
    if not BOT_TOKEN: print("⚠️ Warning: BOT_TOKEN missing.")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(run_web_server())

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)

