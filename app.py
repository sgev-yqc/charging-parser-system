#!/usr/bin/env python3
"""
充电报文解析系统 v2 — 模块化重构版
"""
import streamlit as st
from lib.database import init_db, get_total_stats
from pages import list_page, detail_page


def main():
    # 初始化数据库
    init_db()

    # 初始化 session_state
    if "page_name" not in st.session_state:
        st.session_state.page_name = "list"
    if "selected_order_id" not in st.session_state:
        st.session_state.selected_order_id = None
    if "selected_ids" not in st.session_state:
        st.session_state.selected_ids = set()
    if "page" not in st.session_state:
        st.session_state.page = 1
    if "per_page" not in st.session_state:
        st.session_state.per_page = 50

    # 页面路由
    if st.session_state.page_name == "list":
        list_page.render()
    elif st.session_state.page_name == "detail":
        detail_page.render()
    else:
        st.session_state.page_name = "list"
        st.rerun()


if __name__ == "__main__":
    st.set_page_config(
        page_title="充电报文解析系统",
        page_icon="🔋",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    main()
