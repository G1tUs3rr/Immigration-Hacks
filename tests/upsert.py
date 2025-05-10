import sys
import asyncio
sys.path.append('/Users/jasonlee_1/projects/Immigration-Hacks')

import os
os.chdir('/Users/jasonlee_1/projects/Immigration-Hacks')
# from app.vector_store import generate_embedding, upsert_vectors
# import pdfplumber
from scripts.chunker_pipeline import process_document_pipeline

async def main():
    with open('snippet.txt', 'r') as f:
        snippet = f.read()

    results = await process_document_pipeline(snippet, 1000, 500, "Fundamentals_of_Immigration_Law.pdf")
    return results

if __name__ == "__main__":
    results = asyncio.run(main())
    print("Processing complete!")
