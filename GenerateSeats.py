import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import random
import tempfile
import datetime
import io
import os
import math
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image, ImageDraw, ImageFont
from AlgorithmFunctions import manhattan_distance, generate_unique_abbreviation
from Debugging import log_record, debug

try:
    plt.rcParams['font.sans-serif'] = ['SimSun']
except:
    try:
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
    except:
        print("无法找到字体，中文名显示可能会出现乱码")

plt.rcParams["axes.unicode_minus"] = False

def calculate_energy(seating_arrangement, groups, rows, cols):
    energy = 0
    for group in groups:
        group_positions = []
        for student in group:
            for i in range(rows):
                for j in range(cols):
                    if seating_arrangement[i][j] == student:
                        group_positions.append((i, j))
        for i in range(len(group_positions)):
            for j in range(i + 1, len(group_positions)):
                if manhattan_distance(group_positions[i], group_positions[j]) > 1:
                    energy += 1
    return energy

# 生成座位排列
def generate_seating_arrangement(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats, steps):

    if steps > 50:
        gr.Info(f"自检模块检测到结果不合规，正在重新尝试生成 *{steps - 1}")
        return "i"

    if num_students is None or rows is None or cols is None or students_data is None:
        raise gr.Error("必填信息有空缺，生成失败，请检查")

    def _check_seating(seating):
        all_students = [student[1] for student in students_data]
        flat_seating = [student for row in seating for student in row if student not in ['空', '预留空位']]
        student_count = {}
        for student in flat_seating:
            if student in student_count:
                student_count[student] += 1
            else:
                student_count[student] = 1
        for student in all_students:
            if student not in student_count or student_count[student] != 1:
                return False
        return True
    
    #debug(teams, "teams")
    #debug(groups, "groups")
    #debug(reserved_seats, "reserved_seats")

########################################################################################################################################################

    if teams is None and groups is None and reserved_seats is None:
        gr.Info("当前执行秩序方面没有任何要求的简单排序，如果你启用了秩序优化模式但是看到了此提示，请检查你是否正确地进行了勾选、选择和输入。另外，如果你启用了秩序优化模式但是没有进行输入，也会看到此提示")
        students = sorted(students_data, key=lambda x: x[2])  # 按身高排序
        seating_arrangement = [['空'] * cols for _ in range(rows)]
        # 计算需要留出的空位数量
        empty_seats = rows * cols - num_students
        if empty_seats > 0:
            # 从右下角开始留空位
            for i in range(rows - 1, -1, -1):
                for j in range(cols - 1, -1, -1):
                    if empty_seats > 0 and seating_arrangement[i][j] == '空':
                        seating_arrangement[i][j] = '预留空位'
                        empty_seats -= 1
        # 按身高填充自由同学座位
        free_student_index = 0
        for i in range(rows):
            for j in range(cols):
                if seating_arrangement[i][j] == '空' and free_student_index < len(students):
                    seating_arrangement[i][j] = students[free_student_index][1]
                    free_student_index += 1
        
        # 同一行内自由同学随机排列
        for i in range(rows):
            row_free_indices = [j for j in range(cols) if
                                seating_arrangement[i][j] not in (reserved_seats or {}) and all(
                                    seating_arrangement[i][j] not in group for group in (groups or [])) and
                                seating_arrangement[i][j] != '预留空位']
            row_free_students = [seating_arrangement[i][j] for j in row_free_indices]
            random.shuffle(row_free_students)
            for j, student in zip(row_free_indices, row_free_students):
                seating_arrangement[i][j] = student

        # 相同身高的自由同学随机互换
        height_groups = {}
        for i in range(rows):
            for j in range(cols):
                student = seating_arrangement[i][j]
                if student not in (reserved_seats or {}) and all(student not in group for group in (groups or [])) and student != '预留空位':
                    student_height = next((s[2] for s in students_data if s[1] == student), 0)
                    if student_height not in height_groups:
                        height_groups[student_height] = []
                    height_groups[student_height].append((i, j))

        for height, positions in height_groups.items():
            students_at_height = [seating_arrangement[pos[0]][pos[1]] for pos in positions]
            random.shuffle(students_at_height)
            for pos, student in zip(positions, students_at_height):
                seating_arrangement[pos[0]][pos[1]] = student

        # 计算自由同学应在的行数并尝试交换
        free_student_positions = []
        height_ratios = [s[2] for s in students]
        min_height = min(height_ratios)
        max_height = max(height_ratios)
        for i in range(rows):
            for j in range(cols):
                student = seating_arrangement[i][j]
                if student not in (reserved_seats or {}) and all(student not in group for group in (groups or [])) and student != '预留空位':
                    student_height = next((s[2] for s in students_data if s[1] == student), 0)
                    height_ratio = (student_height - min_height) / (max_height - min_height) if max_height > min_height else 0
                    target_row = int(height_ratio * (rows - 1))
                    free_student_positions.append((i, j, student, target_row))

        num_free_students = len(free_student_positions)

        for i in range(num_free_students):
            j = random.randrange(i, num_free_students)
            if i == j: continue
            current_row1, col1, student1, target_row1 = free_student_positions[i]
            current_row2, col2, student2, target_row2 = free_student_positions[j]
            # 检查交换后是否仍满足偏移量要求
            if abs(current_row2 - target_row1) <= 1 and abs(current_row1 - target_row2) <= 1:
                if random.random() < 0.8:  # 80% 的概率进行交换
                    # 交换座位表中的信息
                    seating_arrangement[current_row1][col1], seating_arrangement[current_row2][col2] = student2, student1
                    # 正确更新 free_student_positions 列表中的信息
                    free_student_positions[i] = (current_row2, col2, student2, target_row1)
                    free_student_positions[j] = (current_row1, col1, student1, target_row2)
        for i in range(num_free_students):
            rowt, colt, studentt, x = free_student_positions[i]
            seating_arrangement[rowt][colt]=studentt

########################################################################################################################################################

    elif mode == 0 and enable_optimization:
        # 使用连续光滑映射 + 能量函数的规划器
        students = sorted(students_data, key=lambda x: x[2])
        initial_seating = [['空'] * cols for _ in range(rows)]
        assigned_students = set()

        heights = [s[2] for s in students]
        min_height = min(heights)
        max_height = max(heights)

        # 处理预留座位
        if reserved_seats:
            for student, (row, col) in reserved_seats.items():
                if 0 <= row < rows and 0 <= col < cols:
                    initial_seating[row][col] = student
                    assigned_students.add(student)
                else:
                    raise ValueError("预留座位位置超出范围，请检查")

        # 计算需要留出的空位数量
        empty_seats = rows * cols - num_students
        if empty_seats > 0:
            for i in range(rows - 1, -1, -1):
                for j in range(cols - 1, -1, -1):
                    if empty_seats > 0 and initial_seating[i][j] == '空':
                        initial_seating[i][j] = '预留空位'
                        empty_seats -= 1

        # 构造连续光滑的身高->目标行映射函数
        # 使用 tanh S 型映射以获得更平滑且可控的梯度
        def height_to_row_continuous(h):
            if max_height <= min_height:
                return 0.0
            h_norm = (h - min_height) / (max_height - min_height)
            # tanh S 型，k 控制斜率，0.5 为中心
            k = 6.0
            s = 0.5 * (1.0 + math.tanh(k * (h_norm - 0.5)))
            # 平移并缩放到行范围 [0, rows-1]
            return s * (rows - 1)

        # 列目标可以沿列方向平滑分布，利用身高排序索引做连续映射
        total_unassigned = len([s for s in students if s[1] not in (reserved_seats or {})])
        def index_to_col_continuous(idx):
            if total_unassigned <= 1:
                return (cols - 1) / 2.0
            return (idx / (total_unassigned - 1)) * (cols - 1)

        # 为每个学生构造连续目标位置 (row_target, col_target)
        # 增加入一点随机扰动以提升随机性（每次运行结果差异更大）
        continuous_targets = {}
        # 按身高排序的未分配学生索引，用于列映射
        unassigned_idx = 0
        for s in students:
            name = s[1]
            if name in (reserved_seats or {}):
                continue
            # 基准目标
            r_t = height_to_row_continuous(s[2])
            c_t = index_to_col_continuous(unassigned_idx)
            # 添加小幅高斯扰动（标准差随行列大小缩放，确保连续性但带来随机性）
            noise_r = random.gauss(0, 0.12 * rows)
            noise_c = random.gauss(0, 0.12 * cols)
            continuous_targets[name] = (max(0.0, min(rows - 1, r_t + noise_r)), max(0.0, min(cols - 1, c_t + noise_c)))
            unassigned_idx += 1

        # 初始解：对非小团体学生进行按身高分桶并随机化，以增加多样性
        current_solution = [row[:] for row in initial_seating]
        # 识别小团体成员集合
        group_members = set(m for g in (groups or []) for m in g)

        # 非小团体且非预留学生列表（按身高排序）
        non_group_students = [s for s in students if s[1] not in group_members and s[1] not in (reserved_seats or {})]
        # 将非小团体学生按身高分桶（宽度 5）并在桶内随机打乱，允许在相近身高中交换
        buckets = {}
        for s in non_group_students:
            h = s[2]
            key = int(h // 5)
            buckets.setdefault(key, []).append(s)
        shuffled_non_group = []
        for key in sorted(buckets.keys()):
            bucket = buckets[key][:]
            random.shuffle(bucket)
            shuffled_non_group.extend(bucket)

        # 合并需要先放置的小团体学生（保持先插入，但不会在优化阶段被随意移动）与经过随机化的非小团体学生
        placement_order = []
        # 先放置小团体学生以便保留分布形状
        for s in students:
            if s[1] in group_members:
                placement_order.append(s)
        # 再放置非小团体（随机化后的）
        placement_order.extend(shuffled_non_group)

        # 将每个未分配的学生按 placement_order 放置到最近的空位
        for s in placement_order:
            name = s[1]
            if name in assigned_students:
                continue
            empty_positions = [(i, j) for i in range(rows) for j in range(cols) if current_solution[i][j] == '空']
            if not empty_positions:
                break
            r_t, c_t = continuous_targets.get(name, (rows // 2, cols // 2))
            # 使用欧氏距离选择最近空位，但随机选择 top-k 来提升随机性
            dists = [(p, (p[0] - r_t) ** 2 + (p[1] - c_t) ** 2) for p in empty_positions]
            dists.sort(key=lambda x: x[1])
            k = max(1, min(5, len(dists)//10 + 1))
            top_k = [p for p, _ in dists[:k]]
            pos_choice = random.choice(top_k)
            current_solution[pos_choice[0]][pos_choice[1]] = name
            assigned_students.add(name)

        # 能量函数：平衡身高偏差能量与小团体分散（或聚合）能量
        def get_positions_map(sol):
            pos = {}
            for i in range(rows):
                for j in range(cols):
                    student = sol[i][j]
                    if student not in ['空', '预留空位']:
                        pos[student] = (i, j)
            return pos

        def energy(sol, temperature=1.0):
            pos = get_positions_map(sol)
            # 身高能量：平方误差
            height_energy = 0.0
            for s in students:
                name = s[1]
                if name in pos:
                    r_t, c_t = continuous_targets.get(name, (0.0, 0.0))
                    i, j = pos[name]
                    height_energy += (i - r_t) ** 2

            # 小团体能量：优先惩罚成员对不满足接近距离的对（manhattan > 1），其次为分布均匀性
            group_energy = 0.0
            for g in (groups or []):
                members = [m for m in g if m in pos]
                if len(members) <= 1:
                    continue
                dists = []
                adjacency_violations = 0
                for a in range(len(members)):
                    for b in range(a + 1, len(members)):
                        p1 = pos[members[a]]
                        p2 = pos[members[b]]
                        # 使用曼哈顿距离判断是否相邻
                        manh = abs(p1[0]-p2[0]) + abs(p1[1]-p2[1])
                        if manh > 1:
                            adjacency_violations += 1
                        d = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2
                        dists.append(d)
                if dists:
                    # 目标距离针对当前教室尺度与小团体规模可适配
                    target_d = max(1.0, ((rows - 1) ** 2 + (cols - 1) ** 2) / max(4.0, 4.0 * len(members)))
                    variance_penalty = sum((dd - target_d) ** 2 for dd in dists) / len(dists)
                    # 强化惩罚：每个 adjacency violation 增加大 penalty
                    group_energy += variance_penalty + adjacency_violations * 10.0

            # 归一化项，避免规模问题
            height_norm = height_energy / (rows ** 2 + 1)
            group_norm = group_energy / (max(1, (rows ** 2 + cols ** 2)))

            temp_factor = max(0.01, min(1.0, temperature))
            w_height_temp = 1.0 * (1.0 - 0.6 * (1 - temp_factor))
            w_group_temp = 1.0 * (0.8 + 0.2 * (1 - temp_factor))
            S = w_height_temp + w_group_temp

            w_group = S / 2
            w_height = w_group

            return w_height * height_norm + w_group * group_norm

        # 模拟退火优化（交换两个非预留学生）
        current_energy = energy(current_solution, temperature=1.0)
        best_solution = [row[:] for row in current_solution]
        best_energy = current_energy

        # 使用多次随机重启 + 多种邻域操作以提高结果多样性与收敛性
        T = 1.0
        T_min = 1e-4
        alpha = 0.993
        max_iters = 8000
        restarts = 3

        best_overall = [row[:] for row in current_solution]
        best_overall_energy = energy(best_overall, temperature=T)

        for restart in range(restarts):
            # 每次重启增加微小扰动到 continuous targets 的位置
            perturbed_targets = {k: (v[0] + random.gauss(0, 0.2), v[1] + random.gauss(0, 0.2)) for k, v in continuous_targets.items()}
            # 重新创建当前解为初始放置（使用 perturbed_targets 的近邻策略）
            cur = [row[:] for row in initial_seating]
            assigned = set([s for s in (reserved_seats or {}).keys()])
            # 简单的重放置：按 placement_order，但优先使用 perturbed_targets
            for s in placement_order:
                name = s[1]
                if name in assigned:
                    continue
                empty_positions = [(i, j) for i in range(rows) for j in range(cols) if cur[i][j] == '空']
                if not empty_positions:
                    break
                r_t, c_t = perturbed_targets.get(name, (rows // 2, cols // 2))
                dists = [(p, (p[0] - r_t) ** 2 + (p[1] - c_t) ** 2) for p in empty_positions]
                dists.sort(key=lambda x: x[1])
                k = max(1, min(5, len(dists)//10 + 1))
                top_k = [p for p, _ in dists[:k]]
                pos_choice = random.choice(top_k)
                cur[pos_choice[0]][pos_choice[1]] = name
                assigned.add(name)

            cur_energy = energy(cur, temperature=T)
            current = [row[:] for row in cur]
            current_energy = cur_energy

            non_group_list = [s[1] for s in students if s[1] not in group_members and s[1] not in (reserved_seats or {})]

            iter_count = 0
            while T > T_min and iter_count < max_iters:
                iter_count += 1
                # 邻域操作：swap 或 move
                if random.random() < 0.7 and len(non_group_list) >= 2:
                    # 尝试选择身高相近的候选以便改善身高序列
                    a = random.choice(non_group_list)
                    ha = next((s[2] for s in students if s[1] == a), 0)
                    close = [sname for sname in non_group_list if sname != a and abs(next((s[2] for s in students if s[1] == sname), 0) - ha) <= 5]
                    if close and random.random() < 0.7:
                        b = random.choice(close)
                    else:
                        b = random.choice([x for x in non_group_list if x != a])
                    pos_map = get_positions_map(current)
                    pa = pos_map.get(a)
                    pb = pos_map.get(b)
                    if not pa or not pb:
                        T *= alpha
                        continue
                    new_sol = [row[:] for row in current]
                    new_sol[pa[0]][pa[1]], new_sol[pb[0]][pb[1]] = new_sol[pb[0]][pb[1]], new_sol[pa[0]][pa[1]]
                else:
                    # move: 将某个非小团体学生移动到随机可用位置（扩大邻域）
                    cand = random.choice(non_group_list) if non_group_list else None
                    if not cand:
                        T *= alpha
                        continue
                    pos_map = get_positions_map(current)
                    p_old = pos_map.get(cand)
                    empties = [(i, j) for i in range(rows) for j in range(cols) if current[i][j] == '空']
                    if not p_old or not empties:
                        T *= alpha
                        continue
                    p_new = random.choice(empties)
                    new_sol = [row[:] for row in current]
                    new_sol[p_new[0]][p_new[1]] = cand
                    new_sol[p_old[0]][p_old[1]] = '空'

                new_e = energy(new_sol, temperature=T)
                delta = new_e - current_energy
                if delta < 0 or random.random() < math.exp(-delta / max(1e-6, T)):
                    current = new_sol
                    current_energy = new_e
                    if current_energy < best_overall_energy:
                        best_overall_energy = current_energy
                        best_overall = [row[:] for row in current]

                T *= alpha

            # 结束一次重启，将温度重置再试下一次
            T = 1.0

        seating_arrangement = best_overall

#######################################################################################################################################################

    elif mode == 1 and enable_optimization:
            
            def dfs(start, size, seating_arrangement):
                # 优先尝试宽度为 2 - 3 列的区域
                width_options = [2, 3]
                random.shuffle(width_options)  # 添加搜索随机性，随机排列宽度选项
                for width in width_options:
                    stack = [start]
                    visited = set()
                    path = []
                    while stack:
                        # 随机选择栈中的元素
                        random_index = random.randint(0, len(stack) - 1)
                        current = stack.pop(random_index)
                        if current in visited:
                            continue
                        visited.add(current)
                        path.append(current)
                        if len(path) == size:
                            return path
                        # 优先在宽度范围内进行搜索
                        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                        #random.shuffle(directions)  # 随机排列搜索方向
                        for dx, dy in directions:
                            new_x, new_y = current[0] + dx, current[1] + dy
                            if 0 <= new_x < len(seating_arrangement) and 0 <= new_y < len(seating_arrangement[0]) and seating_arrangement[new_x][new_y] == '空' and (new_x, new_y) not in visited:
                                # 简单检查宽度
                                if abs(new_y - start[1]) < width:
                                    stack.append((new_x, new_y))
                return None
        

            seating_arrangement = [['空'] * cols for _ in range(rows)]
            # 记录已安排座位的学生
            assigned_students = set()

            # 处理预留座位
            if reserved_seats:
                for student, (row, col) in reserved_seats.items():
                    if 0 <= row < rows and 0 <= col < cols:
                        seating_arrangement[row][col] = student
                        assigned_students.add(student)
                    else:
                        raise ValueError("预留座位位置超出范围，请检查")

            # 计算需要留出的空位数量
            empty_seats = rows * cols - num_students
            if empty_seats > 0:
                # 从右下角开始留空位
                for i in range(rows - 1, -1, -1):
                    for j in range(cols - 1, -1, -1):
                        if empty_seats > 0 and seating_arrangement[i][j] == '空':
                            seating_arrangement[i][j] = '预留空位'
                            empty_seats -= 1

            # 检查小团体里的预定座位是否太近
            if groups:
                for group in groups:
                    reserved_group_students = [student for student in group if student in reserved_seats]
                    if len(reserved_group_students) > 1:
                        positions = {student: reserved_seats[student] for student in reserved_group_students}
                        for student1 in reserved_group_students:
                            for student2 in reserved_group_students:
                                if student1 != student2:
                                    if manhattan_distance(positions[student1], positions[student2]) <= 1:
                                        raise gr.Error("小团体中预留座位的同学距离太近，请调整")

            # 处理目标小组，消去有预定座位的同学
            new_teams = []
            for team in teams:
                new_team = [student for student in team if student not in reserved_seats]
                new_teams.append(new_team)

            n = len(sorts)
            sortx = [0] * n
            for i, x in enumerate(sorts):
                sortx[x - 1] = i
            # 两个两个遍历 sortx
            length = len(sortx)
            if length % 2 == 0:
                end_index = length - 2
            else:
                end_index = length - 1

            for i in range(0, end_index, 2):
                if random.random() < 0.5:
                    sortx[i], sortx[i + 1] = sortx[i + 1], sortx[i]
            # 将 sortx 再按 sort 的规则存到 sort 里
            for i, x in enumerate(sortx):
                sorts[x] = i + 1

            priority_sorted = sorted(set(sorts))
            for priority in priority_sorted:
                team_index = sorts.index(priority)
                team = new_teams[team_index]
                team_students = sorted([(student, next((s[2] for s in students_data if s[1] == student), 0)) for student in team], key=lambda x: x[1])
                team_students = [student[0] for student in team_students]

                available_seats = [(i, j) for i in range(rows) for j in range(cols) if seating_arrangement[i][j] == '空']
                best_region = None
                best_score_team = float('inf')
                for start_seat in available_seats:
                    path = dfs(start_seat, len(team_students), seating_arrangement)
                    if path:
                        score = 0
                        for i, student in enumerate(team_students):
                            min_distance = float('inf')
                            for seat in path:
                                distance = manhattan_distance(start_seat, seat)
                                min_distance = min(min_distance, distance)
                            score += min_distance
                        if score < best_score_team:
                            best_score_team = score
                            best_region = path

                if best_region:
                    # 确认小组分布图形所占的每一行的个数
                    row_counts = [0] * rows
                    for seat in best_region:
                        row_counts[seat[0]] += 1

                    # 将小组内的成员按照身高排序
                    team_students_sorted = sorted(team_students, key=lambda s: next((stud[2] for stud in students_data if stud[1] == s), 0))

                    # 一行一行从矮到高填充
                    index = 0
                    for row in range(rows):
                        for _ in range(row_counts[row]):
                            seat = next((s for s in best_region if s[0] == row and seating_arrangement[s[0]][s[1]] == '空'), None)
                            if seat:
                                seating_arrangement[seat[0]][seat[1]] = team_students_sorted[index]
                                assigned_students.add(team_students_sorted[index])
                                index += 1

                    # 同一组同一行的人 shuffle
                    for row in range(rows):
                        same_row_seats = [seat for seat in best_region if seat[0] == row]
                        same_row_students = [seating_arrangement[seat[0]][seat[1]] for seat in same_row_seats if seating_arrangement[seat[0]][seat[1]] in team_students]
                        if len(same_row_students) > 1:
                            random.shuffle(same_row_students)
                            for i, seat in enumerate(same_row_seats):
                                seating_arrangement[seat[0]][seat[1]] = same_row_students[i]

                    # 同一组内身高相同或相差<平均身高/50的随机互换（用遍历）
                    height_list = [next((stud[2] for stud in students_data if stud[1] == s), 0) for s in team_students]
                    average_height = sum(height_list) / len(height_list) if height_list else 0
                    height_pairs = []
                    for i in range(len(team_students)):
                        for j in range(i + 1, len(team_students)):
                            height1 = next((stud[2] for stud in students_data if stud[1] == team_students[i]), 0)
                            height2 = next((stud[2] for stud in students_data if stud[1] == team_students[j]), 0)
                            if abs(height1 - height2) < average_height / 50:
                                height_pairs.append((team_students[i], team_students[j]))

                    random.shuffle(height_pairs)
                    for student1, student2 in height_pairs:
                        seat1 = next((seat for seat in best_region if seating_arrangement[seat[0]][seat[1]] == student1), None)
                        seat2 = next((seat for seat in best_region if seating_arrangement[seat[0]][seat[1]] == student2), None)
                        if seat1 and seat2:
                            seating_arrangement[seat1[0]][seat1[1]], seating_arrangement[seat2[0]][seat2[1]] = seating_arrangement[seat2[0]][seat2[1]], seating_arrangement[seat1[0]][seat1[1]]

            # 处理剩余的自由同学和最后一组无法聚集的同学
            remaining_students = [student for student in students_data if
                                student[1] not in assigned_students and student[1] not in (reserved_seats or {})]
            remaining_indices = [(i, j) for i in range(rows) for j in range(cols) if seating_arrangement[i][j] == '空']
            remaining_student_index = 0
            for seat in remaining_indices:
                if remaining_student_index < len(remaining_students):
                    seating_arrangement[seat[0]][seat[1]] = remaining_students[remaining_student_index][1]
                    remaining_student_index += 1

########################################################################################################################################################

    else:
        gr.Info("当前执行秩序方面没有任何要求的简单排序，如果你启用了秩序优化模式但是看到了此提示，请检查你是否正确地进行了勾选、选择和输入")
        students = sorted(students_data, key=lambda x: x[2])  # 按身高排序
        seating_arrangement = [['空'] * cols for _ in range(rows)]
        # 计算需要留出的空位数量
        empty_seats = rows * cols - num_students
        if empty_seats > 0:
            # 从右下角开始留空位
            for i in range(rows - 1, -1, -1):
                for j in range(cols - 1, -1, -1):
                    if empty_seats > 0 and seating_arrangement[i][j] == '空':
                        seating_arrangement[i][j] = '预留空位'
                        empty_seats -= 1
        # 按身高填充自由同学座位
        free_student_index = 0
        for i in range(rows):
            for j in range(cols):
                if seating_arrangement[i][j] == '空' and free_student_index < len(students):
                    seating_arrangement[i][j] = students[free_student_index][1]
                    free_student_index += 1
        
        # 同一行内自由同学随机排列
        for i in range(rows):
            row_free_indices = [j for j in range(cols) if
                                seating_arrangement[i][j] not in (reserved_seats or {}) and all(
                                    seating_arrangement[i][j] not in group for group in (groups or [])) and
                                seating_arrangement[i][j] != '预留空位']
            row_free_students = [seating_arrangement[i][j] for j in row_free_indices]
            random.shuffle(row_free_students)
            for j, student in zip(row_free_indices, row_free_students):
                seating_arrangement[i][j] = student

        # 相同身高的自由同学随机互换
        height_groups = {}
        for i in range(rows):
            for j in range(cols):
                student = seating_arrangement[i][j]
                if student not in (reserved_seats or {}) and all(student not in group for group in (groups or [])) and student != '预留空位':
                    student_height = next((s[2] for s in students_data if s[1] == student), 0)
                    if student_height not in height_groups:
                        height_groups[student_height] = []
                    height_groups[student_height].append((i, j))

        for height, positions in height_groups.items():
            students_at_height = [seating_arrangement[pos[0]][pos[1]] for pos in positions]
            random.shuffle(students_at_height)
            for pos, student in zip(positions, students_at_height):
                seating_arrangement[pos[0]][pos[1]] = student

        # 计算自由同学应在的行数并尝试交换
        free_student_positions = []
        height_ratios = [s[2] for s in students]
        min_height = min(height_ratios)
        max_height = max(height_ratios)
        for i in range(rows):
            for j in range(cols):
                student = seating_arrangement[i][j]
                if student not in (reserved_seats or {}) and all(student not in group for group in (groups or [])) and student != '预留空位':
                    student_height = next((s[2] for s in students_data if s[1] == student), 0)
                    height_ratio = (student_height - min_height) / (max_height - min_height) if max_height > min_height else 0
                    target_row = int(height_ratio * (rows - 1))
                    free_student_positions.append((i, j, student, target_row))

        num_free_students = len(free_student_positions)

        for i in range(num_free_students):
            j = random.randrange(i, num_free_students)
            if i == j: continue
            current_row1, col1, student1, target_row1 = free_student_positions[i]
            current_row2, col2, student2, target_row2 = free_student_positions[j]
            # 检查交换后是否仍满足偏移量要求
            if abs(current_row2 - target_row1) <= 1 and abs(current_row1 - target_row2) <= 1:
                if random.random() < 0.8:  # 80% 的概率进行交换
                    # 交换座位表中的信息
                    seating_arrangement[current_row1][col1], seating_arrangement[current_row2][col2] = student2, student1
                    # 正确更新 free_student_positions 列表中的信息
                    free_student_positions[i] = (current_row2, col2, student2, target_row1)
                    free_student_positions[j] = (current_row1, col1, student1, target_row2)
        for i in range(num_free_students):
            rowt, colt, studentt, x = free_student_positions[i]
            seating_arrangement[rowt][colt]=studentt

########################################################################################################################################################

        # 检查座位安排是否符合要求
    if _check_seating(seating_arrangement):
            log_record("Successed", seating_arrangement, "Result generated successfully.")
            return seating_arrangement
    else:
            gr.Info("生成的座位安排不符合要求，正在重新生成")
            log_record("Half Failed", seating_arrangement, f"Result not legal. Already tried {steps} times.")
            return generate_seating_arrangement(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats, steps + 1)
    

def generate_images(seating_arrangement, students_data, teams=[]):

    names = [student[1] for student in students_data]
    abbreviations = generate_unique_abbreviation(names)
    student_dict = {student[1]: student for student in students_data}
    rows = len(seating_arrangement)
    cols = len(seating_arrangement[0])

    # 学号图片
    fig1, ax1 = plt.subplots()
    table1 = ax1.table(cellText=[[student_dict[student][0] if student != '空' and student != '预留空位' else '' for student in row] for row in
                                 seating_arrangement], loc='center', cellLoc='center')
    table1.auto_set_font_size(False)
    table1.set_fontsize(10)
    # 设置表格单元格尺寸以保证为正方形
    for key, cell in table1.get_celld().items():
        cell.set_height(1 / rows)
        cell.set_width(1 / cols)
    ax1.axis('off')
    buf1 = io.BytesIO()
    fig1.savefig(buf1, format='png')
    buf1.seek(0)
    img1 = Image.open(buf1)

    # 全名图片
    fig2, ax2 = plt.subplots()
    table2 = ax2.table(cellText=[[student_dict[student][1] if student != '空' and student != '预留空位' else '' for student in row] for row in seating_arrangement],
                       loc='center', cellLoc='center')
    table2.auto_set_font_size(False)
    table2.set_fontsize(10)
    # 设置表格单元格尺寸以保证为正方形
    for key, cell in table2.get_celld().items():
        cell.set_height(1 / rows)
        cell.set_width(1 / cols)
    ax2.axis('off')
    buf2 = io.BytesIO()
    fig2.savefig(buf2, format='png')
    buf2.seek(0)
    img2 = Image.open(buf2)

    # 简写名图片
    fig3, ax3 = plt.subplots()
    table3 = ax3.table(
        cellText=[[abbreviations[student] if student != '空' and student != '预留空位' else '' for student in row] for row in seating_arrangement],
        loc='center', cellLoc='center')
    table3.auto_set_font_size(False)
    table3.set_fontsize(10)
    # 设置表格单元格尺寸以保证为正方形
    for key, cell in table3.get_celld().items():
        cell.set_height(1 / rows)
        cell.set_width(1 / cols)
    ax3.axis('off')
    buf3 = io.BytesIO()
    fig3.savefig(buf3, format='png')
    buf3.seek(0)
    img3 = Image.open(buf3)

    # 身高热力图
    colors = [(80 / 255, 80 / 255, 80 / 255), (220 / 255, 220 / 255, 220 / 255)]
    my_colormap = LinearSegmentedColormap.from_list("", colors)
    # 扩展颜色映射，添加白色对应值
    my_colormap.set_under('white')

    heights = [[student_dict[student][2] if student != '空' and student != '预留空位' else 0 for student in row] for row in seating_arrangement]
    max_height = max(max(row) for row in heights) if any(heights) else 1
    normalized_heights = [[(1 - height / max_height) if height > 0 else -1 for height in row] for row in heights]
    fig4, ax4 = plt.subplots()
    im4 = ax4.imshow(normalized_heights, cmap=my_colormap, alpha=1)  # 使用自定义颜色映射
    for i in range(rows):
        for j in range(cols):
            if heights[i][j] > 0:
                ax4.text(j, i, str(heights[i][j]), ha='center', va='center', color='black')
    ax4.axis('off')
    buf4 = io.BytesIO()
    fig4.savefig(buf4, format='png')
    buf4.seek(0)
    img4 = Image.open(buf4)

    # 小组分布灰度图
    if teams:
        group_mapping = {}
        group_index = 1
        all_students_in_teams = set()
        for team in teams:
            for student in team:
                group_mapping[student] = group_index
                all_students_in_teams.add(student)
            group_index += 1

        colors = [(255 / 255, 255 / 255, 255 / 255), (80 / 255, 80 / 255, 80 / 255)]
        my_colormap = LinearSegmentedColormap.from_list("", colors)
        # 扩展颜色映射，添加白色对应值
        my_colormap.set_under('white')
        group_heights = []
        for row in seating_arrangement:
            new_row = []
            for student in row:
                if student != '空' and student != '预留空位':
                    if student in all_students_in_teams:
                        new_row.append(group_mapping.get(student, 0))
                    else:
                        # 不在任何小组中的人标记为白色，对应值设为小于颜色映射最低值
                        new_row.append(-1)
                else:
                    new_row.append(0)
            group_heights.append(new_row)

        max_group = max(max(row) for row in group_heights if row) if any(group_heights) else 1
        normalized_group_heights = []
        for row in group_heights:
            new_normalized_row = []
            for height in row:
                if height > 0:
                    new_normalized_row.append(1 - height / max_group)
                else:
                    # 保持非小组同学的值小于最低值，以显示为白色
                    new_normalized_row.append(-1)
            normalized_group_heights.append(new_normalized_row)

        fig5, ax5 = plt.subplots()
        im5 = ax5.imshow(normalized_group_heights, cmap=my_colormap, alpha=1)
        for i in range(rows):
            for j in range(cols):
                student = seating_arrangement[i][j]
                if student != '空' and student != '预留空位':
                    student_id = student_dict[student][0]
                    ax5.text(j, i, str(student_id), ha='center', va='center', color='black')
        ax5.axis('off')
        buf5 = io.BytesIO()
        fig5.savefig(buf5, format='png')
        buf5.seek(0)
        img5 = Image.open(buf5)
    else:
        # 创建一个空白的白色图像
        img5 = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img5)
        # 设置字体
        font = ImageFont.load_default()
        # 计算文本的位置
        text = "This Image Is Not Useful"
        # 修改这一行
        left, top, right, bottom = draw.textbbox((0, 0), text)
        text_width = right - left
        text_height = bottom - top
        x = (img5.width - text_width) // 2
        y = (img5.height - text_height) // 2
        # 在图像上绘制文本
        draw.text((x, y), text, fill='black', font=font)

    return img1, img2, img3, img4, img5

def generate_csv(seating_arrangement):
    if isinstance(seating_arrangement, np.ndarray):
        seating_arrangement = seating_arrangement.tolist()
    # 处理座位数据，将 '预留空位' 和 '空' 替换为空字符串
    processed_seating_arrangement = []
    for row in seating_arrangement:
        new_row = []
        for seat in row:
            if seat in ['预留空位', '空']:
                new_row.append('')
            else:
                new_row.append(seat)
        processed_seating_arrangement.append(new_row)

    df = pd.DataFrame(processed_seating_arrangement)
    csv_content = df.to_csv(sep=',', na_rep='nan', index=False, header=False, encoding='utf-8-sig')
    temp_dir = tempfile.gettempdir()
    now = datetime.datetime.now()
    # 格式化日期和时间为字符串
    timestamp = now.strftime("%Y%m%dd%Hh%Mm%Ss")
    # 拼接临时文件的完整路径
    temp_file_path = os.path.join(temp_dir, f"result_{timestamp}.csv")
    try:
        # 以写入模式打开临时文件，指定 newline='' 避免多余换行符处理
        with open(temp_file_path, 'w', encoding='utf-8-sig', newline='') as temp_file:
            # 将 CSV 内容写入临时文件
            temp_file.write(csv_content)
        # 返回临时文件的路径
        return temp_file_path
    except Exception as e:
        raise gr.Error(f"写入csv文件时出错 {e}")