"""Register all blueprints."""

from .auth_routes import auth_bp
from .company_routes import company_bp
from .agent_routes import agent_bp
from .work_routes import work_bp
from .file_routes import files_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(work_bp)
    app.register_blueprint(files_bp)
