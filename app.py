#!/usr/bin/env python3
"""
充电报文解析系统 - 完整版
支持: 批量上传、订单管理、本地存储、多格式导出
"""
import streamlit as st
import pandas as pd
import re
import os
import json
from datetime import datetime
from io import BytesIO
import shutil
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# 配置与常量
# ═══════════════════════════════════════════════════════════════════════════════

# 数据存储目录
DATA_DIR = Path("/root/charging_parser_system/data")
ORDERS_FILE = DATA_DIR / "orders.json"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

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

# ═══════════════════════════════════════════════════════════════════════════════
# 报文解析核心代码
# ═══════════════════════════════════════════════════════════════════════════════

MSG_MAP = {
    0x1826f456: ("CHM", 9728, "充电机→车辆", "充电机握手"),
    0x182756f4: ("BHM", 9984, "车辆→充电机", "车辆握手"),
    0x1801f456: ("CRM", 256, "充电机→车辆", "充电机辨识"),
    0x1c0256f4: ("BRM", 512, "车辆→充电机", "BMS和车辆辨识"),
    0x1c0656f4: ("BCP", 1536, "车辆→充电机", "车辆充电参数"),
    0x1807f456: ("CTS", 1792, "充电机→车辆", "时间同步"),
    0x1808f456: ("CML", 2048, "充电机→车辆", "充电机最大输出能力"),
    0x100956f4: ("BRO", 2304, "车辆→充电机", "车辆准备就绪"),
    0x100af456: ("CRO", 2560, "充电机→车辆", "充电机准备就绪"),
    0x181056f4: ("BCL", 4096, "车辆→充电机", "电池充电需求"),
    0x1c1156f4: ("BCS", 4352, "车辆→充电机", "电池充电总状态"),
    0x1812f456: ("CCS", 4608, "充电机→车辆", "充电机充电状态"),
    0x181356f4: ("BSM", 4864, "车辆→充电机", "车辆状态信息"),
    0x1c1556f4: ("BMV", 5376, "车辆→充电机", "单体蓄电池电压"),
    0x1c1656f4: ("BMT", 5632, "车辆→充电机", "动力蓄电池温度"),
    0x1c1756f4: ("BSP", 5888, "车辆→充电机", "动力蓄电池预留"),
    0x101956f4: ("BST", 6400, "车辆→充电机", "车辆中止充电"),
    0x101af456: ("CST", 6656, "充电机→车辆", "充电机中止充电"),
    0x181c56f4: ("BSD", 7168, "车辆→充电机", "车辆统计数据"),
    0x181df456: ("CSD", 7424, "充电机→车辆", "充电机统计数据"),
    0x081e56f4: ("BEM", 7680, "车辆→充电机", "BMS及车辆错误报文"),
    0x081ff456: ("CEM", 7936, "充电机→车辆", "充电机错误报文"),
    0x1cec56f4: ("TP_CM_REQ", 0xEC00, "车辆→充电机", "TP连接管理(请求)"),
    0x1cecf456: ("TP_CM_RSP", 0xEC00, "充电机→车辆", "TP连接管理(响应)"),
    0x1ceb56f4: ("TP_DT", 0xEB00, "车辆→充电机", "TP数据传输"),
}

def get_phase(name):
    phases = {
        "CHM": "握手", "BHM": "握手", "CRM": "握手", "BRM": "握手",
        "BCP": "参数", "CTS": "参数", "CML": "参数",
        "BRO": "准备", "CRO": "准备",
        "BCL": "充电", "BCS": "充电", "CCS": "充电",
        "BSM": "充电", "BMV": "充电", "BMT": "充电", "BSP": "充电",
        "BST": "中止", "CST": "中止",
        "BSD": "结束", "CSD": "结束",
        "BEM": "错误", "CEM": "错误",
        "TP_CM_REQ": "传输", "TP_CM_RSP": "传输", "TP_DT": "传输"
    }
    return phases.get(name, "其他")

def parse_line(line):
    m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+([0-9a-fA-F]+)\s+(.*)', line)
    if not m:
        return None
    ts_str = m.group(1)
    can_id = int(m.group(2), 16) & 0x1FFFFFFF
    data_str = m.group(3).strip()
    data = [int(x, 16) for x in data_str.split()]
    return ts_str, can_id, data

# 解码函数
def decode_chm(data):
    if len(data) < 3: return "数据不足"
    return f"协议版本=V{data[2]}.{data[1]}.{data[0]}"

def decode_bhm(data):
    if len(data) < 2: return "数据不足"
    return f"绝缘检测允许电压={(data[1] << 8 | data[0]) * 0.1:.1f}V"

def decode_crm(data):
    if len(data) < 8: return "数据不足"
    result = "未辨识" if data[0] == 0x00 else "已辨识" if data[0] == 0xAA else f"0x{data[0]:02X}"
    charger_id = (data[4] << 24) | (data[3] << 16) | (data[2] << 8) | data[1]
    return f"辨识结果={result}, 充电机编号={charger_id}"

def decode_brm(data_49bytes):
    if len(data_49bytes) < 49:
        return f"数据不足({len(data_49bytes)}/49字节)"
    ver = f"V{data_49bytes[0]}.{data_49bytes[1]}.{data_49bytes[2]}"
    batt_types = {0x01: "铅酸", 0x02: "镍氢", 0x03: "磷酸铁锂", 0x04: "锰酸锂",
                  0x05: "钴酸锂", 0x06: "三元材料", 0x07: "聚合物锂离子",
                  0x08: "钛酸锂", 0xFF: "其他"}
    batt_type = batt_types.get(data_49bytes[3], f"未知(0x{data_49bytes[3]:02X})")
    cap = (data_49bytes[5] << 8 | data_49bytes[4]) * 0.1
    volt = (data_49bytes[7] << 8 | data_49bytes[6]) * 0.1
    evin = bytes(data_49bytes[24:41]).decode('ascii', errors='replace').rstrip('\x00')
    return f"协议版本={ver}, 电池类型={batt_type}, 额定容量={cap:.1f}Ah, 额定电压={volt:.1f}V, EVIN={evin}"

def decode_bcp(data_13bytes):
    if len(data_13bytes) < 13: return f"数据不足({len(data_13bytes)}/13)"
    v_max = (data_13bytes[1] << 8 | data_13bytes[0]) * 0.01
    i_max = ((data_13bytes[3] << 8 | data_13bytes[2]) * 0.1) - 400
    energy = (data_13bytes[5] << 8 | data_13bytes[4]) * 0.1
    v_total = (data_13bytes[7] << 8 | data_13bytes[6]) * 0.1
    t_max = data_13bytes[8] - 50
    soc = (data_13bytes[10] << 8 | data_13bytes[9]) * 0.1
    v_if = (data_13bytes[12] << 8 | data_13bytes[11]) * 0.1
    return f"单体最高压={v_max:.2f}V, 最高电流={i_max:.1f}A, 能量={energy:.1f}kWh, 总压={v_total:.1f}V, 最高温={t_max}°C, SOC={soc:.1f}%, 接口压={v_if:.1f}V"

def decode_cml(data):
    if len(data) < 8: return "数据不足"
    v_high = (data[1] << 8 | data[0]) * 0.1
    v_low = (data[3] << 8 | data[2]) * 0.1
    i_max = ((data[5] << 8 | data[4]) * 0.1) - 400
    i_min = ((data[7] << 8 | data[6]) * 0.1) - 400
    return f"最高压={v_high:.1f}V, 最低压={v_low:.1f}V, 最大流={i_max:.1f}A, 最小流={i_min:.1f}A"

def decode_bro_cro(data):
    if len(data) < 1: return "数据不足"
    return {"0x00": "未准备好", "0xAA": "✅ 已准备好", "0xFF": "无效"}.get(f"0x{data[0]:02X}", f"0x{data[0]:02X}")

def decode_bcl(data):
    if len(data) < 5: return "数据不足"
    v_req = (data[1] << 8 | data[0]) * 0.1
    i_req = ((data[3] << 8 | data[2]) * 0.1) - 400
    mode = "恒压" if data[4] == 0x01 else "恒流" if data[4] == 0x02 else f"0x{data[4]:02X}"
    return f"电压需求={v_req:.1f}V, 电流需求={i_req:.1f}A, 模式={mode}"

def decode_ccs(data):
    if len(data) < 7: return "数据不足"
    v = (data[1] << 8 | data[0]) * 0.1
    i = ((data[3] << 8 | data[2]) * 0.1) - 400
    t = (data[5] << 8 | data[4])
    allow = "允许" if (data[6] & 0x03) == 0x01 else "暂停"
    return f"电压={v:.1f}V, 电流={i:.1f}A, 累计充电={t}min, 充电允许={allow}"

def decode_bsm(data):
    if len(data) < 7: return "数据不足"
    cell_high = data[0]
    t_high, t_high_idx = data[1] - 50, data[2]
    t_low, t_low_idx = data[3] - 50, data[4]
    b6, b7 = data[5], data[6]
    faults = []
    status_map = {0: "正常", 1: "过高", 2: "过低"}
    if ((b6 >> 0) & 0x03) != 0: faults.append(f"电压{status_map.get((b6 >> 0) & 0x03, '异常')}")
    if ((b6 >> 2) & 0x03) != 0: faults.append(f"SOC{status_map.get((b6 >> 2) & 0x03, '异常')}")
    if ((b6 >> 4) & 0x03) != 0: faults.append(f"电流{status_map.get((b6 >> 4) & 0x03, '异常')}")
    if ((b6 >> 6) & 0x03) != 0: faults.append(f"温度异常")
    if ((b7 >> 0) & 0x03) != 0: faults.append(f"绝缘异常")
    if ((b7 >> 2) & 0x03) != 0: faults.append(f"连接器异常")
    charge_allow = "允许" if ((b7 >> 4) & 0x01) == 1 else "禁止"
    fault_str = f" ⚠️{'、'.join(faults)}" if faults else ""
    return f"最高单体#{cell_high}, 最高温={t_high}°C(#{t_high_idx}), 最低温={t_low}°C(#{t_low_idx}), 充电{charge_allow}{fault_str}"

def decode_bst(data):
    if len(data) < 4: return "数据不足"
    b1 = data[0]
    reasons = []
    if (b1 & 0x03) == 0x01: reasons.append("SOC目标")
    if ((b1 >> 2) & 0x03) == 0x01: reasons.append("总电压")
    if ((b1 >> 4) & 0x03) == 0x01: reasons.append("单体电压")
    if ((b1 >> 6) & 0x03) == 0x01: reasons.append("充电机中止")
    return f"中止原因: {', '.join(reasons) if reasons else '正常'}"

def decode_cst(data):
    if len(data) < 4: return "数据不足"
    b1 = data[0]
    reasons = []
    if (b1 & 0x03) == 0x01: reasons.append("达到设定条件")
    if ((b1 >> 2) & 0x03) == 0x01: reasons.append("人工中止")
    if ((b1 >> 4) & 0x03) == 0x01: reasons.append("故障中止")
    if ((b1 >> 6) & 0x03) == 0x01: reasons.append("车辆中止")
    return f"中止原因: {'/'.join(reasons) if reasons else '正常'}"

def decode_bsd(data):
    if len(data) < 7: return "数据不足"
    soc = data[0]
    v_min = (data[2] << 8 | data[1]) * 0.01
    v_max = (data[4] << 8 | data[3]) * 0.01
    t_min = data[5] - 50
    t_max = data[6] - 50
    return f"中止SOC={soc}%, 最低单体压={v_min:.2f}V, 最高单体压={v_max:.2f}V, 温度范围={t_min}~{t_max}°C"

def decode_csd(data):
    if len(data) < 8: return "数据不足"
    t = (data[1] << 8 | data[0])
    energy = (data[3] << 8 | data[2]) * 0.1
    charger_id = (data[7] << 24) | (data[6] << 16) | (data[5] << 8) | data[4]
    return f"充电时长={t}min, 输出能量={energy:.1f}kWh, 充电机编号={charger_id}"

def decode_cts(data):
    if len(data) < 7: return "数据不足"
    sec = (data[0] >> 4) * 10 + (data[0] & 0x0F)
    minute = (data[1] >> 4) * 10 + (data[1] & 0x0F)
    hour = (data[2] >> 4) * 10 + (data[2] & 0x0F)
    day = (data[3] >> 4) * 10 + (data[3] & 0x0F)
    month = (data[4] >> 4) * 10 + (data[4] & 0x0F)
    year = 2000 + (data[5] >> 4) * 10 + (data[5] & 0x0F)
    return f"同步时间={year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{sec:02d}"

def handle_tp_cm(direction, data, tp_buf):
    control = data[0]
    if control == 0x10:
        tp_buf['total_bytes'] = (data[2] << 8) | data[1]
        tp_buf['total_packets'] = data[3]
        tp_buf['state'] = 'receiving'
        tp_buf['received'] = 0
        tp_buf['data'] = []
        return f"[TP] {direction} RTS: 共{tp_buf['total_bytes']}字节, {tp_buf['total_packets']}帧"
    elif control == 0x11:
        return f"[TP] {direction} CTS: 允许发送{data[1]}帧"
    elif control == 0x13:
        return f"[TP] {direction} ACK: 接收完成"
    return f"[TP] {direction} CM: 0x{control:02X}"

def handle_tp_dt(data, tp_buf):
    seq = data[0]
    payload = data[1:] + [0xFF] * (7 - len(data[1:]))
    tp_buf['data'].extend(payload)
    tp_buf['received'] += 1
    if tp_buf['received'] >= tp_buf['total_packets']:
        return "COMPLETE"
    return f"[TP] 数据传输: 序号{seq}"

def parse_file_content(content):
    """解析文件内容"""
    results = []
    lines = content.decode('utf-8').split('\n')
    tp_buf = {'state': 'idle', 'data': [], 'total_bytes': 0, 'total_packets': 0, 'received': 0}
    
    for line in lines:
        line = line.strip()
        if not line or any(line.startswith(x) for x in ['插枪', '充电开始', '充电结束', '拔枪']):
            if line:
                results.append({"type": "header", "content": line})
            continue
        
        parsed = parse_line(line)
        if not parsed:
            continue
        
        ts_str, can_id, data = parsed
        
        if can_id in MSG_MAP:
            name, pgn, direction, desc = MSG_MAP[can_id]
            phase = get_phase(name)
            
            if name in ["TP_CM_REQ", "TP_CM_RSP", "TP_DT"]:
                if name in ["TP_CM_REQ", "TP_CM_RSP"]:
                    decoded = handle_tp_cm(direction, data, tp_buf)
                else:
                    decoded = handle_tp_dt(data, tp_buf)
                    if decoded == "COMPLETE":
                        full_data = bytes(tp_buf['data'][:tp_buf['total_bytes']])
                        if tp_buf['total_bytes'] == 49:
                            results.append({"type": "data", "name": "BRM", "pgn": 512, "ts": ts_str, 
                                          "direction": direction, "phase": get_phase("BRM"), 
                                          "decoded": decode_brm(full_data)})
                        elif tp_buf['total_bytes'] == 13:
                            results.append({"type": "data", "name": "BCP", "pgn": 1536, "ts": ts_str,
                                          "direction": direction, "phase": get_phase("BCP"),
                                          "decoded": decode_bcp(full_data)})
                        tp_buf = {'state': 'idle', 'data': [], 'total_bytes': 0, 'total_packets': 0, 'received': 0}
                        continue
                results.append({"type": "data", "name": name, "pgn": pgn, "ts": ts_str,
                              "direction": direction, "phase": phase, "decoded": decoded})
            else:
                decoders = {
                    "CHM": decode_chm, "BHM": decode_bhm, "CRM": decode_crm,
                    "CML": decode_cml, "BRO": decode_bro_cro, "CRO": decode_bro_cro,
                    "BCL": decode_bcl, "CCS": decode_ccs, "BSM": decode_bsm,
                    "BST": decode_bst, "CST": decode_cst, "BSD": decode_bsd,
                    "CSD": decode_csd, "CTS": decode_cts
                }
                decoded = decoders.get(name, lambda x: "原始数据: " + " ".join(f"{b:02x}" for b in x))(data)
                results.append({"type": "data", "name": name, "pgn": pgn, "ts": ts_str,
                              "direction": direction, "phase": phase, "decoded": decoded})
        else:
            results.append({"type": "unknown", "name": "UNKNOWN", "pgn": 0, "ts": ts_str,
                          "direction": "未知", "phase": "其他", 
                          "decoded": f"未知ID: 0x{can_id:08X}"})
    
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# 订单管理功能
# ═══════════════════════════════════════════════════════════════════════════════

def extract_order_id(filename):
    """从文件名提取订单号"""
    name = filename.rsplit('.', 1)[0]
    parts = name.split('_')
    if len(parts) >= 3:
        order_part = parts[2]
        if '.' in order_part:
            order_part = order_part.split('.')[0]
        return order_part
    return name

def load_orders():
    """加载订单列表"""
    if ORDERS_FILE.exists():
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_orders(orders):
    """保存订单列表"""
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

def add_order(order_id, filename, file_content):
    """添加新订单"""
    orders = load_orders()
    order_dir = DATA_DIR / order_id
    order_dir.mkdir(exist_ok=True)
    
    original_file = order_dir / filename
    with open(original_file, 'wb') as f:
        f.write(file_content)
    
    results = parse_file_content(file_content)
    result_file = order_dir / "parsed_result.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    orders[order_id] = {
        "order_id": order_id,
        "filename": filename,
        "upload_time": datetime.now().isoformat(),
        "status": "已完成",
        "file_size": len(file_content),
        "message_count": len([r for r in results if r["type"] == "data"]),
        "original_file": str(original_file),
        "result_file": str(result_file)
    }
    
    save_orders(orders)
    return orders[order_id]

def delete_order(order_id):
    """删除订单"""
    orders = load_orders()
    if order_id in orders:
        order_dir = DATA_DIR / order_id
        if order_dir.exists():
            shutil.rmtree(order_dir)
        del orders[order_id]
        save_orders(orders)
        return True
    return False

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
        orders = load_orders()
        
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
                        orders = load_orders()
                        if order_id in orders:
                            # 删除旧订单
                            delete_order(order_id)
                        
                        # 添加新订单
                        order_info = add_order(order_id, uploaded_file.name, file_content)
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
        
        orders = load_orders()
        
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
                            delete_order(order_id)
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
        orders = load_orders()
        
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