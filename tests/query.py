import sys
import asyncio
sys.path.append('/Users/jasonlee_1/projects/Immigration-Hacks')

import os
os.chdir('/Users/jasonlee_1/projects/Immigration-Hacks')
# from app.vector_store import generate_embedding, upsert_vectors
# import pdfplumber
from app.vector_store import query_vector_store

async def main():
    results = await query_vector_store('What is the purpose of the visa waiver program?', top_k=1)
    return results

if __name__ == "__main__":
    results = asyncio.run(main())
    print(results)
