import os
from .base_tool import BaseTool
from typing import Dict, Any
import logging # Add logging import
import re # Import re for text cleaning

# Attempt to import PyPDF2 and set a flag
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

logger = logging.getLogger(__name__) # Initialize logger for this module

# Define a base path for file operations, e.g., the current working directory or a specific 'workspace' subdirectory.
# This helps in sandboxing file access. For this example, we use os.getcwd().
# In a more secure application, this should be a strictly defined and controlled directory.
FILE_READ_BASE_PATH = os.getcwd() 
MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1MB limit for reading
MAX_CHARS_RETURN = 10000 # Increased slightly for potentially longer text extractions

def _clean_pdf_text(text: str) -> str:
    """Cleans extracted PDF text by normalizing whitespace."""
    if not text:
        return ""
    # Replace multiple spaces with a single space
    text = re.sub(r' +', ' ', text)
    # Replace multiple newlines with a single newline
    text = re.sub(r'\\n+', '\\n', text)
    # Remove leading/trailing whitespace from each line
    text = "\\n".join([line.strip() for line in text.split('\\n')])
    # Replace sequences of space-newline-space (often from column breaks or formatting) with a single space
    text = re.sub(r' \\n ', ' ', text)
    # Finally, strip leading/trailing whitespace from the whole text
    return text.strip()

class FileReaderTool(BaseTool):
    """A tool for reading content from files (text, PDF)."""

    @property
    def name(self) -> str:
        return "file_reader"

    @property
    def description(self) -> str:
        desc = f"Reads content from specified files. Supports plain text and PDF. Use 'file_path' for relative path. Max content returned: {MAX_CHARS_RETURN} chars."
        if not PYPDF2_AVAILABLE:
            desc += " (PDF support potentially limited or disabled due to missing PyPDF2 library)" # Slightly reworded
        logger.info(f"FileReaderTool initialized. PYPDF2_AVAILABLE: {PYPDF2_AVAILABLE}") # Log availability at init
        return desc

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The relative path to the file (e.g., 'docs/report.pdf', 'notes.txt'). Use 'file_path'."
                }
            },
            "required": ["file_path"]
        }

    def execute(self, file_path: str) -> str:
        logger.debug(f"FileReaderTool execute called for file_path: '{file_path}'") # Log entry
        logger.debug(f"PYPDF2_AVAILABLE at execution time: {PYPDF2_AVAILABLE}") # Log flag status

        if not file_path:
            return "Error: File path parameter is required."

        absolute_filepath = "" # Initialize to handle potential early exit
        try:
            absolute_filepath = os.path.abspath(os.path.join(FILE_READ_BASE_PATH, file_path))
            logger.debug(f"Absolute filepath resolved to: {absolute_filepath}")

            if not absolute_filepath.startswith(os.path.abspath(FILE_READ_BASE_PATH)):
                logger.warning(f"Access denied: '{absolute_filepath}' is outside base path '{FILE_READ_BASE_PATH}'.")
                return "Error: Access denied. Path is outside allowed directory."
            if ".." in file_path:
                logger.warning(f"Path traversal attempt: '..' in '{file_path}'.")
                return "Error: Path should not contain '..'."
        except Exception as e:
            logger.error(f"Error processing file_path '{file_path}': {e}", exc_info=True)
            return f"Error processing file_path '{file_path}': {str(e)}"

        if os.path.isabs(file_path):
            logger.warning(f"Absolute path rejected: '{file_path}'.")
            return "Error: Absolute file paths are not allowed."

        try:
            if not os.path.exists(absolute_filepath):
                logger.warning(f"File not found at '{absolute_filepath}' (from '{file_path}').")
                return f"Error: File not found at '{file_path}' (resolved: '{absolute_filepath}')"
            if not os.path.isfile(absolute_filepath):
                logger.warning(f"Path '{absolute_filepath}' is not a file.")
                return f"Error: Path '{file_path}' is not a file."

            if os.path.getsize(absolute_filepath) > MAX_FILE_SIZE_BYTES:
                logger.warning(f"File '{absolute_filepath}' too large.")
                return f"Error: File '{file_path}' too large (>{MAX_FILE_SIZE_BYTES / (1024*1024):.1f}MB)."

            file_extension = os.path.splitext(absolute_filepath)[1].lower()
            logger.debug(f"Determined file extension: '{file_extension}' for file: {absolute_filepath}")
            content = ""

            if file_extension == ".pdf":
                logger.debug("Attempting PDF processing path.")
                if not PYPDF2_AVAILABLE:
                    logger.warning("PyPDF2 not available, returning error for PDF.")
                    return "Error: Cannot read PDF. PyPDF2 library is not installed. Please install it (e.g., pip install PyPDF2)."
                try:
                    with open(absolute_filepath, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text_parts = []
                        for page_num in range(len(reader.pages)):
                            page = reader.pages[page_num]
                            extracted_text = page.extract_text()
                            if extracted_text:
                                text_parts.append(extracted_text)
                        raw_content = "\n".join(text_parts)
                        content = _clean_pdf_text(raw_content)
                    logger.info(f"Successfully extracted and cleaned text from PDF '{file_path}'. Original length: {len(raw_content)}, Cleaned length: {len(content)}")
                    if not content.strip():
                         logger.info(f"No text content extracted or remained after cleaning from PDF '{file_path}'. Might be image-based.")
                         return f"Info: PDF file '{file_path}' was read, but no text content could be extracted or remained after cleaning (it might be an image-based PDF or empty)."
                except PyPDF2.errors.PdfReadError as pe:
                     logger.error(f"PyPDF2 PdfReadError for '{file_path}': {pe}", exc_info=True)
                     return f"Error reading PDF '{file_path}': Invalid or corrupted PDF file. Details: {str(pe)}"
                except Exception as e:
                    logger.error(f"Generic error processing PDF file '{file_path}': {e}", exc_info=True)
                    return f"Error processing PDF file '{file_path}': {str(e)}"
            else: # Assume plain text for other files
                logger.debug(f"Attempting plain text processing path for '{file_path}'.")
                try:
                    with open(absolute_filepath, 'r', encoding='utf-8') as f:
                        content = f.read(MAX_CHARS_RETURN + 1)
                    logger.info(f"Successfully read text file '{file_path}'. Length: {len(content)}")
                except UnicodeDecodeError:
                    logger.warning(f"UnicodeDecodeError for '{file_path}'.")
                    return f"Error: Could not decode file '{file_path}' using UTF-8. It might be a binary file of an unsupported type or use a different encoding."
                except Exception as e:
                    logger.error(f"Error reading text file '{file_path}': {e}", exc_info=True)
                    return f"Error reading text file '{file_path}': {str(e)}"
            
            # Common truncation and empty content check for all successfully read types
            if len(content) > MAX_CHARS_RETURN:
                logger.info(f"Content from '{file_path}' truncated to {MAX_CHARS_RETURN} characters.")
                return content[:MAX_CHARS_RETURN] + f"\n... (file content truncated at {MAX_CHARS_RETURN} characters)"
            
            if not content.strip(): # Check after potential truncation
                 logger.info(f"File '{file_path}' resulted in no content after processing.")
                 return f"Info: File '{file_path}' is empty or contains no extractable/readable text content after processing."
            
            return content

        except FileNotFoundError:
            # This specific error is less likely now due to the os.path.exists check above,
            # but kept for robustness / unexpected scenarios.
            logger.warning(f"FileNotFoundError (unexpected) for '{file_path}'.")
            return f"Error: File not found at '{file_path}'."
        except PermissionError:
            logger.warning(f"PermissionError for '{file_path}'.")
            return f"Error: Permission denied for file '{file_path}'."
        except Exception as e:
            logger.error(f"Outer catch-all error reading file '{file_path}': {e}", exc_info=True)
            return f"Unexpected error reading file '{file_path}': {str(e)}" 