"""
订单详情页面 — 统计卡片、阶段分布、报文表格、导出
"""
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from lib.database import get_order, get_order_messages, get_order_phases
from lib.database import get_all_phases, get_all_msg_names
from lib.export import export_excel, export_json, export_txt
from lib.config import CSS


def render():
    """渲染订单详情页"""
    order_id = st.session_state.get("selected_order_id")
    if not order_id:
        st.error("未选择订单")
        if st.button("← 返回订单列表"):
            st.session_state.page_name = "list"
            st.rerun()
        return

    order = get_order(order_id)
    if not order:
        st.error(f"订单 {order_id} 不存在或已被删除")
        if st.button("← 返回订单列表"):
            st.session_state.page_name = "list"
            st.session_state.selected_order_id = None
            st.rerun()
        return

    messages = get_order_messages(order_id)
    phases = get_order_phases(order_id)
    all_phases = get_all_phases(order_id)
    all_msg_names = get_all_msg_names(order_id)

    st.markdown(CSS, unsafe_allow_html=True)

    # ── 导航 + 面包屑 ──
    st.markdown(f"""
    <div class="nav">
        <div class="nav-logo">🔋 充电报文解析</div>
        <div class="nav-links">
            <a class="nav-link" onclick="alert('back')">订单管理</a>
            <a class="nav-link active">订单详情</a>
        </div>
    </div>
    <div class="page">
    <div class="breadcrumb">
        <a onclick="alert('back')">订单管理</a>
        <span>›</span>
        <span>订单详情</span>
    </div>
    """, unsafe_allow_html=True)

    # ── 返回按钮 ──
    back_col, title_col = st.columns([1, 5])
    with back_col:
        if st.button("← 返回列表"):
            st.session_state.page_name = "list"
            st.session_state.selected_order_id = None
            st.rerun()

    st.markdown(f"<h2 style='font-weight:300;margin-bottom:16px;'>"
                f"<code style='font-family:Source Code Pro,monospace;background:#f0f4f8;"
                f"padding:2px 10px;border-radius:4px;color:#02BE7A;'>{order_id}</code></h2>",
                unsafe_allow_html=True)

    # ── 导出按钮 ──
    exp_cols = st.columns([1, 1, 1, 1, 8])
    fp = order.get("file_path")
    # Excel
    excel_buf = export_excel(messages, order_id)
    with exp_cols[0]:
        st.download_button("📊 Excel", excel_buf,
                          file_name=f"{order_id}_解析结果.xlsx",
                          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          key=f"dl_xlsx_{order_id}", use_container_width=True)
    # JSON
    json_str = export_json(messages)
    with exp_cols[1]:
        st.download_button("📋 JSON", json_str,
                          file_name=f"{order_id}_解析结果.json",
                          key=f"dl_json_{order_id}", use_container_width=True)
    # TXT
    txt_str = export_txt(messages, order_id)
    with exp_cols[2]:
        st.download_button("📝 TXT", txt_str,
                          file_name=f"{order_id}_解析结果.txt",
                          key=f"dl_txt_{order_id}", use_container_width=True)
    # 原文件
    with exp_cols[3]:
        if fp and Path(fp).exists():
            with open(fp, "rb") as f:
                st.download_button("📄 原文件", f.read(),
                                  file_name=order["filename"],
                                  key=f"dl_orig_{order_id}", use_container_width=True)

    # ── 统计卡片（6 宫格） ──
    data_msgs = [m for m in messages if m["msg_type"] == "data"]
    st.markdown("<div class='stat-grid'>", unsafe_allow_html=True)

    pile_id = order.get("charging_pile_id", "")
    pile_html = (f"<span class='num-sm'>{pile_id}</span>" if pile_id else "-")
    ut = (order.get("upload_time", "") or "-")[:16]
    fsize = f"{order['file_size']/1024:.1f} KB" if order.get("file_size") else "-"

    stats = [
        (str(len(data_msgs)), "总报文数"),
        (str(len(phases)), "涉及阶段"),
        (pile_html, "充电桩编号"),
        (fsize, "文件大小"),
        (ut, "上传时间"),
        (order.get("status", "-"), "状态"),
    ]
    for num, lbl in stats:
        st.markdown(f"<div class='stat-card'><div class='num'>{num}</div>"
                    f"<div class='lbl'>{lbl}</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 阶段分布 ──
    if phases:
        st.markdown("<div class='section-title'>📊 阶段分布</div>", unsafe_allow_html=True)
        tags = "".join(f"<span class='phase-tag'>{p} {c}</span>"
                      for p, c in sorted(phases.items()))
        st.markdown(f"<div class='phase-bar'>{tags}</div>", unsafe_allow_html=True)

    # ── 筛选 ──
    st.markdown("<div class='section-title'>🔍 筛选报文</div>", unsafe_allow_html=True)
    fc1, fc2 = st.columns(2)
    with fc1:
        sel_phase = st.selectbox("阶段", ["全部"] + all_phases,
                                 key=f"pf_{order_id}", label_visibility="collapsed")
    with fc2:
        sel_msg = st.selectbox("报文", ["全部"] + all_msg_names,
                               key=f"mf_{order_id}", label_visibility="collapsed")

    # 过滤
    filtered = messages
    if sel_phase and sel_phase != "全部":
        filtered = [m for m in filtered if m["phase"] == sel_phase]
    if sel_msg and sel_msg != "全部":
        filtered = [m for m in filtered if m["msg_name"] == sel_msg]

    # ── 解析结果表格 ──
    st.markdown("<div class='section-title'>📋 解析结果</div>", unsafe_allow_html=True)

    if filtered:
        rows = []
        for m in filtered:
            rows.append({
                "序号": m["seq"],
                "时间戳": m["timestamp"],
                "报文": m["msg_name"],
                "阶段": m["phase"],
                "方向": m["direction"],
                "解析内容": m["decoded"][:200],
            })
        df = pd.DataFrame(rows)
        st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=df.columns.tolist(),
            key=f"detail_table_{order_id}",
            height=480,
        )
    else:
        st.info("无匹配的报文数据")

    st.markdown("</div>", unsafe_allow_html=True)
