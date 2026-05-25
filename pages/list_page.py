"""
订单列表页面 — 筛选、分页、勾选、批量删除
"""
import streamlit as st
import pandas as pd
from lib.database import search_orders, delete_orders, get_total_stats
from lib.config import CSS, C_TEXT_MUTED, C_BORDER, C_GREEN, C_WHITE, C_DARK
from lib.config import SORT_OPTIONS, STATUS_OPTIONS, PER_PAGE_OPTIONS


def render():
    """渲染订单列表页"""
    st.markdown(CSS, unsafe_allow_html=True)

    # ── 导航栏 ──
    stats = get_total_stats()
    st.markdown(f"""
    <div class="nav">
        <div class="nav-logo">🔋 充电报文解析</div>
        <div class="nav-links">
            <a class="nav-link active">订单管理</a>
            <a class="nav-link">上传文件</a>
        </div>
        <div class="nav-status">
            <span>共 <strong>{stats['order_count']}</strong> 个订单 ·
                  <strong>{stats['msg_count']:,}</strong> 条报文</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="page">
    <div class="page-head">
        <div>
            <h1>订单管理</h1>
            <div class="sub">检索、查看、管理所有充电报文订单</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 筛选栏 ──
    with st.form("filter_form", clear_on_submit=False, border=False):
        cols = st.columns([2, 1, 2, 1, 0.8])
        with cols[0]:
            search = st.text_input("🔍 关键词", placeholder="订单号 / 文件名 / 桩编号",
                                  value=st.session_state.get("search", ""))
        with cols[1]:
            status_opts = STATUS_OPTIONS
            cur_status = st.session_state.get("status_filter", "全部")
            status_idx = status_opts.index(cur_status) if cur_status in status_opts else 0
            status_sel = st.selectbox("状态", status_opts, index=status_idx)
        with cols[2]:
            date_cols = st.columns(2)
            with date_cols[0]:
                d_from = st.date_input("起始", value=None, label_visibility="collapsed",
                                       key="list_date_from")
            with date_cols[1]:
                d_to = st.date_input("截止", value=None, label_visibility="collapsed",
                                     key="list_date_to")
        with cols[3]:
            sort_rev = {v: k for k, v in SORT_OPTIONS.items()}
            cur_sort = st.session_state.get("sort_by", "newest")
            cur_sort_label = SORT_OPTIONS.get(cur_sort, "上传时间(新→旧)")
            sort_keys = list(SORT_OPTIONS.values())
            sort_idx = sort_keys.index(cur_sort_label) if cur_sort_label in sort_keys else 0
            sort_sel = st.selectbox("排序", sort_keys, index=sort_idx)
        with cols[4]:
            st.write("")  # spacer
            st.write("")
            submitted = st.form_submit_button("🔍 查询", use_container_width=True)

    if submitted:
        st.session_state.search = search
        st.session_state.status_filter = status_sel
        st.session_state.date_from = d_from.strftime("%Y-%m-%d") if d_from else ""
        st.session_state.date_to = d_to.strftime("%Y-%m-%d") if d_to else ""
        st.session_state.sort_by = {v: k for k, v in SORT_OPTIONS.items()}.get(sort_sel, "newest")
        st.session_state.page = 1
        st.rerun()

    # 从 session 读取筛选参数
    search_val = st.session_state.get("search", "")
    status_val = st.session_state.get("status_filter", "全部")
    date_from_val = st.session_state.get("date_from", "")
    date_to_val = st.session_state.get("date_to", "")
    sort_val = st.session_state.get("sort_by", "newest")

    # ── 分页 ──
    per_page = st.session_state.get("per_page", 50)
    page = st.session_state.get("page", 1)

    orders, total = search_orders(search_val, status_val, date_from_val,
                                  date_to_val, sort_val, page, per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
        st.session_state.page = page

    selected_ids = st.session_state.get("selected_ids", set())

    # ── 批量操作栏 ──
    st.markdown(f"""
    <div class="batch-bar">
        <span>显示第 <strong>{min(total, 1)}</strong>–<strong>{min(page * per_page, total)}</strong> 条，
              共 <strong>{total}</strong> 条</span>
        <span style="margin-left:auto;">已选 <strong>{len(selected_ids)}</strong> 条</span>
    </div>
    """, unsafe_allow_html=True)

    batch_cols = st.columns([1, 10])
    with batch_cols[0]:
        if selected_ids and st.button("🗑️ 删除选中", type="secondary", use_container_width=True):
            delete_orders(list(selected_ids))
            st.session_state.selected_ids = set()
            st.session_state.page = 1
            st.rerun()

    if selected_ids:
        st.info(f"已选择 {len(selected_ids)} 条订单，点击「删除选中」执行批量删除")

    # ── 数据表格 ──
    if orders:
        rows = []
        for o in orders:
            oid = o["order_id"]
            rows.append({
                "勾选": oid in selected_ids,
                "订单号": oid,
                "文件名": o["filename"],
                "桩编号": o["charging_pile_id"] or "-",
                "报文": o["message_count"] or "-",
                "大小": f"{o['file_size']/1024:.1f} KB" if o["file_size"] else "-",
                "状态": o["status"],
                "上传时间": (o["upload_time"] or "-")[:19],
            })

        df = pd.DataFrame(rows)

        edited = st.data_editor(
            df,
            column_config={
                "勾选": st.column_config.CheckboxColumn("", width="small", help="选择"),
                "订单号": st.column_config.TextColumn("订单号", width="medium"),
                "文件名": st.column_config.TextColumn("文件名", width="large"),
                "桩编号": st.column_config.TextColumn("桩编号", width="small"),
                "报文": st.column_config.NumberColumn("报文", width="small"),
                "大小": st.column_config.TextColumn("大小", width="small"),
                "状态": st.column_config.TextColumn("状态", width="small"),
                "上传时间": st.column_config.TextColumn("上传时间", width="medium"),
            },
            use_container_width=True,
            hide_index=True,
            disabled=["订单号", "文件名", "桩编号", "报文", "大小", "状态", "上传时间"],
            key=f"order_table_{page}",
            height=420,
        )

        # 同步选中状态
        new_selected = set()
        for i, row in edited.iterrows():
            if row["勾选"]:
                new_selected.add(orders[i]["order_id"])
        st.session_state.selected_ids = new_selected

        # ── 分页控件 ──
        st.markdown("---")

        pag_cols = st.columns([0.8, 0.8, 0.8, 1, 0.8, 0.8, 0.5, 2])
        with pag_cols[0]:
            if st.button("‹‹ 首页", disabled=(page <= 1), use_container_width=True):
                st.session_state.page = 1
                st.rerun()
        with pag_cols[1]:
            if st.button("‹ 上一页", disabled=(page <= 1), use_container_width=True):
                st.session_state.page = max(1, page - 1)
                st.rerun()
        with pag_cols[2]:
            st.markdown(f"<div style='text-align:center;padding:6px;font-size:13px;color:{C_TEXT_MUTED};'>{page}/{total_pages}</div>",
                        unsafe_allow_html=True)
        with pag_cols[3]:
            if st.button("下一页 ›", disabled=(page >= total_pages), use_container_width=True):
                st.session_state.page = min(total_pages, page + 1)
                st.rerun()
        with pag_cols[4]:
            if st.button("末页 ››", disabled=(page >= total_pages), use_container_width=True):
                st.session_state.page = total_pages
                st.rerun()
        with pag_cols[5]:
            new_pp = st.selectbox("每页", PER_PAGE_OPTIONS,
                                  index=PER_PAGE_OPTIONS.index(per_page),
                                  label_visibility="collapsed", key="per_page_select")
            if new_pp != per_page:
                st.session_state.per_page = new_pp
                st.session_state.page = 1
                st.rerun()
        with pag_cols[6]:
            # 跳转输入
            goto = st.text_input("跳转", value="", placeholder="页号",
                                 label_visibility="collapsed", key="goto_page")
            if goto and goto.isdigit():
                p = int(goto)
                if 1 <= p <= total_pages:
                    st.session_state.page = p
                    st.rerun()

        st.markdown("---")

        # ── 查看订单详情（按钮式） ──
        st.markdown("<div style='font-size:13px;color:#64748d;margin-bottom:8px;'>"
                    "点击订单号查看详情：</div>", unsafe_allow_html=True)
        view_cols = st.columns(6)
        for i, o in enumerate(orders[:30]):
            with view_cols[i % 6]:
                oid = o["order_id"]
                short_oid = oid[:12] + "..." if len(oid) > 15 else oid
                if st.button(f"📄 {short_oid}", key=f"view_{oid}", use_container_width=True):
                    st.session_state.page_name = "detail"
                    st.session_state.selected_order_id = oid
                    st.rerun()

    else:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#bbb;font-size:14px;">
            <div style="font-size:48px;margin-bottom:12px;">📭</div>
            <div>暂无订单数据</div>
            <div style="margin-top:6px;">请先上传文件或调整筛选条件</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # close .page
