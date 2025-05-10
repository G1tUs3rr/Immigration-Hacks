# Plan: Enhance Telegram Bot with RAG using GPT-4

**Objective:** Modify the `handle_message` function in `app/telegram_bot.py` to implement a Retrieval Augmented Generation (RAG) pipeline. This pipeline will use embeddings of user queries, perform cosine similarity searches (top_k=10) against a vector store, de-duplicate results, construct a detailed context, and then use a GPT-4 model (`gpt-4.1-nano`) to generate an informed message for the user, replacing the current placeholder text.

**User Requirements Summary:**
*   Embed user's query.
*   Run cosine similarity search (top_k = 10).
*   De-duplicate Pinecone query returns.
*   Construct context for GPT-4 using:
    *   A) Original text (from embedding metadata)
    *   B) Document context (from embedding metadata)
    *   C) Contextualization already made by GPT-3.5 turbo (from embedding metadata)
    *   D) User's query
*   Use GPT-4 model: `gpt-4.1-nano`.
*   Send informed message to user.
*   Error Handling:
    *   Vector search fail/no results: "I couldn't find relevant information for your query. Please try rephrasing."
    *   GPT-4 call fail: "I'm having trouble generating a response right now. Please try again later."
*   Context Concatenation: User's Query, then for each retrieved document: Original Text, Document Context, GPT-3.5 Contextualization. Clearly label each section.

---

**I. Configuration Updates (Recommended)**

1.  **File:** `config.py`
2.  **Action:** Add a new configuration variable for the GPT-4 model name to make it easily configurable.
    ```python
    # In config.py
    GPT4_MODEL_NAME = os.getenv("GPT4_MODEL_NAME", "gpt-4.1-nano")
    ```

---

**II. Modifications to `app/telegram_bot.py`**

1.  **Imports:**
    *   Ensure necessary imports are present at the top of `app/telegram_bot.py`:
        ```python
        import logging
        import openai # For ChatCompletion
        from app.vector_store import query_vector_store
        from app.config import OPENAI_API_KEY # Ensure this is available
        # If using the config variable from step I:
        # from app.config import GPT4_MODEL_NAME 
        ```
    *   Initialize logger if not already present:
        ```python
        logger = logging.getLogger(__name__)
        ```

2.  **Modify `handle_message` function:**
    *   The existing `handle_message` function will be significantly updated as follows:

    ```python
    # In app/telegram_bot.py

    # If not loading GPT4_MODEL_NAME from config.py, define it here:
    # GPT4_MODEL_NAME = "gpt-4.1-nano" 
    # Otherwise, it should be imported or accessed via the config module.

    async def handle_message(update: Update, context):
        user_query = update.message.text
        chat_id = update.effective_chat.id
        logger.info(f"Received query from chat_id {chat_id}: {user_query}")

        # Ensure OpenAI API key is set for the openai client
        # This might be handled globally or per client instantiation
        if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_PLACEHOLDER":
            logger.error("OpenAI API key is not configured. Cannot proceed with GPT-4 call.")
            await update.message.reply_text("I'm having trouble connecting to the AI service right now. Please try again later.")
            return
        
        # Determine GPT-4 model name (either from config or defined directly)
        # Example assuming it's loaded from config:
        # from app.config import GPT4_MODEL_NAME
        # If not, ensure GPT4_MODEL_NAME is defined in this scope. For this plan, we'll assume it's available.
        # For clarity, if not from config:
        current_gpt4_model_name = "gpt-4.1-nano" # Replace with config.GPT4_MODEL_NAME if implemented

        try:
            # 1. Embed user's query and perform vector search
            logger.info(f"Performing vector search for query: {user_query}")
            search_results = await query_vector_store(user_query, top_k=10)

            if not search_results:
                logger.info("Vector search returned no results.")
                await update.message.reply_text("I couldn't find relevant information for your query. Please try rephrasing.")
                return

            # 2. De-duplicate search results based on 'original_text'
            unique_results = []
            seen_original_texts = set()
            for match in search_results:
                # Ensure metadata and original_text exist
                if hasattr(match, 'metadata') and match.metadata:
                    original_text = match.metadata.get("original_text")
                    if original_text and original_text not in seen_original_texts:
                        unique_results.append(match)
                        seen_original_texts.add(original_text)
                    elif not original_text: # If original_text is missing, keep it but log warning
                        logger.warning(f"Match ID {match.id} missing 'original_text' in metadata, keeping it.")
                        unique_results.append(match) # Or decide to discard
                else:
                    logger.warning(f"Match ID {match.id} missing metadata, skipping.")


            if not unique_results:
                logger.info("Vector search returned no unique/valid results after de-duplication.")
                await update.message.reply_text("I couldn't find relevant information for your query. Please try rephrasing.")
                return

            logger.info(f"Retrieved {len(unique_results)} unique documents after de-duplication.")

            # 3. Construct context for GPT-4
            context_prompt_parts = [f"User Query: {user_query}\n\n--- Relevant Information Extracted ---\n"]

            for i, match in enumerate(unique_results):
                metadata = match.metadata # Assumes metadata exists after filtering
                original_text = metadata.get("original_text", "N/A")
                doc_context = metadata.get("document_context", "N/A")
                gpt35_summary = metadata.get("contextualized_summary", "N/A")

                context_prompt_parts.append(f"\n--- Document {i+1} ---\n")
                context_prompt_parts.append(f"Original Text Snippet: {original_text}\n")
                context_prompt_parts.append(f"Overall Document Context: {doc_context}\n")
                context_prompt_parts.append(f"Contextual Summary (AI-generated for this snippet): {gpt35_summary}\n")
            
            final_prompt_context = "".join(context_prompt_parts)
            logger.debug(f"Constructed prompt context for GPT-4 (first 500 chars): {final_prompt_context[:500]}")

            # 4. Call GPT-4 for response generation
            logger.info(f"Sending request to GPT-4 model: {current_gpt4_model_name}")
            
            client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
            
            system_message_content = (
                "You are an expert U.S. Immigration Law assistant. "
                "Based on the user's query and the provided relevant information snippets, "
                "answer the user's question comprehensively and clearly. "
                "If the information seems insufficient to fully answer, state that you can only provide partial information based on the snippets. "
                "Do not make up information not present in the provided snippets."
            )
            
            gpt_response = await client.chat.completions.create(
                model=current_gpt4_model_name,
                messages=[
                    {"role": "system", "content": system_message_content},
                    {"role": "user", "content": final_prompt_context} # Contains the query and retrieved contexts
                ],
                temperature=0.3, # Lower temperature for more factual responses
                max_tokens=1500  # Adjust as needed, considering response length and cost
            )
            
            informed_response = gpt_response.choices[0].message.content.strip()
            logger.info("Received response from GPT-4.")

            # 5. Send informed message to user
            await update.message.reply_text(informed_response)

        except openai.APIError as e:
            logger.error(f"OpenAI API error during GPT-4 call: {e}", exc_info=True)
            await update.message.reply_text("I'm having trouble generating a response right now. Please try again later.")
        except Exception as e:
            logger.error(f"An unexpected error occurred in handle_message: {e}", exc_info=True)
            await update.message.reply_text("An unexpected error occurred while processing your request. Please try again.")
    ```

---

**III. Mermaid Diagram of the RAG flow in `handle_message`**

```mermaid
graph TD
    A[User Sends Message] --> B{handle_message};
    B --> C[Get User Query];
    C --> D{Embed Query & Vector Search top_k=10};
    D -- Search Results --> E{De-duplicate Results by 'original_text'};
    E -- No Unique/Valid Results --> F[Reply: "Couldn't find relevant information..."];
    E -- Unique Results --> G{Construct GPT-4 Prompt};
    G --> H[User Query (as part of prompt)];
    G --> I[For each unique doc: \n - Label: Document N \n - Original Text \n - Document Context \n - GPT-3.5 Summary];
    H --> J{GPT-4 API Call (model='gpt-4.1-nano')};
    I --> J;
    J -- Success --> K[Get GPT-4 Response];
    K --> L[Send Informed Response to User];
    J -- API Error --> M[Reply: "I'm having trouble generating a response..."];
    D -- No Search Results / Initial Error --> F;
    subgraph ErrorHandling
        M;
        F;
        N[Reply: "An unexpected error occurred..."];
    end
    B -- Any Other Uncaught Exception --> N;
```

---

**IV. Summary of Changes:**

*   **`config.py`:** (Recommended) Add `GPT4_MODEL_NAME` variable.
*   **`app/telegram_bot.py`:**
    *   Update imports (add `logging`, `openai`, `query_vector_store`, relevant config).
    *   Initialize `logger`.
    *   Significantly refactor `handle_message` to:
        1.  Retrieve user query.
        2.  Call `query_vector_store` from `app.vector_store` with `top_k=10`.
        3.  Implement de-duplication logic for search results based on `original_text` in metadata.
        4.  Construct a detailed context string for GPT-4, including the user's query and labeled sections for each retrieved document (Original Text, Document Context, GPT-3.5 Contextualization).
        5.  Call the specified GPT-4 model (`gpt-4.1-nano` or from config) using the `openai` library.
        6.  Implement error handling for vector search failures, lack of unique results, and GPT-4 API errors, providing user-friendly messages.
        7.  Send the GPT-4 generated response back to the user.
---
This plan should guide the implementation of the RAG functionality in the Telegram bot.