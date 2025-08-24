import asyncio
import json
import logging
import os
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from dotenv import load_dotenv

from src.test.prompt import PROMPT

load_dotenv()


logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('client.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai = AsyncOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.messages = []

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        logger.info("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query_loop(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        # 1. 初始化，将用户查询添加到消息历史
        self.messages.append({
            "role": "user",
            "content": query
        })

        final_text_parts = []

        # 获取可用的工具列表，这部分只需要在循环开始前执行一次
        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]
        logger.info("=========list_tools===========")
        logger.info("available_tools:", available_tools)

        # 2. 主循环
        while True:
            try:
                # 2a. 调用 LLM，发送完整的消息历史
                logger.info(f"==================> Calling LLM with messages: {self.messages}")
                response = await self.openai.chat.completions.create(
                    model="qwen-max",
                    max_tokens=2000,
                    messages=self.messages,
                    tools=available_tools,
                    parallel_tool_calls=True
                )
                assistant_message = response.choices[0].message
                logger.info(f"==================> LLM Response: {assistant_message}")

                # 2b. 处理 LLM 响应

                # 如果响应包含工具调用
                if assistant_message.tool_calls:

                    # 将助手的工具调用消息添加到历史
                    self.messages.append(assistant_message)

                    tool_results_texts = []
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                        # 执行工具调用
                        result = await self.session.call_tool(tool_name, tool_args)
                        tool_result_text = result.content[0].text
                        tool_results_texts.append(tool_result_text)

                        # 将工具执行结果添加到历史
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result_text
                        })

                    # 拼接并保存工具执行结果的文本，用于最终返回
                    final_text_parts.append(f"[Calling tool(s) and got results: {', '.join(tool_results_texts)}]")

                    # 重新进入循环，将新的消息历史发送给 LLM
                    continue  # 重新开始循环，处理下一个决策

                # 如果响应是最终答案（不包含工具调用）
                else:
                    step_content = assistant_message.content

                    # 如果模型返回了最终答案，将其添加到历史并退出
                    if step_content:
                        final_text_parts.append(step_content)
                        self.messages.append(assistant_message)
                    step_answer_key = "Step Answer:"
                    final_answer_key = "Final Answer:"

                    if step_answer_key in step_content:
                        index = step_content.find(step_answer_key)
                        if index != -1:
                            result = step_content[index + len(step_answer_key):]  # 取关键字之后的所有内容
                            logger.info("get_step_answer:", result.strip())  # .strip() 去除前后空白
                            continue
                        else:
                            logger.info(f"{step_answer_key} not found")

                    if final_answer_key in step_content:
                        index = step_content.find(final_answer_key)
                        if index != -1:
                            result = step_content[index + len(final_answer_key):]  # 取关键字之后的所有内容
                            logger.info("get_final_answer_key:", result.strip())  # .strip() 去除前后空白
                            break
                        else:
                            logger.info(f"{final_answer_key} not found")
                            break
                    logger.info("No more messages. Exiting loop.")
                    break  # 退出循环

            except Exception as e:
                logger.info(f"An error occurred in the loop: {e}")
                break  # 出现错误时也退出循环

        logger.info("[all messages]: ", self.messages)
        return "\n".join(final_text_parts)

    async def chat(self):
        logger.info("\nMCP Client Started!")
        logger.info("Type your queries or 'quit' to exit.")
        response = await self.process_query_loop(PROMPT)

        logger.info("\n[response]:\n" + response)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        logger.info("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())