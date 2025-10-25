"""
Bank API - Models Package

SQLAlchemy ORM models for the Bank API.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Create SQLAlchemy instance
db = SQLAlchemy(model_class=Base)


def init_db(app: Flask) -> None:
    """
    Initialize database with Flask app.
    
    Args:
        app: Flask application instance
    """
    db.init_app(app)
    
    # Import all models to ensure they're registered with SQLAlchemy
    from app.models.customer import Customer
    from app.models.account import Account
    from app.models.transaction import Transaction
    from app.models.loan_application import LoanApplication
    from app.models.user import User


# Import models for easy access
from app.models.customer import Customer
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.loan_application import LoanApplication
from app.models.user import User

__all__ = [
    'db',
    'init_db',
    'Customer',
    'Account',
    'Transaction',
    'LoanApplication',
    'User',
]

