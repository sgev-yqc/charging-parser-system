"""Charging parser system - Streamlit entry point and page router."""

import streamlit as st

from charging_parser.config import get_data_dir
from charging_parser.storage import OrderStore
from views import detail_page, list_page, upload_dialog

st.set_page_config(
    page_title="充电报文解析系统",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    '<style>html, body, [class*="css"] '
    '{ font-family: "Microsoft YaHei", "微软雅黑", sans-serif; }</style>',
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

header = st.columns([4, 1], vertical_alignment="center")
header[0].title("🔋 充电报文解析系统")
header[0].caption("GB/T 27930 充电通信报文解析工具")
if header[1].button("＋ 上传解析", type="primary", width="stretch"):
    upload_dialog.open_dialog(store)

st.divider()

if st.session_state.page == "detail":
    detail_page.render(store, DATA_DIR)
else:
    list_page.render(store, DATA_DIR)
