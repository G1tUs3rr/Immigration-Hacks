import os
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ChatMemberHandler
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context):
    await update.message.reply_text(
        "Welcome to the Immigration Assistant! Ask me any questions about U.S. immigration laws."
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "I can help you with questions about U.S. immigration laws. Just ask your question!"
    )

async def handle_message(update: Update, context):
    query = update.message.text
    # For now, just echo back the message
    await update.message.reply_text(f"You asked: {query}\n\nhellooo haahaaha ceholder response. The actual response generation will be implemented later.")

async def handle_new_follower(update: Update, context):
    """Handles new members joining the chat."""
    if update.my_chat_member:
        new_chat_member = update.my_chat_member.new_chat_member
        if new_chat_member.status == ChatMember.MEMBER:
            user_id = new_chat_member.user.id
            if not context.user_data.get(f"disclaimer_sent_{user_id}", False):
                disclaimer_text = (
                    "Thank you for following! I am not a lawyer, and the information "
                    "provided by this chatbot is for informational purposes only. It is "
                    "not intended to be legal advice and should not be relied upon as "
                    "such. Immigration laws can be complex and vary by jurisdiction. "
                    "For personalized guidance and to ensure your rights are protected, "
                    "please consult a qualified immigration attorney."
                )
                await context.bot.send_message(chat_id=update.effective_chat.id, text=disclaimer_text)
                context.user_data[f"disclaimer_sent_{user_id}"] = True

def main():
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(ChatMemberHandler(handle_new_follower, ChatMemberHandler.MY_CHAT_MEMBER))

    # Start the bot
    print("Starting bot...")
    application.run_polling()

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables")
    else:
        main()