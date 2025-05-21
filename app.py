import gradio as gr
from main import initialize_agent
import os
import logging
import shutil

# Configure logging for the Gradio app
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("app.log"),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__) # Use a logger specific to this module (app)

UPLOADS_DIR = "uploads" # Directory to store uploaded files

# Attempt to initialize the agent
logger.info("Gradio app attempting to initialize AI Agent...")
agent = initialize_agent() # Use the new initializer from main.py

if agent:
    logger.info("AI Agent initialized successfully for Gradio app.")
else:
    logger.error("AI Agent failed to initialize. Gradio app might not function correctly.")

# Ensure uploads directory exists
if not os.path.exists(UPLOADS_DIR):
    try:
        os.makedirs(UPLOADS_DIR)
        logger.info(f"Created directory: {UPLOADS_DIR}")
    except Exception as e:
        logger.error(f"Failed to create directory {UPLOADS_DIR}: {e}", exc_info=True)

def agent_chat_interface(message: str, history: list, uploaded_file_obj=None):
    logger.info(f"Gradio ChatInterface input. Message: '{message}', History: {history}, File: {uploaded_file_obj}")

    if agent is None:
        logger.error("Agent not initialized. Cannot process request.")
        # For ChatInterface, we should append to history or return a message string
        # For simplicity, let's just return an error message string that will be displayed.
        return "Error: Agent not initialized. Check logs."

    processed_input = message.strip() if message else ""
    
    if uploaded_file_obj:
        try:
            temp_file_path = uploaded_file_obj.name # .name gives the temp path for gr.File
            original_filename = os.path.basename(temp_file_path) 
            safe_filename = "".join(c for c in original_filename if c.isalnum() or c in ('.', '_', '-')).strip()
            if not safe_filename: safe_filename = "uploaded_file"
            
            destination_path = os.path.join(UPLOADS_DIR, safe_filename)
            shutil.copy(temp_file_path, destination_path)
            logger.info(f"File uploaded and saved to: {destination_path}")
            
            upload_info = f"(User uploaded file '{safe_filename}' to path '{destination_path}')"
            if processed_input:
                processed_input = f"{upload_info}\n{processed_input}"
            else:
                # If user just uploads a file without a message, create a default query for it.
                processed_input = f"{upload_info}\nWhat is in this file?"
            logger.info(f"Input to agent after file processing: {processed_input}")

        except Exception as e:
            logger.error(f"Error processing uploaded file '{uploaded_file_obj.name if uploaded_file_obj else 'N/A'}': {e}", exc_info=True)
            return f"Error processing uploaded file: {str(e)}"

    if not processed_input: 
        logger.warning("Empty input received (after potential file processing).")
        return "Please enter a query, or upload a file and optionally add a query."
    
    try:
        # The agent.process_request expects a single string input.
        # We don't use 'history' directly for the agent call here, as our agent is stateless per request.
        # The ChatInterface itself will manage displaying the history.
        response = agent.process_request(processed_input)
        logger.info(f"Agent response (first 100 chars): {str(response)[:100]}")
        return str(response)
    except Exception as e:
        logger.error(f"Error in agent.process_request: {e}", exc_info=True)
        return f"Sorry, an internal error occurred: {str(e)}"

# Using gr.ChatInterface
chat_ui = gr.ChatInterface(
    fn=agent_chat_interface,
    title="<img src='file/opsera_logo.png' alt='Opsera Logo' style='height:40px; margin-right:10px;'>AI Agent (Chat UI)",
    description=("Interact with the AI agent. Upload files using the button below the textbox. "
                 "The agent can use tools like a calculator, weather fetcher, and file reader."),
    additional_inputs=[
        gr.File(label="Upload File (Optional)", type="filepath")
    ],
    # examples are structured differently for ChatInterface, typically as a list of messages for history
    # For simplicity with file uploads, we might omit direct examples here or provide text-only ones.
    examples=[
        ["What is 15 * 24 / 3?"],
        ["What's the weather in New York?"],
        ["Read the README.md file"] # User would need to place README.md for agent to find or upload it.
    ],
    theme=gr.themes.Default(neutral_hue=gr.themes.colors.slate),
    # For Gradio 4.19.1, use allow_flagging. If you upgrade Gradio, switch to flagging_options.
    # allow_flagging="never" # Removing this as it might cause issues with newer Gradio versions
)

if __name__ == "__main__":
    if agent is not None:
        logger.info("Starting Gradio ChatInterface...")
        chat_ui.launch()
    else:
        logger.error("Agent not initialized. Gradio interface will not start.")
        print("CRITICAL: AI Agent could not be initialized. Gradio application cannot start.") 