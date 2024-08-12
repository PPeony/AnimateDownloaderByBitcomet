# python使用bitcomet下载动漫
__操作系统为windows__
## TODO
1. 增加log的方式，记录日志到文件
2. 设置界面背景
3. 删除废弃代码

## V2.0
1. 增加了界面（ai辅助帮忙）
2. 旧的代码废弃
3. 界面可以编辑，可以修改搜索用的名字，当前的集数
4. 可以从界面配置下载目录
### 操作方式
1. 先点击start，从配置文件中读取值，默认配置文件位置在```D:\animate\db.txt```，开始获取链接，链接全部获取后，即表格中的每一行都变色了，表示此阶段完成。
![start](.\doc\pic\开始任务1.PNG)
浅绿色表示可以获取到链接，深绿色表示获取不到链接。

参考文件格式：第一个为动漫的real_name，横杠分隔；第二个为搜索用的名字，这个名字会用在url请求参数上，需要为3个字符以上；第三个名字是html页面中搜索出的文件名字，用于匹配，可以有多个，逗号分隔；最后一个是当前的集数，如果只有1位数，需要以0开头，比如01，02
```editorconfig
夜樱家的大作战-夜樱家-夜樱家,Yozakura-19
不时轻声地以俄语遮羞的邻座艾莉同学-俄语的-俄語,俄语,不时轻声地以俄语遮羞的邻座艾莉同学,不時輕聲地以俄語遮羞的鄰座艾琳同學-07
```
2. 之后会自动进入下一阶段，开始根据磁力链接调用bitcomet下载，下载完成后，该行会变成黄色，集数自动加一。
![download_done](.\doc\pic\下载完成.PNG)
3. 这之后需要点击move，move会把下载后的视频文件移动到指定文件夹中。移动成功后，该行会变蓝。
![moved](.\doc\pic\moved.PNG)
4. 最后一步，点击save，保存当前的集数。save已经是最后一步了，而且重复save不会有问题，所以这一步不会更新行的颜色。是否save成功可以查看console输出。下面提供一个样例输出：
```sql
read property success
Processing and updating data:
over
wait
start to check task
60 sec passed
wait for D:\animate\[Up to 21°C] Yozakura-san Chi no Daisakusen - 18 (ABEMA 1920x1080 AVC AAC MP4) [EA1A92B1].mp4.bc!
120 sec passed
wait for D:\animate\[Up to 21°C] Yozakura-san Chi no Daisakusen - 18 (ABEMA 1920x1080 AVC AAC MP4) [EA1A92B1].mp4.bc!
180 sec passed
wait for D:\animate\[Up to 21°C] Yozakura-san Chi no Daisakusen - 18 (ABEMA 1920x1080 AVC AAC MP4) [EA1A92B1].mp4.bc!
start to move animate
文件 [Up to 21°C] Yozakura-san Chi no Daisakusen - 18 (ABEMA 1920x1080 AVC AAC MP4) [EA1A92B1].mp4 移动成功！
save property success
Data saved!
```

## V1.0原理
1. 找到一个下载资源的网站
2. 根据python代码中的 ```animate_list``` 里面的值，爬虫找到所需动漫的磁力链接
3. 使用bitcomet命令行下载
4. 代码中没有使用数据库，用db.txt文件存储每次下载到了哪一集

## 注意
需要先手动打开bitcomet才能命令行下载