"""Upload and parse dialog - an action invoked from the page header."""

import pandas as pd
import streamlit as st

from charging_parser.storage import extract_order_id


def _parse_files(store, uploaded_files):
    results = []
    progress = st.progress(0.0)
    status = st.empty()

    for index, uploaded_file in enumerate(uploaded_files):
        status.text(f"正在处理：{uploaded_file.name}")
        progress.progress((index + 1) / len(uploaded_files))
        try:
            content = uploaded_file.getvalue()
            order_id = extract_order_id(uploaded_file.name)
            if order_id in store.load_orders():
                store.delete_order(order_id)
            store.add_order(order_id, uploaded_file.name, content)
            results.append({"文件名": uploaded_file.name, "订单号": order_id, "状态": "✅ 成功"})
        except Exception as error:
            results.append({"文件名": uploaded_file.name, "订单号": "-", "状态": f"❌ 失败：{error}"})

    progress.empty()
    status.empty()
    return results


@st.dialog("上传并解析报文", width="large")
def _dialog(store):
    if "uploader_round" not in st.session_state:
        st.session_state.uploader_round = 0

    uploaded_files = st.file_uploader(
        "选择 .txt 报文文件（可多选）",
        type=["txt"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_round}",
    )
    if not uploaded_files:
        st.caption("系统会从文件名自动识别订单号并解析，支持同时上传多个文件。")
        return

    preview = pd.DataFrame([
        {
            "文件名": uploaded_file.name,
            "订单号": extract_order_id(uploaded_file.name),
            "大小 (KB)": round(len(uploaded_file.getvalue()) / 1024, 1),
        }
        for uploaded_file in uploaded_files
    ])
    st.dataframe(preview, hide_index=True)

    if st.button("开始上传并解析", type="primary"):
        st.session_state.last_upload_results = _parse_files(store, uploaded_files)
        # Bump the uploader key so a freshly opened dialog starts empty.
        st.session_state.uploader_round += 1
        st.rerun()


def open_dialog(store):
    """Show the upload dialog."""
    _dialog(store)
