"""
Bank API - v1 API Package

Version 1 of the REST API endpoints.
"""

from flask import Flask


def register_v1_blueprints(app: Flask) -> None:
    """
    Register all v1 API blueprints.
    
    Args:
        app: Flask application instance
    """
    from app.api.v1.auth import auth_bp
    from app.api.v1.customers import customers_bp
    from app.api.v1.accounts import accounts_bp
    from app.api.v1.transactions import transactions_bp
    from app.api.v1.loans import loans_bp
    from app.api.v1.admin import admin_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/v1/auth')
    app.register_blueprint(customers_bp, url_prefix='/v1/customers')
    app.register_blueprint(accounts_bp, url_prefix='/v1/accounts')
    app.register_blueprint(transactions_bp, url_prefix='/v1/transactions')
    app.register_blueprint(loans_bp, url_prefix='/v1/loan-applications')
    app.register_blueprint(admin_bp, url_prefix='/v1/admin')

