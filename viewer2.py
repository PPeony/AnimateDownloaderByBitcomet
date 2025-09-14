import flet as ft
from threading import Event
from dataclasses import dataclass
from typing import List, Dict
import json
import os
import time
from threading import Thread

from utils import log, call_ai


# https://flet.dev/docs/controls/view/

# 模拟 download 函数（你可以替换成真实的下载逻辑）
def download(config_list: List[Dict]) -> List[Dict]:
    """
    模拟下载函数，返回包含 magnet 和 path 的结果
    实际使用时替换为你的爬虫或下载逻辑
    """
    # 这里模拟返回你提供的结果（实际应调用你的下载器）
    mock_result = [
        {
            "name": "碧蓝之海",
            "magnet": "magnet:?xt=urn:btih:5e29ee41c7d3752c98e8f5c730394107b5176d39",
            "chapter": 7,
            "path": "D:\\animate\\【7月】碧蓝之海2 07.mp4.bc!"
        },
        {
            "name": "沉默魔女的秘密",
            "magnet": "magnet:?xt=urn:btih:9cb95e8e3b126f8ef553cf1decf1d5084c788bd9",
            "chapter": 6,
            "path": "D:\\animate\\[Haruhana] Silent Witch - Chinmoku no Majo no Kakushigoto - 06 [WebRip][HEVC-10bit 1080p][CHT_JPN].mkv.bc!"
        }
    ]
    # 模拟其中一个失败（可选）
    # mock_result[1]["magnet"] = ""
    return mock_result


# 全局变量：用于存储当前所有任务的监控状态
monitoring_tasks = {}


@dataclass
class AnimeTask:
    row: ft.DataRow
    timer: int = 0
    max_timer: int = 300  # 最多检查 300 秒
    interval: int = 1  # 每 60 秒检查一次
    stop_event: Event = None


def main(page: ft.Page):
    page.title = "自动下载管理器"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    window_width = 900
    window_height = 800

    page.window.width = window_width
    page.window.height = window_height
    page.scroll = ft.ScrollMode.AUTO
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    page.window.center()
    # 表格数据容器
    rows = []

    # 读取配置文件
    config_path = "D:\\animate\\animate_storage.json"  # 修改为你实际的路径
    if not os.path.exists(config_path):
        page.add(ft.Text(f"错误：未找到配置文件 {config_path}", color="red"))
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        page.add(ft.Text(f"读取配置文件失败：{str(e)}", color="red"))
        return

    # 创建表格
    datatable = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("名称")),
            ft.DataColumn(ft.Text("搜索名")),
            ft.DataColumn(ft.Text("章节")),
            ft.DataColumn(ft.Text("更新日")),
            ft.DataColumn(ft.Text("字幕组")),
            ft.DataColumn(ft.Text("状态")),
        ],
        rows=rows,
        # expand=True,
    )

    # 包装表格在容器中，可滚动
    table_container = ft.Container(
        content=ft.Column([datatable], scroll=ft.ScrollMode.AUTO),
        height=300,
        # expand=True,
    )

    # 加载配置数据到表格
    task_map = {}  # name -> config item
    for item in config_data:
        row = ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(item["name"])),
                ft.DataCell(ft.Text(item["search_name"])),
                ft.DataCell(ft.Text(str(item["chapter"]))),
                ft.DataCell(ft.Text(str(item["update_date"]))),
                ft.DataCell(ft.Text(item["fansub_name"] or "未知")),
                ft.DataCell(ft.Text("待下载", color="gray"), placeholder=True),
            ]
        )
        rows.append(row)
        task_map[item["name"]] = item

    # 下载按钮
    start_btn = ft.ElevatedButton("开始下载", icon=ft.Icons.PLAY_ARROW)
    call_ai_btn = ft.ElevatedButton("Call AI", icon=ft.Icons.ROCKET_LAUNCH, color=ft.Colors.DEEP_PURPLE)
    # 日志输出框
    log_area = ft.Column([], scroll=ft.ScrollMode.ALWAYS, height=100, width=500)

    # 更新某行的状态和颜色
    def update_row_status(name: str, status: str, color: str):
        for row in rows:
            if row.cells[0].content.value == name:
                row.color = color
                row.cells[5].content.value = status
                row.cells[5].content.color = "white" if color else "black"
                break
        datatable.update()

    # 监控单个文件是否下载完成
    def monitor_file(task: AnimeTask, file_path: str):
        def check_done():
            # 移除 .bc! 后缀后的路径
            clean_path = file_path[:-3] if file_path.endswith(".bc!") else None
            if not clean_path:
                return False
            return os.path.exists(clean_path) and not os.path.exists(file_path)

        while task.timer < task.max_timer and not task.stop_event.is_set():
            time.sleep(task.interval)
            task.timer += task.interval

            if check_done():
                # 下载完成
                page.run_thread(lambda n=task.row.cells[0].content.value: update_row_status(n, "下载完成", "green"))
                log(f"✅ {task.row.cells[0].content.value} 下载完成", log_area)
                break
        else:
            if not check_done():
                log(f"⏰ {task.row.cells[0].content.value} 下载超时或未完成", log_area)

        # 清理任务
        if task.row.cells[0].content.value in monitoring_tasks:
            del monitoring_tasks[task.row.cells[0].content.value]

    # 开始下载的处理函数
    def start_download(e):
        start_btn.disabled = True
        start_btn.text = "下载中..."
        start_btn.icon = ft.Icons.HOURGLASS_EMPTY
        start_btn.update()

        log("开始执行下载任务...")

        try:
            result = download(config_data)  # 调用你的下载函数
        except Exception as ex:
            log(f"❌ 下载函数出错：{str(ex)}", log_area)
            start_btn.disabled = False
            start_btn.text = "开始下载"
            start_btn.icon = ft.Icons.PLAY_ARROW
            start_btn.update()
            return

        log("下载请求已发出，正在处理结果...", log_area)

        # 处理返回结果，更新表格
        downloaded_paths = []
        for res in result:
            name = res["name"]
            magnet = res.get("magnet", "")
            path = res.get("path", "")

            if magnet and path:
                update_row_status(name, "下载中", "blue")
                log(f"📘 {name} 下载任务已启动", log_area)
                downloaded_paths.append(path)
            else:
                update_row_status(name, "下载失败", "yellow")
                log(f"❌ {name} 下载失败", log_area)

        # 启动监控线程
        for res in result:
            name = res["name"]
            path = res.get("path", "")
            magnet = res.get("magnet", "")

            if magnet and path and os.path.exists(path):  # 只监控存在的 .bc! 文件
                stop_event = Event()
                task = AnimeTask(row=None, stop_event=stop_event)
                for row in rows:
                    if row.cells[0].content.value == name:
                        task.row = row
                        break

                monitoring_tasks[name] = task
                Thread(target=monitor_file, args=(task, path), daemon=True).start()

        start_btn.disabled = True
        start_btn.update()

    start_btn.on_click = start_download

    # 页面布局
    page.add(
        ft.Text("AnimateDownloader", size=24, weight=ft.FontWeight.BOLD, ),
        ft.Divider(),
        table_container,
        ft.Divider(),
        ft.Row(
            [
                start_btn,
                call_ai_btn,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        ),
        ft.Divider(),
        ft.Text("运行日志", size=16, weight=ft.FontWeight.BOLD, ),
        log_area,
    )

    log("系统就绪，点击“开始下载”启动任务", log_area)

    # 绑定按钮事件
    call_ai_btn.on_click = lambda e: call_ai(
        page=page,
        log_func=log,
        call_ai_btn=call_ai_btn,
        log_area=log_area,
    )


# 启动应用
ft.app(target=main, view=ft.AppView.FLET_APP)
