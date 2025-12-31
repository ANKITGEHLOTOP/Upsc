import os
import asyncio
import aiohttp
import io
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# ---------------- CONFIG ----------------
# ⚠️ REPLACE THIS WITH YOUR NEW TOKEN FROM BOTFATHER
BOT_TOKEN = "8410273601:AAGyjlU3YpRWnPrwVMNiiUDDFzkN1fceXEo"

BASE_HEADERS = {
    "sec-ch-ua-platform": "\"Windows\"",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "content-type": "application/json",
    "origin": "https://www.selectionway.com",
    "referer": "https://www.selectionway.com/"
}

COURSES_API = "https://backend.multistreaming.site/api/courses/"
CLASSES_API = "https://backend.multistreaming.site/api/courses/{course_id}/classes?populate=full"
PDFS_API = "https://backend.multistreaming.site/api/courses/{course_id}/study-materials"

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------- API HELPERS ----------------
def clean_url(url):
    return url.replace(" ", "%") if url else ""

async def fetch_courses(session: aiohttp.ClientSession):
    try:
        async with session.get(COURSES_API) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("state") == 200:
                    return data.get("data", [])
    except Exception as e:
        logging.error(f"Error fetching courses: {e}")
    return []

async def fetch_classes(session: aiohttp.ClientSession, course_id: str):
    url = CLASSES_API.format(course_id=course_id)
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("state") == 200:
                    return data.get("data", {})
    except Exception as e:
        logging.error(f"Error fetching classes: {e}")
    return {}

async def fetch_pdfs(session: aiohttp.ClientSession, course_id: str):
    url = PDFS_API.format(course_id=course_id)
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("state") == 200:
                    return data.get("data", [])
    except Exception as e:
        logging.error(f"Error fetching PDFs: {e}")
    return []

def extract_video_links(classes_data):
    videos = []
    if not classes_data or "classes" not in classes_data:
        return videos
    
    for topic in classes_data["classes"]:
        for cls in topic.get("classes", []):
            title = cls.get("title", "Unknown")
            best_url = cls.get("class_link")
            quality = "link"
            
            # Prioritize qualities
            for q in ["720p", "480p", "360p"]:
                for rec in cls.get("mp4Recordings", []):
                    if rec.get("quality") == q:
                        best_url = rec.get("url")
                        quality = q
                        break
                if best_url and quality == q:
                    break
            
            if best_url:
                videos.append(f"{title} ({quality}) -> {clean_url(best_url)}")
    return videos

def extract_pdf_links(pdfs_data):
    pdfs = []
    for pdf in pdfs_data:
        title = pdf.get("title", "Unknown PDF")
        url = pdf.get("materialLink") or pdf.get("url")
        if url:
            pdfs.append(f"{title} -> {clean_url(url)}")
    return pdfs

# ---------------- BOT HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message and lists available courses."""
    status_msg = await update.message.reply_text("📡 Fetching courses list...")
    
    headers = BASE_HEADERS.copy()
    headers["host"] = "backend.multistreaming.site"
    
    async with aiohttp.ClientSession(headers=headers) as session:
        courses = await fetch_courses(session)
        
    if not courses:
        await status_msg.edit_text("❌ No courses found or API error.")
        return

    # Store courses in context for easier access later (optional, but good for caching)
    context.user_data['courses'] = {str(c['id']): c for c in courses}
    
    message_text = "📚 **Available Batches:**\n\n"
    keyboard = []
    
    # Create buttons for courses (Split into chunks if too many, but here we list basic)
    # Telegram has a limit on message size. If > 50 courses, we might need a different approach.
    # For now, let's list them as text and ask user to copy ID.
    
    for c in courses:
        c_id = c.get('id')
        c_title = c.get('title')
        message_text += f"🆔 `{c_id}` : {c_title}\n"

    message_text += "\n👇 **Copy an ID from above and reply with it to extract.**"
    
    # Split message if too long (Telegram limit 4096 chars)
    if len(message_text) > 4000:
        # Simple chunking
        chunks = [message_text[i:i+4000] for i in range(0, len(message_text), 4000)]
        for chunk in chunks:
            await update.message.reply_markdown(chunk)
    else:
        await status_msg.edit_text(message_text, parse_mode='Markdown')

async def handle_course_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text input (Course ID) and generates the file."""
    course_id = update.message.text.strip()
    
    # Basic validation: check if numeric
    if not course_id.isdigit():
        await update.message.reply_text("❌ Please send a valid numeric Course ID.")
        return

    status_msg = await update.message.reply_text(f"⏳ Processing Course ID: {course_id}...")

    headers = BASE_HEADERS.copy()
    headers["host"] = "backend.multistreaming.site"

    async with aiohttp.ClientSession(headers=headers) as session:
        # 1. Get Course Info (to get title)
        # We try to get title from cache or default to ID
        course_title = f"Course_{course_id}"
        courses_map = context.user_data.get('courses', {})
        batch_pdf = None
        
        if course_id in courses_map:
            course_obj = courses_map[course_id]
            course_title = course_obj.get('title', course_title)
            batch_pdf = course_obj.get('batchInfoPdfUrl')
        
        # 2. Fetch Data
        classes_data, pdfs_data = await asyncio.gather(
            fetch_classes(session, course_id),
            fetch_pdfs(session, course_id)
        )

        # 3. Process Data
        video_links = extract_video_links(classes_data)
        pdf_links = extract_pdf_links(pdfs_data)

        if batch_pdf:
            pdf_links.insert(0, f"Batch PDF -> {clean_url(batch_pdf)}")

        if not video_links and not pdf_links:
            await status_msg.edit_text("❌ No content found for this ID.")
            return

        # 4. Create In-Memory File
        safe_filename = "".join(c for c in course_title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        file_buffer = io.StringIO()
        
        file_buffer.write(f"Course: {course_title}\n")
        file_buffer.write(f"ID: {course_id}\n")
        file_buffer.write("-" * 50 + "\n\n")
        
        if video_links:
            file_buffer.write("🎥 VIDEOS:\n")
            file_buffer.write("=" * 50 + "\n")
            for link in video_links:
                file_buffer.write(link + "\n\n")
        
        if pdf_links:
            file_buffer.write("📄 PDFs & MATERIALS:\n")
            file_buffer.write("=" * 50 + "\n")
            for link in pdf_links:
                file_buffer.write(link + "\n\n")

        # Reset pointer to start of file
        file_buffer.seek(0)
        
        # Convert String buffer to Bytes buffer for Telegram
        bytes_io = io.BytesIO(file_buffer.getvalue().encode('utf-8'))
        bytes_io.name = f"{safe_filename}.txt"

        # 5. Send File
        await update.message.reply_document(
            document=bytes_io,
            caption=f"✅ **Extraction Complete**\nfound {len(video_links)} videos and {len(pdf_links)} PDFs.",
            parse_mode='Markdown'
        )
        await status_msg.delete()

# ---------------- MAIN ----------------
if __name__ == '__main__':
    # Initialize Bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_course_id))
    
    print("🤖 Bot is running...")
    application.run_polling()

