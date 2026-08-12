"""Authentication routes."""

import time
from flask import Blueprint, request, session, jsonify

from ..auth.auth_client import login as auth_login, verify_token
from ..auth.decorators import get_client_ip, get_current_user
from ..utils.response import success, error

auth_bp = Blueprint('auth', __name__, url_prefix='/api')


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = (data or {}).get('username', '').strip()
    password = (data or {}).get('password', '').strip()

    if not username or not password:
        return error('用户名和密码不能为空')

    client_ip = get_client_ip()
    result = auth_login(username, password, client_ip)

    if not result['success']:
        return error(result['error'])

    session['token'] = result['token']
    session['username'] = result['user_info']['username']
    session['uid'] = result['user_info'].get('uid')
    session['login_time'] = time.time()

    return success({'username': result['user_info']['username']})


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return success(message='已退出登录')


@auth_bp.route('/user/info')
def user_info():
    token = session.get('token')
    if not token:
        return error('未登录', 401)

    v = verify_token(token, get_client_ip())
    if not v['valid']:
        session.clear()
        return error(v['error'], 401)

    return success({
        'username': session.get('username', ''),
        'uid': session.get('uid'),
    })
