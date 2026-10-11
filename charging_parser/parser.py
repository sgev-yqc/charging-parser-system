"""Parse CAN log lines and reassemble GB/T 27930 transport messages."""

import re

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

def decode_bcs(data_9bytes):
    if len(data_9bytes) < 9: return f"数据不足({len(data_9bytes)}/9字节)"
    voltage = int.from_bytes(data_9bytes[0:2], 'little') * 0.1
    current = int.from_bytes(data_9bytes[2:4], 'little') * 0.1 - 400
    cell = int.from_bytes(data_9bytes[4:6], 'little')
    cell_voltage = (cell & 0x0FFF) * 0.01
    cell_group = cell >> 12
    soc = data_9bytes[6]
    remaining = int.from_bytes(data_9bytes[7:9], 'little')
    return (f"充电电压={voltage:.1f}V, 充电电流={current:.1f}A, "
            f"最高单体电压={cell_voltage:.2f}V(组号{cell_group}), "
            f"当前SOC={soc}%, 估算剩余时间={remaining}min")

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
        tp_buf['pgn'] = int.from_bytes(bytes(data[5:8]), 'little')
        tp_buf['direction'] = direction
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
    decoded = f"[TP] 数据传输: 序号{seq}, 原始数据=" + " ".join(f"{byte:02X}" for byte in data[1:])
    if tp_buf['state'] != 'receiving':
        return decoded + " (未收到RTS)", False
    payload = data[1:] + [0xFF] * (7 - len(data[1:]))
    tp_buf['data'].extend(payload)
    tp_buf['received'] += 1
    return decoded, tp_buf['received'] >= tp_buf['total_packets']

def parse_file_content(content):
    """解析文件内容"""
    results = []
    lines = content.decode('utf-8').split('\n')
    tp_buf = {'state': 'idle', 'data': [], 'total_bytes': 0, 'total_packets': 0,
              'received': 0, 'pgn': None, 'direction': None}
    
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
                    decoded, complete = handle_tp_dt(data, tp_buf)
                results.append({"type": "data", "name": name, "pgn": pgn, "ts": ts_str,
                              "direction": direction, "phase": phase, "decoded": decoded})
                if name == "TP_DT" and complete:
                    full_data = bytes(tp_buf['data'][:tp_buf['total_bytes']])
                    semantic = {
                        0x0200: ("BRM", 49, decode_brm),
                        0x0600: ("BCP", 13, decode_bcp),
                        0x1100: ("BCS", 9, decode_bcs),
                    }.get(tp_buf['pgn'])
                    if semantic and tp_buf['total_bytes'] == semantic[1]:
                        msg_name, _, decoder = semantic
                        results.append({"type": "data", "name": msg_name, "pgn": tp_buf['pgn'],
                                        "ts": ts_str, "direction": tp_buf['direction'],
                                        "phase": get_phase(msg_name), "decoded": decoder(full_data)})
                    tp_buf = {'state': 'idle', 'data': [], 'total_bytes': 0, 'total_packets': 0,
                              'received': 0, 'pgn': None, 'direction': None}
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
