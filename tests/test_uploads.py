import io
import tarfile
import zipfile

import pytest
from fastapi.testclient import TestClient

from api import create_app
from charging_parser.storage import OrderStore
from charging_parser import uploads

SAMPLE = b'2026-01-01 00:00:00.000 1826f456 01 02 03\n'


def pack(suffix, members):
    buffer = io.BytesIO()
    if suffix == '.zip':
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in members:
                archive.writestr(name, data)
    else:
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            for name, data in members:
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
    return buffer.getvalue()


@pytest.mark.parametrize('suffix', ['.tgz', '.tar.gz', '.zip'])
def test_archive_workflow(tmp_path, suffix):
    store = OrderStore(tmp_path / 'orders')
    client = TestClient(create_app(store, frontend_dist=tmp_path / 'missing'))
    content = pack(suffix, [('nested/log.1.txt', b'ignored'), ('nested/log.2.TXT', SAMPLE)])
    filename = 'BMS_20260101_000123' + suffix
    def upload(data, replace=False):
        return client.post('/api/orders/upload', files=[('files', (filename, data))],
                           data={'replace': str(replace).lower()}).json()['results'][0]
    result = upload(content)
    assert result['ok'] and result['order_id'] == filename and result['message_count'] == 1
    assert store.load_orders()[filename]['source_member'] == 'nested/log.2.TXT'
    assert client.get(f'/api/orders/{filename}/export/original').content == content
    assert not upload(content)['ok']
    for members in [[], [('x.1.txt', SAMPLE)], [('a.2.txt', SAMPLE), ('b.2.txt', SAMPLE)]]:
        assert not upload(pack(suffix, members), replace=True)['ok']
        assert client.get(f'/api/orders/{filename}/export/original').content == content
    assert not upload(b'broken archive', replace=True)['ok']
    assert client.get(f'/api/orders/{filename}/export/original').content == content
    assert upload(content, replace=True)['ok']


@pytest.mark.parametrize('suffix', ['.tgz', '.tar.gz', '.zip'])
def test_member_size_limit(monkeypatch, suffix):
    monkeypatch.setattr(uploads, 'MAX_LOG_BYTES', 3)
    with pytest.raises(ValueError):
        uploads.read_upload('log' + suffix, pack(suffix, [('log.2.txt', SAMPLE)]))


def test_tar_scan_limit(monkeypatch):
    monkeypatch.setattr(uploads, 'MAX_TAR_BYTES', 512)
    with pytest.raises(ValueError):
        uploads.read_upload('log.tgz', pack('.tgz', [('ignored.1.txt', SAMPLE)]))
