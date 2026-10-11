"""Charging parser system - Streamlit entry point and page router."""

import streamlit as st

from charging_parser.config import get_data_dir
from charging_parser.storage import OrderStore
from views import detail_page, list_page

st.set_page_config(
    page_title="充电报文解析系统",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """<style>
    html, body, [class*="css"] { font-family: "Microsoft YaHei", "微软雅黑", sans-serif; }
    .block-container { max-width: 1320px; padding-top: 2rem; padding-bottom: 4rem; }
    h1, h2, h3 { color: #14243a; letter-spacing: -.025em; }
    div[data-testid="stButton"] > button[kind="primary"] {
        background: #087f69; border-color: #087f69; color: white;
        border-radius: 10px; font-weight: 650; min-height: 42px;
    }
    div[data-testid="stButton"] > button { border-radius: 10px; }
    .app-hero {
        padding: 26px 32px; border-radius: 18px;
        background: linear-gradient(115deg, #10253d 0%, #173b4f 68%, #145c5b 100%);
        color: #fff; box-shadow: 0 12px 30px rgba(16, 37, 61, .10);
    }
    .app-hero .eyebrow { color: #78e0c5; font-size: 13px; font-weight: 700; letter-spacing: .08em; }
    .app-hero h1 { color: #fff; font-size: 30px; margin: 8px 0 7px; }
    .app-hero p { color: #d6e4ec; font-size: 15px; margin: 0; }
    .section-heading { margin: 12px 0 3px; font-size: 21px; font-weight: 700; color: #14243a; }
    .section-caption { color: #62758b; font-size: 14px; margin-bottom: 12px; }
    .stat-card { padding: 17px 20px; border: 1px solid #dae5e8; border-radius: 14px; background: white; }
    .stat-card .label { color: #617489; font-size: 13px; }
    .stat-card .value { color: #14243a; font-size: 27px; font-weight: 750; margin-top: 5px; }
    .stat-card .hint { color: #708295; font-size: 12px; margin-top: 3px; }
    .order-head { color: #617489; font-size: 13px; font-weight: 650; padding: 2px 0 8px; }
    .order-primary { color: #17344d; font-weight: 650; overflow-wrap: anywhere; }
    .order-secondary { color: #6a7d90; font-size: 12px; overflow-wrap: anywhere; }
    .status-ok { display: inline-block; padding: 4px 9px; border-radius: 20px; background: #e6f5ef; color: #12745a; font-size: 12px; font-weight: 650; }
    .status-other { display: inline-block; padding: 4px 9px; border-radius: 20px; background: #fff0e8; color: #a25021; font-size: 12px; font-weight: 650; }
    </style>""",
    unsafe_allow_html=True,
)

DATA_DIR = get_data_dir()
store = OrderStore(DATA_DIR)

# Consume deep-link parameters once, then clear them so the URL stays in sync
# with the rendered page instead of forcing every later rerun back to detail.
query = st.query_params
if "page" not in st.session_state:
    st.session_state.page = query.get("page", "list")
    if query.get("view_order"):
        st.session_state.selected_order_id = query["view_order"]
        st.session_state.page = "detail"
    st.query_params.clear()

st.markdown(
    '<div class="app-hero"><div class="eyebrow">GB/T 27930 · 充电通信</div>'
    '<h1>报文解析工作台</h1><p>上传原始报文，按订单查看解析结果并导出。</p></div>',
    unsafe_allow_html=True,
)

if st.session_state.page == "detail":
    detail_page.render(store, DATA_DIR)
else:
    list_page.render(store, DATA_DIR)
