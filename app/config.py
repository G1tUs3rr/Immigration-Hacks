import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
# This is useful for local development to keep secrets out of version control.
# Create a .env file in the root directory with your actual keys.
# Example .env file content:
# TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
# PINECONE_API_KEY="your_pinecone_api_key_here"
# PINECONE_ENVIRONMENT="your_pinecone_environment_here" # e.g., "gcp-starter" or "us-west1-gcp"
# PINECONE_INDEX_NAME="your_pinecone_index_name_here"
# OPENAI_API_KEY="your_openai_api_key_here" # Added for OpenAI
# MY_CHAT_ID="your_telegram_chat_id_for_testing" # Optional: for testing send_telegram_message

load_dotenv(override=True)

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_PLACEHOLDER")
# You might want a more secure way to set your webhook token/path if you use one in main.py
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "YOUR_SECURE_PATH_TOKEN_PLACEHOLDER")


# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_PLACEHOLDER")
GPT4_MODEL_NAME = os.getenv("GPT4_MODEL_NAME", "gpt-4.1-nano")

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "YOUR_PINECONE_API_KEY_PLACEHOLDER")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "YOUR_PINECONE_ENVIRONMENT_PLACEHOLDER") # e.g., "us-west1-gcp" or "us-east-1"
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "immigration-docs") # Example index name

# Embedding Model Configuration (now for OpenAI)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
# Dimension for text-embedding-3-small is 1536.
# Other models like text-embedding-3-large have 3072.
# ada-002 (legacy) has 1536.
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1536"))


# Optional: For testing telegram_bot.py directly
MY_CHAT_ID = os.getenv("MY_CHAT_ID") # Your personal Telegram chat ID for direct test messages

# Application settings
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

# Logging configuration (can be expanded)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


# --- Sanity checks and warnings ---
if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_PLACEHOLDER":
    print("WARNING: TELEGRAM_BOT_TOKEN is not set. Please set it in your .env file or environment variables.")

# Note: The check for PINECONE_ENVIRONMENT placeholder was already there, so I'm ensuring it's correct.
# The OPENAI_API_KEY check was added in the previous (partially applied) diff.

if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_PLACEHOLDER":
    print("WARNING: OPENAI_API_KEY is not set. Please set it in your .env file or environment variables. Embeddings will fail.")

if PINECONE_API_KEY == "YOUR_PINECONE_API_KEY_PLACEHOLDER":
    print("WARNING: PINECONE_API_KEY is not set. Please set it in your .env file or environment variables.")

if PINECONE_ENVIRONMENT == "YOUR_PINECONE_ENVIRONMENT_PLACEHOLDER": # Ensuring this check is correct
    print("WARNING: PINECONE_ENVIRONMENT is not set. Please set it in your .env file or environment variables.")

# You can add more configurations here as needed, e.g., database URLs, external API endpoints, etc.

# Example of how to use these in other files:
# from config import TELEGRAM_BOT_TOKEN, PINECONE_API_KEY, OPENAI_API_KEY