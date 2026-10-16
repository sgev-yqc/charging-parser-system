# 🔋 充电报文解析系统

基于 GB/T 27930 协议的充电通信报文解析工具，支持批量上传、订单管理、多格式导出。

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![React](https://img.shields.io/badge/React-19-149eca.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.143-009688.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 功能特性

- 📤 **批量上传** - 弹窗选择多个文件，拖拽或点击
- 🔍 **自动识别** - 从文件名自动提取订单号
- 💾 **本地存储** - 原始报文与解析结果永久保存到本地
- 🔎 **条件筛选** - 按关键字、上传时间范围筛选订单
- 📋 **订单管理** - 排序、分页、批量删除
- 👁️ **结果查看** - 详情页展示统计、阶段分布与报文明细
- 📥 **多格式导出** - Excel、JSON、TXT、原始文件

## 🚀 本地启动

需要 Python 3.12、Node.js（含 npm）和 Git。React 界面通过本地 FastAPI 接口调用项目中的解析、存储与导出模块。

```bash
git clone https://github.com/sgev-yqc/charging-parser-system.git
cd charging-parser-system
```

macOS / Linux：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8501
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8501
```

打开 http://127.0.0.1:8501 使用。开发时可以另开终端运行 `npm run dev --prefix frontend`，通过 http://127.0.0.1:5173 预览；API 仍需在 8501 端口运行。在启动 API 的终端按 `Ctrl+C` 停止。如果 8501 已被占用，请先停止占用该端口的旧服务。

**目前仅绑定本机地址，尚未加入登录和权限管理；不要直接暴露到公网。**

### 使用 conda

若已用 conda，也可以用它替代 Python 虚拟环境。进入项目目录后运行：

```powershell
conda create -n charging-parser python=3.12 -y
conda activate charging-parser
pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
python -m uvicorn api:app --host 127.0.0.1 --port 8501
```

## 数据目录

订单和解析文件默认保存在项目目录下的 `data/` 文件夹（该文件夹已在 `.gitignore` 中）。如需指定位置，使用项目内配置文件。

**项目内配置文件**

复制 `config.example.json` 为 `config.local.json`，再修改 `data_dir`（`config.local.json` 已被 `.gitignore` 忽略，不会提交到仓库）：

```json
{
  "data_dir": "~/charging-parser-data"
}
```

`data_dir` 可以是绝对路径，也可以是相对项目根目录的路径（如 `data`）。

## 📁 项目结构

```
charging-parser-system/
├── api.py                  # HTTP API 与静态页面服务
├── frontend/               # React 界面；构建结果位于 frontend/dist
├── charging_parser/        # 解析、存储、配置与导出
│   ├── parser.py           # GB/T 27930 报文解析
│   ├── storage.py          # 订单存储（JSON 文件）
│   ├── config.py           # 数据目录配置
│   └── export.py           # Excel / JSON / TXT 导出
├── config.example.json     # 数据目录配置样例
├── requirements.txt        # 运行依赖
├── requirements-dev.txt    # 测试依赖（含运行依赖）
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

其他命名格式直接使用完整源文件名（包括 `.txt`）作为订单号，例如 `37417900000036460025010502684421.3_corrected.txt`。

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

## 🖥️ 界面与交互

界面默认进入解析工作台：

1. 左侧是工作空间导航；顶部显示当前位置，并提供「上传报文」入口。
2. 工作台显示订单总数、已解析报文数和最近上传时间。解析记录支持按订单号或文件名搜索、按上传日期筛选、排序与分页。
3. 点击订单号或行末按钮进入订单详情；勾选订单后可批量删除，删除前会弹窗确认。
4. 点击「上传并解析」打开弹窗，选择一个或多个 TXT、TGZ、TAR.GZ 或 ZIP 文件。按完整原文件名（含扩展名，不区分大小写）核查重复；同名文件已存在时需要确认替换，不同文件名即使包含相同订单号也可分别保存。
5. 详情页显示有效报文、阶段、报文类型、未识别帧和源文件大小；可搜索并按阶段、报文类型筛选报文明细，每页显示 50 条，并可下载原文件、Excel、JSON 或 TXT。
6. BRM、BCP、BCS 完整多帧传输默认折叠，仅显示组合后的解析结果。点击结果可展开或收起关联传输帧，查看原始 CAN 行及解析内容；不完整或帧序异常的传输帧保持可见。明细使用原始 TXT 行号，筛选和分页不重新编号；组合结果显示关联帧的行号范围。
7. 旧解析记录会从保留的原文件读取行号及多帧关联，无需重新上传，不改写原文件或旧解析文件。

### 上传与存储规则

- 直接上传的 TXT 使用 UTF-8 编码。压缩包自动查找唯一的 `.2.txt` 车桩交互报文，支持子目录及大小写后缀，忽略其他分文件。不搜索嵌套压缩包；缺少或存在多个 `.2.txt` 时明确报错。
- 上传文件与包内目标 TXT 均不超过 50 MB；TGZ/TAR.GZ 展开扫描内容不超过 250 MB。
- 原压缩包按原字节保存，「下载原文件」返回上传的原压缩包。
- 新上传记录的标识和存储目录均使用完整原文件名（含扩展名）。旧记录按保存的源文件名检查重复，原目录不自动搬迁；确认替换后使用新目录。
- 解析范围为 GB/T 27930 A 类系统车桩交互报文，不负责其他分文件的采样数据或控制器私有报文解析。

## 🔧 技术栈

- **React / Vite** - 界面
- **FastAPI / Uvicorn** - 本地接口和页面服务
- **Pandas / OpenPyXL** - 数据处理与 Excel 导出

## 📄 协议支持

- GB/T 27930-2015 电动汽车非车载传导式充电机与电池管理系统之间的通信协议

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📜 License

MIT License
