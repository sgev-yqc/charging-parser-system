"""订单详情 — 纯 Streamlit 原生"""
import streamlit as st
import pandas as pd
from pathlib import Path
from lib.database import get_order, get_order_messages, get_order_phases
from lib.database import get_all_phases, get_all_msg_names
from lib.export import export_excel, export_json, export_txt


def render():
    nav1, nav2, _ = st.columns([1, 1.5, 10])
    with nav1:
        if st.button("← 返回列表", use_container_width=True):
            st.session_state.page = "list"
            st.session_state.selected_order_id = None
            st.rerun()
    with nav2:
        if st.button("📤 上传文件", use_container_width=True):
            st.session_state.page = "upload"
            st.rerun()

    st.markdown("---")

    order_id = st.session_state.get("selected_order_id")
    if not order_id:
        st.error("未选择订单")
        return

    order = get_order(order_id)
    if not order:
        st.error(f"订单 {order_id} 不存在")
        return

    messages = get_order_messages(order_id)
    phases = get_order_phases(order_id)
    all_phases = get_all_phases(order_id)
    all_msg_names = get_all_msg_names(order_id)
    data_msgs = [m for m in messages if m.get("msg_type") == "data"]

    st.code(order_id, language=None)
    st.caption(f"订单号 · {order.get('charging_pile_id', '-')}")

    # 导出
    exp = st.columns([1, 1, 1, 1, 8])
    excel_buf = export_excel(messages, order_id)
    with exp[0]:
        st.download_button("📊 Excel", excel_buf,
                          file_name=f"{order_id}_解析结果.xlsx",
                          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          use_container_width=True)
    json_str = export_json(messages)
    with exp[1]:
        st.download_button("📋 JSON", json_str,
                          file_name=f"{order_id}_解析结果.json",
                          use_container_width=True)
    txt_str = export_txt(messages, order_id)
    with exp[2]:
        st.download_button("📝 TXT", txt_str,
                          file_name=f"{order_id}_解析结果.txt",
                          use_container_width=True)
    fp = order.get("file_path")
    with exp[3]:
        if fp and Path(fp).exists():
            with open(fp, "rb") as f:
                st.download_button("📄 原文件", f.read(),
                                  file_name=order.get("filename", "原文件"),
                                  use_container_width=True)

    # 统计卡片
    pile_id = order.get("charging_pile_id", "") or "-"
    ut = (order.get("upload_time", "") or "-")[:16]
    fsize = order.get("file_size", 0)
    size_str = f"{fsize/1024:.1f} KB" if fsize else "-"

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1: st.metric("总报文数", len(data_msgs))
    with m2: st.metric("涉及阶段", len(phases))
    with m3: st.metric("充电桩编号", pile_id)
    with m4: st.metric("文件大小", size_str)
    with m5: st.metric("上传时间", ut)
    with m6: st.metric("状态", order.get("status", "-"))

    # 阶段分布
    if phases:
        st.markdown("**📊 阶段分布**")
        tags = ", ".join(f"{p}({c}条)" for p, c in sorted(phases.items()))
        st.caption(tags)

    # 筛选
    st.markdown("**🔍 筛选报文**")
    fc1, fc2 = st.columns(2)
    with fc1:
        sel_phase = st.selectbox("阶段", ["全部"] + all_phases, label_visibility="collapsed", key="pf")
    with fc2:
        sel_msg = st.selectbox("报文", ["全部"] + all_msg_names, label_visibility="collapsed", key="mf")

    filtered = messages
    if sel_phase and sel_phase != "全部":
        filtered = [m for m in filtered if m.get("phase") == sel_phase]
    if sel_msg and sel_msg != "全部":
        filtered = [m for m in filtered if m.get("msg_name") == sel_msg]

    st.markdown("**📋 解析结果**")
    if filtered:
        rows = [{
            "序号": m.get("seq", ""),
            "时间戳": m.get("timestamp", ""),
            "报文": m.get("msg_name", ""),
            "阶段": m.get("phase", ""),
            "方向": m.get("direction", ""),
            "解析内容": (m.get("decoded", "") or "")[:200],
        } for m in filtered]
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         "序号": st.column_config.NumberColumn(width="small"),
                         "解析内容": st.column_config.TextColumn(width="large"),
                     },
                     height=480)
    else:
        st.info("无匹配报文")
