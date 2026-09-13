import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import random
import tempfile
import datetime
import io
import os
import hashlib
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
        # 基于能量函数的离散动作 Q-learning；预留座位和小团体学生不参与动作。
        students = sorted(students_data, key=lambda x: x[2])
        initial_seating = [['空'] * cols for _ in range(rows)]
        assigned_students = set()
        if reserved_seats:
            for student, (row, col) in reserved_seats.items():
                if not (0 <= row < rows and 0 <= col < cols):
                    raise ValueError("预留座位位置超出范围，请检查")
                initial_seating[row][col] = student
                assigned_students.add(student)

        empty_seats = rows * cols - num_students
        for i in range(rows - 1, -1, -1):
            for j in range(cols - 1, -1, -1):
                if empty_seats > 0 and initial_seating[i][j] == '空':
                    initial_seating[i][j] = '预留空位'
                    empty_seats -= 1

        heights = [s[2] for s in students]
        min_height, max_height = min(heights), max(heights)
        total_unassigned = len([s for s in students if s[1] not in (reserved_seats or {})])

        def height_to_row(h):
            if max_height == min_height:
                return (rows - 1) / 2.0
            normalized = (h - min_height) / (max_height - min_height)
            return normalized * (rows - 1)

        continuous_targets = {}
        target_index = 0
        for student in students:
            name = student[1]
            if name in (reserved_seats or {}):
                continue
            target_col = ((target_index / max(1, total_unassigned - 1)) * (cols - 1)
                          if total_unassigned > 1 else (cols - 1) / 2.0)
            continuous_targets[name] = (height_to_row(student[2]), target_col)
            target_index += 1

        group_members = set(member for group in (groups or []) for member in group)
        placement_order = [s for s in students if s[1] in group_members]
        non_group_students = [s for s in students
                              if s[1] not in group_members
                              and s[1] not in (reserved_seats or {})]
        random.shuffle(non_group_students)
        placement_order.extend(non_group_students)
        current_solution = [row[:] for row in initial_seating]
        for student in placement_order:
            name = student[1]
            if name in assigned_students:
                continue
            available = [(i, j) for i in range(rows) for j in range(cols)
                         if current_solution[i][j] == '空']
            if not available:
                break
            target = continuous_targets.get(name, ((rows - 1) / 2.0, (cols - 1) / 2.0))
            available.sort(key=lambda p: (p[0] - target[0]) ** 2 + (p[1] - target[1]) ** 2)
            position = random.choice(available[:max(1, min(5, len(available)))])
            current_solution[position[0]][position[1]] = name
            assigned_students.add(name)

        def get_positions_map(solution):
            return {(student, (i, j))
                    for i, row in enumerate(solution)
                    for j, student in enumerate(row)
                    if student not in ('空', '预留空位')}

        def energy(solution):
            positions = dict(get_positions_map(solution))
            height_energy = sum(
                (positions[name][0] - continuous_targets.get(name, (0.0, 0.0))[0]) ** 2
                for _, name, _ in students if name in positions
            )
            # 显式惩罚身高次序倒置：行号越大表示越靠后，后排不应比前排矮。
            height_order_energy = 0.0
            positioned_students = [student for student in students if student[1] in positions]
            for index, (_, first, first_height) in enumerate(positioned_students):
                for _, second, second_height in positioned_students[index + 1:]:
                    first_row = positions[first][0]
                    second_row = positions[second][0]
                    if first_height < second_height and first_row > second_row:
                        height_order_energy += (first_row - second_row) ** 2
                    elif first_height > second_height and first_row < second_row:
                        height_order_energy += (second_row - first_row) ** 2
            row_heights = []
            for row_index in range(rows):
                heights_in_row = [
                    next(student[2] for student in students if student[1] == name)
                    for name, (row, _) in positions.items() if row == row_index
                ]
                if heights_in_row:
                    row_heights.append((row_index, sum(heights_in_row) / len(heights_in_row)))
            row_profile_energy = sum(
                max(0.0, previous_height - next_height) ** 2
                for (_, previous_height), (_, next_height)
                in zip(row_heights, row_heights[1:])
            )

            group_energy = 0.0
            for group in (groups or []):
                members = [name for name in group if name in positions]
                pair_distances = []
                for index, first in enumerate(members):
                    for second in members[index + 1:]:
                        p1, p2 = positions[first], positions[second]
                        manhattan = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
                        pair_distances.append(manhattan)
                if pair_distances:
                    # 距离越大惩罚越小；相邻或同座位区域会受到额外惩罚。
                    max_distance = max(1.0, rows + cols - 2)
                    group_energy += sum(
                        1.0 - min(distance, max_distance) / max_distance
                        for distance in pair_distances
                    ) / len(pair_distances)
                    group_energy += sum(5.0 for distance in pair_distances if distance <= 1)
            height_norm = height_energy / (rows ** 2 + 1)
            height_order_norm = height_order_energy / (rows ** 2 + 1)
            row_profile_norm = row_profile_energy / max(1.0, (max_height - min_height) ** 2)
            group_norm = group_energy / max(1, rows ** 2 + cols ** 2)
            return (
                0.25 * height_norm
                + 0.25 * height_order_norm
                + 0.20 * row_profile_norm
                + 0.30 * group_norm
            )

        # 小团体也必须能够移动，否则分散奖励无法真正改变其座位。
        movable_names = [s[1] for s in students if s[1] not in (reserved_seats or {})]
        action_count = max(1, len(movable_names) * (len(movable_names) - 1) // 2)
        feature_size = 6
        model_version = 3
        config_signature = repr((
            num_students, rows, cols, students_data, enable_optimization, mode,
            teams, sorts, groups, reserved_seats
        )).encode("utf-8")
        config_hash = hashlib.sha256(config_signature).hexdigest()[:16]
        model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "rl_models", f"seat_q_policy_{config_hash}.npz"
        )
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        weights = np.zeros(feature_size, dtype=np.float64)
        loaded_model = False
        if os.path.exists(model_path):
            loaded = np.load(model_path)
            if (loaded.get("model_version", np.array(0)).item() == model_version
                    and loaded.get("weights", np.empty(0)).shape == (feature_size,)):
                weights = loaded["weights"].astype(np.float64)
                loaded_model = True

        def candidate_actions(solution):
            positions = dict(get_positions_map(solution))
            pairs = [(movable_names[i], movable_names[j])
                     for i in range(len(movable_names))
                     for j in range(i + 1, len(movable_names))
                     if movable_names[i] in positions and movable_names[j] in positions]
            random.shuffle(pairs)
            return pairs[:min(96, len(pairs))]

        def apply_swap(solution, first, second):
            positions = dict(get_positions_map(solution))
            result = [row[:] for row in solution]
            p1, p2 = positions[first], positions[second]
            result[p1[0]][p1[1]], result[p2[0]][p2[1]] = result[p2[0]][p2[1]], result[p1[0]][p1[1]]
            return result

        def action_features(current_energy, next_energy, first, second):
            height_gap = abs(
                next(s[2] for s in students if s[1] == first)
                - next(s[2] for s in students if s[1] == second)
            ) / max(1.0, max_height - min_height)
            delta = next_energy - current_energy
            return np.array([1.0, current_energy, next_energy, delta, height_gap, delta * delta], dtype=np.float64)

        def select_action(solution, current_energy, epsilon):
            actions = candidate_actions(solution)
            if not actions:
                return None
            scored = []
            for first, second in actions:
                candidate = apply_swap(solution, first, second)
                candidate_energy = energy(candidate)
                features = action_features(current_energy, candidate_energy, first, second)
                scored.append((float(np.dot(weights, features)), first, second, candidate, candidate_energy, features))
            if random.random() < epsilon:
                return random.choice(scored)
            return max(scored, key=lambda item: item[0])

        # 每个配置独立训练，避免不同班级的奖励分布相互污染。
        training_episodes = 40 if loaded_model else 80
        print(
            f"[RL] Training started ({'fine-tuning' if loaded_model else 'first run'}), "
            f"episodes={training_episodes}, actions={action_count}",
            flush=True,
        )
        for episode in range(training_episodes):
            state = [row[:] for row in current_solution]
            state_energy = energy(state)
            episode_steps = min(400, max(60, action_count * 2))
            for _ in range(episode_steps):
                selected = select_action(state, state_energy, epsilon=0.25)
                if selected is None:
                    break
                _, first, second, next_state, next_energy, features = selected
                reward = state_energy - next_energy
                next_selected = select_action(next_state, next_energy, epsilon=0.0)
                next_value = (next_selected[0] if next_selected else 0.0)
                target = reward + 0.85 * next_value
                weights += 0.03 * (target - float(np.dot(weights, features))) * features
                state, state_energy = next_state, next_energy
            print(
                f"[RL] Training progress: {episode + 1}/{training_episodes}, "
                f"energy={state_energy:.4f}",
                flush=True,
            )
        np.savez(model_path, weights=weights, feature_size=feature_size,
                 model_version=model_version)
        print(f"[RL] Model saved: {model_path}", flush=True)

        best_solution = [row[:] for row in current_solution]
        best_energy = energy(best_solution)
        state = [row[:] for row in current_solution]
        state_energy = best_energy
        optimization_steps = min(800, max(120, action_count * 4))
        print(f"[RL] Inference optimization started: steps={optimization_steps}", flush=True)
        for step in range(optimization_steps):
            selected = select_action(state, state_energy, epsilon=0.05)
            if selected is None:
                break
            _, _, _, next_state, next_energy, _ = selected
            state, state_energy = next_state, next_energy
            if state_energy < best_energy:
                best_solution = [row[:] for row in state]
                best_energy = state_energy
            if (step + 1) % 20 == 0 or step + 1 == optimization_steps:
                print(
                    f"[RL] Inference progress: {step + 1}/{optimization_steps}, "
                    f"best_energy={best_energy:.4f}",
                    flush=True,
                )
        seating_arrangement = best_solution

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