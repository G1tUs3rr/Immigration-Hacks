import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT4_MODEL_NAME = "gpt-4-turbo-preview"  # or your preferred GPT-4 model 