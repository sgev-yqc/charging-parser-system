"""File-backed order storage, independent of the Streamlit interface."""

import json
import shutil
from datetime import datetime
from pathlib import Path

from charging_parser.parser import parse_file_content


def extract_order_id(filename):
    """Extract the order ID from a BMS filename."""
    name = filename.rsplit('.', 1)[0]
    parts = name.split('_')
    if len(parts) >= 3:
        order_part = parts[2]
        if '.' in order_part:
            order_part = order_part.split('.')[0]
        return order_part
    return name


class OrderStore:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.orders_file = self.data_dir / "orders.json"

    def load_orders(self):
        """Load the order index, or return an empty index on first use."""
        if self.orders_file.exists():
            with self.orders_file.open('r', encoding='utf-8') as file:
                return json.load(file)
        return {}

    def save_orders(self, orders):
        """Save the order index in the configured directory."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self.orders_file.open('w', encoding='utf-8') as file:
            json.dump(orders, file, ensure_ascii=False, indent=2)

    def add_order(self, order_id, filename, file_content):
        """Store an original file and its parsed results."""
        orders = self.load_orders()
        order_dir = self.data_dir / order_id
        order_dir.mkdir(parents=True, exist_ok=True)

        original_file = order_dir / filename
        with original_file.open('wb') as file:
            file.write(file_content)

        results = parse_file_content(file_content)
        result_file = order_dir / "parsed_result.json"
        with result_file.open('w', encoding='utf-8') as file:
            json.dump(results, file, ensure_ascii=False, indent=2)

        orders[order_id] = {
            "order_id": order_id,
            "filename": filename,
            "upload_time": datetime.now().isoformat(),
            "status": "已完成",
            "file_size": len(file_content),
            "message_count": len([result for result in results if result["type"] == "data"]),
            "original_file": str(original_file),
            "result_file": str(result_file),
        }

        self.save_orders(orders)
        return orders[order_id]

    def delete_order(self, order_id):
        """Remove an order and its saved files."""
        orders = self.load_orders()
        if order_id in orders:
            order_dir = self.data_dir / order_id
            if order_dir.exists():
                shutil.rmtree(order_dir)
            del orders[order_id]
            self.save_orders(orders)
            return True
        return False
