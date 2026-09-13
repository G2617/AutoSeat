import gradio as gr
import os
import datetime
import AlgorithmFunctions
from AlgorithmFunctions import load_json_files, import_json_config, save_image_and_get_path
from GradioFunctions import generate_page, if_and_ud2

with gr.Blocks(title="配置文件直接导入模式") as demo:
        gr.Markdown("**社交的班委 暗黑座位学 食人师 ~ 欢迎使用班级座位排列工具** *Powered by Jiang*")
        gr.Markdown("此界面为配置文件直接导入模式，如果在主界面更改了模式，那么此界面会改变")

        rows_output = gr.State()
        cols_output = gr.State()
        arrangement_output = gr.State()
        input_method_output = gr.State()
        students_data_output = gr.State()
        optimization_output = gr.State()
        mode_output = gr.State()
        teams_output = gr.State()
        sorts_output = gr.State()
        groups_output = gr.State()
        reserved_seats_output = gr.State()

        with gr.Tab("导入界面"):
                gr.Markdown("**在此界面导入配置文件**")
                gr.Markdown("如果下拉列表中没有信息，说明您还没有保存过配置文件，请回到主界面使用自定义输入模式")
                # 导入 JSON 配置的下拉列表
                json_files = load_json_files()
                json_file_input = gr.Dropdown(choices=json_files, label="选择配置文件", visible=True)
                import_json_button = gr.Button("导入配置文件", visible=True)

        with gr.Tab("结果界面"):
                gr.Markdown("**导入完成并点击生成按钮后，在此界面查看结果，你可以在三列即三个结果中选择最佳一个下载**")
                gr.Markdown("每个结果所在列最后有一个结果评估框可供参考")
                # 创建3个纵列
                with gr.Row():
                    # 第一列
                    with gr.Column():
                        gr.Markdown("**结果一**")
                        img1_col1 = gr.Image(label="学号座位表", visible=False)
                        img2_col1 = gr.Image(label="全名座位表", visible=False)
                        img3_col1 = gr.Image(label="简写名座位表", visible=False)
                        img4_col1 = gr.Image(label="身高热力图", visible=False)
                        img5_col1 = gr.Image(label="小组分布灰度图", visible=False)
                        download_csvs_col1 = gr.File(label="下载全名座位表表格", type="filepath", visible=False)
                        download_img1_col1 = gr.File(label="下载学号座位表图片", type="filepath", visible=False)
                        download_img2_col1 = gr.File(label="下载全名座位表图片", type="filepath", visible=False)
                        download_img3_col1 = gr.File(label="下载简写名座位表图片", type="filepath", visible=False)
                        download_img4_col1 = gr.File(label="下载身高热力图", type="filepath", visible=False)
                        download_img5_col1 = gr.File(label="下载小组分布灰度图", type="filepath", visible=False)
                        eval_col1 = gr.TextArea(label="此结果评估", lines = 16, visible=False, interactive=False)
                    
                    # 第二列
                    with gr.Column():
                        gr.Markdown("**结果二**")
                        img1_col2 = gr.Image(label="学号座位表", visible=False)
                        img2_col2 = gr.Image(label="全名座位表", visible=False)
                        img3_col2 = gr.Image(label="简写名座位表", visible=False)
                        img4_col2 = gr.Image(label="身高热力图", visible=False)
                        img5_col2 = gr.Image(label="小组分布灰度图", visible=False)
                        download_csvs_col2 = gr.File(label="下载全名座位表表格", type="filepath", visible=False)
                        download_img1_col2 = gr.File(label="下载学号座位表图片", type="filepath", visible=False)
                        download_img2_col2 = gr.File(label="下载全名座位表图片", type="filepath", visible=False)
                        download_img3_col2 = gr.File(label="下载简写名座位表图片", type="filepath", visible=False)
                        download_img4_col2 = gr.File(label="下载身高热力图", type="filepath", visible=False)
                        download_img5_col2 = gr.File(label="下载小组分布灰度图", type="filepath", visible=False)
                        eval_col2 = gr.TextArea(label="此结果评估", lines = 16, visible=False, interactive=False)
                    
                    # 第三列
                    with gr.Column():
                        gr.Markdown("**结果三**")
                        img1_col3 = gr.Image(label="学号座位表", visible=False)
                        img2_col3 = gr.Image(label="全名座位表", visible=False)
                        img3_col3 = gr.Image(label="简写名座位表", visible=False)
                        img4_col3 = gr.Image(label="身高热力图", visible=False)
                        img5_col3 = gr.Image(label="小组分布灰度图", visible=False)
                        download_csvs_col3 = gr.File(label="下载全名座位表表格", type="filepath", visible=False)
                        download_img1_col3 = gr.File(label="下载学号座位表图片", type="filepath", visible=False)
                        download_img2_col3 = gr.File(label="下载全名座位表图片", type="filepath", visible=False)
                        download_img3_col3 = gr.File(label="下载简写名座位表图片", type="filepath", visible=False)
                        download_img4_col3 = gr.File(label="下载身高热力图", type="filepath", visible=False)
                        download_img5_col3 = gr.File(label="下载小组分布灰度图", type="filepath", visible=False)
                        eval_col3 = gr.TextArea(label="此结果评估", lines = 16, visible=False, interactive=False)

                # 为每列添加独立的状态变量
                csv_file_col1 = gr.State()
                csv_file_col2 = gr.State()
                csv_file_col3 = gr.State()
                
                # 再次生成按钮
                regenerate_button = gr.Button("用当前配置文件再次生成座位表", visible=False)
                # 保存配置为 JSON 文件按钮
                save_config_button = gr.Button("将当前配置保存为文件", visible=False)
                save_config_output = gr.File(label="保存的配置文件", type="filepath", visible=False)
                gr.Markdown("**进行新一轮导入务必手动刷新网页**")

            # 导入 JSON 配置
        import_json_button.click(
            lambda config_file: [
                *import_json_config(config_file),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jsons', config_file)
            ],
            inputs=json_file_input,
            outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output],
            api_name="import_json"
        ).then(
            # 为每列独立生成结果
            lambda num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats, _: [
                *generate_page(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats),
                *generate_page(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats),
                *generate_page(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats)
            ],
            inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output, optimization_output],
            outputs=[
                csv_file_col1, img1_col1, img2_col1, img3_col1, img4_col1, img5_col1, eval_col1,
                csv_file_col2, img1_col2, img2_col2, img3_col2, img4_col2, img5_col2, eval_col2,
                csv_file_col3, img1_col3, img2_col3, img3_col3, img4_col3, img5_col3, eval_col3
            ],
            api_name="generate_seating_after_import"
        ).then(
            # 第一列结果更新
            lambda csv1, img1, img2, img3, img4, img5, eval_: [
                gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
                gr.update(value=csv1, visible=True),
                gr.update(value=save_image_and_get_path(img1, "student_id_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img2, "full_name_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img3, "abbreviation_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img4, "height_heatmap"), visible=True),
                gr.update(value=save_image_and_get_path(img5, "team_map"), visible=True),
                gr.update(value=eval_, visible=True)
            ],
            inputs=[csv_file_col1, img1_col1, img2_col1, img3_col1, img4_col1, img5_col1, eval_col1],
            outputs=[img1_col1, img2_col1, img3_col1, img4_col1, img5_col1,
                    download_csvs_col1, download_img1_col1, download_img2_col1, download_img3_col1, download_img4_col1, download_img5_col1,
                    eval_col1]
        ).then(
            # 第一列结果更新
            lambda csv1, img1, img2, img3, img4, img5, eval_: [
                gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
                gr.update(value=csv1, visible=True),
                gr.update(value=save_image_and_get_path(img1, "student_id_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img2, "full_name_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img3, "abbreviation_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img4, "height_heatmap"), visible=True),
                gr.update(value=save_image_and_get_path(img5, "team_map"), visible=True),
                gr.update(value=eval_, visible=True)
            ],
            inputs=[csv_file_col2, img1_col2, img2_col2, img3_col2, img4_col2, img5_col2, eval_col2],
            outputs=[img1_col2, img2_col2, img3_col2, img4_col2, img5_col2,
                    download_csvs_col2, download_img1_col2, download_img2_col2, download_img3_col2, download_img4_col2, download_img5_col2,
                    eval_col2]
        ).then(
            # 第一列结果更新
            lambda csv1, img1, img2, img3, img4, img5, eval_: [
                gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
                gr.update(value=csv1, visible=True),
                gr.update(value=save_image_and_get_path(img1, "student_id_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img2, "full_name_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img3, "abbreviation_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img4, "height_heatmap"), visible=True),
                gr.update(value=save_image_and_get_path(img5, "team_map"), visible=True),
                gr.update(value=eval_, visible=True)
            ],
            inputs=[csv_file_col3, img1_col3, img2_col3, img3_col3, img4_col3, img5_col3, eval_col3],
            outputs=[img1_col3, img2_col3, img3_col3, img4_col3, img5_col3,
                    download_csvs_col3, download_img1_col3, download_img2_col3, download_img3_col3, download_img4_col3, download_img5_col3,
                    eval_col3]
        ).then(
            lambda: [gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)],
            outputs=[img1_col1, img2_col1, img3_col1, img4_col1, img5_col1],
            api_name="show_info_after_import"
        ).then(
            lambda: [gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)],
            outputs=[img1_col2, img2_col2, img3_col2, img4_col2, img5_col2],
            api_name="show_info_after_import"
        ).then(
            if_and_ud2,
            inputs=[gr.State(0)],
            outputs=[img1_col3, img2_col3, img3_col3, img4_col3, img5_col3],
            api_name="show_info_after_import"
        ).then(
            lambda: gr.update(visible=True),
            outputs=save_config_button,
        ).then(
            lambda: gr.update(visible=True),
            outputs=regenerate_button,
        )

        regenerate_button.click(
            lambda config_file: [
                *import_json_config(config_file),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jsons', config_file)
            ],
            inputs=json_file_input,
            outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output],
            api_name="import_json"
        ).then(
            # 为每列独立生成结果
            lambda num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats, _: [
                *generate_page(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats),
                *generate_page(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats),
                *generate_page(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats)
            ],
            inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output, optimization_output],
            outputs=[
                csv_file_col1, img1_col1, img2_col1, img3_col1, img4_col1, img5_col1, eval_col1,
                csv_file_col2, img1_col2, img2_col2, img3_col2, img4_col2, img5_col2, eval_col2,
                csv_file_col3, img1_col3, img2_col3, img3_col3, img4_col3, img5_col3, eval_col3
            ],
            api_name="generate_seating_after_import"
        ).then(
            # 第一列结果更新
            lambda csv1, img1, img2, img3, img4, img5, eval_: [
                gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
                gr.update(value=csv1, visible=True),
                gr.update(value=save_image_and_get_path(img1, "student_id_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img2, "full_name_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img3, "abbreviation_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img4, "height_heatmap"), visible=True),
                gr.update(value=save_image_and_get_path(img5, "team_map"), visible=True),
                gr.update(value=eval_, visible=True)
            ],
            inputs=[csv_file_col1, img1_col1, img2_col1, img3_col1, img4_col1, img5_col1, eval_col1],
            outputs=[img1_col1, img2_col1, img3_col1, img4_col1, img5_col1,
                    download_csvs_col1, download_img1_col1, download_img2_col1, download_img3_col1, download_img4_col1, download_img5_col1,
                    eval_col1]
        ).then(
            # 第一列结果更新
            lambda csv1, img1, img2, img3, img4, img5, eval_: [
                gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
                gr.update(value=csv1, visible=True),
                gr.update(value=save_image_and_get_path(img1, "student_id_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img2, "full_name_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img3, "abbreviation_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img4, "height_heatmap"), visible=True),
                gr.update(value=save_image_and_get_path(img5, "team_map"), visible=True),
                gr.update(value=eval_, visible=True)
            ],
            inputs=[csv_file_col2, img1_col2, img2_col2, img3_col2, img4_col2, img5_col2, eval_col2],
            outputs=[img1_col2, img2_col2, img3_col2, img4_col2, img5_col2,
                    download_csvs_col2, download_img1_col2, download_img2_col2, download_img3_col2, download_img4_col2, download_img5_col2,
                    eval_col2]
        ).then(
            # 第一列结果更新
            lambda csv1, img1, img2, img3, img4, img5, eval_: [
                gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
                gr.update(value=csv1, visible=True),
                gr.update(value=save_image_and_get_path(img1, "student_id_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img2, "full_name_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img3, "abbreviation_seating"), visible=True),
                gr.update(value=save_image_and_get_path(img4, "height_heatmap"), visible=True),
                gr.update(value=save_image_and_get_path(img5, "team_map"), visible=True),
                gr.update(value=eval_, visible=True)
            ],
            inputs=[csv_file_col3, img1_col3, img2_col3, img3_col3, img4_col3, img5_col3, eval_col3],
            outputs=[img1_col3, img2_col3, img3_col3, img4_col3, img5_col3,
                    download_csvs_col3, download_img1_col3, download_img2_col3, download_img3_col3, download_img4_col3, download_img5_col3,
                    eval_col3]
        ).then(
            lambda: [gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)],
            outputs=[img1_col1, img2_col1, img3_col1, img4_col1, img5_col1],
            api_name="show_info_after_import"
        ).then(
            lambda: [gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)],
            outputs=[img1_col2, img2_col2, img3_col2, img4_col2, img5_col2],
            api_name="show_info_after_import"
        ).then(
            if_and_ud2,
            inputs=[gr.State(0)],
            outputs=[img1_col3, img2_col3, img3_col3, img4_col3, img5_col3],
            api_name="show_info_after_import"
        )


        def save_config_button_click_wrapper():
            imported_json_file_path = AlgorithmFunctions.imported_json_file_path
            # 如果是从 JSON 导入的，复制文件并改名保存
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_folder = os.path.join(current_dir, 'jsons')
            if not os.path.exists(json_folder):
                os.makedirs(json_folder)
            now = datetime.datetime.now()
            timestamp = now.strftime("%Y%m%dd%Hh%Mm%Ss")
            file_name = f'config_{timestamp}.json'
            file_path = os.path.join(json_folder, file_name)
            import shutil
            shutil.copyfile(str(imported_json_file_path), file_path)
            dir_name = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            gr.Info(f"保存成功，已经保存为\n{dir_name}\n目录下的\n{file_name}\n配置文件，点击重启程序来刷新配置列表")
            imported_json_file_path = None  # 重置记录
            return file_path

            # 保存配置为 JSON 文件
        save_config_button.click(
            fn=save_config_button_click_wrapper,
            inputs=None,
            outputs=save_config_output
        )

demo.launch(css=".gradio-textarea { height: auto; overflow: visible; }")