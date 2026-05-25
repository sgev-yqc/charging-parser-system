"""
导出功能模块 — Excel / JSON / TXT
"""
import json
import pandas as pd
from io import BytesIO
from datetime import datetime


def export_excel(messages, order_id=None):
    """导出解析结果为 Excel BytesIO"""
    data = []
    for m in messages:
        if m["msg_type"] == "header":
            data.append({"序号": "", "时间戳": "", "阶段": m["decoded"],
                        "报文": "========", "方向": "", "解析内容": m["decoded"]})
        else:
            data.append({"序号": m["seq"], "时间戳": m["timestamp"],
                        "阶段": m["phase"], "报文": m["msg_name"],
                        "方向": m["direction"], "解析内容": m["decoded"]})
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='CAN报文解析')
        ws = writer.sheets['CAN报文解析']
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 8
        ws.column_dimensions['D'].width = 10
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 80
    output.seek(0)
    return output


def export_json(messages):
    """导出为 JSON 字符串"""
    return json.dumps(messages, ensure_ascii=False, indent=2)


def export_txt(messages, order_id=None):
    """导出为 TXT 文本"""
    oid = order_id or "未知"
    lines = [
        "=" * 80,
        f"充电报文解析结果 - {oid}",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 80,
        "",
    ]
    for m in messages:
        if m["msg_type"] == "header":
            lines.extend(["", f"【{m['decoded']}】", "-" * 80])
        else:
            lines.append(f"[{m['timestamp']}] {m['msg_name']:<8} | "
                        f"{m['phase']:<4} | {m['decoded']}")
    return "\n".join(lines)
