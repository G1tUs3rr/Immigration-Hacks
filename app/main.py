from fastapi import FastAPI, Request, HTTPException
from telegram import Update
import os
from dotenv import load_dotenv
from app.telegram_bot import process_telegram_update

load_dotenv()

app = FastAPI()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET_TOKEN")

@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook token")
    
    update = await request.json()
    await process_telegram_update(Update.de_json(update, None))
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "ok", "message": "Immigration Bot is running"}

if __name__ == "__main__":
    import uvicorn
    # This is for local development. For production, use a proper ASGI server like Gunicorn with Uvicorn workers.
    # The host and port can also be configured via config.py or environment variables.
    uvicorn.run(app, host="0.0.0.0", port=8000)