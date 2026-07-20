import json
from zoneinfo import ZoneInfo
from datetime import datetime

import asyncio
import httpx
import ssl
import anthropic

import logging

from aiohttp import ClientSession

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

async def agent_loop(session: ClientSession, tools: dict, mcp_tools):
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
                    # if block.name == "get_weather":
                    #     result = get_weather(**block.input)
                    if block.name == "get_time":
                        result = get_time(**block.input)
                    elif block.name in mcp_tools:
                        result = await session.call_tool(block.name, block.input)
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


logger = init_logging()
client = init_llm_client()

# load tools
with open("resources/tools-no-weather.json", "r") as t:
    tools = json.load(t)

# system prompt
with open("resources/system_prompt.txt", "r") as s:
    system_prompt = s.read()

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    # TODO externalize the URL
    url = "http://localhost:8080/mcp"
    async with streamable_http_client(url) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            mcpTools = await session.list_tools()
            logger.debug(f"MCP Tools from {url}")
            for tool in mcpTools.tools:
                logger.debug(f"{tool.name} - {tool.description}")
            tools.extend(
                {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
                for t in mcpTools.tools)
            mcp_tools = [t.name for t in mcpTools.tools]
            logger.debug(f"MCP TOOLS FOUND: {mcp_tools}")

            await agent_loop(session, tools, mcp_tools)

asyncio.run(main())