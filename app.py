#!/usr/bin/env python3
"""
充电报文解析系统 - 完整版
支持: 批量上传、订单管理、本地存储、多格式导出
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

from charging_parser.config import get_data_dir
from charging_parser.storage import OrderStore, extract_order_id

# ═══════════════════════════════════════════════════════════════════════════════
# 配置与常量
# ═══════════════════════════════════════════════════════════════════════════════

DATA_DIR = get_data_dir()
store = OrderStore(DATA_DIR)

# 页面配置
st.set_page_config(
    page_title="充电报文解析系统",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════════
# CSS样式
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1e88e5; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #666; margin-bottom: 1.5rem; }
    .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; 
                 border-radius: 12px; color: white; text-align: center; }
    .stat-card.success { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .stat-number { font-size: 2.5rem; font-weight: bold; }
    .phase-待解析 { background-color: #fff3e0; color: #e65100; padding: 4px 12px; border-radius: 20px; }
    .phase-已完成 { background-color: #e8f5e9; color: #2e7d32; padding: 4px 12px; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

def export_to_excel(results):
    """导出为Excel"""
    data = []
    for i, r in enumerate(results, 1):
        if r["type"] == "header":
            data.append({"序号": i, "时间戳": "", "阶段": r["content"], "报文名": "========",
                        "PGN": "", "方向": "", "解析内容": r["content"]})
        else:
            data.append({"序号": i, "时间戳": r.get("ts", ""), "阶段": r.get("phase", ""), 
                        "报文名": r.get("name", ""), "PGN": r.get("pgn", ""), 
                        "方向": r.get("direction", ""), "解析内容": r.get("decoded", "")})
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='CAN报文解析')
        worksheet = writer.sheets['CAN报文解析']
        worksheet.column_dimensions['A'].width = 8
        worksheet.column_dimensions['B'].width = 20
        worksheet.column_dimensions['C'].width = 10
        worksheet.column_dimensions['D'].width = 12
        worksheet.column_dimensions['E'].width = 10
        worksheet.column_dimensions['F'].width = 15
        worksheet.column_dimensions['G'].width = 80
    
    output.seek(0)
    return output

def export_to_txt(results):
    """导出为TXT"""
    lines = []
    lines.append("=" * 80)
    lines.append("充电报文解析结果")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")
    
    for r in results:
        if r["type"] == "header":
            lines.append("")
            lines.append(f"【{r['content']}】")
            lines.append("-" * 80)
        else:
            lines.append(f"[{r.get('ts', '')}] {r.get('name', ''):<8} | {r.get('phase', ''):<6} | {r.get('decoded', '')}")
    
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════════
# Streamlit 页面
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # 页面头部
    st.markdown('<div class="main-header">🔋 充电报文解析系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">GB/T 27930 充电通信协议解析工具</div>', unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        st.markdown("### 📊 系统统计")
        orders = store.load_orders()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("总订单数", len(orders))
        with col2:
            total_msgs = sum(o.get("message_count", 0) for o in orders.values())
            st.metric("总报文数", total_msgs)
        
        st.markdown("---")
        st.markdown("### 📁 数据存储")
        st.code(f"{DATA_DIR}", language="bash")
        
        st.markdown("---")
        st.markdown("### 📝 使用说明")
        st.markdown("""
        1. **批量上传**: 支持多文件同时上传
        2. **自动解析**: 系统自动识别订单号并解析
        3. **结果查看**: 点击订单查看详细解析结果
        4. **多格式导出**: 支持Excel、JSON、TXT格式
        """)
    
    # 创建标签页
    tab1, tab2 = st.tabs(["📤 上传文件", "📋 订单列表"])
    
    # 标签页1: 上传文件
    with tab1:
        st.markdown("### 📤 批量上传")
        
        uploaded_files = st.file_uploader(
            "拖拽文件到此处或点击上传",
            type=['txt'],
            accept_multiple_files=True,
            help="支持同时上传多个BMS报文文件"
        )
        
        if uploaded_files:
            st.markdown(f"**已选择 {len(uploaded_files)} 个文件**")
            
            if st.button("🚀 开始上传并解析", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                success_count = 0
                failed_count = 0
                results_list = []
                
                for i, uploaded_file in enumerate(uploaded_files):
                    progress = (i + 1) / len(uploaded_files)
                    progress_bar.progress(progress)
                    status_text.text(f"正在处理: {uploaded_file.name}...")
                    
                    try:
                        file_content = uploaded_file.getvalue()
                        order_id = extract_order_id(uploaded_file.name)
                        
                        # 检查是否已存在
                        orders = store.load_orders()
                        if order_id in orders:
                            # 删除旧订单
                            store.delete_order(order_id)
                        
                        # 添加新订单
                        order_info = store.add_order(order_id, uploaded_file.name, file_content)
                        success_count += 1
                        results_list.append({"文件名": uploaded_file.name, "订单号": order_id, "状态": "✅ 成功"})
                    except Exception as e:
                        failed_count += 1
                        results_list.append({"文件名": uploaded_file.name, "订单号": "-", "状态": f"❌ 失败: {str(e)}"})
                
                progress_bar.empty()
                status_text.empty()
                
                # 显示结果
                st.success(f"处理完成! 成功: {success_count}, 失败: {failed_count}")
                st.dataframe(pd.DataFrame(results_list), use_container_width=True, hide_index=True)
                
                if success_count > 0:
                    st.info("💡 请切换到「订单列表」标签页查看解析结果")
    
    # 标签页2: 订单列表
    with tab2:
        st.markdown("### 📋 订单列表")
        
        orders = store.load_orders()
        
        if not orders:
            st.info("暂无订单，请先上传文件")
        else:
            # 搜索和筛选
            col1, col2 = st.columns([3, 1])
            with col1:
                search_term = st.text_input("🔍 搜索订单号或文件名", placeholder="输入关键词搜索...")
            with col2:
                sort_by = st.selectbox("排序方式", ["上传时间(新→旧)", "上传时间(旧→新)", "订单号"])
            
            # 筛选订单
            filtered_orders = orders
            if search_term:
                filtered_orders = {k: v for k, v in orders.items() 
                                  if search_term.lower() in k.lower() or search_term.lower() in v.get('filename', '').lower()}
            
            # 排序
            orders_list = list(filtered_orders.items())
            if sort_by == "上传时间(新→旧)":
                orders_list.sort(key=lambda x: x[1].get('upload_time', ''), reverse=True)
            elif sort_by == "上传时间(旧→新)":
                orders_list.sort(key=lambda x: x[1].get('upload_time', ''))
            elif sort_by == "订单号":
                orders_list.sort(key=lambda x: x[0])
            
            # 批量操作
            if orders_list:
                st.markdown("---")
                selected_orders = st.multiselect(
                    "选择订单进行批量操作",
                    options=[order_id for order_id, _ in orders_list],
                    format_func=lambda x: f"{x} ({orders[x].get('filename', '-')})"
                )
                
                col1, col2 = st.columns([1, 5])
                with col1:
                    if selected_orders and st.button("🗑️ 删除选中", type="secondary"):
                        for order_id in selected_orders:
                            store.delete_order(order_id)
                        st.success(f"已删除 {len(selected_orders)} 个订单")
                        st.rerun()
                
                st.markdown("---")
                
                # 显示订单列表
                for order_id, order_info in orders_list:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 2])
                        
                        with col1:
                            st.markdown(f"**订单号**: `{order_id}`")
                        with col2:
                            st.markdown(f"**文件名**: {order_info.get('filename', '-')}")
                        with col3:
                            status = order_info.get('status', '待解析')
                            st.markdown(f'<span class="phase-{status}">{status}</span>', unsafe_allow_html=True)
                        with col4:
                            size_kb = order_info.get('file_size', 0) / 1024
                            st.markdown(f"{size_kb:.1f} KB")
                        with col5:
                            upload_time = order_info.get('upload_time', '')[:19].replace('T', ' ')
                            st.markdown(f"📅 {upload_time}")
                        
                        # 操作按钮
                        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1, 3])
                        
                        with btn_col1:
                            if st.button("👁️ 查看", key=f"view_{order_id}"):
                                st.session_state['selected_order'] = order_id
                                st.session_state['show_detail'] = True
                        
                        with btn_col2:
                            # 下载原始文件
                            original_file = Path(order_info.get('original_file', ''))
                            if original_file.exists():
                                with open(original_file, 'rb') as f:
                                    st.download_button(
                                        "📄 原文件",
                                        f.read(),
                                        file_name=order_info.get('filename', 'original.txt'),
                                        key=f"dl_orig_{order_id}"
                                    )
                        
                        with btn_col3:
                            # 下载解析结果
                            result_file = Path(order_info.get('result_file', ''))
                            if result_file.exists():
                                with open(result_file, 'r', encoding='utf-8') as f:
                                    results = json.load(f)
                                    
                                    # Excel下载
                                    excel_data = export_to_excel(results)
                                    st.download_button(
                                        "📊 Excel",
                                        excel_data,
                                        file_name=f"{order_id}_解析结果.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key=f"dl_excel_{order_id}"
                                    )
                        
                        with btn_col4:
                            # JSON和TXT下载
                            result_file = Path(order_info.get('result_file', ''))
                            if result_file.exists():
                                with open(result_file, 'r', encoding='utf-8') as f:
                                    results = json.load(f)
                                    json_data = json.dumps(results, ensure_ascii=False, indent=2)
                                    
                                    col4a, col4b = st.columns(2)
                                    with col4a:
                                        st.download_button(
                                            "📋 JSON",
                                            json_data,
                                            file_name=f"{order_id}_解析结果.json",
                                            key=f"dl_json_{order_id}"
                                        )
                                    with col4b:
                                        txt_data = export_to_txt(results)
                                        st.download_button(
                                            "📝 TXT",
                                            txt_data,
                                            file_name=f"{order_id}_解析结果.txt",
                                            key=f"dl_txt_{order_id}"
                                        )
                        
                        st.markdown("---")
    
    # 详情弹窗
    if st.session_state.get('show_detail') and st.session_state.get('selected_order'):
        order_id = st.session_state['selected_order']
        orders = store.load_orders()
        
        if order_id in orders:
            order_info = orders[order_id]
            result_file = Path(order_info.get('result_file', ''))
            
            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                
                with st.expander(f"📊 订单 {order_id} 解析详情", expanded=True):
                    # 统计信息
                    data_results = [r for r in results if r["type"] == "data"]
                    phases = {}
                    msg_types = {}
                    for r in data_results:
                        phases[r.get("phase", "其他")] = phases.get(r.get("phase", "其他"), 0) + 1
                        msg_types[r.get("name", "未知")] = msg_types.get(r.get("name", "未知"), 0) + 1
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("总报文数", len(data_results))
                    with col2:
                        st.metric("涉及阶段", len(phases))
                    with col3:
                        st.metric("报文类型", len(msg_types))
                    
                    # 阶段分布
                    st.markdown("**阶段分布**")
                    phase_cols = st.columns(len(phases) if phases else 1)
                    for i, (phase, count) in enumerate(sorted(phases.items())):
                        with phase_cols[i % 4]:
                            st.markdown(f"**{phase}**: {count}条")
                    
                    # 详细数据表格
                    st.markdown("**详细解析结果**")
                    
                    # 筛选器
                    filter_col1, filter_col2 = st.columns(2)
                    with filter_col1:
                        selected_phases = st.multiselect("筛选阶段", options=list(phases.keys()), default=list(phases.keys()), key=f"phase_filter_{order_id}")
                    with filter_col2:
                        selected_msgs = st.multiselect("筛选报文", options=list(msg_types.keys()), default=list(msg_types.keys()), key=f"msg_filter_{order_id}")
                    
                    # 过滤数据
                    filtered_results = [r for r in results 
                                      if r["type"] == "header" or 
                                      (r.get("phase") in selected_phases and r.get("name") in selected_msgs)]
                    
                    # 显示表格
                    display_data = []
                    for r in filtered_results:
                        if r["type"] == "header":
                            display_data.append({
                                "时间戳": "",
                                "阶段": f"📌 {r['content']}",
                                "报文": "",
                                "方向": "",
                                "解析内容": ""
                            })
                        else:
                            display_data.append({
                                "时间戳": r.get("ts", ""),
                                "阶段": r.get("phase", ""),
                                "报文": r.get("name", ""),
                                "方向": r.get("direction", ""),
                                "解析内容": r.get("decoded", "")[:200]  # 限制长度
                            })
                    
                    st.dataframe(
                        pd.DataFrame(display_data),
                        use_container_width=True,
                        hide_index=True,
                        height=400
                    )
                    
                    if st.button("❌ 关闭详情"):
                        st.session_state['show_detail'] = False
                        st.rerun()

if __name__ == "__main__":
    main()
