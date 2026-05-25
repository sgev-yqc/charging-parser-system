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
├── app.py              # 主入口（仅页面路由）
├── lib/
│   ├── config.py       # 配色、CSS、常量
│   ├── parser.py       # CAN报文解析（GB/T 27930）
│   ├── database.py     # SQLite 存储层
│   └── export.py       # Excel/JSON/TXT 导出
├── pages/
│   ├── list_page.py    # 订单列表页（筛选/分页/批量删除）
│   └── detail_page.py  # 订单详情页（统计/阶段/报文表格）
├── data/               # SQLite DB + 原始文件（自动生成）
└── README.md
```

## 开发规范

### 分支策略
- `main` — 稳定版
- `refactor-new-ui` — 当前重构分支
- 新功能开 feature 分支，合 main 前提 PR

### 配色方案（用户指定，不可修改）
- 主色：绿色 `#02BE7A`
- 危险：红色 `#EE6666`
- 警告：橙色 `#DE6B33`
- 正文：深色 `#1a1a2e`
- 底色：灰白 `#f5f6f7`

### UI 设计原则
- Stripe 风格（白底 + 品牌色 + 细边框）
- 两页式架构：订单列表（分页表格） + 独立详情页
- 筛选栏在列表页顶部，批量操作在表格上方
- `st.data_editor` 实现勾选，`st.session_state` 管理页面路由
- 拒绝 expander 假弹窗

### 数据库
- SQLite，文件路径：`/root/charging_parser_system/data/parser.db`
- 两张表：`orders`（订单索引）、`parsed_messages`（解析报文）
- 订单 ID 从文件名自动提取，充电桩编号为订单 ID 前 16 位

### GB/T 27930 CAN 报文
- 解析核心在 `lib/parser.py`，MSG_MAP 字典映射 CAN ID → 报文名
- 报文按阶段分组：握手/参数/准备/充电/中止/结束/错误/传输
- BRM 和 BCP 使用 TP 传输协议（多帧），其它为单帧

### 部署
- 腾讯云服务器，端口 8501
- 启动命令：`streamlit run app.py --server.port 8501 --server.address 0.0.0.0`

### 工作流程（AI Agent 守则）

**重要：每次修改本项目的代码前，必须按以下流程执行：**

1. **理解需求** — 如果有疑问，先问用户
2. **展示方案** — 给出改动方案，等用户说"做"再动手
3. **写代码** — 保持模块化，一个文件一个职责
4. **验证** — 语法检查 + 逻辑验证
5. **推送** — 推送到 feature 分支，不在 main 上直接改

输出文件只能放到：
`/mnt/c/Users/60363/Documents/WPSDrive/1175044652/WPS云盘/00_Obsidian_QC/Obsidian_office/Obsidian_Attachment/【Agent】Surface Hermes/【Agent】【code-coder】/`

**不要往桌面放文件。**
