"""File serving route for uploaded files."""

import os
from flask import Blueprint, send_from_directory, current_app

from ..auth.decorators import login_required
from ..utils.response import error

files_bp = Blueprint('files', __name__, url_prefix='/api/files')


@files_bp.route('/<path:filepath>')
@login_required
def serve_file(filepath):
    """Serve uploaded files. Path format: {subfolder}/{filename}"""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    full_path = os.path.join(upload_folder, filepath)

    if not os.path.isfile(full_path):
        return error('文件不存在', 404)

    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    return send_from_directory(directory, filename)
