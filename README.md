# python使用bitcomet下载动漫
__操作系统为windows__
## 原理
1. 找到一个下载资源的网站
2. 根据python代码中的 ```animate_list``` 里面的值，爬虫找到所需动漫的磁力链接
3. 使用bitcomet命令行下载
4. 代码中没有使用数据库，用db.txt文件存储每次下载到了哪一集

## 注意
需要先手动打开bitcomet才能命令行下载