import argparse
import asyncio
import logging
import re
import os
import sys

# Add project root to sys.path to allow imports from 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.vector_store import generate_embedding, upsert_vectors, init_pinecone
from app.config import OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME
import openai

# --- Configuration & Setup ---
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def _estimate_tokens(text: str) -> int:
    """Estimates token count based on 1 token ~ 4 characters."""
    if not text:
        return 0
    return len(text) // 4

def chunk_text(text: str, chunk_size_upper_tokens: int, chunk_size_lower_tokens: int) -> list[str]:
    """
    Chunks text, prioritizing paragraph breaks, then sentence breaks,
    while respecting upper and lower token limits.
    """
    logger.info(f"Chunking text. Upper_limit: {chunk_size_upper_tokens} tokens, Lower_limit: {chunk_size_lower_tokens} tokens.")
    
    final_chunks = []
    if not text.strip():
        logger.warning("Input text is empty or whitespace only.")
        return final_chunks

    # Split by paragraphs (one or more blank lines)
    paragraphs = re.split(r'\n\s*\n+', text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    current_chunk_parts = []
    current_chunk_char_count = 0

    for i, paragraph in enumerate(paragraphs):
        paragraph_char_count = len(paragraph)
        paragraph_tokens = _estimate_tokens(paragraph)

        # If current paragraph itself is larger than upper limit, it needs to be split by sentences
        if paragraph_tokens > chunk_size_upper_tokens:
            # Finalize any existing current_chunk_parts before processing the large paragraph
            if current_chunk_parts:
                assembled_chunk = "\n\n".join(current_chunk_parts)
                if _estimate_tokens(assembled_chunk) >= chunk_size_lower_tokens or not final_chunks: # Keep if substantial or only one
                    final_chunks.append(assembled_chunk)
                elif final_chunks: # Try to append to last chunk if it doesn't make it too big
                    if _estimate_tokens(final_chunks[-1] + "\n\n" + assembled_chunk) <= chunk_size_upper_tokens:
                        final_chunks[-1] += "\n\n" + assembled_chunk
                    else:
                        final_chunks.append(assembled_chunk) # Add as its own if cannot append
                current_chunk_parts = []
                current_chunk_char_count = 0
            
            # Split the large paragraph by sentences
            # Regex: looks for . ! ? followed by a space or newline. Not perfect for all cases (e.g. Mr. Smith).
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            temp_sentence_chunk_parts = []
            temp_sentence_char_count = 0
            for sentence in sentences:
                sentence_char_count = len(sentence)
                if _estimate_tokens(temp_sentence_char_count + sentence_char_count) <= chunk_size_upper_tokens:
                    temp_sentence_chunk_parts.append(sentence)
                    temp_sentence_char_count += sentence_char_count + 1 # +1 for space
                else:
                    if temp_sentence_chunk_parts: # Finalize current sentence group
                        final_chunks.append(" ".join(temp_sentence_chunk_parts))
                    temp_sentence_chunk_parts = [sentence] # Start new group with current sentence
                    temp_sentence_char_count = sentence_char_count
            
            if temp_sentence_chunk_parts: # Add any remaining sentence group
                final_chunks.append(" ".join(temp_sentence_chunk_parts))
            continue # Move to the next paragraph

        # Try to add current paragraph to current_chunk_parts
        if _estimate_tokens(current_chunk_char_count + paragraph_char_count) <= chunk_size_upper_tokens:
            current_chunk_parts.append(paragraph)
            current_chunk_char_count += paragraph_char_count + (len("\n\n") if current_chunk_parts else 0)
        else:
            # Finalize current_chunk_parts as it's full
            if current_chunk_parts:
                final_chunks.append("\n\n".join(current_chunk_parts))
            # Start new chunk with current paragraph
            current_chunk_parts = [paragraph]
            current_chunk_char_count = paragraph_char_count

        # If current_chunk is "full enough" (>= lower_tokens), finalize it
        if _estimate_tokens(current_chunk_char_count) >= chunk_size_lower_tokens:
            if current_chunk_parts:
                final_chunks.append("\n\n".join(current_chunk_parts))
                current_chunk_parts = []
                current_chunk_char_count = 0
    
    # Add any remaining parts in current_chunk_parts
    if current_chunk_parts:
        final_chunks.append("\n\n".join(current_chunk_parts))

    # Post-processing: Attempt to merge small chunks if they are below lower_token_limit
    merged_chunks = []
    i = 0
    while i < len(final_chunks):
        current_merged_chunk = final_chunks[i]
        current_merged_tokens = _estimate_tokens(current_merged_chunk)
        i += 1
        # If current chunk is too small, try to merge with next ones
        while current_merged_tokens < chunk_size_lower_tokens and i < len(final_chunks):
            next_chunk_tokens = _estimate_tokens(final_chunks[i])
            if current_merged_tokens + next_chunk_tokens <= chunk_size_upper_tokens:
                current_merged_chunk += "\n\n" + final_chunks[i] # Assuming paragraph merge
                current_merged_tokens += next_chunk_tokens
                i += 1
            else:
                break # Next chunk makes it too big
        merged_chunks.append(current_merged_chunk)
    
    final_chunks = [chunk for chunk in merged_chunks if chunk.strip()] # Ensure no empty chunks
    logger.info(f"Generated {len(final_chunks)} final chunks after attempting merges.")
    return final_chunks


async def contextualize_chunk_with_gpt(
    current_chunk_text: str,
    document_context: str,
    preceding_chunk_text: str | None = None,
    succeeding_chunk_text: str | None = None
) -> str:
    if not openai.api_key: # Check if API key was set
        logger.error("OpenAI API key not set. Cannot contextualize chunk.")
        return "Error: OpenAI API key not configured."

    prompt_messages = [
        {"role": "system", "content": "You are an expert assistant helping to contextualize text chunks. Create a 2-3 sentence contextual summary for the current chunk based on the provided document context and surrounding text."},
        {"role": "user", "content": f"""
Document Context: "{document_context}"
---
Current Chunk: "{current_chunk_text}"
---
Preceding Chunk (if any): "{preceding_chunk_text if preceding_chunk_text else 'N/A'}"
---
Succeeding Chunk (if any): "{succeeding_chunk_text if succeeding_chunk_text else 'N/A'}"
---
Based on the document context and the surrounding text (previous, current, and next chunks), briefly explain the main topic or add key contextual details specifically for the "Current Chunk". Focus on information that would help understand this "Current Chunk" in relation to the larger document and its immediate neighbors. Provide only the contextual explanation for the "Current Chunk".
        """}
    ]
    try:
        # Using pre-v1.0 openai library syntax as per existing app.vector_store and plan
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=prompt_messages,
            temperature=0.3, 
            max_tokens=200  # Increased slightly for potentially richer context
        )
        contextualization = response.choices[0].message['content'].strip()
        logger.info(f"Contextualized chunk (first 30 chars): '{current_chunk_text[:30]}...' -> '{contextualization[:50]}...'")
        return contextualization
    except Exception as e:
        logger.error(f"Error contextualizing chunk with GPT: {e}", exc_info=True)
        return f"Error during contextualization: {str(e)}"


async def process_document_pipeline(text_content: str, chunk_size_upper: int, chunk_size_lower: int, doc_context: str):
    logger.info("Starting document processing pipeline...")

    if not all([PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME]) or \
       PINECONE_API_KEY == "YOUR_PINECONE_API_KEY_PLACEHOLDER":
        logger.error("Pinecone credentials not fully configured. Aborting.")
        return

    # 1. Initialize Pinecone (ensure it's ready)
    if not init_pinecone(): 
        logger.error("Failed to initialize Pinecone. Aborting pipeline.")
        return
    logger.info("Pinecone initialized successfully.")

    # 2. Chunk text
    logger.info("Chunking text...")
    chunks = chunk_text(text_content, chunk_size_upper, chunk_size_lower)
    if not chunks:
        logger.warning("No chunks were generated from the text.")
        return
    logger.info(f"Generated {len(chunks)} chunks.")

    vectors_to_upsert = []
    for i, chunk_text_original in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)} (length: {len(chunk_text_original)} chars)...")

        preceding_chunk = chunks[i-1] if i > 0 else None
        succeeding_chunk = chunks[i+1] if i < len(chunks) - 1 else None
        
        logger.debug(f"Contextualizing chunk {i+1}...")
        contextualized_summary = await contextualize_chunk_with_gpt(
            chunk_text_original,
            doc_context,
            preceding_chunk,
            succeeding_chunk
        )

        logger.debug(f"Generating embedding for original chunk {i+1}...")
        embedding = await generate_embedding(chunk_text_original) 

        if embedding:
            # Create a more robust unique ID
            doc_hash = hash(doc_context + text_content[:100]) # Simple hash of doc context and start of text
            chunk_id = f"doc_{doc_hash}_chunk_{i}"
            
            metadata = {
                "original_text": chunk_text_original,
                "contextualized_summary": contextualized_summary,
                "document_context": doc_context,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "estimated_tokens": _estimate_tokens(chunk_text_original)
            }
            vectors_to_upsert.append((chunk_id, embedding, metadata))
            logger.info(f"Prepared vector for chunk {i+1} (ID: {chunk_id}).")
        else:
            logger.warning(f"Failed to generate embedding for chunk {i+1}. Skipping.")

    if vectors_to_upsert:
        logger.info(f"Upserting {len(vectors_to_upsert)} vectors to Pinecone...")
        upsert_responses = await upsert_vectors(vectors_to_upsert) 
        if upsert_responses:
            total_upserted = 0
            # The structure of upsert_responses might vary; adapt if needed.
            # Assuming it's a list of responses, each with an 'upserted_count'
            if isinstance(upsert_responses, list) and upsert_responses and hasattr(upsert_responses[0], 'upserted_count'):
                 total_upserted = sum(res.upserted_count for res in upsert_responses)
            logger.info(f"Successfully upserted {total_upserted} vectors to Pinecone (details may vary by client version).")
        else:
            logger.error("Failed to upsert vectors to Pinecone or no response received.")
    else:
        logger.info("No vectors to upsert.")
    
    logger.info("Document processing pipeline finished.")

# --- Main Execution ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    parser = argparse.ArgumentParser(description="Chunks text, contextualizes with GPT, embeds, and upserts to Pinecone.")
    parser.add_argument("text_input", help="Raw text string or path to a text file (UTF-8 encoded).")
    parser.add_argument("--chunk_size_upper", type=int, required=True, help="Upper limit for chunk size in tokens (e.g., 500).")
    parser.add_argument("--chunk_size_lower", type=int, default=100, help="Lower limit for chunk size in tokens (default: 100).")
    parser.add_argument("--document_context", type=str, required=True, help="Overall context/summary for the document.")
    
    args = parser.parse_args()

    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_PLACEHOLDER":
        logging.error("OpenAI API key is not configured in .env or environment variables. Please set OPENAI_API_KEY.")
        sys.exit(1)
    openai.api_key = OPENAI_API_KEY # Set for pre-v1.0 openai library

    text_content = ""
    if os.path.isfile(args.text_input):
        try:
            with open(args.text_input, 'r', encoding='utf-8') as f:
                text_content = f.read()
            logging.info(f"Successfully read text from file: {args.text_input}")
        except Exception as e:
            logging.error(f"Failed to read text from file {args.text_input}: {e}", exc_info=True)
            sys.exit(1)
    else:
        text_content = args.text_input 
        logging.info("Using provided string as text input.")

    if not text_content.strip():
        logging.error("Input text is empty. Nothing to process.")
        sys.exit(1)
    
    if args.chunk_size_lower >= args.chunk_size_upper:
        logging.error(f"chunk_size_lower ({args.chunk_size_lower}) must be less than chunk_size_upper ({args.chunk_size_upper}).")
        sys.exit(1)

    asyncio.run(process_document_pipeline(
        text_content,
        args.chunk_size_upper,
        args.chunk_size_lower,
        args.document_context
    ))