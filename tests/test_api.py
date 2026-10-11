"""HTTP checks for the new UI without touching the configured data directory."""

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from api import create_app
from charging_parser.storage import OrderStore


def test_order_workflow_and_exports():
    sample = b"2026-01-01 00:00:00.000 1826f456 01 02 03\n"
    with TemporaryDirectory() as temporary:
        app = create_app(OrderStore(Path(temporary) / "orders"), frontend_dist=Path(temporary) / "missing")
        client = TestClient(app)

        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/orders").json() == {"orders": []}

        uploaded = client.post("/api/orders/upload", files=[("files", ("BMS_20260101_sample.txt", sample, "text/plain"))]).json()
        assert uploaded["results"][0]["ok"] is True
        assert uploaded["results"][0]["message_count"] == 1

        orders = client.get("/api/orders").json()["orders"]
        assert len(orders) == 1 and orders[0]["order_id"] == "sample"
        detail = client.get("/api/orders/sample").json()
        assert detail["types"] == {"CHM": 1}
        assert detail["phases"] == {"握手": 1}
        messages = client.get("/api/orders/sample/messages", params={"name": "CHM"}).json()
        assert messages["total"] == 1 and messages["rows"][0]["decoded"]

        for format_name in ("original", "excel", "json", "txt"):
            exported = client.get(f"/api/orders/sample/export/{format_name}")
            assert exported.status_code == 200 and exported.content
            assert "attachment" in exported.headers["content-disposition"]

        duplicate = client.post("/api/orders/upload", files=[("files", ("BMS_20260101_sample.txt", sample, "text/plain"))]).json()
        assert duplicate["results"][0]["ok"] is False
        assert client.get("/api/orders").json()["orders"][0]["order_id"] == "sample"

        assert client.delete("/api/orders/sample").status_code == 200
        assert client.get("/api/orders/sample").status_code == 404


def test_upload_rejects_unsafe_order_id():
    with TemporaryDirectory() as temporary:
        app = create_app(OrderStore(Path(temporary) / "orders"), frontend_dist=Path(temporary) / "missing")
        response = TestClient(app).post("/api/orders/upload", files=[("files", ("../bad.txt", b"x", "text/plain"))])
        assert response.json()["results"][0]["ok"] is False
        assert not (Path(temporary) / "orders").exists()


def test_upload_uses_complete_filename_for_non_bms_orders():
    sample = b"2026-01-01 00:00:00.000 1826f456 01 02 03\n"
    order_id = "37417900000036460025010502684421"
    filename = f"{order_id}.3_corrected.txt"
    with TemporaryDirectory() as temporary:
        app = create_app(OrderStore(Path(temporary) / "orders"), frontend_dist=Path(temporary) / "missing")
        client = TestClient(app)
        response = client.post("/api/orders/upload", files=[("files", (filename, sample, "text/plain"))])
        assert response.json()["results"][0]["ok"] is True
        assert response.json()["results"][0]["order_id"] == filename
        detail = client.get(f"/api/orders/{filename}")
        assert detail.status_code == 200
        assert detail.json()["order"]["order_id"] == filename
        assert client.get(f"/api/orders/{filename}/export/original").content == sample
