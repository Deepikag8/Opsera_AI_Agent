import os
import requests
from .base_tool import BaseTool
from typing import Dict, Any
import json

# Define the API URL directly or get from environment
WEATHER_API_BASE_URL = os.getenv("WEATHER_API_URL", "http://api.openweathermap.org/data/2.5/weather")

class WeatherFetcherTool(BaseTool):
    """A tool for fetching current weather information."""

    @property
    def name(self) -> str:
        return "weather_fetcher"

    @property
    def description(self) -> str:
        return "Fetches the current weather for a specific city. Provide the full city name (e.g., 'New Delhi', 'London', 'Washington D.C.'). Avoid abbreviations (like 'DC') or state/country names as they may not be recognized or may yield unintended results. The tool uses the WEATHER_API_KEY from the environment. Only provide the 'city' parameter."

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name to fetch weather for (e.g., London,UK)."
                }
            },
            "required": ["city"]
        }

    def execute(self, city: str) -> str:
        api_key = os.getenv("WEATHER_API_KEY")

        if not city:
            return "Error: City parameter is required."
        if not api_key:
            return "Error: WEATHER_API_KEY is not set in the environment. This tool cannot function."

        params = {
            'q': city,
            'appid': api_key,
            'units': 'metric'
        }

        try:
            response = requests.get(WEATHER_API_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if str(data.get("cod")) != "200":
                return f"Error fetching weather for {city}: {data.get('message', 'Unknown error from API')}"

            main_weather = data.get('weather', [{}])[0].get('main', 'N/A')
            description = data.get('weather', [{}])[0].get('description', 'N/A')
            temp = data.get('main', {}).get('temp', 'N/A')
            feels_like = data.get('main', {}).get('feels_like', 'N/A')
            humidity = data.get('main', {}).get('humidity', 'N/A')
            wind_speed = data.get('wind', {}).get('speed', 'N/A')

            return (
                f"Current weather in {data.get('name', city)}:\n"
                f"- Condition: {main_weather} ({description})\n"
                f"- Temperature: {temp}°C (Feels like: {feels_like}°C)\n"
                f"- Humidity: {humidity}%\n"
                f"- Wind Speed: {wind_speed} m/s"
            )

        except requests.exceptions.HTTPError as http_err:
            error_message = f"HTTP error fetching weather for {city}: {http_err}. Response: {response.text}"
            if response.status_code == 401:
                error_message += " (This often indicates an invalid or missing API key)"
            return error_message
        except requests.exceptions.RequestException as e:
            return f"Network error connecting to weather service for {city}: {str(e)}"
        except json.JSONDecodeError:
            return f"Error: Could not parse weather data response for {city}. Raw response: {response.text if 'response' in locals() else 'No response object'}"
        except Exception as e:
            return f"An unexpected error occurred while fetching weather for {city}: {str(e)}" 