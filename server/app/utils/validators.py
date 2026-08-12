"""Common validation utilities."""

import re


def normalize_company_name(value):
    """全角括号转半角，去首尾空格。"""
    return (value or '').strip().replace('（', '(').replace('）', ')')


def sanitize_filename_part(value):
    """移除文件系统不安全字符，保留中文。"""
    normalized = (value or '').strip().replace('（', '(').replace('）', ')')
    return re.sub(r'[/:*?"<>|\\：＊？＂＜＞｜＼／]', '', normalized)
