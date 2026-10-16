"""Local HTTP API for the charging message parser workbench."""

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from charging_parser.uploads import SUPPORTED_SUFFIXES, read_upload
from charging_parser.config import get_data_dir
from charging_parser.export import export_excel, export_json, export_txt
from charging_parser.storage import OrderStore, extract_order_id
from charging_parser.parser import parse_file_content

MAX_FILE_BYTES = 50 * 1024 * 1024
SAFE_ORDER_ID = re.compile(r'[^<>:"/\\|?*\x00-\x1f]{1,255}\Z')
FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"


def _order_info(order_id, info):
    return {
        "order_id": order_id,
        "filename": info.get("filename", ""),
        "status": info.get("status", ""),
        "file_size": info.get("file_size", 0),
        "message_count": info.get("message_count", 0),
        "upload_time": info.get("upload_time", ""),
    }


def _messages_for(store, order_id):
    orders = store.load_orders()
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="订单不存在")
    path = Path(orders[order_id].get("result_file", ""))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="解析结果文件不存在")
    with path.open("r", encoding="utf-8") as handle:
        messages = json.load(handle)
    # Reparse legacy results from the preserved source, without rewriting user files.
    if any('line_number' not in message for message in messages):
        original = Path(orders[order_id]['original_file'])
        _, content = read_upload(original.name, original.read_bytes())
        messages = parse_file_content(content)
    return orders[order_id], messages


def create_app(order_store=None, frontend_dist=FRONTEND_DIST):
    store = order_store or OrderStore(get_data_dir())
    app = FastAPI(title="充电报文解析系统 API", version="1.0.0")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/orders")
    def list_orders():
        orders = store.load_orders()
        items = [_order_info(order_id, info) for order_id, info in orders.items()]
        items.sort(key=lambda item: item["upload_time"], reverse=True)
        return {"orders": items}

    @app.get("/api/orders/{order_id}")
    def get_order(order_id: str):
        info, messages = _messages_for(store, order_id)
        data = [message for message in messages if message.get("type") == "data"]
        return {
            "order": _order_info(order_id, info),
            "phases": dict(Counter(message.get("phase", "其他") for message in data)),
            "types": dict(Counter(message.get("name", "未知") for message in data)),
            "unknown_count": sum(message.get("type") == "unknown" for message in messages),
            "total_rows": len(messages),
        }

    @app.get("/api/orders/{order_id}/messages")
    def get_messages(
        order_id: str,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        phase: str = "",
        name: str = "",
        q: str = "",
        collapsed: bool = True,
    ):
        _, messages = _messages_for(store, order_id)
        term = q.casefold().strip()
        filtered = []
        children = {}
        for message in messages:
            if 'transport_parent' in message:
                children.setdefault(message['transport_parent'], []).append(message)
        for index, message in enumerate(messages, 1):
            if collapsed and 'transport_parent' in message:
                continue
            if message.get("type") == "header" and (phase or name or term):
                continue
            if phase and message.get("phase") != phase:
                continue
            if name and message.get("name") != name:
                continue
            if term and not any(term in str(message.get(key, "")).casefold() for key in ("name", "decoded", "ts", "pgn")):
                continue
            row = {"sequence": index, **message}
            if collapsed and 'transport_lines' in message:
                row['frames'] = children.get(message['line_number'], [])
            filtered.append(row)
        start = (page - 1) * page_size
        return {"rows": filtered[start:start + page_size], "total": len(filtered), "page": page, "page_size": page_size}

    @app.post("/api/orders/upload")
    def upload_orders(files: list[UploadFile] = File(...), replace: bool = Form(False)):
        if not files:
            raise HTTPException(status_code=400, detail="请选择报文文件")
        results = []
        seen = set()
        for upload in files:
            filename = upload.filename or ""
            order_id = extract_order_id(filename)
            result = {"filename": filename, "order_id": order_id, "ok": False}
            try:
                if not filename.lower().endswith(SUPPORTED_SUFFIXES) or Path(filename).name != filename or "\\" in filename:
                    raise ValueError("仅支持文件名安全的 TXT、TGZ、TAR.GZ、ZIP 文件")
                if not SAFE_ORDER_ID.fullmatch(order_id) or order_id in {".", ".."} or Path(order_id).is_reserved():
                    raise ValueError("源文件名无法作为安全的订单号")
                if order_id.casefold() in seen:
                    raise ValueError("本批次中原文件名重复")
                seen.add(order_id.casefold())
                existing = store.load_orders()
                previous_order_id = next((key for key, info in existing.items()
                                          if info.get("filename", "").casefold() == filename.casefold()), None)
                if previous_order_id is not None and not replace:
                    raise ValueError("同名文件已存在，请确认替换后重试")
                content = upload.file.read(MAX_FILE_BYTES + 1)
                if len(content) > MAX_FILE_BYTES:
                    raise ValueError("文件超过 50 MB 限制")
                source_member, log_content = read_upload(filename, content)
                info = store.add_order(order_id, filename, content, log_content=log_content, source_member=source_member, previous_order_id=previous_order_id)
                result.update(ok=True, message_count=info["message_count"])
            except (ValueError, UnicodeError) as error:
                result["error"] = str(error)
            except Exception as error:
                result["error"] = f"解析失败：{error}"
            results.append(result)
        return {"results": results}

    @app.delete("/api/orders/{order_id}")
    def delete_order(order_id: str):
        if order_id not in store.load_orders():
            raise HTTPException(status_code=404, detail="订单不存在")
        store.delete_order(order_id)
        return {"deleted": order_id}

    @app.get("/api/orders/{order_id}/export/{format_name}")
    def export_order(order_id: str, format_name: str):
        info, messages = _messages_for(store, order_id)
        if format_name == "original":
            path = Path(info.get("original_file", ""))
            if not path.is_file():
                raise HTTPException(status_code=404, detail="原始文件不存在")
            data, filename, media_type = path.read_bytes(), info.get("filename", "original.txt"), "text/plain; charset=utf-8"
        elif format_name == "excel":
            data, filename, media_type = export_excel(messages).getvalue(), f"{order_id}_解析结果.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format_name == "json":
            data, filename, media_type = export_json(messages).encode("utf-8"), f"{order_id}_解析结果.json", "application/json; charset=utf-8"
        elif format_name == "txt":
            data, filename, media_type = export_txt(messages, order_id).encode("utf-8"), f"{order_id}_解析结果.txt", "text/plain; charset=utf-8"
        else:
            raise HTTPException(status_code=404, detail="不支持的导出格式")
        disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
        return Response(content=data, media_type=media_type, headers={"Content-Disposition": disposition})

    static_dir = Path(frontend_dist)
    if static_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str):
            if path.startswith("api/"):
                raise HTTPException(status_code=404, detail="接口不存在")
            return FileResponse(static_dir / "index.html")

    return app


app = create_app()
