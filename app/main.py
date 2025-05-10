from http.server import BaseHTTPRequestHandler
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize the application
application = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Immigration Assistant! Ask me any questions about U.S. immigration laws."
    )
<<<<<<< HEAD

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I can help you with questions about U.S. immigration laws. Just ask your question!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    # For now, just echo back the message
    await update.message.reply_text(f"You asked: {query}\n\nThis is a placeholder response. The actual response generation will be implemented later.")

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Immigration Bot is running")
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            update = Update.de_json(json.loads(post_data), application.bot)
            application.process_update(update)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(str(e).encode())
=======

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I can help you with questions about U.S. immigration laws. Just ask your question!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    # For now, just echo back the message
    await update.message.reply_text(f"You asked: {query}\n\nThis is a placeholder response. The actual response generation will be implemented later.")

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

def process_telegram_update(request):
    """Process incoming Telegram updates."""
    try:
        update = Update.de_json(json.loads(request.get_json()), application.bot)
        application.process_update(update)
        return {"statusCode": 200, "body": "OK"}
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}

def handler(request):
    """Vercel serverless function handler."""
    if request.method == "POST":
        return process_telegram_update(request)
    return {"statusCode": 200, "body": "Immigration Bot is running"}
>>>>>>> main
