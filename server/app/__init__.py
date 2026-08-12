"""Flask application factory."""

import os
from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import init_db
from .routes import register_blueprints


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    # 跨域支持（开发时前端跑在不同端口）
    CORS(app, supports_credentials=True)

    # 初始化数据库
    init_db(app)

    # 注册蓝图
    register_blueprints(app)

    # 确保上传目录存在
    for subdir in ('营业执照', '被代理人营业执照', '授权委托书', '权属证明'):
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], subdir), exist_ok=True)

    return app
