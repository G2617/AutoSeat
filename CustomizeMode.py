import gradio as gr
import os
from AlgorithmFunctions import save_config_to_json, save_image_and_get_path
from GradioFunctions import welcome_page, seating_arrangement_page, input_method_page, input_students_page
from GradioFunctions import optimization_mode_page, mode_selection_page, optimization_input_page, fill_target_teams_priority, generate_page
from GradioFunctions import get_initial_data, show_reservation_input, show_group_input, show_target_teams_input
from GradioFunctions import if_and_ud1, if_and_ud2

with gr.Blocks(title="自定义输入模式") as demo:
    gr.Markdown("**欢迎使用班级座位排列工具** *Powered by Jiang*")
    gr.Markdown("此界面为自定义输入模式，如果在主界面更改了模式，那么此界面会改变")
    
    with gr.Tab("基础输入界面"):
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

            gr.Markdown("**在此界面进行基础信息的输入**")
            num_students_input = gr.Number(label="请输入班级人数 两个人及以上", minimum=2)
            num_students_submit = gr.Button("提交班级人数")
            rows_input = gr.Number(label="请输入行数", visible=False)
            cols_input = gr.Number(label="请输入列数", visible=False)
            arrangement_submit = gr.Button("提交行列数", visible=False)
            input_method_input = gr.Radio(["文件输入", "文本输入"], label="请选择学生信息输入方式", visible=False)
            file_input = gr.File(label="请拖入符合规格的 xlsx 文件", visible=False)
            text_input = gr.Textbox(label="请按每行每个学生的学号，两个到四个字的全名，大致身高的格式输入学生信息，Shift+Enter来换行", visible=False)
            students_submit = gr.Button("提交学生信息", visible=False)
            
    with gr.Tab("秩序优化界面"):
                with gr.Column():
                    gr.Markdown("**基础信息的输入完成后，在此界面进行秩序优化，这一部分可以跳过直接生成**")
                    gr.Markdown("如果多次启用或关闭秩序优化模式时设置组件没有正常出现，可以切换一下选择进行更新，如果仍不起作用建议刷新此网页。同时建议不要多次切换是否启用秩序优化模式")
                    gr.Markdown("**使用提示**")
                    gr.Markdown("在 *秩序优化模式* 中，")
                    gr.Markdown("1. 每个**目标小组**指的是**需要尽量挨在一起的若干个同学，即组员**")
                    gr.Markdown("2. 每个**小团体**指的是**挨在一起会影响秩序的若干个同学，需要尽量分开**，因此输入的**小团体**个数尽量少一些")
                    gr.Markdown("3. **特定同学座位预定**指的是**需要确保生成结果中必须坐在特定位置的同学**")
                    gr.Markdown("只要开启了秩序优化模式，**小团体**和**特定同学座位预定**就可以启用，但非必填；")
                    gr.Markdown("只有在选择了**小组聚集模式**时，**目标小组**才会被启用，为必填项。另外，启用**小组聚集模式**时，**小团体**的要求会弱化。")
                    optimization_input = gr.Checkbox(label="是否启用秩序优化模式", visible=False)
                    mode_input = gr.Radio(["离散模式", "小组聚集模式"], label="选择模式", visible=False)

                    target_teams_input_method = gr.Radio(["文件输入", "文本输入"], label="请选择目标小组输入方式", visible=False)
                    target_teams_file_input = gr.File(label="请拖入 txt 文件", visible=False)
                    target_teams_text_input = gr.Textbox(label="请分行输入目标小组信息，每行若干个人的全名，用空格隔开，Shift+Enter来换行", visible=False)
                    teams_submit = gr.Button("提交目标小组", visible=False)
                    target_teams_priority_input = gr.Dataframe(
                        headers=["小组名", "优先顺序"],
                        datatype=["str", "number"],
                        col_count=(2, "fixed"),
                        row_count=(0, "dynamic"),
                        visible=False,
                        interactive=True,
                        type="pandas",
                        label="目标小组优先顺序配置 优先顺序请输入从一到小组个数的正整数序列"
                    )

                    group_input_method = gr.Radio(["文件输入", "文本输入"], label="请选择小团体输入方式", visible=False)
                    group_file_input = gr.File(label="请拖入 txt 文件", visible=False)
                    group_text_input = gr.Textbox(label="请分行输入小团体信息，每行若干个人的全名，用空格隔开，Shift+Enter来换行，如果误触选项留空即可", visible=False)

                    reservation_checkbox = gr.Checkbox(label="特定同学座位预定", value=False, visible=False)
                    reserved_students_input = gr.Dataframe(
                        headers=["学生学号", "学生姓名", "预定行", "预定列"],
                        datatype=["str", "str", "number", "number"],
                        col_count=(4, "fixed"),
                        row_count=(0, "dynamic"),
                        visible=False,
                        interactive=True,
                        type="pandas",
                        label="预定座位配置 行和列请输入正整数 不进行预定的同学请留空"
                    )
                with gr.Column():
                    optimization_input_submit = gr.Button("提交优化", visible=False)
                    generate_button = gr.Button("生成座位排列", visible=False)

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
            regenerate_button = gr.Button("用当前输入再次生成座位表", visible=False)
            # 保存配置为 JSON 文件按钮
            save_config_button = gr.Button("将当前配置保存为文件", visible=False)
            save_config_output = gr.File(label="保存的配置文件", type="filepath", visible=False)
            gr.Markdown("**进行新一轮自定义务必手动刷新网页**")

    if (True):
            num_students_submit.click(
                welcome_page,
                inputs=num_students_input,
                outputs=arrangement_output
            ).then(
                lambda: [gr.update(visible=True)] * 3,
                outputs=[rows_input, cols_input, arrangement_submit]
            )

            arrangement_submit.click(
                seating_arrangement_page,
                inputs=[arrangement_output, rows_input, cols_input],
                outputs=[arrangement_output, rows_output, cols_output]
            ).then(
                lambda: gr.update(visible=True),
                outputs=[input_method_input]
            )

            input_method_input.change(
                input_method_page,
                inputs=[arrangement_output, rows_output, cols_output, input_method_input],
                outputs=[arrangement_output, rows_output, cols_output, input_method_output]
            ).then(
                lambda x, y, z, w: gr.update(visible=True) if w == "文件输入" else gr.update(visible=False),
                inputs=[arrangement_output, rows_output, cols_output, input_method_output],
                outputs=[file_input]
            ).then(
                lambda x, y, z, w: gr.update(visible=True) if w == "文本输入" else gr.update(visible=False),
                inputs=[arrangement_output, rows_output, cols_output, input_method_output],
                outputs=[text_input]
            ).then(
                lambda x, y, z, w: gr.update(visible=True),
                inputs=[arrangement_output, rows_output, cols_output, input_method_output],
                outputs=[students_submit]
            )

            students_submit.click(
                input_students_page,
                inputs=[arrangement_output, rows_output, cols_output, input_method_output, file_input, text_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output]
            ).then(
                if_and_ud1,
                inputs=[gr.State(0)],
                outputs=[generate_button, optimization_input]
            )

            optimization_input.change(
                optimization_mode_page,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output]
            ).then(
                lambda x, y, z, w, v: gr.update(visible=False) if v else gr.update(visible=True),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output],
                outputs=[generate_button]
            ).then(
                lambda x, y, z, w, v: 
                [
                        gr.update(visible=True) if v else gr.update(visible=False),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update(),
                        gr.update(visible=False) if not v else gr.update()
                 ],
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output],
                outputs=[mode_input, target_teams_input_method, target_teams_text_input, target_teams_file_input, teams_submit, group_input_method, group_text_input, group_file_input, reservation_checkbox, reserved_students_input, target_teams_priority_input, optimization_input_submit]
            )

            mode_input.change(
                mode_selection_page,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=m == 1),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[target_teams_input_method]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=m == 1),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[teams_submit]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=False if m == 0 else None),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[target_teams_text_input]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=False if m == 0 else None),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[target_teams_file_input]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=True if m == 0 else False),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[group_input_method]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=True if m == 0 else False),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[reservation_checkbox]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=False),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[group_text_input]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=False),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[group_file_input]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=True if m == 0 else False),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[optimization_input_submit]
            ).then(
                lambda x, y, z, w, v, m: gr.update(visible=False if m == 0 else None),
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output],
                outputs=[target_teams_priority_input]
            )

            #*****#
            target_teams_input_method.change(
                show_target_teams_input,
                inputs=target_teams_input_method,
                outputs=[target_teams_file_input, target_teams_text_input]
            ).then(
                lambda x: gr.update(visible=True),
                inputs=[target_teams_input_method],
                outputs=[teams_submit]
            )
            teams_submit.click(
                optimization_input_page,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, target_teams_file_input, target_teams_text_input, group_file_input, group_text_input, reservation_checkbox, reserved_students_input, target_teams_priority_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output]
            ).then(
                fill_target_teams_priority,
                inputs=teams_output,
                outputs=target_teams_priority_input
            ).then(
                lambda: gr.update(visible=True),
                outputs=[target_teams_priority_input]
            ).then(
                lambda: gr.update(visible=True),
                outputs=[group_input_method]
            ).then(
                lambda: gr.update(visible=True),
                outputs=[reservation_checkbox]
            ).then(
                lambda: gr.update(visible=True),
                outputs=[optimization_input_submit]
            )
            #*****#
            group_input_method.change(
                show_group_input,
                inputs=group_input_method,
                outputs=[group_file_input, group_text_input]
            ).then(
                lambda x: gr.update(visible=True),
                inputs=[group_input_method],
                outputs=[optimization_input_submit]
            )
            #*****#
            reservation_checkbox.change(
                show_reservation_input,
                inputs=reservation_checkbox,
                outputs=reserved_students_input
            ).then(
                get_initial_data,
                inputs=students_data_output,
                outputs=reserved_students_input
            ).then(
                lambda x: gr.update(visible=True),
                inputs=[reserved_students_input],
                outputs=[optimization_input_submit]
            )
            #*****#
            optimization_input_submit.click(
                optimization_input_page,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, target_teams_file_input, target_teams_text_input, group_file_input, group_text_input, reservation_checkbox, reserved_students_input, target_teams_priority_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output]
            ).then(
                lambda: gr.update(visible=True),
                outputs=generate_button
            )

            generate_button.click(
                lambda: gr.Info("设定输入成功，请等待"),
                outputs=[gr.State()]
            ).then(
                optimization_input_page,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, target_teams_file_input, target_teams_text_input, group_file_input, group_text_input, reservation_checkbox, reserved_students_input, target_teams_priority_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output]
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
                lambda: gr.Info("设定输入成功，请等待"),
                outputs=[gr.State()]
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

            def save_config_button_click_wrapper(arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output):
                    # 正常保存配置逻辑
                    num_students = arrangement_output.value if hasattr(arrangement_output, 'value') else arrangement_output
                    rows = rows_output.value if hasattr(rows_output, 'value') else rows_output
                    cols = cols_output.value if hasattr(cols_output, 'value') else cols_output
                    students_data = students_data_output.value if hasattr(students_data_output, 'value') else students_data_output
                    enable_optimization = optimization_output.value if hasattr(optimization_output, 'value') else optimization_output
                    mode = mode_output.value if hasattr(mode_output, 'value') else mode_output
                    teams = teams_output.value if hasattr(teams_output, 'value') else teams_output
                    sorts = sorts_output.value if hasattr(sorts_output, 'value') else sorts_output
                    groups = groups_output.value if hasattr(groups_output, 'value') else groups_output
                    reserved_seats = reserved_seats_output.value if hasattr(reserved_seats_output, 'value') else reserved_seats_output

                    file_path = save_config_to_json(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats, None)
                    dir_name = os.path.dirname(file_path)
                    file_name = os.path.basename(file_path)
                    gr.Info(f"保存成功，已经保存为\n{dir_name}\n目录下的\n{file_name}\n配置文件，点击重启程序来刷新配置列表")
                    return file_path

            # 保存配置为 JSON 文件
            save_config_button.click(
                fn=save_config_button_click_wrapper,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output],
                outputs=save_config_output
            )

if __name__ == "__main__":
    demo.launch(css=".gradio-textarea { height: auto; overflow: visible; }")