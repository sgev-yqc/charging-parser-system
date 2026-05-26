"""上传文件 — 纯 Streamlit 原生"""
import streamlit as st
import pandas as pd
from lib.database import add_order, extract_order_id
from lib.config import CSS


def render():
    st.markdown(CSS, unsafe_allow_html=True)
    nav1, nav2, _ = st.columns([1, 1.5, 10])
    with nav1:
        if st.button("📋 订单管理", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()
    with nav2:
        st.button("📤 上传文件", disabled=True, use_container_width=True)

    st.markdown("---")
    st.header("上传文件")
    st.caption("批量上传 BMS 报文文件，自动解析并入库")

    uploaded_files = st.file_uploader(
        "选择 .txt 报文文件", type=["txt"],
        accept_multiple_files=True,
        help="支持同时上传多个 BMS 报文文件",
        label_visibility="collapsed")

    if uploaded_files:
        st.markdown(f"**已选择 {len(uploaded_files)} 个文件**")
        info = [{
            "文件名": f.name,
            "订单号": extract_order_id(f.name),
            "大小": f"{len(f.getvalue())/1024:.1f} KB",
        } for f in uploaded_files]
        st.dataframe(pd.DataFrame(info), use_container_width=True, hide_index=True)

        if st.button("🚀 开始上传并解析", type="primary", use_container_width=True):
            bar = st.progress(0)
            status = st.empty()
            suc, fail = [], []
            for i, f in enumerate(uploaded_files):
                bar.progress((i + 1) / len(uploaded_files))
                status.text(f"正在处理: {f.name}...")
                try:
                    oid = add_order(f)
                    suc.append({"文件名": f.name, "订单号": oid, "状态": "✅ 成功"})
                except Exception as e:
                    fail.append({"文件名": f.name, "订单号": "-", "状态": f"❌ {e}"})
            bar.empty()
            status.empty()
            st.success(f"处理完成! 成功 {len(suc)}, 失败 {len(fail)}")
            if suc:
                st.dataframe(pd.DataFrame(suc), use_container_width=True, hide_index=True)
            if fail:
                st.dataframe(pd.DataFrame(fail), use_container_width=True, hide_index=True)
            if suc:
                st.info("💡 上传完成，切换到「订单管理」查看")
