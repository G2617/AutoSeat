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
from concurrent.futures import ProcessPoolExecutor, as_completed
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image, ImageDraw, ImageFont
import AlgorithmFunctions
from AlgorithmFunctions import manhattan_distance, generate_unique_abbreviation
from Debugging import log_record, debug


RL_CPU_RATIO = 0.45
RL_MAX_WORKERS = 6
GROUP_HEIGHT_WEIGHT = 5.0


def _rl_worker_count(task_count):
    """Limit RL process fan-out so the UI remains responsive."""
    cpu_count = os.cpu_count() or 1
    return max(1, min(task_count, RL_MAX_WORKERS, int(cpu_count * RL_CPU_RATIO) or 1))


def _group_candidate_energy(seating, height_by_name, new_teams, groups, rows, cols):
    positions = {
        name: (row, col)
        for row, values in enumerate(seating)
        for col, name in enumerate(values)
        if name not in ('空', '预留空位')
    }
    height_penalty = 0.0
    height_gradient_penalty = 0.0
    for members in new_teams:
        placed = [name for name in members if name in positions]
        for index, first in enumerate(placed):
            for second in placed[index + 1:]:
                row_gap = positions[first][0] - positions[second][0]
                height_gap = height_by_name[first] - height_by_name[second]
                if row_gap * height_gap < 0:
                    height_penalty += abs(row_gap * height_gap) ** 1.25
        rows_with_heights = {}
        for name in placed:
            rows_with_heights.setdefault(positions[name][0], []).append(
                height_by_name[name]
            )
        row_profile = [
            (row, sum(heights) / len(heights))
            for row, heights in sorted(rows_with_heights.items())
        ]
        for (_, previous_height), (_, following_height) in zip(
            row_profile, row_profile[1:]
        ):
            if previous_height > following_height:
                height_gradient_penalty += previous_height - following_height
    connectivity_penalty = 0.0
    for members in new_teams:
        placed = [positions[name] for name in members if name in positions]
        if len(placed) < 2:
            continue
        remaining = set(placed)
        components = 0
        adjacent_edges = 0
        while remaining:
            components += 1
            frontier = [remaining.pop()]
            while frontier:
                current = frontier.pop()
                neighbors = {
                    position for position in remaining
                    if manhattan_distance(position, current) == 1
                }
                adjacent_edges += len(neighbors)
                remaining.difference_update(neighbors)
                frontier.extend(neighbors)
        pair_count = max(1, len(placed) * (len(placed) - 1) // 2)
        connectivity_penalty += 35.0 * max(0, components - 1)
        connectivity_penalty += 2.5 * max(0, len(placed) - 1 - adjacent_edges)
        connectivity_penalty += sum(
            min(
                manhattan_distance(position, other)
                for other in placed if other != position
            )
            for position in placed
        ) / max(1, len(placed))
        bounding_area = (
            max(position[0] for position in placed)
            - min(position[0] for position in placed) + 1
        ) * (
            max(position[1] for position in placed)
            - min(position[1] for position in placed) + 1
        )
        connectivity_penalty += 0.8 * max(0, bounding_area - len(placed))
        connectivity_penalty -= 1.5 * adjacent_edges / pair_count

    group_penalty = 0.0
    for group in groups or []:
        placed = [name for name in group if name in positions]
        for index, first in enumerate(placed):
            for second in placed[index + 1:]:
                distance = manhattan_distance(positions[first], positions[second])
                group_penalty += 1.0 / (1.0 + distance)
                if distance <= 1:
                    group_penalty += 2.0
    return (
        GROUP_HEIGHT_WEIGHT * (
            height_penalty / max(1, rows ** 2)
            + height_gradient_penalty / max(1.0, rows * 100.0)
        )
        + connectivity_penalty
        + group_penalty
    )


def _train_q_episode(payload):
    """Train one independent episode in a separate process."""
    (initial_solution, students, continuous_targets, groups, rows, cols,
     movable_names, initial_weights, max_height, min_height, action_count) = payload
    episode_weights = initial_weights.copy()

    def positions_map(solution):
        return {(student, (i, j))
                for i, row in enumerate(solution)
                for j, student in enumerate(row)
                if student not in ('空', '预留空位')}

    positions_by_student = {
        student[1]: student[2] for student in students
    }

    def energy(solution):
        positions = dict(positions_map(solution))
        height_energy = sum(
            (positions[name][0] - continuous_targets.get(name, (0.0, 0.0))[0]) ** 2
            for _, name, _ in students if name in positions
        )
        height_order_energy = 0.0
        positioned = [student for student in students if student[1] in positions]
        for index, (_, first, first_height) in enumerate(positioned):
            for _, second, second_height in positioned[index + 1:]:
                first_row, second_row = positions[first][0], positions[second][0]
                if first_height < second_height and first_row > second_row:
                    height_order_energy += (first_row - second_row) ** 2
                elif first_height > second_height and first_row < second_row:
                    height_order_energy += (second_row - first_row) ** 2
        row_heights = []
        for row_index in range(rows):
            values = [positions_by_student[name] for name, (row, _) in positions.items()
                      if row == row_index]
            if values:
                row_heights.append((row_index, sum(values) / len(values)))
        row_profile_energy = sum(
            max(0.0, previous - following) ** 2
            for (_, previous), (_, following) in zip(row_heights, row_heights[1:])
        )
        group_energy = 0.0
        for group in (groups or []):
            members = [name for name in group if name in positions]
            distances = []
            for index, first in enumerate(members):
                for second in members[index + 1:]:
                    p1, p2 = positions[first], positions[second]
                    distances.append(abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]))
            if distances:
                max_distance = max(1.0, rows + cols - 2)
                group_energy += sum(
                    1.0 - min(distance, max_distance) / max_distance
                    for distance in distances
                ) / len(distances)
                group_energy += sum(5.0 for distance in distances if distance <= 1)
        return (
            0.25 * height_energy / (rows ** 2 + 1)
            + 0.25 * height_order_energy / (rows ** 2 + 1)
            + 0.20 * row_profile_energy / max(1.0, (max_height - min_height) ** 2)
            + 0.30 * group_energy / max(1, rows ** 2 + cols ** 2)
        )

    def apply_swap(solution, first, second):
        positions = dict(positions_map(solution))
        result = [row[:] for row in solution]
        p1, p2 = positions[first], positions[second]
        result[p1[0]][p1[1]], result[p2[0]][p2[1]] = (
            result[p2[0]][p2[1]], result[p1[0]][p1[1]]
        )
        return result

    def select_action(solution, current_energy, epsilon):
        positions = dict(positions_map(solution))
        actions = [
            (movable_names[i], movable_names[j])
            for i in range(len(movable_names))
            for j in range(i + 1, len(movable_names))
            if movable_names[i] in positions and movable_names[j] in positions
        ]
        random.shuffle(actions)
        scored = []
        for first, second in actions[:min(96, len(actions))]:
            candidate = apply_swap(solution, first, second)
            candidate_energy = energy(candidate)
            height_gap = abs(
                positions_by_student[first] - positions_by_student[second]
            ) / max(1.0, max_height - min_height)
            delta = candidate_energy - current_energy
            features = np.array(
                [1.0, current_energy, candidate_energy, delta, height_gap, delta * delta],
                dtype=np.float64,
            )
            scored.append((
                float(np.dot(episode_weights, features)), candidate, candidate_energy,
                features,
            ))
        if not scored:
            return None
        if random.random() < epsilon:
            return random.choice(scored)
        return max(scored, key=lambda item: item[0])

    state = [row[:] for row in initial_solution]
    state_energy = energy(state)
    episode_steps = min(400, max(60, action_count * 2))
    for _ in range(episode_steps):
        selected = select_action(state, state_energy, epsilon=0.25)
        if selected is None:
            break
        _, next_state, next_energy, features = selected
        reward = state_energy - next_energy
        next_selected = select_action(next_state, next_energy, epsilon=0.0)
        next_value = next_selected[0] if next_selected else 0.0
        target = reward + 0.85 * next_value
        episode_weights += (
            0.03 * (target - float(np.dot(episode_weights, features))) * features
        )
        state, state_energy = next_state, next_energy
    return episode_weights, state_energy, state

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
        model_version = 4
        imported_config_path = AlgorithmFunctions.imported_json_file_path
        if imported_config_path and os.path.isfile(imported_config_path):
            # 直接对 JSON 原始字节做 SHA-256；同名文件内容变化必然得到新模型键。
            with open(imported_config_path, "rb") as config_file:
                config_hash = hashlib.sha256(config_file.read()).hexdigest()
            model_source = os.path.basename(imported_config_path)
        else:
            # 自定义输入没有 JSON 文件时，使用等价配置内容作为回退指纹。
            config_signature = repr((
                num_students, rows, cols, students_data, enable_optimization, mode,
                teams, sorts, groups, reserved_seats
            )).encode("utf-8")
            config_hash = hashlib.sha256(config_signature).hexdigest()
            model_source = "runtime-input"
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
                    and loaded.get("config_hash", np.array("")).item() == config_hash
                    and loaded.get("weights", np.empty(0)).shape == (feature_size,)):
                weights = loaded["weights"].astype(np.float64)
                loaded_model = True
        print(
            f"[RL] Model binding: source={model_source}, sha256={config_hash}, "
            f"loaded={loaded_model}",
            flush=True,
        )

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

        def select_action(solution, current_energy, epsilon, policy_weights):
            actions = candidate_actions(solution)
            if not actions:
                return None
            scored = []
            for first, second in actions:
                candidate = apply_swap(solution, first, second)
                candidate_energy = energy(candidate)
                features = action_features(current_energy, candidate_energy, first, second)
                scored.append((float(np.dot(policy_weights, features)), first, second,
                               candidate, candidate_energy, features))
            if random.random() < epsilon:
                return random.choice(scored)
            return max(scored, key=lambda item: item[0])

        # 每个配置独立训练，避免不同班级的奖励分布相互污染。
        training_episodes = 6 if loaded_model else 48
        worker_count = _rl_worker_count(training_episodes)
        print(
            f"[RL] Training started ({'fine-tuning' if loaded_model else 'first run'}), "
            f"episodes={training_episodes}, actions={action_count}, "
            f"workers={worker_count}, total_tasks={training_episodes}, "
            f"completed=0/{training_episodes} (0%)",
            flush=True,
        )

        worker_payload = (
            current_solution, students, continuous_targets, groups, rows, cols,
            movable_names, weights, max_height, min_height, action_count
        )
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(_train_q_episode, worker_payload)
                for _ in range(training_episodes)
            ]
            episode_results = []
            for episode, future in enumerate(as_completed(futures), start=1):
                episode_results.append(future.result())
                energies = [result[1] for result in episode_results]
                completion = episode * 100 / training_episodes
                print(
                    f"[RL] Training progress: {episode}/{training_episodes}, "
                    f"current={energies[-1]:.4f}, mean={np.mean(energies):.4f}, "
                    f"best={min(energies):.4f}, completed={episode}/"
                    f"{training_episodes} ({completion:.1f}%)",
                    flush=True,
                )

        # 并行 episode 从同一初始布局出发；采用精英轨迹，避免平均权重稀释低能量策略。
        best_training_result = min(episode_results, key=lambda result: result[1])
        weights = best_training_result[0]
        np.savez(model_path, weights=weights, feature_size=feature_size,
                 model_version=model_version, config_hash=config_hash)
        print(
            f"[RL] Finished: tasks={training_episodes}, "
            f"best_energy={best_training_result[1]:.4f}, "
            f"mean_energy={np.mean([result[1] for result in episode_results]):.4f}, "
            f"completed={training_episodes}/{training_episodes} (100%)",
            flush=True,
        )
        print(f"[RL] Model saved: {model_path}", flush=True)

        best_solution = [row[:] for row in best_training_result[2]]
        best_energy = energy(best_solution)
        state = [row[:] for row in best_solution]
        state_energy = best_energy
        optimization_steps = min(800, max(120, action_count * 4))
        print(f"[RL] Inference optimization started: steps={optimization_steps}", flush=True)
        for step in range(optimization_steps):
            selected = select_action(state, state_energy, epsilon=0.05,
                                     policy_weights=weights)
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
        # 小组模式采用按优先级的随机化连通区域搜索，不使用强化学习。
        reserved_seats = reserved_seats or {}
        height_by_name = {student[1]: student[2] for student in students_data}
        new_teams = [
            [name for name in team if name not in reserved_seats]
            for team in (teams or [])
        ]
        available_seat_count = rows * cols - len(reserved_seats) - max(
            0, rows * cols - num_students
        )
        required_team_seats = sum(len(team) for team in new_teams)
        if required_team_seats > available_seat_count:
            raise gr.Error(
                f"目标小组共需要 {required_team_seats} 个座位，但当前只有 "
                f"{available_seat_count} 个可用座位"
            )
        team_order = sorted(
            range(len(new_teams)),
            key=lambda index: sorts[index] if index < len(sorts) else index + 1,
        )

        def make_base_layout():
            seating = [['空'] * cols for _ in range(rows)]
            for name, (row, col) in reserved_seats.items():
                if not (0 <= row < rows and 0 <= col < cols):
                    raise ValueError("预留座位位置超出范围，请检查")
                seating[row][col] = name
            empty_count = rows * cols - num_students
            empty_positions = [
                (row, col) for row in range(rows) for col in range(cols)
                if seating[row][col] == '空'
            ]
            for row, col in empty_positions[-empty_count:] if empty_count > 0 else []:
                seating[row][col] = '预留空位'
            return seating

        def grow_region(start, size, seating, rng):
            """Grow a connected region without recursive DFS backtracking."""
            if size <= 0 or seating[start[0]][start[1]] != '空':
                return None
            region = [start]
            region_set = {start}
            while len(region) < size:
                frontier = {
                    (row + row_delta, col + col_delta)
                    for row, col in region
                    for row_delta, col_delta in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if (
                        0 <= row + row_delta < rows
                        and 0 <= col + col_delta < cols
                        and (row + row_delta, col + col_delta) not in region_set
                        and seating[row + row_delta][col + col_delta] == '空'
                    )
                }
                if not frontier:
                    return None
                choices = list(frontier)
                rng.shuffle(choices)
                choices.sort(key=lambda seat: (
                    sum(manhattan_distance(seat, existing) for existing in region),
                    rng.random(),
                ))
                next_seat = choices[0]
                region.append(next_seat)
                region_set.add(next_seat)
            return tuple(region)

        def place_team(seating, team, region):
            result = [row[:] for row in seating]
            ordered_members = sorted(team, key=lambda name: height_by_name.get(name, 0))
            for seat, name in zip(sorted(region, key=lambda value: (value[0], value[1])), ordered_members):
                result[seat[0]][seat[1]] = name
            return result

        def generate_layout(seed):
            rng = random.Random(seed)
            seating = make_base_layout()
            for team_index in team_order:
                team = new_teams[team_index]
                if not team:
                    continue
                starts = [
                    (row, col) for row in range(rows) for col in range(cols)
                    if seating[row][col] == '空'
                ]
                rng.shuffle(starts)
                candidates = []
                for start in starts[:min(96, len(starts))]:
                    region = grow_region(start, len(team), seating, rng)
                    if region is None:
                        continue
                    candidate = place_team(seating, team, region)
                    score = _group_candidate_energy(
                        candidate, height_by_name, [team], groups, rows, cols
                    )
                    score += 0.18 * sum(
                        manhattan_distance(start, seat) for seat in region
                    ) + rng.random() * 0.5
                    candidates.append((score, candidate))
                if not candidates:
                    return None
                _, seating = min(candidates, key=lambda item: item[0])
            remaining = [
                student for student in students_data
                if student[1] not in reserved_seats
                and all(student[1] not in team for team in new_teams)
            ]
            rng.shuffle(remaining)
            for row in range(rows):
                for col in range(cols):
                    if seating[row][col] == '空' and remaining:
                        seating[row][col] = remaining.pop()[1]
            return seating

        candidate_results = []
        seed_base = random.SystemRandom().randrange(1, 2**31 - 1)
        candidate_count = 60
        for candidate_index in range(candidate_count):
            candidate = None
            for retry in range(8):
                candidate = generate_layout(
                    seed_base + candidate_index * 104729 + retry * 1009
                )
                if candidate is not None:
                    break
            if candidate is not None:
                energy = _group_candidate_energy(
                    candidate, height_by_name, new_teams, groups, rows, cols
                )
                candidate_results.append((energy, candidate))
            if (candidate_index + 1) % 3 == 0:
                print(
                    f"[GROUP-SEARCH] Progress: {candidate_index + 1}/{candidate_count} "
                    f"({(candidate_index + 1) * 100 / candidate_count:.1f}%), "
                    f"valid={len(candidate_results)}",
                    flush=True,
                )
        if not candidate_results:
            raise gr.Error(
                "无法为目标小组生成连通区域。请检查预留座位是否把可用座位切割成多个小块，"
                "或减少小组人数、增加行列数后重试"
            )
        selected_energy, seating_arrangement = min(candidate_results, key=lambda item: item[0])
        print(
            f"[GROUP-SEARCH] Finished: candidates={len(candidate_results)}/{candidate_count}, "
            f"best_energy={selected_energy:.4f}, priority_order={team_order}",
            flush=True,
        )
        if _check_seating(seating_arrangement):
            log_record("Successed", seating_arrangement, "Priority-based connected group search completed.")
            return seating_arrangement
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