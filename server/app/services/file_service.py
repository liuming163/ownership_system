"""File upload, compression, and naming service."""

import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from flask import current_app

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# 真实二进制签名 → (扩展名, MIME)
_MAGIC_SIGNATURES = (
    (b'\x89PNG\r\n\x1a\n',     '.png',  'image/png'),
    (b'\xff\xd8\xff',           '.jpg',  'image/jpeg'),
    (b'GIF87a',                 '.gif',  'image/gif'),
    (b'GIF89a',                 '.gif',  'image/gif'),
    (b'BM',                     '.bmp',  'image/bmp'),
    (b'%PDF-',                  '.pdf',  'application/pdf'),
)


def _sniff_ext(data):
    """嗅探二进制签名，返回 (扩展名, MIME)；不匹配返回 (None, None)。"""
    head = data[:8]
    for sig, ext, mime in _MAGIC_SIGNATURES:
        if head.startswith(sig):
            return ext, mime
    return None, None


def _normalize_ext(data, declared_ext, file_kind='文件'):
    """校验声明的扩展名与真实 MIME 是否一致。
    返回 (data, real_ext, warning)。
    - 一致: warning=None
    - 不一致: 用真实扩展名 + warning
    """
    real_ext, real_mime = _sniff_ext(data)
    if real_ext is None:
        return data, declared_ext, None
    if real_ext == declared_ext:
        return data, declared_ext, None
    # PNG 头部签名是 8 字节，JPEG 是 3 字节，PDF 是 5 字节
    # 这里 real_ext 已经是对应签名表的扩展名，权威
    return data, real_ext, (
        f'您上传的{file_kind}扩展名为 "{declared_ext}"，'
        f'但实际内容是 {real_mime.split("/")[-1].upper()}，已自动更正为 "{real_ext}"'
    )


def get_upload_dir(sub_folder):
    """获取上传子目录的绝对路径。"""
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], sub_folder)
    os.makedirs(path, exist_ok=True)
    return path


def save_company_license(file_storage, company_name):
    """保存代理主体营业执照。命名：营业执照_{公司名}.{ext}
    返回 (filename, warning_or_None)。"""
    target_dir = get_upload_dir('营业执照')
    declared_ext = Path(file_storage.filename).suffix.lower()
    data = _read_bytes(file_storage)
    data, ext, sniff_warn = _normalize_ext(data, declared_ext, '营业执照')
    data, ext, comp_warn = _compress_if_needed(data, ext)
    # 压缩转 JPEG 会重新覆盖 ext，需保留前面的 sniff 警告
    if comp_warn:
        warning = sniff_warn  # 嗅探警告优先级更高
    else:
        warning = sniff_warn
    filename = f'营业执照_{company_name}{ext}'
    _write_file(target_dir, filename, data)
    return filename, warning


def save_agent_license(file_storage, agent_name):
    """保存被代理人营业执照。命名：营业执照_{被代理人名}.{ext}
    返回 (filename, warning_or_None)。"""
    target_dir = get_upload_dir('被代理人营业执照')
    declared_ext = Path(file_storage.filename).suffix.lower()
    data = _read_bytes(file_storage)
    data, ext, sniff_warn = _normalize_ext(data, declared_ext, '被代理人营业执照')
    data, ext, _ = _compress_if_needed(data, ext)
    filename = f'营业执照_{agent_name}{ext}'
    _write_file(target_dir, filename, data)
    return filename, sniff_warn


def save_auth_file(file_storage, agent_name, company_name, expires_date):
    """保存授权委托书。命名：授权委托书_{被代理人名}_{代理主体名}_截止{YYYYMMDD}.{ext}
    不覆盖旧文件，新日期自然不同名。返回 (filename, warning_or_None)。"""
    target_dir = get_upload_dir('授权委托书')
    declared_ext = Path(file_storage.filename).suffix.lower()
    data = _read_bytes(file_storage)
    data, ext, sniff_warn = _normalize_ext(data, declared_ext, '授权委托书')
    data, ext, _ = _compress_if_needed(data, ext)
    date_str = expires_date.replace('-', '')
    filename = f'授权委托书_{agent_name}_{company_name}_截止{date_str}{ext}'
    # 如果同名已存在（同一天更新多次），加uuid后缀
    full_path = os.path.join(target_dir, filename)
    if os.path.exists(full_path):
        stem = Path(filename).stem
        filename = f'{stem}_{uuid4().hex[:6]}{ext}'
    _write_file(target_dir, filename, data)
    return filename, sniff_warn


def save_proof_file(file_storage, work_name):
    """保存权属证明。命名：权属证明_{作品名}_{uuid8}.{ext}
    返回 (filename, warning_or_None)。"""
    target_dir = get_upload_dir('权属证明')
    declared_ext = Path(file_storage.filename).suffix.lower()
    data = _read_bytes(file_storage)
    data, ext, sniff_warn = _normalize_ext(data, declared_ext, '权属证明')
    data, ext, _ = _compress_if_needed(data, ext)
    uid = uuid4().hex[:8]
    filename = f'权属证明_{work_name}_{uid}{ext}'
    _write_file(target_dir, filename, data)
    return filename, sniff_warn


def save_other_proof_file(file_storage, work_name, index):
    """保存其他证明。命名：其他证明_{作品名}_{序号}_{uuid8}.{ext}
    返回 (filename, warning_or_None)。"""
    target_dir = get_upload_dir('权属证明')
    declared_ext = Path(file_storage.filename).suffix.lower()
    data = _read_bytes(file_storage)
    data, ext, sniff_warn = _normalize_ext(data, declared_ext, '其他证明')
    data, ext, _ = _compress_if_needed(data, ext)
    uid = uuid4().hex[:8]
    filename = f'其他证明_{work_name}_{index}_{uid}{ext}'
    _write_file(target_dir, filename, data)
    return filename, sniff_warn


def _read_bytes(file_storage):
    file_storage.stream.seek(0)
    return file_storage.stream.read()


def _write_file(target_dir, filename, data):
    path = os.path.join(target_dir, filename)
    with open(path, 'wb') as f:
        f.write(data)


def _compress_if_needed(data, ext):
    """超过5MB自动压缩，图片转JPEG，PDF走Ghostscript。
    返回 (data, ext, warning)。"""
    if len(data) <= MAX_FILE_SIZE:
        return data, ext, None

    image_exts = {'.png', '.jpg', '.jpeg', '.bmp'}
    if ext in image_exts:
        result = _compress_image(data)
        if result:
            return result, '.jpg', None

    if ext == '.pdf':
        result = _compress_pdf(data)
        if result:
            return result, '.pdf', None

    # 压缩失败返回原始数据
    return data, ext, None


def _compress_image(data):
    if not Image:
        return None
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        if img.mode in ('RGBA', 'LA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            rgba = img.convert('RGBA')
            bg.paste(rgba, mask=rgba.split()[-1])
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')
    except Exception:
        return None

    long_edge = max(img.size)
    edges = [e for e in [long_edge, 2400, 2000, 1600, 1200] if e <= long_edge]

    for edge in edges:
        work = img
        if edge < long_edge:
            ratio = edge / float(long_edge)
            new_size = (max(1, int(img.size[0] * ratio)), max(1, int(img.size[1] * ratio)))
            work = img.resize(new_size, Image.LANCZOS)
        for quality in (85, 75, 65, 55):
            buf = io.BytesIO()
            work.save(buf, format='JPEG', quality=quality, optimize=True)
            if buf.tell() <= MAX_FILE_SIZE:
                return buf.getvalue()
    return None


def _compress_pdf(data):
    gs = shutil.which('gs') or shutil.which('gswin64c') or shutil.which('gswin32c')
    if not gs:
        return None

    src_path = out_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as src:
            src.write(data)
            src_path = src.name

        for setting in ('/ebook', '/screen'):
            out_fd, out_path = tempfile.mkstemp(suffix='.pdf')
            os.close(out_fd)
            cmd = [
                gs, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                f'-dPDFSETTINGS={setting}', '-dNOPAUSE', '-dQUIET', '-dBATCH',
                f'-sOutputFile={out_path}', src_path,
            ]
            try:
                subprocess.run(cmd, check=True, timeout=120,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue
            if os.path.exists(out_path) and os.path.getsize(out_path) <= MAX_FILE_SIZE:
                with open(out_path, 'rb') as f:
                    return f.read()
        return None
    finally:
        for p in (src_path, out_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
