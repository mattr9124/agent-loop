import json
import asyncio
import os.path

import httpx
import ssl
import anthropic
import logging

from aiohttp import ClientSession
from mcp import ClientSession, stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from contextlib import AsyncExitStack
from zoneinfo import ZoneInfo
from datetime import datetime


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

async def agent_loop(all_sessions: dict[str, ClientSession], tools: dict):
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
                    elif block.name in all_sessions:
                        result = await all_sessions[block.name].call_tool(block.name, block.input)
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

def load_json_file(file_path: str):
    with open(file_path, "r") as json_file:
        return json.load(json_file)

# load tools
TOOLS = load_json_file("resources/tools-no-weather.json")
# load MCPs
MCP_SERVERS = load_json_file("resources/mcp.json")

# system prompt
with open("resources/system_prompt.txt", "r") as s:
    system_prompt = s.read()

async def main():
    async with AsyncExitStack() as stack:
        # all_mcp_tools = []
        tool_to_session: dict[str, ClientSession] = {}

        for mcp_server in MCP_SERVERS:
            if mcp_server["type"] == "http":
                logger.debug(f"Adding http tool {mcp_server["name"]}")
                r, w, _ = await stack.enter_async_context(streamable_http_client(mcp_server["url"]))
            elif mcp_server["type"] == "stdio":
                logger.debug(f"Adding stdio tool {mcp_server["name"]}")
                server_args = [os.path.expandvars(a) for a in mcp_server["args"]]
                params = StdioServerParameters(command=mcp_server["command"], args = server_args)
                r, w = await stack.enter_async_context(stdio_client(params))
            else:
                continue

            session = await stack.enter_async_context(ClientSession(r, w))
            await session.initialize()

            mcp_tools = await session.list_tools()

            for t in mcp_tools.tools:
                tool_to_session[t.name] = session
                TOOLS.append({"name": t.name, "description": t.description, "input_schema": t.inputSchema})

        logger.debug(f"MCP TOOLS FOUND: {list(tool_to_session.keys())}")
        await agent_loop(tool_to_session, TOOLS)

asyncio.run(main())