import asyncio
import json
import os
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env


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
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = self.messages.copy()  # 避免直接操作原列表
        messages.append({
            "role": "user",
            "content": query
        })

        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]
        print("=========list_tools===========")
        print("available_tools:", available_tools)

        # Initial Claude API call
        response = await self.openai.chat.completions.create(
            # model="gpt-4o-mini",
            model="qwen-max",
            # max_tokens=1000,
            messages=messages,
            tools=available_tools,
            parallel_tool_calls=True
        )
        print("response:", response)
        # Process response and handle tool calls
        tool_results = []
        final_text = []

        assistant_message = response.choices[0].message

        cnt = 0
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                print(f">>>>>>>>>>>>>>loop{cnt}")
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                tool_result_text = result.content[0].text
                tool_results.append({"call": tool_name, "result": tool_result_text})
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                final_text.append(f"Tool result: {tool_result_text}")

                # ✅ 将工具调用和结果添加到消息历史
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result_text
                })

                print(f"Tool {tool_name} returned: {result}")
                print("messages", messages)
                # Get next response from OpenAI
                completion = await self.openai.chat.completions.create(
                    model="qwen-max",
                    # max_tokens=1000,
                    # model="gpt-4o-mini",
                    messages=messages,
                )
                print("completion", completion)
                if isinstance(completion.choices[0].message.content, (dict, list)):
                    final_text.append(str(completion.choices[0].message.content))
                else:
                    final_text.append(completion.choices[0].message.content)

        else:
            if isinstance(assistant_message.content, (dict, list)):
                final_text.append(str(assistant_message.content))
            else:
                final_text.append(assistant_message.content)

        self.messages.append({
            "role": "user",
            "content": query
        })
        self.messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": assistant_message.tool_calls
        })

        for tool_call in (assistant_message.tool_calls or []):
            tool_result = next((r for r in tool_results if r["call"] == tool_call.function.name), None)
            if tool_result:
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result["result"]
                })
                # 注意：这里假设 tool_call.id 是由 OpenAI 生成的，实际中可能需要映射
                # 若不一致，建议手动维护 call_id 映射表

            # 最终模型回复（如果有）
        if assistant_message.tool_calls:
            final_content = completion.choices[0].message.content
            self.messages.append({
                "role": "assistant",
                "content": final_content
            })

        print("====>current message: ", self.messages)

        return "\n".join(final_text)

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
        print("=========list_tools===========")
        print("available_tools:", available_tools)

        # 2. 主循环
        while True:
            try:
                # 2a. 调用 LLM，发送完整的消息历史
                print(f"==================> Calling LLM with messages: {self.messages}")
                response = await self.openai.chat.completions.create(
                    model="qwen-max",
                    # model="gpt-4o-mini",
                    # max_tokens=1000,
                    messages=self.messages,
                    tools=available_tools,
                    parallel_tool_calls=True
                )
                assistant_message = response.choices[0].message
                print(f"==================> LLM Response: {assistant_message}")

                # 2b. 处理 LLM 响应

                # 如果响应包含工具调用
                if assistant_message.tool_calls:

                    # 将助手的工具调用消息添加到历史
                    self.messages.append(assistant_message)

                    tool_results_texts = []
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        print(f"Executing tool: {tool_name} with args: {tool_args}")

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
                    final_content = assistant_message.content

                    # 如果模型返回了最终答案，将其添加到历史并退出
                    if final_content:
                        final_text_parts.append(final_content)
                        self.messages.append(assistant_message)

                    print("No more tool calls. Exiting loop.")
                    break  # 退出循环

            except Exception as e:
                print(f"An error occurred in the loop: {e}")
                break  # 出现错误时也退出循环

        return "\n".join(final_text_parts)
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                # 调用工具，获取网页中的磁力链接链接，https://www.comicat.org/search.php?keyword=NUKITASHI，磁力后缀拼在href属性里面，在show后面的字段就是磁力后缀，你只需要返回第一个单元格的完整磁力链接
                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n:response:\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")


    async def chat(self):
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        response = await self.process_query("你必须用工具完成以下几个事情。"
                                            "1. 读取配置文件，位置在D:\\animate\\animate_storage.json."
                                            "2. 第一步会得到一个json数组，你需要在网页上面搜索json数组中每个元素的磁力链接。"
                                            "链接你需要进行拼接，https://www.comicat.org/search.php?keyword={search_name} "
                                            "search_name就是第一步读取的配置文件里面的search_name。"
                                            "工具会返回页面上的部分html信息，磁力链接信息在href属性里面，在show后面的字段就是磁力后缀。"
                                            "这个是调用函数所需要的请求头："
                                            "headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36','Cookie': 'visitor_test=human', }"
                                            "注意原始的配置文件里面还包含chapter，这个是视频的集数，在搜索网页磁力链接的时候，要下载正确的集数。如果没有对应的磁力链接，在最终结果中要展示出来。"
                                            "配置文件里面有多个元素，所以这个步骤你需要调用工具循环多次。"
                                            "你需要记录最后成功找到磁力链接的视频的名字，和他的磁力链接。如果没有找到磁力链接，那填空就可以。"
                                            "你需要生成一个json，类似{name:'xxx',magnet: 'xxx', chapter:'xxx'}，最后结果是一个json数组"
                                            "3. 根据我们上一步拿到的磁力链接，调用bitcomet工具，下载文件。这一步你也需要循环调用工具多次，一次调用工具只能下载一个文件。"
                                            "4. 调用工具，扫描 D:\\animate 文件夹，查看是否有新增的bitcomet下载文件。"
                                            "这个下载文件的文件名字前半部分应该类似于我们刚才获取到的文件的文件名。"
                                            "新增的下载文件的文件名以.bc!为结尾。注意名字和集数都要匹配。如果有的话，你需要返回这个文件夹的完整路径。"
                                            "这一步只需要调用一次工具，工具会返回文件夹内所有的文件内容。"
                                            "最终你需要生成的json需要包含下载中的文件路径。格式类似下面"
                                            " Answer:[{\"name\":\"xxx\",\"magnet\": \"xxx\", \"chapter\":\"xxx\",\"path\":\"xxx\"},"
                                            "{\"name\":\"xxx2\",\"magnet\": \"xxx2\", \"chapter\":\"xxx2\",\"path\":\"xxx2\"}]"
                                            "注意最终你需要返回的只有上述结构。即 Answer:json数组。不要返回多余字符串。")

        print("\n:response:\n" + response)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        # await client.chat_loop()
        await client.chat()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())