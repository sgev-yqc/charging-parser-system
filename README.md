# 🔋 充电报文解析系统

基于 GB/T 27930 协议的充电通信报文解析工具，支持批量上传、订单管理、多格式导出。

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.65-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 功能特性

- 📤 **批量上传** - 弹窗选择多个文件，拖拽或点击
- 🔍 **自动识别** - 从文件名自动提取订单号
- 💾 **本地存储** - 原始报文与解析结果永久保存到本地
- 🔎 **条件筛选** - 按关键字、上传时间范围筛选订单
- 📋 **订单管理** - 排序、分页、批量删除
- 👁️ **结果查看** - 详情页展示统计、阶段分布与报文明细
- 📥 **多格式导出** - Excel、JSON、TXT、原始文件

## 🚀 快速开始

需要安装 Python 3.12 和 Git。先把仓库下载到本地：

```bash
git clone https://github.com/sgev-yqc/charging-parser-system.git
cd charging-parser-system
```

macOS / Linux：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

如果已经用 conda，也可以用它替代 venv：

```bash
conda create -n charging-parser python=3.12 -y
conda activate charging-parser
pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

打开 http://127.0.0.1:8501 即可使用。在启动服务的终端按 `Ctrl+C` 停止。修改代码后，重新运行对应的启动命令。

订单和解析文件默认保存在项目目录下的 `data/` 文件夹（该文件夹已在 `.gitignore` 中）。如需指定位置，有两种方式。

**方式一：项目内配置文件（推荐，持久生效）**

复制 `config.example.json` 为 `config.local.json`，再修改 `data_dir`（`config.local.json` 已被 `.gitignore` 忽略，不会提交到仓库）：

```json
{
  "data_dir": "~/charging-parser-data"
}
```

`data_dir` 可以是绝对路径，也可以是相对项目根目录的路径（如 `data`）。

**方式二：环境变量（对当次运行生效）**

启动前设置 `CHARGING_PARSER_DATA_DIR`。macOS / Linux 示例：

```bash
export CHARGING_PARSER_DATA_DIR="$HOME/charging-parser-data"
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

Windows PowerShell 示例：`$env:CHARGING_PARSER_DATA_DIR="$HOME\charging-parser-data"`，然后运行上面的启动命令。

两者同时存在时，环境变量优先于 `config.local.json`。

## 📁 项目结构

```
charging-parser-system/
├── app.py                  # 入口：页面路由与头部
├── views/                  # 界面视图
│   ├── list_page.py        # 订单列表（筛选 / 排序 / 分页 / 查看）
│   ├── detail_page.py      # 订单详情（统计 / 报文明细 / 导出）
│   └── upload_dialog.py    # 上传解析弹窗
├── charging_parser/        # 解析、存储、配置与导出
│   ├── parser.py           # GB/T 27930 报文解析
│   ├── storage.py          # 订单存储（JSON 文件）
│   ├── config.py           # 数据目录配置
│   └── export.py           # Excel / JSON / TXT 导出
├── .streamlit/config.toml  # 主题配色
├── config.example.json     # 数据目录配置样例
├── requirements.txt        # Python 依赖
├── tests/                  # 回归测试
└── README.md

<数据目录>/
├── orders.json          # 订单索引
└── {订单号}/             # 每个订单的独立目录
    ├── {原始文件名}.txt
    └── parsed_result.json
```

## 📋 使用说明

### 文件名格式

系统从文件名自动提取订单号：

```
BMS_20260520150000_13404900000009670026052002800209.2.txt
                    └──────────────────────────────────┘
                              订单号
```

### 支持的报文类型

| 报文 | 名称 | 方向 |
|-----|------|------|
| CHM/BHM | 握手报文 | 双向 |
| CRM/BRM | 辨识报文 | 双向 |
| BCP/CML | 参数报文 | 双向 |
| BRO/CRO | 准备就绪 | 双向 |
| BCL/BCS/CCS | 充电状态 | 双向 |
| BSM | 电池状态 | 车辆→充电机 |
| BST/CST | 中止报文 | 双向 |
| BSD/CSD | 统计数据 | 双向 |
| BEM/CEM | 错误报文 | 双向 |

## 🖥️ 界面预览

界面是单页结构：**订单列表**是唯一入口页，**上传**是头部的弹窗动作，**详情**从列表点「查看」下钻进入。

```
订单列表（入口页）
├── 头部      标题 + 「＋ 上传解析」按钮 → 打开上传弹窗
├── 条件筛选   关键字（订单号 / 文件名）+ 上传起始 / 截止日期 + 重置筛选
├── 工具栏     订单数与报文数统计、排序方式、每页条数
└── 订单表格   订单号 | 文件名 | 状态 | 大小 | 报文数 | 上传时间 | [查看]
                + 分页 + 批量删除

订单详情（从列表点「查看」进入）
├── 面包屑    ← 返回订单列表
├── 统计卡片   总报文数 / 涉及阶段 / 报文类型 / 文件大小 / 状态 / 上传时间
├── 阶段分布   各阶段汇总条数
├── 报文明细   可按阶段、报文类型筛选的表格
└── 导出       原文件 / Excel / JSON / TXT

上传弹窗（头部按钮触发）
├── 文件选择   支持多选 .txt
├── 文件预览   文件名 / 订单号 / 大小
└── 开始上传并解析（带进度条）
```

## 🔧 技术栈

- **Streamlit** - Web 界面框架
- **Pandas** - 数据处理
- **OpenPyXL** - Excel 导出

## 📄 协议支持

- GB/T 27930-2015 电动汽车非车载传导式充电机与电池管理系统之间的通信协议

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📜 License

MIT License
