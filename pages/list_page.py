"""订单列表 — 纯 Streamlit 原生"""
import streamlit as st
import pandas as pd
from lib.database import search_orders, get_total_stats
from lib.config import C_GREEN, C_TEXT
from lib.config import SORT_OPTIONS, STATUS_OPTIONS, PER_PAGE_OPTIONS


def render():
    nav1, nav2, _, nav3 = st.columns([1, 1.5, 1, 8])
    with nav1:
        st.button("📋 订单管理", disabled=True, use_container_width=True)
    with nav2:
        if st.button("📤 上传文件", use_container_width=True):
            st.session_state.page = "upload"
            st.rerun()
    with nav3:
        stats = get_total_stats()
        st.markdown(
            f"<div style='text-align:right;color:#64748d;font-size:13px;'>"
            f"共 <b>{stats['order_count']}</b> 个订单 · "
            f"<b>{stats['msg_count']:,}</b> 条报文</div>",
            unsafe_allow_html=True)

    st.markdown("---")
    st.header("订单管理")
    st.caption("检索、查看所有充电报文订单")

    # 筛选
    with st.expander("🔍 筛选", expanded=True):
        fc = st.columns([2, 1, 2, 1, 0.8])
        with fc[0]:
            search = st.text_input("关键词", placeholder="订单号/桩编号/文件名",
                                   label_visibility="collapsed")
        with fc[1]:
            status_sel = st.selectbox("状态", STATUS_OPTIONS, label_visibility="collapsed")
        with fc[2]:
            dc = st.columns(2)
            with dc[0]:
                d_from = st.date_input("起始", value=None, label_visibility="collapsed", key="ldf")
            with dc[1]:
                d_to = st.date_input("截止", value=None, label_visibility="collapsed", key="ldt")
        with fc[3]:
            sort_sel = st.selectbox("排序", list(SORT_OPTIONS.values()), label_visibility="collapsed")

    # 查询参数
    sort_map = {v: k for k, v in SORT_OPTIONS.items()}
    sort_by = sort_map.get(sort_sel, "newest")
    per_page = st.session_state.get("per_page", 50)
    page = st.session_state.get("page", 1)

    dfv = d_from.strftime("%Y-%m-%d") if d_from else ""
    dtv = d_to.strftime("%Y-%m-%d") if d_to else ""

    orders, total = search_orders(search, status_sel, dfv, dtv, sort_by, page, per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
        st.session_state.page = page

    st.markdown(f"<div style='font-size:12px;color:#64748d;'>第 {page}/{total_pages} 页 · 共 {total} 条</div>",
                unsafe_allow_html=True)

    # 表格
    if orders:
        rows = []
        for o in orders:
            ut = (o.get("upload_time", "") or "")[:16]
            sz = o.get("file_size", 0)
            rows.append({
                "充电桩编号": o.get("charging_pile_id", ""),
                "订单号": o.get("order_id", ""),
                "大小": f"{sz/1024:.1f} KB" if sz else "-",
                "上传时间": ut,
            })

        df = pd.DataFrame(rows)

        event = st.dataframe(
            df, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row",
            key="order_table",
            column_config={
                "充电桩编号": st.column_config.TextColumn("充电桩编号", width="small"),
                "订单号": st.column_config.TextColumn("订单号", width="large"),
                "大小": st.column_config.TextColumn("大小", width="small"),
                "上传时间": st.column_config.TextColumn("上传时间", width="medium"),
            },
            height=min(45 * len(rows) + 40, 600),
        )

        if event.selection and event.selection.rows:
            idx = event.selection.rows[0]
            oid = orders[idx]["order_id"]
            st.session_state.page = "detail"
            st.session_state.selected_order_id = oid
            st.rerun()

        # 分页
        st.markdown("---")
        pc = st.columns([0.8, 0.8, 0.8, 1, 0.8, 0.8, 0.5, 2])
        with pc[0]:
            if st.button("‹‹ 首页", disabled=(page <= 1), use_container_width=True):
                st.session_state.page = 1; st.rerun()
        with pc[1]:
            if st.button("‹ 上一页", disabled=(page <= 1), use_container_width=True):
                st.session_state.page = max(1, page-1); st.rerun()
        with pc[2]:
            st.markdown(f"<div style='text-align:center;padding:4px;font-size:12px;color:#64748d;'>{page}/{total_pages}</div>",
                        unsafe_allow_html=True)
        with pc[3]:
            if st.button("下一页 ›", disabled=(page >= total_pages), use_container_width=True):
                st.session_state.page = min(total_pages, page+1); st.rerun()
        with pc[4]:
            if st.button("末页 ››", disabled=(page >= total_pages), use_container_width=True):
                st.session_state.page = total_pages; st.rerun()
        with pc[5]:
            npp = st.selectbox("每页", PER_PAGE_OPTIONS,
                               index=PER_PAGE_OPTIONS.index(per_page) if per_page in PER_PAGE_OPTIONS else 0,
                               label_visibility="collapsed", key="pp")
            if npp != per_page:
                st.session_state.per_page = npp
                st.session_state.page = 1
                st.rerun()
        with pc[6]:
            g = st.text_input("跳转", "", placeholder="页号", label_visibility="collapsed", key="gp")
            if g and g.isdigit():
                p = int(g)
                if 1 <= p <= total_pages:
                    st.session_state.page = p; st.rerun()
    else:
        st.info("暂无订单数据")
