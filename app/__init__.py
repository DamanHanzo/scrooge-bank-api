"""
Bank API - Flask Application Factory

This module implements the Flask application factory pattern for creating
and configuring the Flask application instance.
"""

from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_smorest import Api
from sqlalchemy.orm import Session
from decimal import Decimal

from app.config import Config


class DecimalJSONProvider(DefaultJSONProvider):
    """Custom JSON provider that handles Decimal types."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def create_app(config_class=Config) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use (Config, DevelopmentConfig, etc.)
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure custom JSON encoder to handle Decimal types
    app.json = DecimalJSONProvider(app)
    
    # Initialize extensions
    api = initialize_extensions(app)
    
    # Register blueprints
    register_blueprints(api)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Setup logging
    setup_logging(app)
    
    return app


def initialize_extensions(app: Flask) -> Api:
    """
    Initialize Flask extensions.
    
    Args:
        app: Flask application instance
        
    Returns:
        Api instance for registering blueprints
    """
    # CORS - Cross-Origin Resource Sharing
    CORS(app, resources={r"/v1/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})
    
    # JWT - JSON Web Token authentication
    jwt = JWTManager(app)
    
    # Flask-SMOREST - OpenAPI/Swagger documentation
    # Monkey-patch json module to handle Decimal in OpenAPI spec generation
    import json
    _original_dumps = json.dumps
    def custom_dumps(obj, *args, **kwargs):
        class DecimalEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, Decimal):
                    return float(o)
                return super().default(o)
        if 'cls' not in kwargs:
            kwargs['cls'] = DecimalEncoder
        return _original_dumps(obj, *args, **kwargs)
    json.dumps = custom_dumps
    
    api = Api(app)
    
    # Database - SQLAlchemy will be initialized in models
    from app.models import init_db
    init_db(app)
    
    # Register JWT callbacks
    register_jwt_callbacks(jwt)
    
    return api


def register_blueprints(api: Api) -> None:
    """
    Register Flask blueprints for API routes.
    
    Args:
        api: Flask-SMOREST Api instance
    """
    # Import blueprints
    from app.api.v1 import register_v1_blueprints
    
    # Register v1 API blueprints
    register_v1_blueprints(api)


def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers.
    
    Args:
        app: Flask application instance
    """
    from app.middleware.error_handlers import (
        handle_validation_error,
        handle_authentication_error,
        handle_authorization_error,
        handle_not_found_error,
        handle_business_rule_violation,
        handle_generic_error
    )
    from app.exceptions import (
        ValidationError,
        AuthenticationError,
        AuthorizationError,
        NotFoundError,
        BusinessRuleViolationError
    )
    
    app.register_error_handler(ValidationError, handle_validation_error)
    app.register_error_handler(AuthenticationError, handle_authentication_error)
    app.register_error_handler(AuthorizationError, handle_authorization_error)
    app.register_error_handler(NotFoundError, handle_not_found_error)
    app.register_error_handler(BusinessRuleViolationError, handle_business_rule_violation)
    app.register_error_handler(Exception, handle_generic_error)


def register_jwt_callbacks(jwt: JWTManager) -> None:
    """
    Register JWT callback functions.
    
    Args:
        jwt: JWTManager instance
    """
    from flask import jsonify
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': {
                'code': 'TOKEN_EXPIRED',
                'message': 'The token has expired',
            }
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'error': {
                'code': 'INVALID_TOKEN',
                'message': 'Signature verification failed',
            }
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'error': {
                'code': 'MISSING_TOKEN',
                'message': 'Request does not contain an access token',
            }
        }), 401


def setup_logging(app: Flask) -> None:
    """
    Configure application logging.
    
    Args:
        app: Flask application instance
    """
    import logging
    from logging.handlers import RotatingFileHandler
    import os
    
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/bank_api.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Bank API startup')

