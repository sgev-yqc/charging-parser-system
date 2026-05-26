"""配色与路径常量"""
from pathlib import Path

C_GREEN = "#02BE7A"
C_ORANGE = "#DE6B33"
C_RED = "#EE6666"
C_TEXT = "#273951"
C_BG = "#f5f6f7"

DATA_DIR = Path("/tmp/charging_parser_data")
DB_PATH = DATA_DIR / "parser.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 最小化 CSS，仅用于品牌色
CSS = f"""
<style>
    .stApp {{ font-family: 'Microsoft YaHei', '微软雅黑', system-ui, sans-serif; }}
    /* 品牌色按钮 */
    div.stButton > button[data-testid="baseButton-secondary"] {{
        border-color: {C_GREEN}; color: {C_GREEN};
    }}
    div.stButton > button[data-testid="baseButton-secondary"]:hover {{
        background: rgba(2,190,122,0.06);
    }}
</style>
"""

SORT_OPTIONS = {
    "newest": "上传时间(新→旧)",
    "oldest": "上传时间(旧→新)",
    "order_id_asc": "订单号(升序)",
    "order_id_desc": "订单号(降序)",
}
STATUS_OPTIONS = ["全部", "已完成", "待解析", "解析失败"]
PER_PAGE_OPTIONS = [20, 50, 100]
