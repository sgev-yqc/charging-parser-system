"""Order list: primary upload action, search, results, and secondary management."""

from datetime import date
from hashlib import sha1
from html import escape

import pandas as pd
import streamlit as st

from views import upload_dialog

SORT_OPTIONS = {
    "上传时间（新→旧）": ("upload_time", True),
    "上传时间（旧→新）": ("upload_time", False),
    "订单号（升序）": ("order_id", False),
    "订单号（降序）": ("order_id", True),
}
PER_PAGE_OPTIONS = [20, 50, 100]
COLUMN_WIDTHS = [2.0, 3.6, 1.0, 1.1, 1.7, 1.2]
HEADERS = ["订单", "源文件", "状态", "报文数", "上传时间", "操作"]


def _order_date(info):
    try:
        return date.fromisoformat(str(info.get("upload_time", ""))[:10])
    except ValueError:
        return None


def _reset_filters():
    st.session_state.filter_keyword = ""
    st.session_state.filter_start = None
    st.session_state.filter_end = None
    st.session_state.list_page_number = 1


def _apply_filters(orders, keyword, start_date, end_date, sort_label):
    items = list(orders.items())
    if keyword:
        term = keyword.lower()
        items = [
            (order_id, info) for order_id, info in items
            if term in order_id.lower() or term in str(info.get("filename", "")).lower()
        ]
    if start_date or end_date:
        kept = []
        for order_id, info in items:
            uploaded = _order_date(info)
            if uploaded is None:
                continue
            if start_date and uploaded < start_date:
                continue
            if end_date and uploaded > end_date:
                continue
            kept.append((order_id, info))
        items = kept

    field, reverse = SORT_OPTIONS[sort_label]
    if field == "order_id":
        items.sort(key=lambda item: item[0], reverse=reverse)
    else:
        items.sort(key=lambda item: str(item[1].get("upload_time", "")), reverse=reverse)
    return items


def _render_upload_banner():
    results = st.session_state.get("last_upload_results")
    if not results:
        return
    succeeded = sum(1 for row in results if row["状态"].startswith("✅"))
    if succeeded == len(results):
        st.success(f"上传完成：{succeeded} 个文件已解析并入库。")
    else:
        st.warning(f"上传完成：成功 {succeeded} / {len(results)} 个文件。请检查失败项：")
        st.dataframe(pd.DataFrame([row for row in results if not row["状态"].startswith("✅")]), hide_index=True)
    if succeeded == 1:
        order_id = next(row["订单号"] for row in results if row["状态"].startswith("✅"))
        if st.button("查看刚解析的结果 →"):
            st.session_state.pop("last_upload_results", None)
            st.session_state.selected_order_id = order_id
            st.session_state.page = "detail"
            st.rerun()
    if st.button("关闭上传提示"):
        st.session_state.pop("last_upload_results", None)
        st.rerun()


def _render_stats(orders):
    total_messages = sum(info.get("message_count", 0) for info in orders.values())
    latest_upload = max((str(info.get("upload_time", "")) for info in orders.values()), default="")
    stats = st.columns(3)
    values = (
        ("订单总数", str(len(orders)), "已保存的解析记录"),
        ("已解析报文", f"{total_messages:,}", "全部订单合计"),
        ("最近上传", latest_upload[:16].replace("T", " ") or "—", "本地时间"),
    )
    for slot, (label, value, hint) in zip(stats, values):
        slot.markdown(
            f'<div class="stat-card"><div class="label">{label}</div>'
            f'<div class="value">{escape(value)}</div><div class="hint">{hint}</div></div>',
            unsafe_allow_html=True,
        )


def _render_order(order_id, info):
    with st.container(border=True):
        row = st.columns(COLUMN_WIDTHS, vertical_alignment="center")
        row[0].markdown(f'<div class="order-primary">{escape(order_id)}</div>', unsafe_allow_html=True)
        filename = str(info.get("filename", "-"))
        row[1].markdown(
            f'<div class="order-primary">{escape(filename)}</div>'
            f'<div class="order-secondary">{info.get("file_size", 0) / 1024:.1f} KB</div>',
            unsafe_allow_html=True,
        )
        status = str(info.get("status", "-"))
        status_class = "status-ok" if status == "已完成" else "status-other"
        row[2].markdown(f'<span class="{status_class}">{escape(status)}</span>', unsafe_allow_html=True)
        row[3].markdown(f'<div class="order-primary">{info.get("message_count", 0):,}</div>', unsafe_allow_html=True)
        row[4].markdown(escape(str(info.get("upload_time", ""))[:16].replace("T", " ")))
        if row[5].button("查看结果 →", key=f"view_{order_id}", width="stretch"):
            st.session_state.selected_order_id = order_id
            st.session_state.page = "detail"
            st.rerun()


def _render_pagination(page_number, total_pages):
    if total_pages <= 1:
        return
    nav = st.columns([1, 1, 3, 1, 1])
    if nav[0].button("« 首页", disabled=page_number == 1):
        st.session_state.list_page_number = 1
        st.rerun()
    if nav[1].button("‹ 上一页", disabled=page_number == 1):
        st.session_state.list_page_number = page_number - 1
        st.rerun()
    nav[2].caption(f"第 {page_number} / {total_pages} 页")
    if nav[3].button("下一页 ›", disabled=page_number == total_pages):
        st.session_state.list_page_number = page_number + 1
        st.rerun()
    if nav[4].button("末页 »", disabled=page_number == total_pages):
        st.session_state.list_page_number = total_pages
        st.rerun()


def _render_management(store, orders, filtered, data_dir):
    with st.expander("记录管理"):
        st.caption("删除会同时移除原始文件和解析结果。")
        to_delete = st.multiselect(
            "选择要删除的订单",
            options=[order_id for order_id, _ in filtered],
            format_func=lambda order_id: f"{order_id}（{orders[order_id].get('filename', '-')}）",
        )
        selection_key = sha1("\0".join(to_delete).encode("utf-8")).hexdigest()
        confirm_delete = st.checkbox(
            "我确认删除所选订单及其文件",
            disabled=not to_delete,
            key=f"confirm_delete_{selection_key}",
        )
        if st.button("删除所选订单", disabled=not (to_delete and confirm_delete)):
            for order_id in to_delete:
                store.delete_order(order_id)
            st.session_state.list_page_number = 1
            st.rerun()
        st.caption(f"数据存储位置：{data_dir}")


def render(store, data_dir):
    _render_upload_banner()
    orders = store.load_orders()

    action_cols = st.columns([4, 1], vertical_alignment="center")
    action_cols[0].markdown(
        '<div class="section-heading">开始解析</div>'
        '<div class="section-caption">上传 TXT 报文文件，系统会自动识别订单号并生成解析结果。</div>',
        unsafe_allow_html=True,
    )
    if action_cols[1].button("＋ 上传并解析", type="primary", width="stretch"):
        upload_dialog.open_dialog(store)

    if not orders:
        st.info("还没有解析记录。上传 TXT 报文文件后，结果会显示在这里。")
        return

    _render_stats(orders)
    st.markdown(
        '<div class="section-heading">解析记录</div>'
        '<div class="section-caption">搜索订单并打开解析结果。</div>',
        unsafe_allow_html=True,
    )
    search_cols = st.columns([4, 1], vertical_alignment="bottom")
    keyword = search_cols[0].text_input(
        "搜索订单号或文件名", key="filter_keyword", placeholder="输入订单号或文件名")
    search_cols[1].button("清空筛选", width="stretch", on_click=_reset_filters)

    with st.expander("更多筛选与排序"):
        filter_cols = st.columns([1, 1, 1.3, 0.8])
        start_date = filter_cols[0].date_input("上传起始日期", value=None, key="filter_start")
        end_date = filter_cols[1].date_input("上传截止日期", value=None, key="filter_end")
        sort_label = filter_cols[2].selectbox("排序方式", list(SORT_OPTIONS), key="sort_label")
        per_page = filter_cols[3].selectbox(
            "每页显示", PER_PAGE_OPTIONS, key="per_page", format_func=lambda count: f"{count} 条")

    filtered = _apply_filters(orders, keyword, start_date, end_date, sort_label)
    st.caption(f"找到 {len(filtered)} / {len(orders)} 个订单")
    total_pages = max(1, -(-len(filtered) // per_page))
    page_number = min(st.session_state.get("list_page_number", 1), total_pages)
    st.session_state.list_page_number = page_number
    page_items = filtered[(page_number - 1) * per_page:page_number * per_page]

    if not filtered:
        st.info("没有找到符合条件的订单。可以换一个关键词，或清空筛选。")
    else:
        header_cols = st.columns(COLUMN_WIDTHS)
        for column, title in zip(header_cols, HEADERS):
            column.markdown(f'<div class="order-head">{title}</div>', unsafe_allow_html=True)
        for order_id, info in page_items:
            _render_order(order_id, info)
        st.caption(f"显示 {len(page_items)} / {len(filtered)} 个订单")
        _render_pagination(page_number, total_pages)

    _render_management(store, orders, filtered, data_dir)
