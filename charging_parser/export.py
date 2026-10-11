"""Export parsed messages to Excel, JSON, and TXT."""

import json
from datetime import datetime
from io import BytesIO

import pandas as pd


def export_excel(messages):
    """Render parsed messages as an Excel workbook."""
    rows = []
    for index, message in enumerate(messages, 1):
        if message["type"] == "header":
            rows.append({"序号": index, "时间戳": "", "阶段": message["content"], "报文名": "========",
                         "PGN": "", "方向": "", "解析内容": message["content"]})
        else:
            rows.append({"序号": index, "时间戳": message.get("ts", ""), "阶段": message.get("phase", ""),
                         "报文名": message.get("name", ""), "PGN": message.get("pgn", ""),
                         "方向": message.get("direction", ""), "解析内容": message.get("decoded", "")})

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="CAN报文解析")
        worksheet = writer.sheets["CAN报文解析"]
        for column, width in zip("ABCDEFG", (8, 20, 10, 12, 10, 15, 80)):
            worksheet.column_dimensions[column].width = width

    output.seek(0)
    return output


def export_json(messages):
    """Render parsed messages as a pretty-printed JSON string."""
    return json.dumps(messages, ensure_ascii=False, indent=2)


def export_txt(messages, order_id=None):
    """Render parsed messages as a plain-text report."""
    lines = ["=" * 80, "充电报文解析结果"]
    if order_id:
        lines.append(f"订单号: {order_id}")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.extend(["=" * 80, ""])

    for message in messages:
        if message["type"] == "header":
            lines.extend(["", f"【{message['content']}】", "-" * 80])
        else:
            lines.append(f"[{message.get('ts', '')}] {message.get('name', ''):<8} | "
                         f"{message.get('phase', ''):<6} | {message.get('decoded', '')}")

    return "\n".join(lines)
