"""
配色方案、CSS 样式、系统常量
"""
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# 配色（用户指定）
# ═══════════════════════════════════════════════════════════════════════════════
C_GREEN = "#02BE7A"
C_GREEN_HOVER = "#02A86D"
C_RED = "#EE6666"
C_ORANGE = "#DE6B33"
C_DARK = "#1a1a2e"
C_TEXT = "#273951"
C_TEXT_MUTED = "#64748d"
C_BORDER = "#e5edf5"
C_BG = "#f5f6f7"
C_WHITE = "#ffffff"

# ═══════════════════════════════════════════════════════════════════════════════
# 路径
# ═══════════════════════════════════════════════════════════════════════════════
DATA_DIR = Path("/root/charging_parser_system/data")
DB_PATH = DATA_DIR / "parser.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CSS（Stripe 风格 + 用户配色）
# ═══════════════════════════════════════════════════════════════════════════════
CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300;400;500;600&family=Source+Code+Pro:wght@400;500&display=swap');
    * {{ font-family: 'Source Sans 3', system-ui, 'Microsoft YaHei', 'PingFang SC', sans-serif; }}
    .stApp {{ background: {C_BG}; }}
    .st-emotion-cache-6q9sum {{ background: {C_BG} !important; }}

    /* 导航栏 */
    .nav {{ background: {C_WHITE}; border-bottom: 1px solid {C_BORDER}; padding: 0 28px; height: 52px;
            display: flex; align-items: center; gap: 28px; position: sticky; top: 0; z-index: 100; }}
    .nav-logo {{ font-size: 17px; font-weight: 600; color: {C_GREEN}; display: flex; align-items: center; gap: 6px; }}
    .nav-links {{ display: flex; gap: 2px; }}
    .nav-link {{ padding: 6px 14px; border-radius: 4px; font-size: 13px; font-weight: 400; color: {C_DARK};
                cursor: pointer; transition: all 0.12s; text-decoration: none; }}
    .nav-link:hover {{ color: {C_GREEN}; }}
    .nav-link.active {{ color: {C_GREEN}; background: rgba(2,190,122,0.06); }}
    .nav-status {{ margin-left: auto; font-size: 13px; color: {C_TEXT_MUTED}; font-weight: 300;
                  display: flex; align-items: center; gap: 12px; }}

    /* 页面容器 */
    .page {{ max-width: 1360px; margin: 0 auto; padding: 24px 28px; }}
    .page-head {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }}
    .page-head h1 {{ font-size: 24px; font-weight: 300; color: {C_DARK}; letter-spacing: -0.24px; margin: 0; }}
    .page-head .sub {{ font-size: 13px; font-weight: 300; color: {C_TEXT_MUTED}; margin-top: 1px; }}

    /* 筛选栏 */
    .filter-bar {{ background: {C_WHITE}; border: 1px solid {C_BORDER}; border-radius: 6px; padding: 14px 18px;
                   margin-bottom: 16px; }}
    .filter-bar label {{ font-size: 11px; font-weight: 400; color: {C_TEXT}; margin-bottom: 2px; display: block; }}

    /* 表格容器 */
    .table-card {{ background: {C_WHITE}; border: 1px solid {C_BORDER}; border-radius: 6px; overflow: hidden;
        box-shadow: rgba(50,50,93,0.08) 0px 2px 5px -1px, rgba(0,0,0,0.06) 0px 1px 3px -1px; }}

    .badge {{ display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 11px; font-weight: 400; }}
    .badge-ok {{ background: rgba(2,190,122,0.12); color: #1a8a5a; border: 1px solid rgba(2,190,122,0.25); }}
    .badge-wait {{ background: rgba(222,107,51,0.12); color: {C_ORANGE}; border: 1px solid rgba(222,107,51,0.25); }}
    .badge-fail {{ background: rgba(238,102,102,0.12); color: {C_RED}; border: 1px solid rgba(238,102,102,0.25); }}

    /* 详情统计卡片 */
    .stat-grid {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin-bottom: 20px; }}
    .stat-card {{ background: {C_WHITE}; border: 1px solid {C_BORDER}; border-radius: 6px; padding: 12px 14px; }}
    .stat-card .num {{ font-size: 20px; font-weight: 300; color: {C_DARK}; }}
    .stat-card .lbl {{ font-size: 11px; color: {C_TEXT_MUTED}; margin-top: 1px; }}
    .stat-card .num-sm {{ font-family: 'Source Code Pro', monospace; font-size: 14px; color: {C_GREEN}; }}

    .section-title {{ font-size: 14px; font-weight: 400; color: {C_DARK}; margin-bottom: 8px; }}
    .phase-bar {{ display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 16px; }}
    .phase-tag {{ padding: 3px 10px; border-radius: 4px; font-size: 12px;
        background: rgba(2,190,122,0.06); color: {C_GREEN}; border: 1px solid rgba(2,190,122,0.15); }}

    /* 面包屑 */
    .breadcrumb {{ display: flex; align-items: center; gap: 6px; font-size: 13px; color: {C_TEXT_MUTED};
                  margin-bottom: 20px; }}
    .breadcrumb a {{ color: {C_GREEN}; text-decoration: none; cursor: pointer; }}
    .breadcrumb a:hover {{ text-decoration: underline; }}

    .batch-bar {{ display: flex; align-items: center; gap: 12px; font-size: 13px; color: {C_TEXT_MUTED}; margin-bottom: 8px; }}
    hr {{ margin: 8px 0 !important; border-color: {C_BORDER} !important; }}
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 报文常量
# ═══════════════════════════════════════════════════════════════════════════════
SORT_OPTIONS = {
    "newest": "上传时间(新→旧)",
    "oldest": "上传时间(旧→新)",
    "order_id_asc": "订单号(升序)",
    "order_id_desc": "订单号(降序)",
}

STATUS_OPTIONS = ["全部", "已完成", "待解析", "解析失败"]

PER_PAGE_OPTIONS = [20, 50, 100]
