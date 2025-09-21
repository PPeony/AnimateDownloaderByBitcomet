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

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('viwer2.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

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
        Thread(target=start_server_and_wait_for_result, args=(page, call_ai_btn), daemon=True).start()

    except Exception as ex:
        log_func(f"❌ 启动 AI 任务失败：{str(ex)}", log_area)
        call_ai_btn.disabled = False
        call_ai_btn.text = "Call AI"
        call_ai_btn.icon = ft.Icons.ROCKET_LAUNCH
        call_ai_btn.update()
        return

    # 启动监控 result.json 的线程
    def monitor_result_file():
        result_path = "result.json"
        timeout = 300  # 最多等待 300 秒
        interval = 1
        elapsed = 0

        while elapsed < timeout:
            time.sleep(interval)
            elapsed += interval

            if os.path.exists(result_path) and os.path.getsize(result_path) > 0:
                try:
                    with open(result_path, "r", encoding="utf-8") as f:
                        result_data = json.load(f)
                    log_func("✅ AI 返回结果已获取", log_area)
                    log_func(f"🔍 结果：{json.dumps(result_data, ensure_ascii=False, indent=2)}", log_area)

                    # 删除文件
                    os.remove(result_path)
                    log_func("🗑️ result.json 已删除", log_area)

                except Exception as e:
                    log_func(f"❌ 读取 result.json 失败：{str(e)}", log_area)
                finally:
                    break
        else:
            log_func("⏰ AI 任务超时，未生成 result.json", log_area)

        # 恢复按钮
        def reset_button():
            call_ai_btn.disabled = False
            call_ai_btn.text = "Call AI"
            call_ai_btn.icon = ft.Icons.ROCKET_LAUNCH
            call_ai_btn.update()

        page.run_thread(reset_button)

    # 启动监控线程
    Thread(target=monitor_result_file, daemon=True).start()

def start_server_and_wait_for_result(
        page: Any,
        call_ai_btn: Any,
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

    threading.Thread(target=start_socket, daemon=True).start()

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

def start_socket():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((SOCKET_HOST, SOCKET_PORT))
        s.listen(1)
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
                        print("✅ 主程序A：成功收到B返回的JSON数据：", result)
                    except json.JSONDecodeError as e:
                        print("❌ 主程序A：JSON解析失败：", e)
        except Exception as e:
            print("❌ 主程序A：接收数据时出错：", e)