import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from threading import Thread
from typing import Any, Callable
import flet as ft

from flet.core.column import Column

from loader import move_file, move_file_src_to_dest

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('viwer2.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)
gb_download_result = r"""
[
    {
        "name": "碧蓝之海",
        "magnet": "magnet:?xt=urn:btih:96662e0353c653b52dfd6a2f16b35618793da806",
        "chapter": 12,
        "path": "D:\\animate\\[MoezakuraSub]Grand Blue S2[12][WebRip][HEVC_DDP][CHS_JP&CHT_JP].mkv.bc!",
        "download_failed_reason_type": 0,
        "download_failed_reason_detail": ""
    },
    {
        "name": "沉默魔女的秘密",
        "magnet": "",
        "chapter": 12,
        "path": "",
        "download_failed_reason_type": 0,
        "download_failed_reason_detail": ""
    }
]
"""

SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 50007


def mylog(msg: str, log_area: Column):
    log_entry = ft.Text(f"[{time.strftime('%H:%M:%S')}] {msg}", expand=True)
    log_area.controls.append(log_entry)
    log_area.update()


def call_ai(
        page: Any,
        log_func: Callable[[str, Column], None],
        call_ai_btn: Any,
        log_area: Column,
):
    call_ai_btn.disabled = True
    call_ai_btn.text = "AI 调用中..."
    call_ai_btn.icon = ft.Icons.HOURGLASS_EMPTY
    call_ai_btn.update()

    log_func(r"🚀 正在启动 AI 任务：python C:\coding\project\deer-flow\test.py", log_area)

    # 启动 client.py 并传入 server.py 作为参数
    try:
        Thread(target=start_server_and_wait_for_result, args=(page, call_ai_btn, log_area), daemon=True).start()

    except Exception as ex:
        log_func(f"❌ 启动 AI 任务失败：{str(ex)}", log_area)
        call_ai_btn.disabled = False
        call_ai_btn.text = "Call AI"
        call_ai_btn.icon = ft.Icons.ROCKET_LAUNCH
        call_ai_btn.update()
        return


def start_server_and_wait_for_result(
        page: Any,
        call_ai_btn: Any,
        log_area: Column,
):
    # 先启动 B 程序作为子进程
    print("主程序A：启动子程序B...")
    print("Python 执行路径:", sys.executable)
    proc = subprocess.Popen(
        [sys.executable, "-u", r'C:\coding\project\deer-flow\test.py', SOCKET_HOST, str(SOCKET_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # 合并错误输出
        cwd=r'C:\coding\project\deer-flow',
        text=True,  # 直接输出字符串
        bufsize=1,  # 行缓冲
        encoding='utf-8',
        errors="replace",
    )

    threading.Thread(target=start_socket, daemon=True, args=(log_area)).start()

    for line in proc.stdout:
        line = line.rstrip()
        logger.info(f"[Call-AI] {line}")  # 带标签写入 A 的日志

    proc.wait()  # 等待结束

    print("call end1")
    # 等待子进程结束
    stdout, stderr = proc.communicate(timeout=5)
    if proc.returncode != 0:
        print("❌ 子程序B运行出错：", stderr.decode())

    print("call restore_button")
    call_ai_btn.disabled = False
    call_ai_btn.text = "Call AI"
    call_ai_btn.icon = ft.Icons.ROCKET_LAUNCH
    page.update()  # 安全更新 UI


def start_socket(
        log_area: Column
):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((SOCKET_HOST, SOCKET_PORT))
        s.listen(1)
        mylog(f"主程序A：已监听 {SOCKET_HOST}:{SOCKET_PORT}，等待B返回结果...", log_area)
        print(f"主程序A：已监听 {SOCKET_HOST}:{SOCKET_PORT}，等待B返回结果...")

        try:
            conn, addr = s.accept()
            with conn:
                print(f"主程序A：收到B的连接 {addr}")
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk

                if data:
                    try:
                        print("✅ 主程序A：成功收到B返回的数据：", data.decode('utf-8'))
                        result = json.loads(data.decode('utf-8'))
                        global gb_download_result
                        print("✅ 主程序A：成功收到B返回的JSON数据：", result)
                        mylog(f"✅ 主程序A：成功收到B返回的JSON数据：{result}", log_area)
                        gb_download_result = result
                    except json.JSONDecodeError as e:
                        print("❌ 主程序A：JSON解析失败：", e)
                        mylog(f"❌ 主程序A：JSON解析失败：{e}", log_area)
        except Exception as e:
            print("❌ 主程序A：接收数据时出错：", e)
            mylog(f"❌ 主程序A：接收数据时出错：{e}", log_area)


def update_row_status(datatable, rows, name: str, status: str, color: str):
    for row in rows:
        if row.cells[0].content.value == name:
            row.color = color
            row.cells[5].content.value = status
            row.cells[5].content.color = "white" if color else "black"
            break
    datatable.update()


def handle_res(
    config_path: str,
    new_json: str,
    datatable,
    rows,
    log_area: Column
):
    source_dir = 'D:\\animate'
    with open(config_path, 'r', encoding='utf-8') as f:
        try:
            old_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"旧 JSON 文件格式错误: {e}")
    try:
        new_data = json.loads(new_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"新 JSON 字符串格式错误: {e}")
    # 构建新数据的 name 映射，便于快速查找
    new_name_map = {item['name']: item for item in new_data
                    if isinstance(item, dict)
                    and item.get('name')  # name 存在且非空
                    and item.get('download_failed_reason_type') == 0
                    and item.get('path') != ''
                    }
    updated_count = 0
    for item in old_data:
        if isinstance(item, dict) and 'name' in item and 'chapter' in item:
            name = item['name']
            if name in new_name_map:
                new_item = new_name_map[name]
                # 只有完成的才移动，并且集数+1
                path = new_item['path'].removesuffix('.bc!')
                if os.path.exists(path):
                    # 下载成功
                    move_file_src_to_dest(path, os.path.join(source_dir, name))
                    if isinstance(item['chapter'], (int, float)):
                        print('add')
                        item['chapter'] += 1
                        updated_count += 1
                        update_row_status(datatable, rows, name, "已移动", "green")
                        mylog(f"move {path}", log_area)
                    else:
                        print(f"警告: name='{item['name']}' 的 chapter 不是数字，跳过更新")
                else:
                    print(f"move {path} failed, download not finished")
                    mylog(f"move {path} failed, download not finished", log_area)
        # 如果旧数据中对象没有 name 或 chapter，直接跳过

    # 6. 写回文件
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(old_data, f, ensure_ascii=False, indent=2)