"""Order list page: filtering, sorting, pagination, and drill-down."""

from datetime import date

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
COLUMN_WIDTHS = [2.4, 3.2, 1.0, 1.0, 0.9, 1.9, 0.9]
HEADERS = ["订单号", "文件名", "状态", "大小 (KB)", "报文数", "上传时间", ""]


def _order_date(info):
    try:
        return date.fromisoformat(str(info.get("upload_time", ""))[:10])
    except ValueError:
        return None


def _reset_filters():
    st.session_state.filter_keyword = ""
    st.session_state.filter_start = None
    st.session_state.filter_end = None


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
    results = st.session_state.pop("last_upload_results", None)
    if not results:
        return

    succeeded = sum(1 for row in results if row["状态"].startswith("✅"))
    if succeeded == len(results):
        st.success(f"上传完成：{succeeded} 个文件已解析并入库。")
    else:
        st.warning(f"上传完成：成功 {succeeded} / {len(results)} 个文件，以下为失败的：")
        st.dataframe(
            pd.DataFrame([row for row in results if not row["状态"].startswith("✅")]),
            hide_index=True,
        )


def render(store, data_dir):
    _render_upload_banner()

    orders = store.load_orders()
    total_orders = len(orders)

    st.subheader("订单列表")

    if not total_orders:
        st.info("还没有任何订单。点击右上角「＋ 上传解析」上传报文文件即可开始。")
        if st.button("上传解析", type="primary"):
            upload_dialog.open_dialog(store)
        return

    with st.container(border=True):
        st.markdown("**条件筛选**")
        filter_cols = st.columns([2.4, 1.2, 1.2, 0.8])
        keyword = filter_cols[0].text_input(
            "关键字（订单号 / 文件名）", key="filter_keyword", placeholder="输入关键词…")
        start_date = filter_cols[1].date_input("上传起始日期", value=None, key="filter_start")
        end_date = filter_cols[2].date_input("上传截止日期", value=None, key="filter_end")
        filter_cols[3].button("重置筛选", key="filter_reset", on_click=_reset_filters)

    toolbar = st.columns([3, 1.4, 1])
    count_slot = toolbar[0].empty()
    sort_label = toolbar[1].selectbox("排序方式", list(SORT_OPTIONS), key="sort_label")
    per_page = toolbar[2].selectbox(
        "每页显示", PER_PAGE_OPTIONS, key="per_page", format_func=lambda count: f"{count} 条")

    filtered = _apply_filters(orders, keyword, start_date, end_date, sort_label)

    total_messages = sum(info.get("message_count", 0) for info in orders.values())
    if len(filtered) == total_orders:
        count_slot.caption(f"共 {total_orders} 个订单 · {total_messages} 条报文")
    else:
        count_slot.caption(f"筛选出 **{len(filtered)}** / {total_orders} 个订单（已应用条件筛选）")

    total_pages = max(1, -(-len(filtered) // per_page))
    page_number = min(st.session_state.get("list_page_number", 1), total_pages)
    st.session_state.list_page_number = page_number
    start = (page_number - 1) * per_page
    page_items = filtered[start:start + per_page]

    if not filtered:
        st.warning("没有符合筛选条件的订单，试试放宽条件或点「重置筛选」。")
        return

    header_cols = st.columns(COLUMN_WIDTHS)
    for column, title in zip(header_cols, HEADERS):
        column.markdown(f"**{title}**")

    for order_id, info in page_items:
        row = st.columns(COLUMN_WIDTHS)
        row[0].markdown(f"`{order_id}`")
        row[1].markdown(str(info.get("filename", "-")))
        row[2].markdown(str(info.get("status", "-")))
        row[3].markdown(f"{info.get('file_size', 0) / 1024:.1f}")
        row[4].markdown(str(info.get("message_count", 0)))
        row[5].markdown(str(info.get("upload_time", ""))[:19].replace("T", " "))
        if row[6].button("查看", key=f"view_{order_id}"):
            st.session_state.selected_order_id = order_id
            st.session_state.page = "detail"
            st.rerun()

    st.caption(f"显示 {len(page_items)} / {len(filtered)} 个订单")

    if total_pages > 1:
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

    with st.expander("批量删除"):
        to_delete = st.multiselect(
            "选择要删除的订单",
            options=[order_id for order_id, _ in filtered],
            format_func=lambda order_id: f"{order_id}（{orders[order_id].get('filename', '-')}）",
        )
        if st.button("删除选中订单", disabled=not to_delete):
            for order_id in to_delete:
                store.delete_order(order_id)
            st.session_state.list_page_number = 1
            st.rerun()

    with st.expander("数据存储位置"):
        st.code(str(data_dir), language="bash")
