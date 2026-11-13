---
title: AutoSeat
emoji: 🪑
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.26.0
app_file: Main.py
pinned: false
license: gpl-3.0
---

# AutoSeat 班级座位排列工具

AutoSeat 是一个基于 Python 和 Gradio 的班级座位编排工具。你可以输入学生信息和教室行列数，生成多组座位方案，并按身高、目标小组、小团体和指定座位等条件进行辅助安排。

## 演示视频

https://github.com/user-attachments/assets/d3e5b297-a17d-4847-9074-e04715e75b3a

## 上手体验 JSON 文件导入模式

https://modelscope.cn/studios/JiangCarrey/AutoSeat

## 功能

- **自定义输入**：通过文本或 `.xlsx` 表格录入学生信息。
- **秩序优化**：选择离散排列或小组聚集；可设置需要尽量分开的同学小团体，以及指定学生的座位。
- **结果导出**：比较多组方案及评估结果，下载座位表图片和表格。
- **配置管理**：将输入保存为 JSON 配置，以便之后直接导入或编辑。
- **图片辅助输入**：从班级合照检测人脸、辅助估计身高，再将结果带回自定义输入流程。

## 环境要求

- Python **3.10 或 3.11**（推荐）。图片辅助模式依赖 TensorFlow 和 MTCNN；使用其他 Python 版本时，请先确认这些依赖有对应的安装包。
- Windows、macOS 或 Linux。

## 安装与启动

在仓库根目录执行以下命令：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python Main.py
```

如果 PowerShell 不允许执行虚拟环境的激活脚本，可以直接使用虚拟环境中的 Python 安装并启动：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe Main.py
```

启动后在浏览器打开 `http://localhost:7860`，在主界面选择模式并确认。模式界面默认使用本机 `7861` 端口。

> **隐私提示：** 主程序调用 Gradio 时启用了 `share=True`，启动后会创建可从公网访问的分享链接。不要通过该链接处理不适合公开访问的学生个人信息或照片；使用结束后关闭程序（在终端按 `Ctrl+C`），并妥善保管已保存的配置文件。

## 使用流程

首次使用建议选择 **自定义输入**：

1. 输入班级人数及座位行数、列数。座位总数不能少于学生人数。
2. 选择文本或 Excel 输入学生信息：
   - 文本每行一名学生，格式为 `学号 姓名 大致身高`，各项以空格分隔。例如：`A001 张小明 165`。
   - Excel 使用 `.xlsx` 格式，每行一名学生，前三列依次为学号、姓名和大致身高。首行为表头。
   - 学号只能包含英文字母和数字；姓名需为 2 至 4 个汉字。
3. 如需优化，启用秩序优化并选择排列模式。目标小组、小团体和座位预定按界面说明输入；预定行列从 **1** 开始计数。
4. 点击生成座位排列，在结果页比较方案、查看评估，并下载需要的图片或表格。
5. 如需复用输入，可保存为配置文件。

## 其他模式

- **配置文件直接导入**：选择之前保存的 JSON 配置并生成座位表。
- **配置文件编辑**：导入已有配置，修改信息后另存为配置文件。
- **快捷图片输入**：选择程序目录中的 PNG、JPG 或 JPEG 图片。照片中人脸应尽量清晰无遮挡；该功能用于辅助识别和估算，并非精确测量。生成的学生信息仍需核对，再到自定义输入模式中使用。

配置文件保存在仓库的 `jsons/` 目录。该目录中的配置可能包含学生个人信息，请谨慎分享或提交。

## 常见问题

- **端口被占用**：确认本机 `7860` 和 `7861` 端口未被其他程序使用。
- **无法读取 Excel**：请使用 `.xlsx` 文件，并确认已安装依赖（其中 `openpyxl` 用于读取 Excel）。
- **图片辅助模式启动慢或报 TensorFlow 错误**：首次加载人脸检测依赖可能需要一些时间；请使用推荐的 Python 版本，并确认 `requirements.txt` 中依赖安装成功。
