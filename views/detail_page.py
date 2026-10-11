"""Order detail page: statistics, stage breakdown, message table, exports."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from charging_parser.export import export_excel, export_json, export_txt


def render(store, data_dir):
    order_id = st.session_state.get("selected_order_id")
    orders = store.load_orders()

    if not order_id or order_id not in orders:
        st.warning("订单不存在或已被删除。")
        if st.button("返回解析记录"):
            st.session_state.page = "list"
            st.rerun()
        return

    info = orders[order_id]
    result_file = Path(info.get("result_file", ""))
    if not result_file.exists():
        st.error("解析结果文件缺失。")
        return
    with result_file.open("r", encoding="utf-8") as file:
        messages = json.load(file)

    data_messages = [message for message in messages if message["type"] == "data"]
    phases = {}
    message_types = {}
    for message in data_messages:
        phase = message.get("phase", "其他")
        name = message.get("name", "未知")
        phases[phase] = phases.get(phase, 0) + 1
        message_types[name] = message_types.get(name, 0) + 1

    if st.button("← 返回解析记录"):
        st.session_state.page = "list"
        st.session_state.selected_order_id = None
        st.rerun()

    st.subheader(f"订单 {order_id}")

    cards = st.columns(6, border=True)
    cards[0].metric("总报文数", len(data_messages))
    cards[1].metric("涉及阶段", len(phases))
    cards[2].metric("报文类型", len(message_types))
    cards[3].metric("文件大小", f"{info.get('file_size', 0) / 1024:.1f} KB")
    cards[4].metric("状态", info.get("status", "-"))
    cards[5].metric("上传时间", str(info.get("upload_time", ""))[11:19])

    with st.container(border=True):
        st.markdown("**阶段分布**")
        st.caption(" · ".join(f"{phase} {count} 条" for phase, count in sorted(phases.items())))

    filter_cols = st.columns(2)
    selected_phases = filter_cols[0].multiselect("筛选阶段", list(phases), default=list(phases))
    selected_types = filter_cols[1].multiselect("筛选报文", list(message_types), default=list(message_types))

    rows = []
    for index, message in enumerate(messages, 1):
        if message["type"] == "header":
            rows.append({"序号": None, "阶段": f"📌 {message['content']}", "报文": "", "方向": "", "解析内容": ""})
        elif message.get("phase") in selected_phases and message.get("name") in selected_types:
            rows.append({
                "序号": index,
                "阶段": message.get("phase", ""),
                "报文": message.get("name", ""),
                "方向": message.get("direction", ""),
                "解析内容": message.get("decoded", "")[:200],
            })

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        height=480,
        column_config={
            "序号": st.column_config.NumberColumn(width="small"),
            "解析内容": st.column_config.TextColumn(width="large"),
        },
    )

    st.markdown("**导出**")
    download_cols = st.columns(4)
    original_file = Path(info.get("original_file", ""))
    if original_file.exists():
        download_cols[0].download_button(
            "📄 原文件", original_file.read_bytes(),
            file_name=info.get("filename", "original.txt"),
            key=f"dl_orig_{order_id}",
        )
    download_cols[1].download_button(
        "📊 Excel", export_excel(messages),
        file_name=f"{order_id}_解析结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl_excel_{order_id}",
    )
    download_cols[2].download_button(
        "📋 JSON", export_json(messages),
        file_name=f"{order_id}_解析结果.json",
        key=f"dl_json_{order_id}",
    )
    download_cols[3].download_button(
        "📝 TXT", export_txt(messages, order_id),
        file_name=f"{order_id}_解析结果.txt",
        key=f"dl_txt_{order_id}",
    )
