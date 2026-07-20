import json
from zoneinfo import ZoneInfo
from datetime import datetime

import httpx
import ssl
import anthropic
import random
import logging

def get_weather(location: str, unit: str = "celsius") -> dict:
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

def get_time(timezone: str) -> str:
    """Takes a timezone and returns the current time in said timezone"""
    time_in_zone = datetime.now(ZoneInfo(timezone))
    return time_in_zone.strftime("%Y-%m-%d %H:%M:%S %Z")

def init_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        filename="weather_service.log",
        filemode="w",
        format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    logging.getLogger("anthropic").setLevel(logging.DEBUG)

    logger = logging.getLogger("weather_service")
    logger.setLevel(logging.DEBUG)
    return logger

# TODO add support for other LLMs
def init_llm_client():
    ctx = ssl.create_default_context()
    ctx.load_default_certs()

    return anthropic.Anthropic(
        http_client=httpx.Client(verify=ctx)
    )

logger = init_logging()
client = init_llm_client()

# load tools
with open("resources/tools.json", "r") as t:
    tools = json.load(t)

# system prompt
with open("resources/system_prompt.txt", "r") as s:
    system_prompt = s.read()

claude_model = "claude-sonnet-5"
chat_content = []

while True:
    user_prompt = input("\nYou: ")
    if user_prompt.lower() in ("quit", "exit"):
        break

    chat_content.append({"role": "user", "content": user_prompt})

    max_turns = 5
    for turn in range(max_turns):
        message = client.messages.create(
            model=claude_model,
            max_tokens=1024,
            tools=tools,
            system=system_prompt,
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
