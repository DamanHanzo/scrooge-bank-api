"""
Bank API - Configuration

Configuration classes for different environments (Development, Testing, Production).
"""

import os
from datetime import timedelta
from typing import List


class Config:
    """Base configuration class with common settings."""

    # Flask Configuration
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or "postgresql://bank_user:bank_password@localhost:5432/bank_api_dev"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "dev-jwt-secret-key"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000))
    )
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # API Configuration
    API_TITLE = os.environ.get("API_TITLE", "Bank API")
    API_VERSION = os.environ.get("API_VERSION", "v1")
    API_DESCRIPTION = os.environ.get(
        "API_DESCRIPTION",
        """
# Scrooge Banking API

A comprehensive banking API providing account management, transactions, and loan processing capabilities.

## Authentication

All endpoints (except `/v1/auth/login` and `/v1/auth/register`) require JWT authentication.

To authenticate:
1. Login via `/v1/auth/login` to receive an access token
2. Include the token in the `Authorization` header: `Bearer <token>`
3. Tokens expire after 1 hour - use `/v1/auth/refresh` to get a new token

## Features

- **Account Management**: Create and manage checking and loan accounts
- **Transactions**: Deposits, withdrawals with validation and limits
- **Loans**: Apply for loans, track applications, make payments
- **Admin Operations**: Customer management, loan approvals, financial reporting

## Rate Limiting

- 100 requests per minute per user
- 1000 requests per hour per user
""",
    )
    OPENAPI_VERSION = "3.0.2"
    OPENAPI_URL_PREFIX = "/api"
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    OPENAPI_REDOC_PATH = "/redoc"
    OPENAPI_REDOC_URL = "https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"

    # Flask-SMOREST Configuration
    API_SPEC_OPTIONS = {
        "x-internal-id": "1",
        # Security scheme for JWT authentication
        "security": [{"bearerAuth": []}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT Authorization header using the Bearer scheme. "
                    "Example: 'Authorization: Bearer {token}'",
                }
            }
        },
        # Server URLs
        "servers": [
            {
                "url": os.environ.get("API_SERVER_URL", "http://localhost:5025"),
                "description": "Development server",
            }
        ],
        # Contact and license information
        "info": {
            "contact": {
                "name": "API Support",
                "email": os.environ.get("API_CONTACT_EMAIL", "api-support@scoorge-bank.com"),
                "url": os.environ.get("API_CONTACT_URL", "https://scoorge-bank.com/support"),
            },
            "license": {
                "name": os.environ.get("API_LICENSE_NAME", "Proprietary"),
                "url": os.environ.get("API_LICENSE_URL", "https://scoorge-bank.com/terms"),
            },
            "termsOfService": os.environ.get("API_TERMS_URL", "https://scoorge-bank.com/terms"),
        },
    }
    PROPAGATE_EXCEPTIONS = True

    # CORS Configuration
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

    # Feature Flags
    ENABLE_WITHDRAWALS = os.environ.get("ENABLE_WITHDRAWALS", "true").lower() == "true"
    ENABLE_LOANS = os.environ.get("ENABLE_LOANS", "true").lower() == "true"
    ENABLE_RATE_LIMITING = os.environ.get("ENABLE_RATE_LIMITING", "false").lower() == "true"

    # Security Configuration
    REQUIRE_HTTPS = os.environ.get("REQUIRE_HTTPS", "false").lower() == "true"
    MAX_KEYS_PER_CUSTOMER = int(os.environ.get("MAX_KEYS_PER_CUSTOMER", 5))
    API_KEY_ROTATION_DAYS = int(os.environ.get("API_KEY_ROTATION_DAYS", 90))

    # Logging Configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Business Rules
    MAX_WITHDRAWAL_AMOUNT = 10000.00  # Maximum single withdrawal
    DAILY_WITHDRAWAL_LIMIT = 50000.00  # Daily withdrawal limit
    MIN_ACCOUNT_BALANCE = 0.00  # No overdrafts

    # Bank Capital & Reserve Requirements
    BANK_INITIAL_CAPITAL = 250000.00  # Bank's starting capital in USD
    RESERVE_RATIO = 0.25  # Can use 25% of customer deposits for lending
    RESERVE_REQUIREMENT = 0.75  # Must keep 75% of deposits liquid for withdrawals

    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    TESTING = False

    # More verbose logging in development
    LOG_LEVEL = "DEBUG"

    # Disable HTTPS requirement in development
    REQUIRE_HTTPS = False

    # Enable SQL query logging
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    DEBUG = True

    # Use PostgreSQL for tests (same as dev, but separate database)
    # Models use PostgreSQL-specific types (UUID, JSONB), so SQLite won't work
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("TEST_DATABASE_URL")
        or "postgresql://bank_user:bank_password@db:5432/bank_api_test"
    )

    # Same engine options as base config
    # SQLALCHEMY_ENGINE_OPTIONS inherited from Config

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Shorter token expiry for testing
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=1)

    # Disable rate limiting in tests
    ENABLE_RATE_LIMITING = False


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False

    # Require HTTPS in production
    REQUIRE_HTTPS = True

    # Stricter logging
    LOG_LEVEL = "WARNING"

    # Disable SQL query logging
    SQLALCHEMY_ECHO = False

    # More conservative database pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    # Enable rate limiting in production
    ENABLE_RATE_LIMITING = True


# Configuration dictionary for easy access
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(environment: str = None) -> Config:
    """
    Get configuration class based on environment.

    Args:
        environment: Environment name (development, testing, production)

    Returns:
        Configuration class
    """
    if environment is None:
        environment = os.environ.get("FLASK_ENV", "development")

    return config.get(environment, config["default"])
