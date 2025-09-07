import asyncio
import json
import logging
import os
from typing import Optional
from contextlib import AsyncExitStack

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import OpenAI
from langgraph.prebuilt import create_react_agent
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from dotenv import load_dotenv

from src.test.prompt import PROMPT
from src.test.mytypes import State

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('client2.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

mcp_servers = {
    "animate": {
        "command": "python",
        "args": [r"D:\project\AnimateDownloaderByBitcomet\src\test\server.py"],
        "transport": "stdio",
    },
}


def create_agent(agent_name: str, tools: list, prompt_template: str):
    """Factory function to create agents with consistent configuration."""
    chat = ChatOpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    return create_react_agent(
        name=agent_name,
        model=chat,
        tools=tools,
        prompt=prompt_template,
    )


async def work(state: State, agent, agent_name: str):
    agent_input = ""
    result = await agent.ainvoke(
        input=agent_input, config={"recursion_limit": 3}
    )
    response_content = result["messages"][-1].content
    logger.debug(f"{agent_name.capitalize()} full response: {response_content}")
    return response_content


async def main():
    logger.info("=====start client=====")

    client = MultiServerMCPClient(mcp_servers)
    loaded_tools = []
    all_tools = await client.get_tools()
    for tool in all_tools:
        loaded_tools.append(tool)
    agent_type = ""
    prompt = r"You must use tool to get all files in the directory: D:\animate "
    agent = create_agent(agent_type, loaded_tools, prompt)
    state = None
    return await work(state, agent, agent_type)


if __name__ == "__main__":
    import sys

    asyncio.run(main())
