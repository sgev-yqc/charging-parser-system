"""充电报文解析系统 v3 — 纯 Streamlit 原生"""
import streamlit as st
from lib.database import init_db
from pages import list_page, detail_page, upload_page


st.set_page_config(page_title="充电报文解析系统", page_icon="🔋",
                   layout="wide", initial_sidebar_state="collapsed")


def main():
    init_db()

    # 从 URL 参数初始化页面路由
    qp = st.query_params
    if "page" in qp:
        st.session_state.page = qp["page"]
    if "view_order" in qp:
        st.session_state.selected_order_id = qp["view_order"]
        st.session_state.page = "detail"

    if "page" not in st.session_state:
        st.session_state.page = "list"

    page = st.session_state.page
    if page == "list":
        list_page.render()
    elif page == "detail":
        detail_page.render()
    elif page == "upload":
        upload_page.render()


if __name__ == "__main__":
    main()
