import gradio as gr
import os
from AlgorithmFunctions import save_config_to_json, load_json_files, import_json_config, fill_json_config, fill_json_sheet
from GradioFunctions import input_students_page, mode_selection_page, optimization_input_page, show_reservation_input
from GradioFunctions import if_and_ud1, if_and_ud2

with gr.Blocks(title="配置文件编辑模式") as demo:
    gr.Markdown("**社交的班委 暗黑座位学 食人师 ~ 欢迎使用班级座位排列工具** *Powered by Jiang*")
    gr.Markdown("此界面为配置文件编辑模式，如果在主界面更改了模式，那么此界面会改变")
    
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
    file_name = gr.State()
    team_nums = gr.State()

    with gr.Tab("导入界面"):
        gr.Markdown("**在此界面导入配置文件**")
        gr.Markdown("如果下拉列表中没有信息，说明您还没有保存过配置文件，请回到主界面使用自定义输入模式")
        # 导入 JSON 配置的下拉列表
        json_files = load_json_files()
        json_file_input = gr.Dropdown(choices=json_files, label="选择配置文件", visible=True)
        import_json_button = gr.Button("导入配置文件", visible=True)

    with gr.Tab("编辑界面"):
                gr.Markdown("**导入完成并点击生成按钮后，在此界面进行内容编辑**")
                with gr.Column():
                    gr.Markdown("基础输入信息，不能留空")
                    num_students_input = gr.Number(label="请输入班级人数 两个人及以上", minimum=2)
                    rows_input = gr.Number(label="请输入行数", visible=True)
                    cols_input = gr.Number(label="请输入列数", visible=True)
                    gr.Markdown("编辑模式仅支持学生信息的文本框输入")
                    students_text_input = gr.Textbox(label="请按每行每个学生的学号，两个到四个字的全名，大致身高的格式输入学生信息，Shift+Enter来换行", visible=True)
                    simple_submit = gr.Button("提交基础信息的更改", visible=True)
                with gr.Column():
                    gr.Markdown("秩序优化输入信息，根据需求可留空")
                    optimization_input = gr.Checkbox(label="是否启用秩序优化模式", visible=True)
                    mode_input = gr.Radio(["离散模式", "小组聚集模式"], label="选择模式", visible=True)
                    gr.Markdown("编辑模式仅支持目标小组、小团体信息的文本框输入")
                    target_teams_text_input = gr.Textbox(label="请分行输入目标小组信息，每行若干个人的全名，用空格隔开，Shift+Enter来换行", visible=False)
                    teams_submit = gr.Button("提交目标小组", visible=False)
                    priority = gr.State()
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

                    group_text_input = gr.Textbox(label="请分行输入小团体信息，每行若干个人的全名，用空格隔开，Shift+Enter来换行，如果误触选项留空即可", visible=False)
                    gr.Markdown("座位预定表格中如果填入了信息，那么不论是否勾选进行座位预定都会考虑。因此取消勾选前建议将输入内容删除留空")
                    reservation_checkbox = gr.Checkbox(label="特定同学座位预定", value=False, visible=False)
                    reservations = gr.State()
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
                    optimization_input_submit = gr.Button("提交秩序优化信息的更改", visible=True)
    with gr.Tab("保存界面"):
                gr.Markdown("**编辑完成并点击提交按钮后，在此界面进行保存**")
                save_method_input = gr.Radio(["直接保存为一个新的配置文件", "重命名再保存为新的文件"], label="请选择保存方式", visible=False)
                save_text_input = gr.Textbox(label="重命名为", visible=False)
                save_config_button = gr.Button("确认保存", visible=False)
                save_config_output = gr.File(label="保存的配置文件", type="filepath", visible=False)

    if (True):
            
            import_json_button.click(
                import_json_config,
                inputs=json_file_input,
                outputs=[num_students_input, rows_input, cols_input, students_data_output, optimization_input, mode_output, team_nums, sorts_output, groups_output, reserved_seats_output],
                    api_name="import_json"
            ).then(
                fill_json_config,
                inputs=[num_students_input, rows_input, cols_input, students_data_output, optimization_input, mode_output, team_nums, sorts_output, groups_output, reserved_seats_output],
                outputs=[num_students_input, rows_input, cols_input, students_text_input, optimization_input, mode_input, target_teams_text_input, priority, group_text_input, reservations],
                api_name="fill_json_information"
            )

            simple_submit.click(
                if_and_ud1,
                inputs=[gr.State(1)],
                outputs=[gr.State(), gr.State()]
            ).then(
                input_students_page,
                inputs=[num_students_input, rows_input, cols_input, gr.State("文本输入"), gr.State(), students_text_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output]
            ).then(
                mode_selection_page,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output]
            ).then(
                lambda x: [gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)] if x == 1 else [gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)],
                inputs=[mode_output],
                outputs=[target_teams_text_input, teams_submit, group_text_input, reservation_checkbox, optimization_input_submit]
            ).then(
                fill_json_sheet,
                inputs=[students_data_output, reservations, teams_output, priority],
                outputs=[reserved_students_input, gr.State()]
            )

            optimization_input.change(
                lambda x:x,
                inputs=optimization_input,
                outputs=optimization_output
            )

            mode_input.change(
                mode_selection_page,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output]
            ).then(
                lambda x: [gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)] if x == 1 else [gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)],
                inputs=[mode_output],
                outputs=[target_teams_text_input, teams_submit, group_text_input, reservation_checkbox, optimization_input_submit]
            )

            teams_submit.click(
                optimization_input_page,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, gr.State(), target_teams_text_input, gr.State(), group_text_input, reservation_checkbox, reserved_students_input, target_teams_priority_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output]
            ).then(
                fill_json_sheet,
                inputs=[students_data_output, reservations, teams_output, priority],
                outputs=[gr.State(), target_teams_priority_input]
            ).then(
                lambda: [gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)],
                outputs=[target_teams_priority_input, group_text_input, reservation_checkbox]
            )

            reservation_checkbox.change(
                show_reservation_input,
                inputs=reservation_checkbox,
                outputs=reserved_students_input
            ).then(
                lambda x: gr.update(visible=True),
                inputs=[reserved_students_input],
                outputs=[optimization_input_submit]
            )

            optimization_input_submit.click(
                optimization_input_page,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, gr.State(), target_teams_text_input, gr.State(), group_text_input, reservation_checkbox, reserved_students_input, target_teams_priority_input],
                outputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output]
            ).then(
                if_and_ud2,
                inputs=[gr.State(1)],
                outputs=[gr.State(), gr.State(), gr.State(), gr.State(), gr.State()]
            ).then(
                lambda: gr.update(visible=True),
                outputs=save_method_input
            )

            save_method_input.change(
                lambda x: [gr.update(visible= x == "重命名再保存为新的文件"), gr.update(visible=True), None],
                inputs=[save_method_input],
                outputs=[save_text_input, save_config_button, file_name]
            )

            save_text_input.change(
                lambda x: x,
                inputs=[save_text_input],
                outputs=[file_name]
            )

            def save_config_button_click_wrapper(arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output, name):
                    #debug(arrangement_output, "arrangement_output")
                    #debug(rows_output, "rows_output")
                    #debug(cols_output, "cols_output")
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

                    file_path = save_config_to_json(num_students, rows, cols, students_data, enable_optimization, mode, teams, sorts, groups, reserved_seats, name)
                    dir_name = os.path.dirname(file_path)
                    file_name = os.path.basename(file_path)
                    gr.Info(f"保存成功，已经保存为\n{dir_name}\n目录下的\n{file_name}\n配置文件，点击重启程序来刷新配置列表")
                    return file_path

            # 保存配置为 JSON 文件
            save_config_button.click(
                fn=save_config_button_click_wrapper,
                inputs=[arrangement_output, rows_output, cols_output, students_data_output, optimization_output, mode_output, teams_output, sorts_output, groups_output, reserved_seats_output, file_name],
                outputs=save_config_output
            )

if __name__ == "__main__":
    demo.launch()