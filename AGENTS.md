# 充电报文解析系统（Charging Parser System）

## 项目概述

基于 GB/T 27930 协议的充电通信报文解析工具，支持批量上传、订单管理、多格式导出。

## 技术栈

- Python 3.8+ / Streamlit
- SQLite（本地数据库）
- openpyxl / pandas（导出）

## 项目结构

```
charging-parser-system/
├── app.py              # 主入口（页面路由 + URL参数解析）
├── lib/
│   ├── config.py       # 配色常量 + 最小化CSS
│   ├── parser.py       # CAN报文解析（GB/T 27930）
│   ├── database.py     # SQLite 存储层
│   └── export.py       # Excel/JSON/TXT 导出
├── pages/
│   ├── list_page.py    # 订单列表页（筛选/分页/行选跳详情）
│   ├── detail_page.py  # 订单详情页（metric卡片/阶段/报文表格）
│   └── upload_page.py  # 上传页（批量上传/解析/入库）
├── data/               # SQLite DB + 原始文件（自动生成）
├── design/             # 设计方案文档
└── AGENTS.md           # 本文件
```

## 设计原则

- **纯 Streamlit 原生**：不手写 HTML/CSS 表格、不自定义导航栏、不用 components.html
- **最小化 CSS**：只保留品牌色 green #02BE7A，不暴力覆盖 Streamlit 控件
- **行选跳转**：列表页点击行即进入详情，不用额外"查看"按钮
- **URL 路由**：支持 `?page=upload` / `?page=detail&view_order=XXX` 直接跳转

## 开发规范

### 分支策略
- `main` — 稳定版
- `refactor-new-ui` — 当前重构分支

### 配色方案
- 主色：绿色 `#02BE7A`
- 危险：红色 `#EE6666`
- 警告：橙色 `#DE6B33`
- 底色：灰白 `#f5f6f7`

### 数据库
- SQLite，文件路径：`/tmp/charging_parser_data/parser.db`
- 两张表：`orders`（订单索引）、`parsed_messages`（解析报文）
- 订单 ID 从文件名自动提取，充电桩编号为订单 ID 前 16 位

### GB/T 27930 CAN 报文
- 解析核心在 `lib/parser.py`
- 报文按阶段分组：握手/参数/准备/充电/中止/结束/错误/传输
- BRM 和 BCP 使用 TP 传输协议（多帧），其它为单帧

### 部署
- 启动命令：`streamlit run app.py --server.port 8502 --server.address 0.0.0.0`

### 工作流程（AI Agent 守则）
1. **理解需求** — 有疑问先问用户
2. **展示方案** — 给方案，等确认再动手
3. **写代码** — 保持模块化，纯 Streamlit，不手写 HTML/CSS
4. **验证** — 语法检查 + 逻辑验证
5. **推送** — 推送到 feature 分支

输出文件只能放到：
`/mnt/c/Users/60363/Documents/WPSDrive/1175044652/WPS云盘/00_Obsidian_QC/Obsidian_office/Obsidian_Attachment/【Agent】Surface Hermes/【Agent】【code-coder】/`
