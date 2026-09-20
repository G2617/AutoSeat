import gradio as gr
import pandas as pd
import re
from GenerateSeats import generate_images, generate_csv, generate_seating_arrangement
from AlgorithmFunctions import result_evaluation
from Debugging import log_record, debug

# 欢迎语并输入班级人数
def welcome_page(num_students):
    if num_students is None or num_students <= 0:
        raise gr.Error("请输入有效的班级人数")
    return num_students


# 输入座位排列方式
def seating_arrangement_page(num_students, rows, cols):
    try:
        rows = int(rows)
        cols = int(cols)
        if rows * cols < num_students:
            raise gr.Error("座位数量不能少于学生人数，请重新输入合适的行数和列数")
        return num_students, rows, cols
    except ValueError as e:
        raise gr.Error(str(e))
    except:
        raise gr.Error("请输入有效的行数和列数")


# 选择文件输入还是文字框粘贴
def input_method_page(num_students, rows, cols, input_method):
    return num_students, rows, cols, input_method


# 文件输入或文字框粘贴
def input_students_page(num_students, rows, cols, input_method, file=None, text=None):
    if input_method == "文件输入":
        if file is None:
            raise gr.Error("请拖入符合规格的xlsx文件")
        try:
            df = pd.read_excel(file.name)
            students_data = df.values.tolist()
        except:
            raise gr.Error("文件格式错误，请检查文件内容")
    else:
        if text is None or text.strip() == "":
            raise gr.Error("请输入学生信息")
        lines = text.strip().split('\n')
        students_data = []
        for line in lines:
            parts = line.strip().split(' ')
            if len(parts) != 3:
                raise gr.Error("输入格式错误，请确保每行包含学号，全名，大致身高")
            try:
                student_id, name, height = parts
                if not re.match(r'^[a-zA-Z0-9]+$', student_id):
                    raise gr.Error("学号只能包含字母和数字")
                if not (2 <= len(name) <= 4):
                    raise gr.Error("全名必须是两到四个汉字")
                height = float(height)
                students_data.append([student_id, name, height])
            except ValueError as e:
                raise gr.Error(str(e))
            except Exception as e:
                if isinstance(e, ValueError) or isinstance(e, gr.Error):
                    raise gr.Error(str(e))
                else:
                    raise gr.Error("输入格式错误，学号只能包含字母和数字，全名必须是两到四个汉字")

    if len(students_data) != num_students:
        raise gr.Error("输入的学生数量与班级人数不匹配，请检查")

    return num_students, rows, cols, students_data


# 询问是否启用秩序优化模式
def optimization_mode_page(num_students, rows, cols, students_data, enable_optimization):
    return num_students, rows, cols, students_data, enable_optimization


# 处理模式选择
def mode_selection_page(num_students, rows, cols, students_data, enable_optimization, mode):
    if mode == "离散模式":
        return num_students, rows, cols, students_data, enable_optimization, 0
    elif mode == "小组聚集模式":
        return num_students, rows, cols, students_data, enable_optimization, 1


# 秩序优化模式输入
def optimization_input_page(num_students, rows, cols, students_data, enable_optimization, mode, target_teams_file=None, target_teams_text=None, group_file=None,
                            group_text=None, enable_reservation=False, reserved_students=None):
    groups = []
    teams = []
    reserved_seats = {}
    if enable_optimization:
        if mode == 1:
            if target_teams_file:
                try:
                    with open(target_teams_file.name, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    for line in lines:
                        parts = line.strip().split()
                        teams.append(parts)
                except:
                    raise gr.Error("目标小组文件读取错误，请检查文件内容")
            elif target_teams_text:
                lines = target_teams_text.strip().split('\n')
                for line in lines:
                    parts = line.strip().split(' ')
                    teams.append(parts)
            else:
                raise gr.Error("目标小组输入不能为空，请输入")

        if group_file:
            try:
                with open(group_file.name, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for line in lines:
                    parts = line.strip().split()
                    groups.append(parts)
            except:
                raise gr.Error("小团体文件读取错误，请检查文件内容")
        elif group_text:
            lines = group_text.strip().split('\n')
            for line in lines:
                parts = line.strip().split(' ')
                groups.append(parts)
        else:
            gr.Info("小团体输入当前为空，如若不使用此功能请忽略")

        if enable_reservation:
            if not reserved_students.empty:
                student_dict = {s[0]: s[1] for s in students_data}  # 构建学号到姓名的映射
                seat_booked = {}  # 用于记录每个座位是否已被预定
                for index, (id, student, row, col) in enumerate(reserved_students.values.tolist()):
                    row_empty = row is None or row == '' or pd.isna(row)
                    col_empty = col is None or col == '' or pd.isna(col)
                    if not row_empty and not col_empty:
                        if isinstance(id, str) and id.isalnum():
                            if id in student_dict:
                                student = student_dict[id]
                            else:
                                raise gr.Error(f"学号{id}不存在，请检查")
                        else:
                            student = id
                        if student not in [s[1] for s in students_data]:
                            raise gr.Error(f"学生{student}不存在，请检查")
                        try:
                            row = int(row)
                            col = int(col)
                            if row < 0 or row > rows or col < 0 or col > cols:
                                raise gr.Error("座位位置越界，请检查")
                            try:
                                row = int(row)
                                col = int(col)
                                if 1 <= row <= rows and 1 <= col <= cols:
                                    seat_key = (row - 1, col - 1)  # 转换为0基索引
                                    if seat_key in seat_booked:
                                        raise gr.Error(f"座位({row}, {col})被多个同学同时预定，请检查")
                                    reserved_seats[student] = seat_key
                                    seat_booked[seat_key] = True
                                else:
                                    raise gr.Error(f"预定座位{student}位置({row}, {col})超出范围")
                            except ValueError:
                                raise gr.Error(f"预定座位的学生{student}的坐标必须为数字，当前输入为({row}, {col})")
                        except Exception as e:
                            if isinstance(e, ValueError) or isinstance(e, gr.Error):
                                raise gr.Error(str(e))
                            else:
                                raise gr.Error("座位位置输入错误或越界，请检查")
                    else:
                        # 如果未勾选，将行和列置为空
                        reserved_students.at[index, '行'] = None
                        reserved_students.at[index, '列'] = None
            else:
                gr.Info("预定座位输入当前为空，如若不使用此功能请忽略")
    else:
        gr.Info("秩序优化模式已关闭，因此如果目标小组、小团体、预定座位有过输入也会被忽略")
    return num_students, rows, cols, students_data, enable_optimization, mode, teams, groups, reserved_seats


# 生成初始的学生数据，包含学号、姓名、行、列
def generate_initial_student_data(students_data):
    data = []
    for student in students_data:
        data.append([student[0], student[1], None, None])
    return data

# 生成座位排列并输出图片
def generate_page(num_students, rows, cols, students_data, enable_optimization, mode, teams, groups, reserved_seats):
    if num_students is None or rows is None or cols is None or students_data is None:
        log_record("Failed", [], f"Inputs not legal.\nGenerating didn't start because of the error.")
        raise gr.Error("必填信息有空缺，生成失败，请检查")
    else:
        try:
            seating_arrangement = generate_seating_arrangement(num_students, rows, cols, students_data, enable_optimization, mode, teams, groups, reserved_seats, 0)
            if seating_arrangement == "i":
                log_record("Failed", [], "Result not legal.\nGenerating failed after trying several times.")
                raise gr.Error("座位生成失败，请调节输入后重试")
            elif seating_arrangement is None or seating_arrangement is []:
                log_record("Failed", [], "Unexpected error.\nThe result was empty because of unexpected errors.")
                raise gr.Error("座位生成失败，请调节输入后重试")
            img1, img2, img3, img4, img5 = generate_images(seating_arrangement, students_data, teams)
            csv_file = generate_csv(seating_arrangement)
            eval_ = result_evaluation(seating_arrangement, enable_optimization, groups)
            return csv_file, img1, img2, img3, img4, img5, eval_
        except ValueError as e:
            raise gr.Error(str(e))
    
# 生成初始数据
def get_initial_data(students_data):
    return generate_initial_student_data(students_data) if students_data else []

def show_reservation_input(enable):
    return gr.update(visible=enable)

def show_group_input(method):
   return gr.update(visible=method == "文件输入"), gr.update(visible=method == "文本输入")

def show_target_teams_input(method):
    return gr.update(visible=method == "文件输入"), gr.update(visible=method == "文本输入")

def if_and_ud1(x):
    if x == 0:
        gr.Info("请进入秩序优化界面进行设置")
    if x == 1:
        gr.Info("请往下进行秩序优化部分的编辑")
    return gr.update(visible=True), gr.update(visible=True)
    
def if_and_ud2(x):
    if x == 0:
        gr.Info("请进入结果界面查看结果")
    if x == 1:
        gr.Info("编辑完成，请进入保存界面进行保存")
    return gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)