from fastapi import FastAPI, Request, HTTPException
import logging

# Assuming 'config.py' is in the parent directory of 'app'
# and 'services' and 'telegram_bot' are in the same 'app' directory.
# Adjust imports if your structure is different or once those files are created.
# from ..config import TELEGRAM_BOT_TOKEN # Example, will be defined in config.py
# from .services.query_processing_service import process_query
# from .telegram_bot import send_telegram_message

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Placeholder for your Telegram Bot Token verification if needed
# if not TELEGRAM_BOT_TOKEN:
#     logger.warning("TELEGRAM_BOT_TOKEN not set in config.py. Webhook might not function correctly.")

@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    """
    Handles incoming updates from Telegram via Webhook.
    """
    # A more secure way to verify the token would be to compare it with
    # a secret path or a value from your config.
    # For now, we'll just log the token received.
    # if token != "YOUR_SECURE_PATH_TOKEN": # Replace with a secure token or method
    #     logger.error(f"Invalid token received: {token}")
    #     raise HTTPException(status_code=403, detail="Invalid token")

    try:
        data = await request.json()
        logger.info(f"Received data from Telegram: {data}")

        # Extract message and chat_id (this structure depends on the Telegram update object)
        if "message" in data:
            message = data.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text")

            if chat_id and text:
                logger.info(f"Received message: '{text}' from chat_id: {chat_id}")
                # response_text = await process_query(text, chat_id) # To be implemented
                # await send_telegram_message(chat_id, response_text) # To be implemented
                # For now, just acknowledge receipt
                return {"status": "ok", "message": "Received, processing not yet implemented"}
            else:
                logger.warning("Message or chat_id missing in webhook data.")
                return {"status": "error", "message": "Missing message or chat_id"}
        else:
            logger.info("Received non-message update from Telegram (e.g., callback_query, edited_message).")
            # Handle other types of updates if necessary
            return {"status": "ok", "message": "Non-message update received"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Immigration RAG Agent is running."}

if __name__ == "__main__":
    import uvicorn
    # This is for local development. For production, use a proper ASGI server like Gunicorn with Uvicorn workers.
    # The host and port can also be configured via config.py or environment variables.
    uvicorn.run(app, host="0.0.0.0", port=8000)