"""Login required decorator."""

import time
from functools import wraps
from flask import session, request, jsonify

from .auth_client import verify_token

LOGIN_EXPIRE_SECONDS = 43200  # 12小时


def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()


def get_current_user():
    return session.get('username', '')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get('token')
        if not token:
            return jsonify({'success': False, 'error': '未登录', 'login_required': True}), 401

        login_time = session.get('login_time', 0)
        if time.time() - login_time > LOGIN_EXPIRE_SECONDS:
            session.clear()
            return jsonify({'success': False, 'error': '登录已过期，请重新登录', 'login_required': True}), 401

        v = verify_token(token, get_client_ip())
        if not v['valid']:
            session.clear()
            return jsonify({'success': False, 'error': v['error'], 'login_required': True}), 401

        return f(*args, **kwargs)
    return decorated
