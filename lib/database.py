"""
SQLite 存储层 — 订单索引 + 报文数据
"""
import sqlite3, shutil
from datetime import datetime
from pathlib import Path
from lib.config import DATA_DIR, DB_PATH
from lib.parser import parse_file_content


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            charging_pile_id TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            status TEXT DEFAULT '待解析',
            upload_time TEXT,
            file_path TEXT
        );
        CREATE TABLE IF NOT EXISTS parsed_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            seq INTEGER DEFAULT 0,
            msg_type TEXT DEFAULT 'data',
            timestamp TEXT DEFAULT '',
            msg_name TEXT DEFAULT '',
            phase TEXT DEFAULT '',
            direction TEXT DEFAULT '',
            decoded TEXT DEFAULT '',
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_messages_order ON parsed_messages(order_id);
        CREATE INDEX IF NOT EXISTS idx_orders_time ON orders(upload_time);
    """)
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def extract_order_id(filename: str) -> str:
    """从文件名提取订单号"""
    name = filename.rsplit('.', 1)[0]
    parts = name.split('_')
    if len(parts) >= 3:
        order_part = parts[2]
        if '.' in order_part:
            order_part = order_part.split('.')[0]
        return order_part
    return name


def extract_pile_id(order_id: str) -> str:
    """从订单号提取充电桩编号（前16位）"""
    return order_id[:16] if len(order_id) >= 16 else order_id


# ═══════════════════════════════════════════════════════════════════════════════
# 订单 CRUD
# ═══════════════════════════════════════════════════════════════════════════════

def add_order(uploaded_file) -> str:
    """
    上传文件并解析，存入 SQLite
    返回 order_id
    """
    content = uploaded_file.getvalue()
    filename = uploaded_file.name
    order_id = extract_order_id(filename)
    pile_id = extract_pile_id(order_id)
    upload_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 解析报文
    results = parse_file_content(content)
    data_msgs = [r for r in results if r["type"] == "data"]

    # 保存原始文件
    order_dir = DATA_DIR / order_id
    order_dir.mkdir(exist_ok=True)
    file_path = str(order_dir / filename)
    with open(file_path, 'wb') as f:
        f.write(content)

    conn = get_db()
    try:
        # 删除旧记录（如已存在）
        conn.execute("DELETE FROM parsed_messages WHERE order_id = ?", (order_id,))
        conn.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))

        # 插入订单
        conn.execute("""
            INSERT INTO orders (order_id, filename, charging_pile_id, file_size,
                                message_count, status, upload_time, file_path)
            VALUES (?, ?, ?, ?, ?, '已完成', ?, ?)
        """, (order_id, filename, pile_id, len(content), len(data_msgs), upload_time, file_path))

        # 批量插入报文（跳过 header/unknown 等非 data 类型）
        msg_rows = []
        for i, r in enumerate(results, 1):
            if r.get("type") != "data":
                continue
            msg_rows.append((
                order_id, i,
                r.get("type", "data"),
                r.get("ts", ""),
                r.get("name", ""),
                r.get("phase", ""),
                r.get("direction", ""),
                (r.get("decoded", "") or "")[:300],
            ))
        conn.executemany("""
            INSERT INTO parsed_messages (order_id, seq, msg_type, timestamp,
                                         msg_name, phase, direction, decoded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, msg_rows)

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return order_id


def get_order(order_id: str) -> dict | None:
    """获取单个订单信息"""
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def search_orders(search="", status="", date_from="", date_to="",
                  sort_by="newest", page=1, per_page=50):
    """
    搜索订单，返回 (订单列表, 总条数)
    """
    conn = get_db()
    where = []
    params = []

    if search:
        where.append("(order_id LIKE ? OR filename LIKE ? OR charging_pile_id LIKE ?)")
        p = f"%{search}%"
        params.extend([p, p, p])
    if status and status != "全部":
        where.append("status = ?")
        params.append(status)
    if date_from:
        where.append("upload_time >= ?")
        params.append(date_from)
    if date_to:
        where.append("upload_time <= ?")
        params.append(f"{date_to} 23:59")

    where_clause = "WHERE " + " AND ".join(where) if where else ""

    order_map = {
        "newest": "upload_time DESC",
        "oldest": "upload_time ASC",
        "order_id_asc": "order_id ASC",
        "order_id_desc": "order_id DESC",
    }
    order_sql = order_map.get(sort_by, "upload_time DESC")

    # 总数
    total = conn.execute(f"SELECT COUNT(*) FROM orders {where_clause}",
                         params).fetchone()[0]

    # 分页查询
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"SELECT * FROM orders {where_clause} ORDER BY {order_sql} LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()

    conn.close()
    return [dict(r) for r in rows], total


def delete_orders(order_ids: list):
    """批量删除订单（含报文和文件）"""
    conn = get_db()
    try:
        for oid in order_ids:
            row = conn.execute("SELECT file_path FROM orders WHERE order_id = ?",
                              (oid,)).fetchone()
            if row and row["file_path"]:
                fp = Path(row["file_path"])
                if fp.parent.exists():
                    shutil.rmtree(fp.parent, ignore_errors=True)
            conn.execute("DELETE FROM parsed_messages WHERE order_id = ?", (oid,))
            conn.execute("DELETE FROM orders WHERE order_id = ?", (oid,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 报文查询
# ═══════════════════════════════════════════════════════════════════════════════

def get_order_messages(order_id: str, phase="", msg_name=""):
    """获取订单的解析报文列表"""
    conn = get_db()
    where = ["order_id = ?"]
    params = [order_id]
    if phase and phase != "全部":
        where.append("phase = ?")
        params.append(phase)
    if msg_name and msg_name != "全部":
        where.append("msg_name = ?")
        params.append(msg_name)

    rows = conn.execute(
        f"SELECT * FROM parsed_messages WHERE {' AND '.join(where)} ORDER BY seq",
        params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_phases(order_id: str) -> dict:
    """获取订单的阶段分布 {阶段名: 条数}"""
    conn = get_db()
    rows = conn.execute(
        "SELECT phase, COUNT(*) as cnt FROM parsed_messages "
        "WHERE order_id = ? AND msg_type='data' GROUP BY phase ORDER BY cnt DESC",
        (order_id,)
    ).fetchall()
    conn.close()
    return {r["phase"]: r["cnt"] for r in rows}


def get_order_msg_types(order_id: str) -> dict:
    """获取订单的报文类型分布 {报文名: 条数}"""
    conn = get_db()
    rows = conn.execute(
        "SELECT msg_name, COUNT(*) as cnt FROM parsed_messages "
        "WHERE order_id = ? AND msg_type='data' GROUP BY msg_name ORDER BY cnt DESC",
        (order_id,)
    ).fetchall()
    conn.close()
    return {r["msg_name"]: r["cnt"] for r in rows}


def get_all_phases(order_id: str) -> list:
    """获取订单的所有不重复阶段"""
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT phase FROM parsed_messages "
        "WHERE order_id = ? AND msg_type='data' AND phase != '' ORDER BY phase",
        (order_id,)
    ).fetchall()
    conn.close()
    return [r["phase"] for r in rows]


def get_all_msg_names(order_id: str) -> list:
    """获取订单的所有不重复报文名"""
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT msg_name FROM parsed_messages "
        "WHERE order_id = ? AND msg_type='data' AND msg_name != '' ORDER BY msg_name",
        (order_id,)
    ).fetchall()
    conn.close()
    return [r["msg_name"] for r in rows]


def get_total_stats() -> dict:
    """获取系统总统计"""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as order_count, COALESCE(SUM(message_count), 0) as msg_count "
        "FROM orders"
    ).fetchone()
    conn.close()
    return {"order_count": row["order_count"], "msg_count": row["msg_count"]}
