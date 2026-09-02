"""Unified JSON response helpers."""

from flask import jsonify


def success(data=None, message=None, warning=None):
    resp = {'success': True}
    if data is not None:
        resp['data'] = data
    if message:
        resp['message'] = message
    if warning:
        resp['warning'] = warning
    return jsonify(resp)


def error(message, status_code=400):
    return jsonify({'success': False, 'error': message}), status_code
