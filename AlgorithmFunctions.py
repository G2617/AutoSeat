import gradio as gr
import numpy as np
import pandas as pd
import time
import os
import datetime
import json
import tempfile
from PIL import Image
from Debugging import debug

STROKE_LESS_THAN_5 = '一二三四五上下出入人八几儿力刀又三干王亏士工土才寸下大丈与上小口巾千乞川个勺久凡夕么广亡门义之尸弓己已子也女飞刃叉乡井开夫天无元专木五厅不犬太尤巨止少日中内水见午手气长仁什片币斤爪反介父从今凶分乏公仓月氏勿欠风匀文六方火为斗计户认心尺丑巴办以允予劝双立书'
imported_json_file_path = None

# 预加载所有 JSON 文件
def load_json_files():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_folder = os.path.join(current_dir, 'jsons')
    if not os.path.exists(json_folder):
        os.makedirs(json_folder)
    json_files = [f for f in os.listdir(json_folder) if f.endswith('.json')]
    return json_files

# 导入 JSON 配置
def import_json_config(config_file):
    global imported_json_file_path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_folder = os.path.join(current_dir, 'jsons')
    file_path = os.path.join(json_folder, config_file)
    with open(file_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    num_students = config.get('num_students', 0)
    rows = config.get('rows', 0)
    cols = config.get('cols', 0)
    students_data = config.get('students_data', [])
    mode = config.get('mode', 0)
    teams = config.get('teams', [])
    sorts = config.get('sorts', [])
    groups = config.get('groups', [])
    reserved_seats = config.get('reserved_seats', {})
    enable_optimization = bool(config.get('enable_optimization', False))
    gr.Info("配置文件导入成功，请等待")
    imported_json_file_path = file_path
    time.sleep(3)
    return num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats

# 导入 JSON 配置
def fill_json_config(num_students_input, rows_input, cols_input, students_data_output, optimization_input, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output):
    if mode_output == 0:
        mode_input = "离散模式"
    elif mode_output == 1:
        mode_input = "小组聚集模式"
    else:
        mode_output = None

    sorts = sorts_output
    reservations = reserved_seats_output
    students_text_input = ""
    for sub_list in students_data_output:
        id, name, hight = sub_list
        students_text_input += str(id) + ' ' + str(name) + ' ' + str(hight) + '\n'
    students_text_input=students_text_input[:-1]
    target_teams_text_input = ""
    group_text_input = ""
    if mode_output == 0 or mode_output == 1:
        if mode_output == 1:
            for sublist in teams_output:
                for name in sublist:
                    target_teams_text_input += str(name) + ' '
                target_teams_text_input = target_teams_text_input[:-1]
                target_teams_text_input += '\n'
            target_teams_text_input = target_teams_text_input[:-1]
        for sublist in groups_output:
            for name in sublist:
                group_text_input += str(name) + ' '
            group_text_input = group_text_input[:-1]
            group_text_input += '\n'
        group_text_input = group_text_input[:-1]
    return num_students_input, rows_input, cols_input, students_text_input, optimization_input, mode_input, target_teams_text_input, sorts, group_text_input, reservations

def fill_json_sheet(students, reservation, teams, priority):
    reservation_data = []
    for student in students:
        # 检查 student[1] 是否在 reservation 中
        if str(student[1]) in reservation:
            # 如果存在，获取对应的行和列
            i, j = reservation[str(student[1])]
            i += 1
            j += 1
            gr.Info(f"已自动应用学生{student[1]}在配置文件中的原本的预定位置({i}, {j})")
            reservation_data.append([student[0], student[1], i, j])
        else:
            reservation_data.append([student[0], student[1], None, None])
    
    priority_data = []
    if teams:
        data = []
        if len(priority) == len(teams):
            gr.Info("检测到当前输入的目标小组数量仍然与导入的配置文件相同，故自动应用配置文件中的小组顺序")
            for i, team in enumerate(teams, 1):
                if team:
                    group_name = team[0] + "小组"
                    data.append([group_name, priority[i - 1]])
        else:
            gr.Info("检测到当前输入的目标小组数量与导入的配置文件不同，故重新进行排序")
            for i, team in enumerate(teams, 1):
                if team:
                    group_name = team[0] + "小组"
                    data.append([group_name, i])
        priority_data = pd.DataFrame(data, columns=["小组名", "优先顺序"])
    
    if isinstance(reservation_data, pd.DataFrame) and reservation_data.empty:
        reservation_result = []
    else:
        reservation_result = reservation_data

    # 检查 priority_data 是否为空
    if isinstance(priority_data, pd.DataFrame) and priority_data.empty:
        priority_result = []
    else:
        priority_result = priority_data

    return reservation_result, priority_result


# 保存配置为 JSON 文件
def save_config_to_json(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats, name):
    config = {
        'num_students': num_students,
        'rows': rows,
        'cols': cols,
        'students_data': students_data,
        'enable_optimization': enable_optimization,
        'mode': mode,
        'teams': teams,
        'sorts': sorts,
        'groups': groups,
        'reserved_seats': reserved_seats
    }
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_folder = os.path.join(current_dir, 'jsons')
    if not os.path.exists(json_folder):
        os.makedirs(json_folder)
    # 获取当前日期和时间
    now = datetime.datetime.now()
    # 格式化日期和时间为字符串
    timestamp = now.strftime("%Y%m%dd%Hh%Mm%Ss")
    if name is None:
        file_name = f'config_{timestamp}.json'
    elif isinstance(name, gr.State) and name.value is None:
        file_name = f'config_{timestamp}.json'
    else:
        file_name = f'{name}.json'
    file_path = os.path.join(json_folder, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    return file_path

# 生成唯一的简写名
def generate_unique_abbreviation(names):
    abbreviations = {}
    all_chars = ''.join(names)  # 合并所有名字中的字符

    for name in names:
        found = False
        # 尝试单字缩写
        for char in name:
            # 判断是否为汉字且笔画数小于 5
            if char in STROKE_LESS_THAN_5:
                continue
            # 检查该字符是否在其他名字中重复
            if char not in all_chars.replace(name, ''):
                abbreviations[name] = char
                found = True
                break
        # 如果单字缩写不可行，尝试双字缩写
        if not found:
            for i in range(len(name) - 1):
                abbr = name[i:i + 2]
                if all(abbr not in abbr2 for abbr2 in abbreviations.values()):
                    abbreviations[name] = abbr
                    found = True
                    break
        # 如果双字缩写也不可行，使用全名
        if not found:
            abbreviations[name] = name
    return abbreviations

# 计算曼哈顿距离
def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def save_image_and_get_path(img, prefix):
    if img is None:
        raise gr.Error("座位生成失败，请逐个检查你的输入，当输入时遇到警告要及时更改")  # 抛出错误，停止程序执行
        return None
    else:
        # 处理 numpy.ndarray 类型的图像数据
        if isinstance(img, np.ndarray):
            # 如果是灰度图（单通道）
            if len(img.shape) == 2:
                # 将小于某个阈值（这里设为 0.1）的像素值设为 1（白色）
                img[img < 0.1] = 1
                img = (img * 255).astype(np.uint8)
                # 反转灰度图像素值
                img = 255 - img
            # 如果是 RGB 图（三通道）
            elif len(img.shape) == 3:
                # 对于每个通道，将小于某个阈值（这里设为 0.1）的像素值设为 1（白色）
                for channel in range(img.shape[2]):
                    img[:, :, channel][img[:, :, channel] < 0.1] = 1
                img = (img * 255).astype(np.uint8)
                # 反转 RGB 图像素值
                img = 255 - img
            img = Image.fromarray(img)
        with tempfile.NamedTemporaryFile(suffix=".png", prefix=prefix, delete=False) as temp_file:
            try:
                img.save(temp_file.name)
                return temp_file.name
            except:
                raise gr.Error("座位图片保存失败，请调节输入后重试")
                return None

def result_evaluation(seating_arrangement, enable_optimization, groups):
    # 处理seating_arrangement，如果不是列表，尝试转换
    if isinstance(seating_arrangement, np.ndarray):
        seating_arrangement = seating_arrangement.tolist()
    if enable_optimization:
        rows = len(seating_arrangement)
        cols = len(seating_arrangement[0]) if rows > 0 else 0
        output_lines = ""
        output_lines += "秩序优化模式已启用，进行评价..."
        output_lines += "\n[身高排布评价]"
        output_lines += "\n    请观察身高热力图进行判断，深灰色代表高，浅灰色代表矮。没有明显断层为最佳。"
        output_lines += "\n\n[小团体排布评价]"
        total_groups = len(groups)
        fully_satisfied = 0
        tot_pairs = 0
        fullys_pairs = 0
        nsatis = ""
        
        for i, group in enumerate(groups):
            group_positions = []
            for student in group:
                for row in range(rows):
                    for col in range(cols):
                        if seating_arrangement[row][col] == student:
                            group_positions.append((row, col))
                            break
            
            total_pairs = len(group) * (len(group) - 1) // 2
            tot_pairs += total_pairs
            satisfied_pairs = 0
            
            for j in range(len(group_positions)):
                for k in range(j + 1, len(group_positions)):
                    if manhattan_distance(group_positions[j], group_positions[k]) > 1:
                        satisfied_pairs += 1
                    else:
                        student1 = seating_arrangement[group_positions[j][0]][group_positions[j][1]]
                        student2 = seating_arrangement[group_positions[k][0]][group_positions[k][1]]
                        nsatis += f"    第{i+1}个小团体中的{student1}和{student2}没有满足要求\n"
            
            output_lines += f"\n    第{i+1}个小团体含{len(group)}人，{total_pairs}个小组中有{satisfied_pairs}组人满足条件"
            
            fullys_pairs += satisfied_pairs
            if satisfied_pairs == total_pairs:
                fully_satisfied += 1
        
        satisfaction_rate = (fully_satisfied / total_groups * 100) if total_groups > 0 else 100
        satisfactionr_pairs = (fullys_pairs / tot_pairs * 100) if tot_pairs > 0 else 100
        output_lines += f"\n\n    共{total_groups}个小团体，有{fully_satisfied}个小团体全部满足条件，成员全部满足要求的小团体占{satisfaction_rate:.2f}%"
        output_lines += f"\n    共{tot_pairs}个小团体两人组，有{fullys_pairs}个组满足条件，每两两人小组条件满足率{satisfactionr_pairs:.2f}%"
        output_lines += f"\n    其中，\n    "
        if nsatis == "":
            output_lines += "所有人都满足了要求"
        else:
            output_lines += nsatis
        output_lines += "\n\n评价结束"
        return output_lines
    else:
        return "没有启用秩序优化模式，不进行评价"
    return "这里没有评价"