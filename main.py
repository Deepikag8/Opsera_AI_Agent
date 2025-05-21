import os
from typing import List, Dict, Any, Optional
from together import Together
from dotenv import load_dotenv
from tools.calculator import CalculatorTool
# from tools.opsera_search import OpseraSearchTool # Removed
from tools.file_reader import FileReaderTool
from tools.weather_fetcher import WeatherFetcherTool
import config # Use our simplified config
import logging
import inspect # Keep for debugging if needed
import json # ensure json is imported for response parsing
import re # ensure re is imported for response parsing


# Configure logging using values from config.py
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.INFO),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(config.LOG_FILE),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)

# Print Together Client path for debugging, right after imports
# logger.info(f"together.Together path: {inspect.getfile(Together)}") # This might be too verbose for normal runs

class AIAgent:
    """A simple AI agent that can use tools to help users, powered by Together AI."""
    
    def __init__(self):
        load_dotenv() # Ensures .env is loaded
        logger.info("Initializing AIAgent with Together AI...")
        
        # TOGETHER_API_KEY is expected to be in the environment variables
        # The Together client can pick it up automatically if TOGETHER_API_KEY is set.
        # Or, you can pass it explicitly: api_key=os.getenv("TOGETHER_API_KEY")
        if not os.getenv("TOGETHER_API_KEY"):
            logger.error("CRITICAL: TOGETHER_API_KEY not found in environment. Together AI client cannot be initialized.")
            raise ValueError("TOGETHER_API_KEY not set in environment. Please set it in your .env file for the agent to work.")

        try:
            self.client = Together() # Initialize Together client
            logger.info("Together AI client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Together AI client: {e}", exc_info=True)
            # If TOGETHER_API_KEY is not set, the above might not raise an error immediately
            # but calls will fail. It's good practice to check for the key.
            if not os.getenv("TOGETHER_API_KEY"): # This check is somewhat redundant due to the one above, but safe.
                logger.error("TOGETHER_API_KEY not found in environment. Together AI calls will fail.")
            raise # Re-raise the exception

        self.tools = {
            "calculator": CalculatorTool(),
            # "opsera_search": OpseraSearchTool(), # Removed
            "file_reader": FileReaderTool(),
            "weather_fetcher": WeatherFetcherTool()
        }
        logger.debug(f"Tools loaded: {list(self.tools.keys())}")
        
        self.system_message = {
            "role": "system",
            "content": '''You are a helpful AI assistant. You have access to several tools.
Based on the user's request, you need to decide which tool to use.
Respond ONLY with a valid JSON object with 'tool' and 'parameters' keys.
'tool' should be the name of the tool to use.
'parameters' should be an object with the arguments for the tool.
If no tool is appropriate, respond with 'tool': 'no_tool_needed'.
Available tools are: calculator, file_reader, weather_fetcher.'''
        }
        # The system message above is slightly simplified and more direct for JSON output.
        # It also primes the LLM about what to do if no tool is needed.
        logger.debug("AIAgent initialization complete.")
    
    def _get_tool_descriptions(self) -> str:
        """Get descriptions of all available tools."""
        descriptions = []
        for tool_name, tool_instance in self.tools.items():
            # Ensure name and description properties exist
            name = tool_instance.name
            desc = tool_instance.description
            descriptions.append(f"- {name}: {desc}")
        return "\n".join(descriptions)
    
    def _determine_tool(self, user_input: str) -> Dict[str, Any]:
        """Use Together AI to determine which tool to use and with what parameters."""
        logger.debug(f"Determining tool for user input with Together AI: {user_input}")
        tool_descs = self._get_tool_descriptions()
        
        # Constructing a more robust prompt for tool selection
        prompt_content = f'''Available tools:
{tool_descs}

User request: "{user_input}"

Which tool should be used to respond to this user request?
If a tool is appropriate, respond with a JSON object with "tool" and "parameters" keys.
The "tool" key should be one of [{', '.join(self.tools.keys())}].
The "parameters" key should be an object containing the arguments for the selected tool, based on its description and the user query.
If no tool is suitable for the user's request, respond with:
{{"tool": "no_tool_needed", "parameters": {{"original_query": "{user_input}"}}}}

Respond ONLY with the JSON object. Do not add any explanations or surrounding text.'''
        
        messages = [
            self.system_message, 
            {"role": "user", "content": prompt_content}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=config.TOGETHER_MODEL,
                messages=messages,
                temperature=config.LLM_TEMPERATURE,
                # Consider adding response_format if supported and reliable for your Together model
                # response_format={"type": "json_object"} # Example, syntax might vary
            )
            raw_response_content = response.choices[0].message.content
            logger.debug(f"Together AI LLM raw response for tool determination: {raw_response_content}")
            logger.info(f"[CRITICAL_DEBUG] Type of raw_response_content: {type(raw_response_content)}")
            logger.info(f"[CRITICAL_DEBUG] Value of raw_response_content (initial): >>>{raw_response_content}<<<")
            
            result = {}
            cleaned_response_for_parsing = raw_response_content # Start with the original raw content

            try:
                # Perform all cleaning steps on 'cleaned_response_for_parsing'
                cleaned_response_for_parsing = cleaned_response_for_parsing.strip()
                logger.info(f"[CRITICAL_DEBUG] Value after strip(): >>>{cleaned_response_for_parsing}<<<")
                
                # Markdown cleaning (be careful with this if LLM isn't adding markdown)
                if cleaned_response_for_parsing.startswith("```json"):
                    cleaned_response_for_parsing = cleaned_response_for_parsing[len("```json"):].strip()
                elif cleaned_response_for_parsing.startswith("```"):
                     cleaned_response_for_parsing = cleaned_response_for_parsing[len("```"):].strip()
                if cleaned_response_for_parsing.endswith("```"):
                    cleaned_response_for_parsing = cleaned_response_for_parsing[:-len("```")].strip()
                
                logger.info(f"[CRITICAL_DEBUG] Value of cleaned_response_for_parsing (after markdown clean): >>>{cleaned_response_for_parsing}<<<")
                
                # Direct parsing attempt
                result = json.loads(cleaned_response_for_parsing)

            except json.JSONDecodeError as je:
                # Log all relevant states at the point of failure
                logger.warning(f"JSON parsing failed on 'cleaned_response_for_parsing'. Error: {je}")
                logger.info(f"[CRITICAL_DEBUG_EXCEPTION] Value of cleaned_response_for_parsing at failure: >>>{cleaned_response_for_parsing}<<<")
                logger.info(f"[CRITICAL_DEBUG_EXCEPTION] Original raw_response_content at failure: >>>{raw_response_content}<<<") # Check if this is different
                
                # Fallback to regex on the *original* raw_response_content, just in case cleaning was the issue
                logger.info("Attempting fallback regex on original raw_response_content...")
                match_markdown_fallback = re.search(r"\{.*?\}", raw_response_content, re.DOTALL) # Use simpler regex on raw
                if match_markdown_fallback:
                    json_str_fallback = match_markdown_fallback.group(0)
                    logger.info(f"Fallback regex extracted: >>>{json_str_fallback}<<< trying to parse this.")
                    try:
                        result = json.loads(json_str_fallback)
                        logger.info("Fallback regex parsing successful!")
                    except json.JSONDecodeError as je_fallback:
                        logger.error(f"Fallback regex parsing also failed: {je_fallback}")
                        logger.error(f"Could not ultimately extract JSON. Original raw_response_content was: >>>{raw_response_content}<<<")
                        return {"tool": "error_parsing_llm_response", "parameters": {"details": "Could not parse JSON from LLM after cleaning and fallback.", "raw_content": raw_response_content}}
                else:
                    logger.error(f"Fallback regex found no JSON in original raw_response_content: >>>{raw_response_content}<<<")
                    return {"tool": "error_parsing_llm_response", "parameters": {"details": "Could not parse JSON from LLM, and fallback regex found nothing.", "raw_content": raw_response_content}}
            
            # Validate basic structure (if parsing succeeded)
            if not isinstance(result, dict) or "tool" not in result:
                logger.error(f"LLM response was not a valid JSON object with a 'tool' key. Parsed: {result}")
                return {"tool": "error_invalid_llm_response_structure", "parameters": {"details": "LLM response not a dict or missing 'tool' key.", "parsed_content": result}}


            logger.info(f"Together AI LLM determined tool: {result.get('tool')} with params: {result.get('parameters')}")
            return result
        except Exception as e:
            logger.error(f"Error in _determine_tool with client {type(self.client)}: {e}", exc_info=True)
            return {"tool": "error_in_tool_determination", "parameters": {"details": str(e)}}
    
    def process_request(self, user_input: str) -> str:
        logger.info(f"Processing user request: {user_input}")
        try:
            tool_selection = self._determine_tool(user_input)
            tool_name = tool_selection.get("tool")
            parameters = tool_selection.get("parameters", {}) # Default to empty dict

            if not isinstance(parameters, dict): # Ensure parameters is a dict
                logger.warning(f"LLM returned non-dict parameters: {parameters}. Defaulting to empty dict.")
                parameters = {}

            if tool_name in ["error_parsing_llm_response", "error_in_tool_determination", "error_invalid_llm_response_structure"]:
                error_details = parameters.get('details', 'Unknown error during tool determination.')
                logger.error(f"Tool determination failed: {tool_name}, Details: {error_details}")
                return f"Sorry, I had trouble deciding which tool to use. Details: {error_details}"
            
            if tool_name == "no_tool_needed" or not tool_name:
                logger.info(f"LLM determined no tool is needed or did not specify a tool for: '{user_input}'.")
                # You could potentially call another LLM here for a direct answer without tools.
                return "I've processed your request. No specific tool was needed, or I couldn't determine one. How else can I help?"

            if tool_name not in self.tools:
                logger.warning(f"Tool '{tool_name}' not found or not recognized by LLM (available: {list(self.tools.keys())}).")
                return f"Sorry, I don't know how to use the tool '{tool_name}' or it's not available."
            
            tool = self.tools[tool_name]
            logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            
            try:
                result = tool.execute(**parameters) # Pass parameters as keyword arguments
                logger.info(f"Tool {tool_name} executed. Result (first 100 chars): {str(result)[:100]}")
                return result # Return raw result
            except TypeError as te: 
                logger.error(f"TypeError executing tool {tool_name} with params {parameters}: {te}", exc_info=True)
                # Attempt to get expected parameters for a more helpful error message
                try:
                    sig = inspect.signature(tool.execute)
                    expected_params = list(sig.parameters.keys())
                    # Remove 'self' if it's a method
                    if 'self' in expected_params: expected_params.remove('self')
                    error_message = f"Error using tool {tool_name}: incorrect parameters. Expected: {expected_params}. Got: {list(parameters.keys())}. Details: {te}"
                except: # Fallback if introspection fails
                    error_message = f"Error using tool {tool_name}: incorrect parameters. Details: {te}"
                return error_message # Return the specific error message
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                return f"Sorry, an error occurred while using the {tool_name} tool: {e}"
            
        except Exception as e: # Catch-all for unexpected errors during request processing
            logger.error(f"An unexpected error occurred in process_request: {e}", exc_info=True)
            return f"An unexpected error occurred: {e}"

def initialize_agent() -> Optional[AIAgent]:
    """Initializes the AIAgent, handling potential errors during setup."""
    logger.info("Attempting to initialize AI Agent (Together AI)...")
    load_dotenv() 
    if not os.getenv("TOGETHER_API_KEY"):
        logger.error("CRITICAL: TOGETHER_API_KEY environment variable not set. Agent cannot start.")
        # This message will also be printed by the print statement in config.py if it's imported first.
        # Consider if you want duplicate console messages or manage it in one place.
        print("Error: TOGETHER_API_KEY not set. Please add it to your .env file.")
        return None
    try:
        agent = AIAgent()
        logger.info("AI Agent (Together AI) initialized successfully.")
        return agent
    except Exception as e:
        # The AIAgent __init__ now raises ValueError if key is missing, or re-raises other init errors.
        logger.error(f"Failed to initialize AI Agent (Together AI): {e}", exc_info=True)
        print(f"Error: Failed to initialize AI Agent: {e}. Check agent.log for details.")
        return None

def run_cli():
    """Runs the CLI for interacting with the AI agent."""
    agent = initialize_agent()
    if not agent:
        print("Failed to initialize the AI Agent. Exiting CLI.")
        return

    print("AI Agent CLI initialized. Type 'exit' or 'quit' to end.")
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting agent.")
                break
            if not user_input:
                continue
            
            response = agent.process_request(user_input)
            # Directly print the response, which is now the raw tool output or an error message
            print(response) 

        except EOFError: # Handle Ctrl+D
            print("\nExiting agent.")
            break
        except KeyboardInterrupt: # Handle Ctrl+C
            print("\nExiting agent.")
            break
        except Exception as e:
            logger.error(f"Unhandled exception in CLI loop: {e}", exc_info=True)
            print(f"An critical error occurred: {e}")

if __name__ == "__main__":
    run_cli() 