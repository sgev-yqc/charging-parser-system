"""Read one vehicle/charger log without extracting archive paths to disk."""

import io
import tarfile
import zipfile

MAX_LOG_BYTES = 50 * 1024 * 1024
MAX_TAR_BYTES = 250 * 1024 * 1024
SUPPORTED_SUFFIXES = ('.txt', '.tgz', '.tar.gz', '.zip')


def read_upload(filename, content):
    """Return the selected member name and bytes; preserve the upload separately."""
    lower = filename.lower()
    if lower.endswith('.txt'):
        return filename, content
    try:
        if lower.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                candidates = [member for member in archive.infolist()
                              if not member.is_dir() and member.filename.lower().endswith('.2.txt')]
                member = _select(candidates)
                if member.file_size > MAX_LOG_BYTES:
                    raise ValueError('包内 .2.txt 超过 50 MB 限制')
                with archive.open(member) as stream:
                    data = stream.read(MAX_LOG_BYTES + 1)
                name = member.filename
        elif lower.endswith(('.tgz', '.tar.gz')):
            # Streaming mode bounds decompressed scanning as well as member reads.
            with tarfile.open(fileobj=io.BytesIO(content), mode='r|gz') as archive:
                candidates = []
                data = None
                for member in archive:
                    if member.offset_data + member.size > MAX_TAR_BYTES:
                        raise ValueError('压缩包展开内容超过 250 MB 限制')
                    if member.isfile() and member.name.lower().endswith('.2.txt'):
                        candidates.append(member)
                        _select(candidates)
                        if member.size > MAX_LOG_BYTES:
                            raise ValueError('包内 .2.txt 超过 50 MB 限制')
                        with archive.extractfile(member) as stream:
                            data = stream.read(MAX_LOG_BYTES + 1)
                name = _select(candidates).name
        else:
            raise ValueError('仅支持 TXT、TGZ、TAR.GZ、ZIP 文件')
        if len(data) > MAX_LOG_BYTES:
            raise ValueError('包内 .2.txt 超过 50 MB 限制')
        return name, data
    except (tarfile.TarError, zipfile.BadZipFile, OSError, EOFError, RuntimeError, NotImplementedError) as error:
        raise ValueError(f'无法读取压缩包：{error}') from error


def _select(candidates):
    if not candidates:
        raise ValueError('压缩包内未找到 .2.txt 车桩交互报文')
    if len(candidates) > 1:
        raise ValueError('压缩包内存在多个 .2.txt，请按订单拆分后上传')
    return candidates[0]
