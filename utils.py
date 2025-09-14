import json
import os
import subprocess
import time
from threading import Thread
from typing import Any, Callable
import flet as ft

from flet.core.column import Column


def log(msg: str, log_area: Column):
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

    log_func("🚀 正在启动 AI 任务：python src/test/client.py src/test/server.py", log_area)

    # 启动 client.py 并传入 server.py 作为参数
    try:
        # 假设你在项目根目录运行，路径是相对于当前目录
        process = subprocess.Popen(
            ["python", "src/test/client.py", "src/test/server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd()  # 可选：确保工作目录正确
        )

        # 实时读取 stdout（可选：如果你想实时输出日志）
        def read_output():
            # 读取 stdout
            try:
                for line in process.stdout:
                    try:
                        text = line.decode("utf-8", errors="replace").strip()
                        log_func(f"📤 {text}", log_area)
                    except:
                        # 如果 UTF-8 失败，尝试 GBK（常见于中文 Windows）
                        try:
                            text = line.decode("gbk", errors="replace").strip()
                            log_func(f"📤 {text}", log_area)
                        except:
                            text = line.decode("latin1", errors="replace").strip()
                            log_func(f"📤 {text}", log_area)
            except Exception as e:
                log_func(f"❌ 读取 stdout 异常：{str(e)}", log_area)

            # 读取 stderr
            try:
                for line in process.stderr:
                    try:
                        text = line.decode("utf-8", errors="replace").strip()
                        log_func(f"❌ {text}", log_area)
                    except:
                        try:
                            text = line.decode("gbk", errors="replace").strip()
                            log_func(f"❌ {text}", log_area)
                        except:
                            text = line.decode("latin1", errors="replace").strip()
                            log_func(f"❌ {text}", log_area)
            except Exception as e:
                log_func(f"❌ 读取 stderr 异常：{str(e)}", log_area)

            process.wait()

        # 启动日志读取线程（非阻塞）
        Thread(target=read_output, daemon=True).start()

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
