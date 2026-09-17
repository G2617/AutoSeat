import os
import cv2
import numpy as np
import gradio as gr
from mtcnn import MTCNN
from sklearn.cluster import KMeans

# 全局变量用于缓存检测结果
cached_image = None
cached_face_locations = None
cached_face_landmarks = None
cached_face_images = None
user_inputs = [] # 用户输入元组
cached_face_midpoints = []  # 缓存人脸中心点
calibration_line_y_state = -1 # 水平校准线位置
step_interval_state = 0 # 台阶间隔
calculate_heights = [] # 计算的身高

posture_scores = {
    "坐在地上，例如盘腿坐或屈膝坐": 0.52,
    "蹲姿": 0.56,
    "单膝跪地": 0.7,
    "坐在椅子上": 0.75,
    "弯腰屈膝，即手扶膝盖": 0.91,
    "站姿": 1
}

print("正在启动人脸检测工具...")


def find_images_in_dir():
    """查找程序源文件所在目录下的所有图片文件"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_extensions = ['.png', '.jpg', '.jpeg']
    images = []
    for root, dirs, files in os.walk(script_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                images.append(os.path.join(root, file))
    return images


def detect_faces(image_path):
    """使用MTCNN模型检测人脸并缓存结果"""
    global cached_image, cached_face_locations, cached_face_landmarks, cached_face_images
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # 将BGR转换为RGB

    detector = MTCNN()
    faces = detector.detect_faces(image_rgb)

    face_locations = []
    face_landmarks = []
    face_images = []

    for face in faces:
        x, y, w, h = face['box']
        x1, y1 = abs(x), abs(y)
        x2, y2 = x1 + w, y1 + h
        face_locations.append((y1, x2, y2, x1))

        landmarks = face['keypoints']
        face_landmarks.append(landmarks)

        face_image = image_rgb[y1:y2, x1:x2]
        face_images.append(face_image)

    # 缓存检测结果
    cached_image = image_rgb  # 缓存RGB格式的图像
    cached_face_locations = face_locations
    cached_face_landmarks = face_landmarks
    cached_face_images = face_images

    gr.Info(f"成功检测到{len(face_locations)}个人脸")
    return image_rgb, face_locations, face_landmarks, face_images


def draw_all_boxes():
    """绘制所有检测到的人脸框和眉心红点"""
    global cached_image, cached_face_locations, cached_face_landmarks, cached_face_midpoints
    if cached_image is None:
        return None

    img = cached_image.copy()
    height, width = img.shape[:2]
    cached_face_midpoints = []  # 清空缓存（关键修改）

    for i, (top, right, bottom, left) in enumerate(cached_face_locations):
        # 限制坐标范围
        top = max(0, min(top, height))
        right = max(0, min(right, width))
        bottom = max(0, min(bottom, height))
        left = max(0, min(left, width))

        # 绘制绿色矩形框
        cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)

        # 计算人脸中心点并上移（仅保留y坐标）
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        offset_y = (bottom - top) // 5
        mid_y = center_y - offset_y  # 仅取y坐标（关键修改）
        mid_point = (center_x, mid_y)  # 用于绘制红点

        mid_point = (max(0, min(mid_point[0], width - 1)), max(0, min(mid_point[1], height - 1)))
        cached_face_midpoints.append(mid_y)  # 缓存y坐标（关键修改）
        cv2.circle(img, mid_point, 2, (255, 0, 0), 2)

        # 添加序号标注
        cv2.putText(img, str(i + 1), (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 180, 255), 2)
    return img


def draw_single_box(selected_index):
    """绘制选中人脸的框和眉心红点"""
    global cached_image, cached_face_locations, cached_face_landmarks
    if cached_image is None or selected_index < 0 or selected_index >= len(cached_face_locations):
        return None

    img = cached_image.copy()
    height, width = img.shape[:2]
    top, right, bottom, left = cached_face_locations[selected_index]
    landmarks = cached_face_landmarks[selected_index]

    # 限制坐标范围
    top = max(0, min(top, height))
    right = max(0, min(right, width))
    bottom = max(0, min(bottom, height))
    left = max(0, min(left, width))

    # 绘制绿色矩形框
    cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)
    # 计算人脸中心点并上移
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    offset_y = (bottom - top) // 5
    mid_point = (center_x, center_y - offset_y)

    mid_point = (max(0, min(mid_point[0], width - 1)), max(0, min(mid_point[1], height - 1)))
    cv2.circle(img, mid_point, 2, (255, 0, 0), 2)

    # 添加序号标注
    cv2.putText(img, str(selected_index + 1), (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 180, 255), 2)
    return img


def show_all_faces():
    """生成所有检测到的人脸缩略图"""
    target_size = 100
    resized_faces = []
    for face in cached_face_images:
        h, w = face.shape[:2]
        scale = target_size / max(h, w)
        resized = cv2.resize(face, (int(w * scale), int(h * scale)))
        # 添加填充以确保所有图像尺寸一致
        pad_h = target_size - resized.shape[0]
        pad_w = target_size - resized.shape[1]
        resized = cv2.copyMakeBorder(resized, 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=[0, 0, 0])
        resized_faces.append(resized)

    num_faces = len(resized_faces)
    rows = (num_faces + 7) // 8
    combined = np.zeros((rows * target_size, 8 * target_size, 3), dtype=np.uint8)

    for i, face in enumerate(resized_faces):
        row = i // 8
        col = i % 8
        combined[row * target_size:(row + 1) * target_size,
                 col * target_size:(col + 1) * target_size] = face
        text = str(i + 1)
        text_x = col * target_size + target_size // 2
        text_y = (row + 1) * target_size - 10
        cv2.putText(combined, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
    return combined


def cluster_faces_by_height():
    """根据人脸的垂直位置进行聚类"""
    if cached_face_locations is None or len(cached_face_locations) == 0:
        return [], 0, 0
    # 提取人脸的垂直中心位置
    centers_y = np.array([(top + bottom) // 2 for top, _, bottom, _ in cached_face_locations]).reshape(-1, 1)
    min_app = min(top for top, _, _, _ in cached_face_locations)
    max_app = max(bottom for _, _, bottom, _ in cached_face_locations)
    target_height = max(abs(bottom - top) for top, _, bottom, _ in cached_face_locations)
    # 估计聚类数量
    height = cached_image.shape[0]
    max_clusters = min(abs(max_app - min_app) // (target_height * 1), 10)
    kmeans = KMeans(n_clusters=min(len(cached_face_locations), max_clusters))
    kmeans.fit(centers_y)
    labels = kmeans.labels_
    # 按聚类中心从下到上排序
    sorted_indices = np.argsort(kmeans.cluster_centers_.flatten())
    label_mapping = {old_label: new_label + 1 for new_label, old_label in enumerate(sorted_indices)}
    new_labels = [label_mapping[label] for label in labels]
    return new_labels, min_app, max_app


def draw_all_boxes_with_clusters():
    """绘制所有检测到的人脸框和聚类行号"""
    global cached_image, cached_face_locations, cached_face_landmarks
    if cached_image is None:
        return None

    img = cached_image.copy()
    height, width = img.shape[:2]
    cluster_labels, h_min, h_max = cluster_faces_by_height()

    cv2.line(img, (0, h_min), (width, h_min), (255, 0, 0), 2)
    cv2.line(img, (0, h_max), (width, h_max), (255, 0, 0), 2)

    for i, (top, right, bottom, left) in enumerate(cached_face_locations):
        # 限制坐标范围
        top = max(0, min(top, height))
        right = max(0, min(right, width))
        bottom = max(0, min(bottom, height))
        left = max(0, min(left, width))

        # 绘制绿色矩形框
        cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)

        # 计算人脸中心点并上移
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        offset_y = (bottom - top) // 5
        mid_point = (center_x, center_y - offset_y)

        mid_point = (max(0, min(mid_point[0], width - 1)), max(0, min(mid_point[1], height - 1)))
        cv2.circle(img, mid_point, 2, (255, 0, 0), 2)

        # 添加聚类行号标注
        row_number = cluster_labels[i]
        cv2.putText(img, str(row_number), (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 180, 255), 2)
    return img


def download_selected_face(selected_index):
    """下载选中的人脸图片"""
    if selected_index < 0 or selected_index >= len(cached_face_images):
        return None

    target_size = 250
    face = cached_face_images[selected_index]
    h, w = face.shape[:2]
    scale = target_size / max(h, w)
    resized = cv2.resize(face, (int(w * scale), int(h * scale)))

    temp_file = f"face_{selected_index}.png"
    cv2.imwrite(temp_file, cv2.cvtColor(resized, cv2.COLOR_RGB2BGR))  # 保存为BGR格式
    return temp_file

def create_input_components(n_clusters):
    """创建动态的台阶数和姿势选择组件"""
    step_inputs = []
    posture_inputs = []
    with gr.Accordion("输入每行信息", open=True):
        for i in range(1, n_clusters + 1):
            with gr.Row():
                step_input = gr.Number(label=f"第 {i} 行所在台阶数", value=1)
                posture_input = gr.Dropdown(
                    choices=["坐在地上，例如盘腿坐或屈膝坐", "蹲姿", "单膝跪地", "坐在椅子上", "弯腰屈膝，即手扶膝盖", "站姿"],
                    label=f"第 {i} 行姿势",
                    value="站姿"
                )
                step_inputs.append(step_input)
                posture_inputs.append(posture_input)
    return step_inputs, posture_inputs


def submit_inputs(visible_rows, steps, *all_inputs):  # 可见行索引 + 所有输入值
        """收集可见行的输入数据并验证"""
        global user_inputs
        user_inputs = []
        # all_inputs 格式 [step_1, posture_1, step_2, posture_2, ..., step_10, posture_10]
        for i in visible_rows:
            step = all_inputs[2*i]    # 第i行的台阶数（索引2*i）
            posture = all_inputs[2*i+1]  # 第i行的姿势（索引2*i+1）
            
            if step is None or posture is None:
                raise gr.Error(f"第{i+1}行输入不完整，请检查")
                return ""
            if posture not in posture_scores:
                raise gr.Error(f"第{i+1}行{posture}姿势选择无效")
                return ""
            if step < 1 or step > max(1, steps):
                raise gr.Error(f"第{i+1}行台阶数{step}越界")
                return ""
            if not isinstance(step, int):
                raise gr.Error(f"第{i+1}行台阶数{step}非正整数")
                return ""
            user_inputs.append((step, posture_scores[posture]))
        return str(user_inputs)

def draw_calibration_line(img, line_y):
    """在图片上绘制水平校准红线"""
    if img is None:
        return None
    img_with_line = img.copy()
    line_y = int(line_y)  # 确保为整数像素坐标
    cv2.line(img_with_line, (0, line_y), (img.shape[1], line_y), (255, 0, 0), 2)  # 绘制红线
    return img_with_line

def main():
    # 预加载图片
    images = find_images_in_dir()
    image_names = [os.path.basename(img) for img in images]

    with gr.Blocks(title="快捷图片输入辅助模式") as demo:
        all_marks_state = gr.State(None)
        total_steps_state = gr.State(1)  #总台阶数
        gr.Markdown("**欢迎使用班级座位排列辅助图片输入工具** *Powered by Jiang*")
        gr.Markdown("此界面为快捷图片输入辅助模式，如果在主界面更改了模式，那么此界面会改变")
        gr.Markdown("\n**请选择需要程序目录下导入的图片** 导入图片必须为班级合照，人脸尽量无遮挡，学生脚部在画面中，画面水平且透视效果较小")
        image_selector = gr.Dropdown(choices=image_names, label="请选择图片文件", interactive=True)
        select_button = gr.Button("选择此图片")

        with gr.Row():
            with gr.Column():
                all_marks_view = gr.Image(label="全部标记视图", interactive=False)
                gr.Markdown("**下面是人脸缩略图，后面要用于对照结果，请点击右上角下载暂存备用**")
                all_faces_view = gr.Image(label="所有人脸缩略图", interactive=False)
                cluster_view = gr.Image(label="所在行视图", interactive=False)
            with gr.Column():
                face_selector = gr.Textbox(label="请输入需要查看的人脸序号", interactive=True)
                main_image = gr.Image(label="选中的人脸所在位置", interactive=False)
                selected_face = gr.Image(label="选中的人脸图片", interactive=False)
                download_btn = gr.Button("下载选中的人脸图片")
                download_file = gr.File(label="下载图片")

        gr.Markdown("**身高校准**    请根据图片中学生状态进行填写")
        gr.Markdown("**下方输入照片中学生处在的台阶数量**    更改此项的值会让列表重置，所以请先进行输入。若全体学生处在平地上，请跳过本输入框，直接设置表格")
        total_steps_input = gr.Number(label="学生处在台阶数量输入", interactive=True)
        gr.Markdown("每行具体处在的台阶数是从高往低数第几个台阶")

        # 输入行组件（原Accordion）
        MAX_ROWS = 10
        row_components = []
        with gr.Accordion("输入每行信息", open=True):
            for i in range(1, MAX_ROWS + 1):
                with gr.Row(visible=False) as row:  # 初始隐藏
                    step_input = gr.Number(label=f"第 {i} 行台阶数", value=1)
                    # 关键改进：显式声明姿势选择组件可交互
                    posture_input = gr.Dropdown(
                        choices=["坐在地上，例如盘腿坐或屈膝坐", "蹲姿", "单膝跪地", "坐在椅子上", "弯腰屈膝，即手扶膝盖", "站姿"],
                        label=f"第 {i} 行姿势",
                        value="站姿",
                        interactive=True  # 显式声明可交互
                    )
                row_components.append((row, step_input, posture_input))  # 存储行容器和输入组件

        # 状态变量 当前聚类行数
        n_clusters_state = gr.State(0)
        visible_rows_state = gr.State([])

        # 结果输出组件
        result_textbox = gr.Textbox(label="内容输出", interactive=False, visible=False)
        submit_btn = gr.Button("提交")

        with gr.Row(visible=False) as calibration_group:
            with gr.Column():
                calibration_view = gr.Image(label="身高校准视图", interactive=False)
            with gr.Column():
                gr.Markdown("请调整滑杆直到图片中红线紧贴最前面同学的脚尖，即首个台阶位置")
                calibration_slider = gr.Slider(
                    minimum=0,
                    maximum=0,
                    step=1,
                    label="身高校准线位置",
                    info="拖动滑杆调整水平校准线位置"
                )
                # 新增：滑杆下方的提交按钮
                calibration_submit_btn = gr.Button("确认校准线位置")
                gr.Markdown("请设置台阶高度间隔")
                step_interval_slider = gr.Slider(
                    minimum=0,
                    maximum=0,
                    step=1,
                    label="台阶高度间隔",
                    info="根据台阶数自动计算范围",
                    visible=False  # 初始隐藏，基准线保存后显示
                )
                # 新增：确定间隔并计算身高按钮
                confirm_interval_btn = gr.Button("确定间隔并计算身高", visible=False)
                gr.Markdown("以下是身高计算结果，全选拷贝后进入自定义模式进行学生信息输入，学生数量为人脸数量且不要启用秩序优化模式。学号的排座结果产生后对照请人脸缩略图表")
                calculated_heights_state = gr.Textbox(label="身高计算结果", interactive=True)  # 用于显示计算结果

        # ---------------- 核心交互逻辑 ----------------
        def update_face_selector(image_path):
            """选择图片后更新聚类结果，并显示对应行数的输入组件"""
            global cached_image, cached_face_locations, cached_face_landmarks, cached_face_images
            gr.Info("图片导入成功，请等待识别")
            full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), image_path)
            detect_faces(full_path)
            all_boxes_img = draw_all_boxes()  # 全标注图片（含人脸框和序号）
            all_faces_img = show_all_faces()
            cluster_img = draw_all_boxes_with_clusters()
            n_clusters = len(set(cluster_faces_by_height()[0]))
            n_clusters = min(n_clusters, MAX_ROWS)

            img_height = cached_image.shape[0] if cached_image is not None else 0
            visible_rows = list(range(n_clusters))
            row_updates = [gr.update(visible=(i in visible_rows)) for i in range(MAX_ROWS)]
            step_values = [1] * MAX_ROWS
            return (
                all_boxes_img, all_faces_img, cluster_img,  # 原有图像输出
                *row_updates,
                *step_values,
                n_clusters,
                visible_rows,
                gr.update(maximum=img_height),
                all_boxes_img,  # 校准视图初始底图改为全标注图片（关键修改）
                all_boxes_img   # 输出到all_marks_state缓存全标注图（关键修改）
            )

        def update_total_steps(total_steps, n_clusters):
            """输入台阶数后，自动填充每行的台阶值"""
            if total_steps < 1 or total_steps > n_clusters or not isinstance(total_steps, int):
                raise gr.Error(f"输入必须为不超过{n_clusters}的正整数")
                return [1] * MAX_ROWS  # 保持原值
            
            # 计算每行的台阶值（类似原HTML表格的逻辑）
            step_values = []
            for i in range(1, MAX_ROWS + 1):
                if i <= n_clusters:
                    if i <= (n_clusters // total_steps) * total_steps:
                        step = (i - 1) // (n_clusters // total_steps) + 1
                    else:
                        step = total_steps
                    step_values.append(step)
                else:
                    step_values.append(1)  # 隐藏行保持默认值
            return step_values
        
        def update_calibration_view(all_marks_img, line_y):
            """基于全标注图片绘制红线"""
            return draw_calibration_line(all_marks_img, line_y)

        def update_step_interval_range(base_line_y, total_steps, img_height):
            """动态计算台阶间隔滑杆的最大/最小值"""
            base_line_y = base_line_y[0] if isinstance(base_line_y, (tuple, list)) else base_line_y
            if total_steps == 1:
                gr.Info("台阶数为1，无需设置间隔")
                return gr.update(visible=True, minimum=img_height//100, maximum=img_height//100, interactive=False, value=img_height//100)  # 仅返回滑杆更新
            if not isinstance(base_line_y, (int, float)) or base_line_y is None:
                raise gr.Error("请先确认基准线位置")
                return gr.update(visible=False)  # 仅返回滑杆更新
            
            min_interval = img_height // 100
            max_interval = int(base_line_y) // (total_steps - 1)
            return gr.update(visible=True, minimum=min_interval, maximum=max_interval, interactive=True)  # 仅返回滑杆更新

        def draw_step_lines(all_marks_img, base_line_y, interval, total_steps):
            """基于全标注图绘制多条等距红线（修复类型错误）"""
            if all_marks_img is None or base_line_y is None or interval is None or total_steps < 1:
                return all_marks_img
            
            # 关键修复 处理可能的元组/列表包裹，提取数值
            base_line_y = base_line_y[0] if isinstance(base_line_y, (tuple, list)) else base_line_y
            interval = interval[0] if isinstance(interval, (tuple, list)) else interval
            
            img_with_lines = all_marks_img.copy()
            for i in range(total_steps):
                line_y = base_line_y - i * interval
                line_y = int(max(0, line_y))  # 确保不超出图片顶部
                cv2.line(img_with_lines, (0, line_y), (img_with_lines.shape[1], line_y), (255, 0, 0), 2)
            return img_with_lines
        
        def calculate_heights():
            """核心函数 计算每个人脸的实际身高"""
            global user_inputs, calibration_line_y_state, step_interval_state, calculate_heights
            # 1. 获取必要状态变量
            calibration_line_y = calibration_line_y_state
            step_interval = step_interval_state
            user_inputs_data = user_inputs  # 格式 [(step_1, multiplier_1), (step_2, multiplier_2), ...]
            cluster_labels, _, _ = cluster_faces_by_height()  # 获取人脸所属行号（从1开始）
            
            # 2. 验证必要参数已初始化
            if None in [calibration_line_y, step_interval] or not user_inputs_data or not cluster_labels:
                raise gr.Error("请先完成校准线确认，间隔设置和行信息输入")
                return []
            
            # 3. 按行处理计算身高
            calculated_heights = [0] * len(cached_face_midpoints)  # 初始化结果列表（按人脸标号顺序）
            max_steps = -1
            rows = 0
            for _, (step_number, _) in enumerate(user_inputs_data, start=1):
                if step_number > max_steps:
                    max_steps = step_number
                rows += 1
            for row_idx, (step_number, posture_multiplier) in enumerate(user_inputs_data, start=1):  # 行号从1开始
                # 计算该行起始线y坐标（校准线 - 间隔*(台阶数-1)）
                if max_steps == 1:
                    row_start_y = calibration_line_y - step_interval * (rows - row_idx)
                else:
                    row_start_y = calibration_line_y - step_interval * (max_steps - step_number)
                
                # 找到属于当前行的人脸索引
                face_indices = [i for i, label in enumerate(cluster_labels) if label == row_idx]
                
                # 计算这些人脸的身高
                for face_idx in face_indices:
                    mid_y = cached_face_midpoints[face_idx]  # 该人脸眉心y坐标
                    distance = row_start_y - mid_y  # 像素距离（起始线在下方，眉心在上方）
                    if distance <= 0:
                        gr.Warning(f"人脸{face_idx+1}的眉心位置高于行起始线，可能输入错误")
                    actual_height = distance / posture_multiplier  # 实际身高（像素单位，需根据比例尺转换）
                    calculated_heights[face_idx] = actual_height  # 按标号顺序存储
            
            min_height = min(height for height in calculated_heights if height > 0)  # 过滤掉0
            radio = round(150 / min_height, 2)
            for i in range(len(calculated_heights)):
                calculated_heights[i] = round(calculated_heights[i] * radio, 2)
            result_lines = []
            for idx, height in enumerate(calculated_heights):
                # 生成三位不重复小写字母（按aaa,aab,aac...顺序）
                # 计算各位置字母偏移量（支持最多26^3=17576个唯一名称）
                part1 = idx // (26**2)
                part2 = (idx // 26) % 26
                part3 = idx % 26
                # 转换为字母（超出26的部分自动循环，但实际人脸数量不会超过这个范围）
                name = f"{chr(ord('a') + part1 % 26)}{chr(ord('a') + part2 % 26)}{chr(ord('a') + part3 % 26)}"
                result_lines.append(f"{idx+1} {name} {height}")
            
            return '\n'.join(result_lines)  # 返回格式化字符串

        select_button.click(
            lambda image_path: (*update_face_selector(image_path), 1),  # 初始台阶数为1
            inputs=image_selector,
            outputs=[
                all_marks_view, all_faces_view, cluster_view,
                *[row[0] for row in row_components],
                *[row[1] for row in row_components],
                n_clusters_state,
                visible_rows_state,
                calibration_slider,
                calibration_view,
                all_marks_state,
                total_steps_state  # 新增：初始化台阶数状态
            ]
        )

        # 输入台阶数后更新（同步到状态变量）
        total_steps_input.change(
            lambda steps: steps,
            inputs=total_steps_input,
            outputs=[total_steps_state]
        ).then(
            lambda: gr.Info(f"已设置台阶数为{steps}个")
        ).then(
            fn=lambda steps, n_clusters: (*update_total_steps(steps, n_clusters), steps),  # 返回填充值和台阶数
            inputs=[total_steps_input, n_clusters_state],  # 输入台阶数和聚类行数
            outputs=[*[row[1] for row in row_components], total_steps_state]  # 输出：台阶输入框 + 状态变量
        )

        # 提交按钮点击后收集数据
        submit_btn.click(
            lambda visible_rows, steps, *all_inputs: (
                submit_inputs(visible_rows, steps, *all_inputs),  # 原有数据提交逻辑
                gr.update(visible=True),  # 显示校准组件
                cached_image.copy() if cached_image is not None else None,  # 初始化校准视图
                cached_image.shape[0] if cached_image is not None else 0  # 设置滑杆最大值
            ),
            inputs=[
                visible_rows_state, total_steps_input,
                *[comp for row in row_components for comp in (row[1], row[2])]
            ],
            outputs=[
                result_textbox,  # 原有输出
                calibration_group,  # 控制校准组件可见性
                calibration_view,  # 初始化校准视图
                calibration_slider  # 设置滑杆最大值
            ]
        )

        calibration_slider.change(
            update_calibration_view,
            inputs=[all_marks_state, calibration_slider],  # 使用全标注图状态作为底图（关键修改）
            outputs=calibration_view
        )

        # 其他原有事件（人脸选择、下载等）保持不变
        face_selector.change(
            lambda index: (draw_single_box(int(index)-1) if index else None, 
                          cached_face_images[int(index)-1] if index else None),
            inputs=face_selector,
            outputs=[main_image, selected_face]
        )

        download_btn.click(
            lambda index: download_selected_face(int(index)-1) if index and index.isdigit() else None,
            inputs=face_selector,
            outputs=download_file
        )

        def line_y_change(y):
            global calibration_line_y_state
            calibration_line_y_state = y  # 更新状态变量
            return

        calibration_submit_btn.click(
            # 1. 保存基准线位置到状态变量
            lambda i: line_y_change(i),
            inputs=calibration_slider,
            outputs=None
        ).then(
            # 2. 计算滑杆范围并更新可见性（关键改进）
            fn=lambda line_y, steps, img: (update_step_interval_range(line_y, steps, img.shape[0]), gr.update(visible=True)),  # 同时显示间隔按钮
            inputs=[calibration_slider, total_steps_state, all_marks_state],
            outputs=[step_interval_slider, confirm_interval_btn]  # 输出滑杆更新和按钮可见性
        ).then(
            # 3. 显示最终保存提示（可选增强）
            lambda line_y: gr.Info(f"校准线位置已保存为{line_y}像素，台阶间隔滑杆已启用"),
            inputs=calibration_slider
        )

        # 间隔滑杆拖动时更新校准视图（绘制多红线）
        step_interval_slider.change(
            lambda all_marks_img, base_line_y, interval, steps: 
                draw_step_lines(all_marks_img, base_line_y, interval, steps),
            inputs=[all_marks_state, calibration_slider, step_interval_slider, total_steps_state],
            outputs=calibration_view
        )

        def interval_change(interval):
            global step_interval_state
            step_interval_state = interval  # 更新状态变量
            return

        confirm_interval_btn.click(
            lambda i: interval_change(i),
            inputs=step_interval_slider,
            outputs=None
        ).then(
            lambda: calculate_heights(),
            outputs=[calculated_heights_state]
        ).then(
            lambda heights: gr.Info(f"身高计算完成"),
            outputs=None
        )

    if __name__ == "__main__":
        demo.launch(server_port=7861)


if __name__ == "__main__":
    main()