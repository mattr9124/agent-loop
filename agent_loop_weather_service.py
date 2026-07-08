from zoneinfo import ZoneInfo
from datetime import datetime

import anthropic
import random
import logging

def get_weather(location: str, unit: str) -> dict:
    """Mock weather service..."""

    # Simulated weather conditions
    conditions = random.choice(["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Thunderstorm", "Snowy"])
    humidity = random.randint(20, 95)
    wind_speed = random.randint(3, 45)

    temp_c = random.randint(-5, 35)

    temp = temp_c if unit == "celsius" else convert_c_to_f(temp_c)

    return {
        "location": location,
        "temperature": temp,
        "unit": unit,
        "conditions": conditions,
        "humidity": humidity,
        "wind_speed_kmh": wind_speed
    }


def convert_c_to_f(temp_c: int) -> int:
    """converts Celcius temperature to Fahrenheit"""
    return round(temp_c * (9 / 5) + 32)


client = anthropic.Anthropic()


def get_time(timezone: str) -> str:
    """Takes a timezone and returns the current time in said timezone"""
    time_in_zone = datetime.now(ZoneInfo(timezone))
    return time_in_zone.strftime("%Y-%m-%d %H:%M:%S %Z")


tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, i.e. St. Louis, MO"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The temperature unit to use"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_time",
        "description": "Gets the current time in a given location",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "A timezone such as GMT-5 or CET, it should be in a format "
                                   "that python's ZoneInfo would accept, like Europe/Paris "
                                   "or Asia/Tokyo"
                }
            }
        }
    }
]

logging.basicConfig(level=logging.INFO)

# Turn on debug just for the anthropic SDK
logging.getLogger("anthropic").setLevel(logging.DEBUG)
logger = logging.getLogger("my_thingy")
logger.setLevel(logging.DEBUG)

claude_model = "claude-haiku-4-5-20251001"

user_prompt = input("How can I help you today? ")

chat_content = [{
    "role": "user",
    "content": user_prompt
    # "content": "What's the weather like in Paris? "
    #            "What time is it over there?"
}]

max_turns = 5
for turn in range(max_turns):
    message = client.messages.create(
        model=claude_model,
        max_tokens=1024,
        tools=tools,
        system="If unit is not specified use celsius as a unit",
        messages=chat_content
    )

    logger.debug(message.content)
    chat_content.append({"role": "assistant", "content": message.content})

    if message.stop_reason == "end_turn":
        for block in message.content:
            if block.type == "text":
                print(f"\n{block.text}")
        break

    tool_results = []
    for block in message.content:
        if block.type == "tool_use":
            if block.name == "get_weather":
                result = get_weather(**block.input)
            elif block.name == "get_time":
                result = get_time(**block.input)
            else:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Unknown tool: {block.name}",
                    "is_error": True
                })
                continue

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result)
            })
        elif block.type == "text":
            print(f"Text: {block.text}")

    logger.debug(tool_results)
    chat_content.append({"role": "user", "content": tool_results})
