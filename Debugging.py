import os
import datetime
import numpy as np

def debug(structure, name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 确保文件所在的目录存在
    file_path = current_dir+'\\Debug.txt'
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # 打开文件并写入数据类型
    try:
        with open(file_path, 'a', encoding='utf-8') as file:
            data_type = str(type(structure))
            file.write('\n')
            file.write('Debug to '+str(name)+'\n')
            file.write(data_type+'\n')
            file.write(str(structure)+'\n')
        print(f"数据类型已成功保存到 {file_path}")
    except Exception as e:
        print(f"保存数据类型时出现错误 {e}")

# 日志打印
def log_record(state, seating_arrangement, other_info):
    # 处理seating_arrangement，如果不是列表，尝试转换
    if isinstance(seating_arrangement, np.ndarray):
        seating_arrangement = seating_arrangement.tolist()

    # 获取当前脚本的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取当前时间
    now = datetime.datetime.now()
    # 格式化日期和时间为字符串
    timestamp = now.strftime("%Y%m%dd%Hh%Mm%Ss")

    # 创建logs文件夹（如果不存在）
    log_folder = os.path.join(script_dir, 'logs')
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    # 构建日志文件路径
    log_file_name = f"log_{timestamp}.log"
    log_file_path = os.path.join(log_folder, log_file_name)

    timestamp = now.strftime("%Y.%m.%d - %H:%M:%S")

    # 准备日志内容
    log_content = f"[Generate Time]\n{timestamp}\n\n"
    log_content += f"[State]\n{state}\n\n"
    log_content += "[Result]\n[\n"
    for row in seating_arrangement:
        log_content += f"   {row},\n"
    log_content += f"]\n\n[Other Info]\n{other_info}\n"

    # 写入日志文件
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write(log_content)

    return log_file_path