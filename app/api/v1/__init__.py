"""
Bank API - v1 API Package

Version 1 of the REST API endpoints.
"""

from flask_smorest import Api


def register_v1_blueprints(api: Api) -> None:
    """
    Register all v1 API blueprints.
    
    Args:
        api: Flask-SMOREST Api instance
    """
    from app.api.v1.auth import auth_bp
    from app.api.v1.customers import customers_bp
    from app.api.v1.accounts import accounts_bp
    from app.api.v1.transactions import transactions_bp
    from app.api.v1.loans import loans_bp
    from app.api.v1.admin import admin_bp
    
    # Register blueprints with Flask-SMOREST Api
    api.register_blueprint(auth_bp)
    api.register_blueprint(customers_bp)
    api.register_blueprint(accounts_bp)
    api.register_blueprint(transactions_bp)
    api.register_blueprint(loans_bp)
    api.register_blueprint(admin_bp)

