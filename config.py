import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

"""Configuration settings for the AI agent."""

# LLM settings
# Ensure TOGETHER_API_KEY is loaded and available.
# The Together client in main.py will automatically pick up TOGETHER_API_KEY from the environment.
# You can set a default model here if you wish.
TOGETHER_MODEL = os.getenv("TOGETHER_MODEL", "mistralai/Mixtral-8x7B-Instruct-v0.1")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.7))

# Weather API Key (Example for a tool that might need a specific key)
# The WeatherFetcherTool itself should handle the API key logic (e.g., read from env).
# This is just an example if you wanted to centralize such a key here.
# WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")


# Generic Tool settings (if any)
# MAX_FILE_READ_SIZE = 4096 # Example

# Logging configuration (can also be set directly in main.py or app.py)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = "agent.log"

print(f"Config loaded: Model={TOGETHER_MODEL}, Temp={LLM_TEMPERATURE}, LogLevel={LOG_LEVEL}")
if not os.getenv("TOGETHER_API_KEY"):
    print("Warning: TOGETHER_API_KEY not found in .env file or environment variables. AI agent will not work.")