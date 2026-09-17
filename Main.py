import gradio as gr
import subprocess
import sys
import os
import threading
import queue
import time

sys.setrecursionlimit(100)
MAINMODE = 0
output_queue = queue.Queue()
output_textbox = None
link_component = None
stop_flag = threading.Event()
processes = []  # 用于存储启动的子进程

def change_mode_and_restart(use_mode):
    global MAINMODE
    gr.Info("启动新的模式界面中，请稍等")
    gr.Info("点击新出现的链接后，刚开始加载不出来属于正常现象，等待五秒即可，稍后手动刷新")
    # 杀死所有子进程
    for process in processes:
        try:
            process.kill()
        except Exception as e:
            print(f"Error killing process {e}")
    processes.clear()  # 清空进程列表

    if use_mode == "自定义输入":
        MAINMODE = 1
    elif use_mode == "配置文件直接导入":
        MAINMODE = 2
    elif use_mode == "配置文件编辑":
        MAINMODE = 3
    elif use_mode == "快捷图片输入":
        MAINMODE = 4
    link = start_selected_mode()
    return link

def start_selected_mode():
    python = sys.executable
    # 获取当前脚本的绝对路径
    current_script_path = os.path.abspath(__file__)
    # 获取当前脚本所在的目录
    current_directory = os.path.dirname(current_script_path)
    script_name = ""
    if MAINMODE == 1:
        script_name = "CustomizeMode.py"
    elif MAINMODE == 2:
        script_name = "LoadjsonMode.py"
    elif MAINMODE == 3:
        script_name = "EditjsonMode.py"
    elif MAINMODE == 4:
        script_name = "ImageFunctions.py"

    script_path = os.path.join(current_directory, script_name)
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.Popen(
        [python, script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=child_env,
    )
    processes.append(process)  # 存储子进程

    # 启动一个线程来读取子进程的输出
    threading.Thread(target=read_process_output, args=(process,)).start()

    # 生成更新后的链接
    link = f"http://localhost:7861"
    return f'<a href="{link}" target="_blank">点击此链接前往最新模式界面进行设置</a>'

def read_process_output(process):
    for line in process.stdout:
        output_queue.put(line)
        # 打印子进程的输出到终端
        print(line.strip())
    process.wait()


with gr.Blocks(title="班级座位排列工具") as demo:
    gr.Info("工具页面启动成功")
    gr.Markdown("**欢迎使用班级座位排列工具** *Powered by Jiang*")
    gr.Markdown("此界面为主界面，可以在下方选择模式")
    use_mode_input = gr.Dropdown(choices=["自定义输入", "配置文件直接导入", "配置文件编辑", "快捷图片输入"], label="使用模式选择", value="自定义输入")
    gr.Markdown("**首次使用工具请选择自定义输入模式以了解基础设置项**")
    gr.Markdown("请注意，点击下方按钮更改模式后，之前创建的新模式界面将会改变。如果是启动程序后第一次点击，请忽略此提示")
    change_mode_button = gr.Button("确认更改模式")
    tip = gr.Markdown("请点击下方链接进入新的模式界面👇", visible=False)
    # 提前定义 link_component
    link_component = gr.Markdown(value="")
    change_mode_button.click(
        fn=change_mode_and_restart,
        inputs=[use_mode_input],
        outputs=[link_component]
    ).then(
        lambda: gr.update(visible=True),
        outputs=tip
    )
    # 启动定期更新线程
    update_thread = threading.Thread()
    update_thread.start()

    # 在 Gradio 关闭时停止更新线程和终止子进程
    def on_close():
        stop_flag.set()  # 设置停止标志
        # 终止所有子进程
        for process in processes:
            process.kill()

    demo.close(on_close)

if __name__ == "__main__":
    try:
        demo.launch(server_port=7860, share=True, pwa=True)
    except:
        raise ValueError("人脸工具启动失败，请确保 localhost:7860 未被占用")