import os
import asyncio
import aiohttp
import io
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ---------------- CONFIG ----------------
# ⚠️ TOKEN REPLACEMENT (Make sure this is your latest token)
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

# --- UPDATED EXTRACTOR LOGIC ---
def extract_content_from_classes(classes_data):
    """Extracts BOTH Video links AND Class-attached PDFs (Board PDFs)"""
    content_list = []
    
    if not classes_data or "classes" not in classes_data:
        return content_list
    
    for topic in classes_data["classes"]:
        # Optional: Add Topic Header
        topic_name = topic.get("title", "Unknown Topic")
        # content_list.append(f"\n--- {topic_name} ---") 
        
        for cls in topic.get("classes", []):
            title = cls.get("title", "Unknown Class")
            
            # 1. EXTRACT VIDEO
            best_url = cls.get("class_link")
            quality = "link"
            
            # Check different qualities
            for q in ["720p", "480p", "360p"]:
                for rec in cls.get("mp4Recordings", []):
                    if rec.get("quality") == q:
                        best_url = rec.get("url")
                        quality = q
                        break
                if best_url and quality == q:
                    break
            
            if best_url:
                content_list.append(f"🎥 {title} ({quality}) -> {clean_url(best_url)}")

            # 2. EXTRACT ATTACHED PDF (Board PDF / Notes)
            # Checking multiple common keys where the PDF might be hidden
            class_pdf = cls.get("note") or cls.get("attachment") or cls.get("pdf") or cls.get("material")
            
            if class_pdf:
                content_list.append(f"📝 {title} (Board PDF) -> {clean_url(class_pdf)}")
                
    return content_list

def extract_global_pdfs(pdfs_data):
    """Extracts PDFs from the Study Materials section"""
    pdfs = []
    for pdf in pdfs_data:
        title = pdf.get("title", "Unknown PDF")
        url = pdf.get("materialLink") or pdf.get("url")
        if url:
            pdfs.append(f"📚 {title} -> {clean_url(url)}")
    return pdfs

# ---------------- BOT HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("📡 Fetching courses list...")
    
    headers = BASE_HEADERS.copy()
    headers["host"] = "backend.multistreaming.site"
    
    async with aiohttp.ClientSession(headers=headers) as session:
        courses = await fetch_courses(session)
        
    if not courses:
        await status_msg.edit_text("❌ No courses found or API error.")
        return

    context.user_data['courses'] = {str(c['id']): c for c in courses}
    
    message_text = "📚 **Available Batches:**\n\n"
    for c in courses:
        c_id = c.get('id')
        c_title = c.get('title')
        message_text += f"ID: `{c_id}`\nName: {c_title}\n\n"

    message_text += "👇 **Reply with the Batch ID to extract.**"
    
    if len(message_text) > 4000:
        chunks = [message_text[i:i+4000] for i in range(0, len(message_text), 4000)]
        for chunk in chunks:
            await update.message.reply_markdown(chunk)
    else:
        await status_msg.edit_text(message_text, parse_mode='Markdown')

async def handle_course_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    course_id = update.message.text.strip()
    
    if len(course_id) < 5: 
        await update.message.reply_text("❌ ID too short.")
        return

    status_msg = await update.message.reply_text(f"⏳ Processing ID: `{course_id}`...", parse_mode='Markdown')

    headers = BASE_HEADERS.copy()
    headers["host"] = "backend.multistreaming.site"

    async with aiohttp.ClientSession(headers=headers) as session:
        # Get Title
        course_title = f"Batch_{course_id}"
        batch_pdf = None
        courses_map = context.user_data.get('courses', {})
        if course_id in courses_map:
            course_obj = courses_map[course_id]
            course_title = course_obj.get('title', course_title)
            batch_pdf = course_obj.get('batchInfoPdfUrl')
        
        # Fetch Data
        classes_data, pdfs_data = await asyncio.gather(
            fetch_classes(session, course_id),
            fetch_pdfs(session, course_id)
        )

        # Extract
        class_content_links = extract_content_from_classes(classes_data)
        global_pdf_links = extract_global_pdfs(pdfs_data)

        if batch_pdf:
            global_pdf_links.insert(0, f"📕 Batch Brochure/PDF -> {clean_url(batch_pdf)}")

        if not class_content_links and not global_pdf_links:
            await status_msg.edit_text("❌ No content found.")
            return

        # Create File
        safe_filename = "".join(c for c in course_title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        if not safe_filename: safe_filename = "course_data"
        
        file_buffer = io.StringIO()
        file_buffer.write(f"Course: {course_title}\n")
        file_buffer.write(f"ID: {course_id}\n")
        file_buffer.write("-" * 50 + "\n\n")
        
        if class_content_links:
            file_buffer.write("🎬 CLASS VIDEOS & NOTES:\n")
            file_buffer.write("=" * 50 + "\n")
            for link in class_content_links:
                file_buffer.write(link + "\n\n")
        
        if global_pdf_links:
            file_buffer.write("📚 OTHER STUDY MATERIALS:\n")
            file_buffer.write("=" * 50 + "\n")
            for link in global_pdf_links:
                file_buffer.write(link + "\n\n")

        file_buffer.seek(0)
        bytes_io = io.BytesIO(file_buffer.getvalue().encode('utf-8'))
        bytes_io.name = f"{safe_filename}.txt"

        await update.message.reply_document(
            document=bytes_io,
            caption=f"✅ **Extraction Complete**\nIncludes Videos & Class Notes (Board PDFs).",
            parse_mode='Markdown'
        )
        await status_msg.delete()

# ---------------- MAIN ----------------
if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_course_id))
    print("🤖 Bot is running...")
    application.run_polling()

