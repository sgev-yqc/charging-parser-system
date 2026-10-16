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
        assert len(orders) == 1 and orders[0]["order_id"] == "BMS_20260101_sample.txt"
        detail = client.get("/api/orders/BMS_20260101_sample.txt").json()
        assert detail["types"] == {"CHM": 1}
        assert detail["phases"] == {"握手": 1}
        messages = client.get("/api/orders/BMS_20260101_sample.txt/messages", params={"name": "CHM"}).json()
        assert messages["total"] == 1 and messages["rows"][0]["decoded"]

        for format_name in ("original", "excel", "json", "txt"):
            exported = client.get(f"/api/orders/BMS_20260101_sample.txt/export/{format_name}")
            assert exported.status_code == 200 and exported.content
            assert "attachment" in exported.headers["content-disposition"]

        duplicate = client.post("/api/orders/upload", files=[("files", ("BMS_20260101_sample.txt", sample, "text/plain"))]).json()
        assert duplicate["results"][0]["ok"] is False
        assert client.get("/api/orders").json()["orders"][0]["order_id"] == "BMS_20260101_sample.txt"

        assert client.delete("/api/orders/BMS_20260101_sample.txt").status_code == 200
        assert client.get("/api/orders/BMS_20260101_sample.txt").status_code == 404


def test_upload_rejects_unsafe_order_id():
    with TemporaryDirectory() as temporary:
        app = create_app(OrderStore(Path(temporary) / "orders"), frontend_dist=Path(temporary) / "missing")
        response = TestClient(app).post("/api/orders/upload", files=[("files", ("../bad.txt", b"x", "text/plain"))])
        assert response.json()["results"][0]["ok"] is False
        assert not (Path(temporary) / "orders").exists()


def test_filename_identity_and_legacy_duplicate_matching(tmp_path):
    sample = b"2026-01-01 00:00:00.000 1826f456 01 02 03\n"
    store = OrderStore(tmp_path / 'orders')
    client = TestClient(create_app(store, frontend_dist=tmp_path / 'missing'))
    first = 'BMS_20260101_000123.txt'
    second = 'BMS_20260102_000123.txt'
    store.add_order('000123', first, sample)
    def upload(names, replace=False):
        return client.post('/api/orders/upload',
                           files=[('files', (name, sample)) for name in names],
                           data={'replace': str(replace).lower()}).json()['results']
    assert not upload([first])[0]['ok']
    assert upload([second])[0]['ok']
    assert (tmp_path / 'orders' / second / second).read_bytes() == sample
    assert upload([first], replace=True)[0]['ok']
    assert set(store.load_orders()) == {first, second}
    assert (tmp_path / 'orders' / first / first).read_bytes() == sample
    assert not upload([first.upper()])[0]['ok']
    third = 'BMS_20260103_000123.txt'
    results = upload([third, third.upper()])
    assert results[0]['ok'] and not results[1]['ok']


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
