PROMPT = """
任务描述：

Reasoning：
我会根据你每一步调用工具的结果，整理出完整的结果发给你，你再进行下一步。

Action：
Step 1: 获取配置信息。配置文件位置在 D:\\animate\\animate_storage.json
Action: 调用工具，获取文件中的信息，文件里面是一个json字符串。
Reasoning: 这是第一步，你需要拿到文件里面的字符串后，才能进行第二步操作
Action Input: 配置文件的路径：D:\\animate\\animate_storage.json
Expected output: 预期输出使用下面的格式：
```
Step Answer: [json]
```

Step 2: 网络请求获取磁力链接
Action：通过第一步得到的json数组，对数组中每个元素，在网页上面搜索磁力链接。因此，这个tool你需要调用多次。搜寻的网页：https://www.comicat.org/search.php?keyword={search_name} 
search_name就是第一步读取的配置文件里面的search_name。
工具会返回页面上的部分html信息，磁力链接信息在href属性里面，在show后面的字段就是磁力后缀。链接你需要进行拼接磁力链接的前缀。
工具可能会截断网页，你需要从完整的标签中搜索需要的结果。
注意原始的配置文件里面还包含chapter，这个是视频的集数，在搜索网页磁力链接的时候，要下载正确的集数。如果没有对应的磁力链接，在最终结果中要展示出来。
注意：网页中有一列记录了文件大小，不要选择文件大小大于1GB的文件，除非只有这个文件。
你需要记录最后成功找到磁力链接的视频的名字，和他的磁力链接。如果没有找到磁力链接，那填空字符串就可以。
Reasoning：获取了磁力链接之后，下一步才能下载。
Action Input: 第一步的json数组中的每个元素的 search_name，和请求头{'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36','Cookie': 'visitor_test=human', }
Expected output: 你需要生成一个json，类似{name:'xxx',magnet: 'xxx', chapter:'xxx'}，最后结果是一个json数组,预期输出使用下面的格式：
```
Step Answer: [json]
```

Step 3: 调用bitcomet工具，下载文件
Action: 调用bitcomet工具，下载文件
Reasoning: 需要通过上一步获取到的磁力链接，下载文件
Action Input: 磁力链接
Expected output: 输出bitcomet命令是否调用成功，返回一个json数组
```
Step Answer: [json]
```

Step 3: 调用工具，扫描 D:\\animate 文件夹，查看是否有新增的bitcomet下载文件
Action: 调用工具，扫描 D:\\animate 文件夹，得到文件夹内的所有文件。这个下载文件的文件名字前半部分应该类似于我们Step2获取到的文件的文件名。
新增的下载文件的文件名以.bc!为结尾。注意名字和集数都要匹配。如果有的话，你需要返回这个文件夹的完整路径。
Reasoning: 得到文件夹中的内容后，通过比较step2的json数组，把文件路径填充到json中。
Action Input: 文件路径
Expected output: 返回填充后的json数组。下面是你的回答的形式。
```
Final Answer: [{\"name\":\"xxx\",\"magnet\": \"xxx\", \"chapter\":\"xxx\",\"path\":\"xxx\"},
{\"name\":\"xxx2\",\"magnet\": \"xxx2\", \"chapter\":\"xxx2\",\"path\":\"xxx2\"}]
```

"""

#
#
# To use a tool, please use the following format:
#
# ```
# Thought: Do I need to use a tool? Yes
# Action: the action to take, should be one of [{tool_names}]
# Action Input: the input to the action
# ```
#
# Then wait for Human will response to you the result of action by use Observation.
# ... (this Thought/Action/Action Input/Observation can repeat N times)
# You need to wait until you get them all.
# When one step over, you need to response to the human, use the format:
#
# ```
# Thought: Is this step over? Yes
# Step Answer: [your response here]
# ```
#
# When you have a response to say to the Human finally, or if you do not need to use a tool, you MUST use the format:
#
# ```
# Thought: Do I need to use a tool? No
# Final Answer: [your response here]
# ```
#
# Begin!