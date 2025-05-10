import os
import logging # Added
import openai # Added
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ChatMemberHandler
from dotenv import load_dotenv

# Added imports from project
from app.vector_store import query_vector_store
from app.config import OPENAI_API_KEY, GPT4_MODEL_NAME

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')


async def start(update: Update, context):
    await update.message.reply_text(
        "Welcome to the Immigration Assistant! Ask me any questions about U.S. immigration laws."
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "I can help you with questions about U.S. immigration laws. Just ask your question!"
    )

async def handle_message(update: Update, context):
    user_query = update.message.text
    chat_id = update.effective_chat.id
    logger.info(f"Received query from chat_id {chat_id}: {user_query}")

    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_PLACEHOLDER":
        logger.error("OpenAI API key is not configured. Cannot proceed with GPT-4 call.")
        await update.message.reply_text("I'm having trouble connecting to the AI service right now. Please try again later.")
        return
    
    current_gpt4_model_name = GPT4_MODEL_NAME # Using from app.config

    # Initialize prompt components
    final_prompt_context = f"User Query: {user_query}"
    system_message_content = "You are an expert U.S. Immigration Law assistant. Answer the user's question comprehensively and clearly based on your general knowledge."
    rag_context_available = False

    try:
        # 1. Attempt to get RAG context
        logger.info(f"Performing vector search for query: {user_query}")
        search_results = await query_vector_store(user_query, top_k=10)

        unique_results = []
        if search_results:
            min_similarity_threshold = 0.60
            filtered_by_score_results = [
                match for match in search_results
                if hasattr(match, 'score') and match.score >= min_similarity_threshold
            ]

            if filtered_by_score_results:
                logger.info(f"Retrieved {len(filtered_by_score_results)} results after applying similarity threshold {min_similarity_threshold}.")
                
                seen_original_texts = set()
                for match in filtered_by_score_results:
                    if hasattr(match, 'metadata') and match.metadata:
                        original_text = match.metadata.get("original_text")
                        if original_text and original_text not in seen_original_texts:
                            unique_results.append(match)
                            seen_original_texts.add(original_text)
                        elif not original_text:
                            logger.warning(f"Match ID {match.id if hasattr(match, 'id') else 'N/A'} missing 'original_text' in metadata (after score filtering), keeping it.")
                            unique_results.append(match) # Or decide to discard
                    else:
                        logger.warning(f"Match ID {match.id if hasattr(match, 'id') else 'N/A'} missing metadata (after score filtering), skipping.")
            else:
                logger.info(f"No results met the minimum similarity threshold of {min_similarity_threshold}.")
        else:
            logger.info("Vector search returned no initial results.")

        if unique_results:
            rag_context_available = True
            logger.info(f"Retrieved {len(unique_results)} unique documents after de-duplication for RAG context.")
            
            context_prompt_parts = ["\n\n--- Relevant Information Extracted ---\n"]
            for i, match in enumerate(unique_results):
                metadata = match.metadata
                original_text = metadata.get("original_text", "N/A")
                doc_context = metadata.get("document_context", "N/A")
                gpt35_summary = metadata.get("contextualized_summary", "N/A")

                context_prompt_parts.append(f"\n--- Document {i+1} ---\n")
                context_prompt_parts.append(f"Original Text Snippet: {original_text}\n")
                context_prompt_parts.append(f"Overall Document Context: {doc_context}\n")
                context_prompt_parts.append(f"Contextual Summary (AI-generated for this snippet): {gpt35_summary}\n")
            
            final_prompt_context += "".join(context_prompt_parts)
            system_message_content = (
                "You are an expert U.S. Immigration Law assistant. "
                "Based on the user's query and the provided relevant information snippets, "
                "answer the user's question comprehensively and clearly. "
                "If the information seems insufficient to fully answer, state that you can only provide partial information based on the snippets. "
                "Do not make up information not present in the provided snippets."
            )
        else:
            logger.info("No RAG context available (either no search results, threshold not met, or no unique results). Proceeding with query only.")

        # 4. Call GPT-4 for response generation
        logger.info(f"Sending request to GPT-4 model: {current_gpt4_model_name}. RAG context available: {rag_context_available}")
        logger.debug(f"System Message: {system_message_content}")
        logger.debug(f"User Prompt Context (first 300 chars): {final_prompt_context[:300]}")

        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        gpt_response = await client.chat.completions.create(
            model=current_gpt4_model_name,
            messages=[
                {"role": "system", "content": system_message_content},
                {"role": "user", "content": final_prompt_context}
            ],
            temperature=0.3,
            max_tokens=1500
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

async def handle_new_follower(update: Update, context):
    """Handles new members joining the chat."""
    if update.my_chat_member:
        new_chat_member = update.my_chat_member.new_chat_member
        if new_chat_member.status == ChatMember.MEMBER:
            user_id = new_chat_member.user.id
            if not context.user_data.get(f"disclaimer_sent_{user_id}", False):
                disclaimer_text = (
                    "Thank you for following! I am not a lawyer, and the information "
                    "provided by this chatbot is for informational purposes only. It is "
                    "not intended to be legal advice and should not be relied upon as "
                    "such. Immigration laws can be complex and vary by jurisdiction. "
                    "For personalized guidance and to ensure your rights are protected, "
                    "please consult a qualified immigration attorney."
                )
                await context.bot.send_message(chat_id=update.effective_chat.id, text=disclaimer_text)
                context.user_data[f"disclaimer_sent_{user_id}"] = True

def main():
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(ChatMemberHandler(handle_new_follower, ChatMemberHandler.MY_CHAT_MEMBER))

    # Start the bot
    print("Starting bot...")
    application.run_polling()

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables")
    else:
        main()