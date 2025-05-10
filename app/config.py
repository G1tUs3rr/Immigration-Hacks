import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT4_MODEL_NAME = "gpt-4-turbo-preview"
PINECONE_API_KEY = 'pcsk_5qyWbq_NfK8eH4k8A6RTizYNx8A8kVi4hGqcEpPFK1S4Ps38hjudPcCu78QrzJs6URKRji'
PINECONE_INDEX_NAME = 'immigration-hacks'
PINECONE_ENVIRONMENT = 'us-east1'
EMBEDDING_MODEL_NAME = 'text-embedding-3-small'
EMBEDDING_DIMENSION = 1536

# or your preferred GPT-4 model 