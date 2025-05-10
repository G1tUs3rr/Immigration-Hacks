# Immigration RAG Agent

This project is a Retrieval Augmented Generation (RAG) agent focused on U.S. immigration laws and related topics. It uses a vector database (Pinecone) to store embeddings of legal documents and articles, and provides an interface via a Telegram bot to answer user queries.

## Project Structure

```
immigration_rag_agent/
├── app/                                # Main application source code
│   ├── __init__.py                     # Makes 'app' a Python package
│   ├── main.py                         # FastAPI app definition, Telegram webhook endpoint
│   ├── telegram_bot.py                 # Logic for interacting with Telegram API
│   ├── vector_store.py                 # Logic for interacting with Pinecone
│   └── services/                       # Core business logic
│       ├── __init__.py
│       └── query_processing_service.py # Handles queries, orchestrates search
├── config.py                           # Configuration (API keys, etc.)
├── data/                               # Stores raw and processed documents
│   ├── raw_documents/                  # Raw input documents (e.g., PDFs, text files)
│   │   └── .gitkeep
│   └── processed_texts/                # Cleaned/chunked texts before vectorization
│       └── .gitkeep
├── scripts/                            # Utility and standalone scripts
│   └── ingest_documents.py             # Script for document ingestion pipeline
├── .gitignore                          # Specifies intentionally untracked files
├── README.md                           # This file
└── requirements.txt                    # Python dependencies
```

## Features

-   **Telegram Bot Interface**: Users can interact with the agent via Telegram.
-   **RAG Pipeline**:
    -   Document ingestion: Processes and stores document embeddings in Pinecone.
    -   Query processing: Retrieves relevant document chunks based on user queries using vector similarity search.
    -   Response generation: (Currently basic, can be extended with an LLM for more natural answers).
-   **Configurable**: API keys and settings managed via `config.py` and a `.env` file.

## Prerequisites

-   Python 3.8+
-   Pinecone account and API key
-   Telegram Bot Token
-   Access to an embedding model (e.g., via `sentence-transformers`)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd immigration_rag_agent
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: `requirements.txt` will need to be created based on the libraries used, e.g., `fastapi`, `uvicorn`, `python-telegram-bot` or `httpx`, `pinecone-client`, `sentence-transformers`, `python-dotenv`, etc.)*

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory by copying `.env.example` (if provided) or creating it manually. Add your API keys and other configurations:
    ```env
    TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
    WEBHOOK_SECRET_TOKEN="your_secure_path_token_for_webhook_if_used" # Optional

    PINECONE_API_KEY="your_pinecone_api_key_here"
    PINECONE_ENVIRONMENT="your_pinecone_environment_here" # e.g., "gcp-starter"
    PINECONE_INDEX_NAME="your_chosen_pinecone_index_name" # e.g., "immigration-docs"
    EMBEDDING_DIMENSION="384" # Or 768, etc., depending on your chosen model
    EMBEDDING_MODEL_NAME="sentence-transformers/all-MiniLM-L6-v2" # Or your chosen model

    # Optional: For testing telegram_bot.py directly
    # MY_CHAT_ID="your_telegram_chat_id_for_testing"
    ```
    Ensure these variables are correctly picked up by `config.py`.

## Running the Application

### 1. Ingest Documents

Before users can query the agent, you need to populate the Pinecone vector database with your documents.

-   Place your raw legal documents and articles into the `data/raw_documents/` directory.
-   Run the ingestion script:
    ```bash
    python scripts/ingest_documents.py
    ```
    This script will:
    -   Load documents from `data/raw_documents/`.
    -   Clean and chunk the text.
    -   Generate embeddings.
    -   Upsert the embeddings and metadata to your configured Pinecone index.
    *(Ensure `ingest_documents.py` is correctly configured to use your embedding model and Pinecone settings via `config.py`)*

### 2. Start the Web Server

The FastAPI application handles webhook requests from Telegram.

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
-   `--reload`: Enables auto-reloading on code changes (for development).
-   The server will run on `http://0.0.0.0:8000`.

### 3. Set up Telegram Webhook

You need to tell Telegram where to send updates for your bot.
Replace `YOUR_TELEGRAM_BOT_TOKEN` and `YOUR_SERVER_PUBLIC_URL` (e.g., from ngrok if testing locally, or your deployed server URL).

```bash
curl -F "url=https://YOUR_SERVER_PUBLIC_URL/webhook/YOUR_SECURE_PATH_TOKEN" \
     "https://api.telegram.org/botYOUR_TELEGRAM_BOT_TOKEN/setWebhook"
```
-   `YOUR_SECURE_PATH_TOKEN` should match the token you expect in `app/main.py` for basic security.
-   Ensure your server is publicly accessible for Telegram to reach the webhook. For local development, tools like `ngrok` can be used (`ngrok http 8000`).

## Usage

Once the server is running and the webhook is set, you can send messages to your Telegram bot. The bot will process your query and respond with information retrieved from the vector store.

## To-Do / Potential Enhancements

-   **Create `requirements.txt`**: Populate with all necessary Python libraries.
-   **Implement actual document parsing**: Enhance `ingest_documents.py` to handle various file types (PDF, DOCX, HTML) and perform robust text extraction and cleaning.
-   **Refine embedding generation**: Ensure the chosen embedding model in `config.py` and `ingest_documents.py` is suitable and consistently used.
-   **Implement Pinecone Index Creation**: Uncomment and configure index creation logic in `ingest_documents.py` and potentially `app/vector_store.py` if dynamic creation is needed.
-   **Connect `config.py` properly**: Ensure all modules (`main.py`, `telegram_bot.py`, `vector_store.py`, `ingest_documents.py`) correctly import and use configurations from the root `config.py`.
-   **Error Handling and Logging**: Enhance error handling and logging throughout the application.
-   **Security**: Implement more robust webhook security.
-   **Advanced RAG**: Integrate a Large Language Model (LLM) in `query_processing_service.py` to generate more conversational and context-aware answers based on retrieved documents, instead of just returning raw chunks.
-   **Testing**: Add unit and integration tests.
-   **Deployment**: Document deployment steps (e.g., Docker, cloud platforms).