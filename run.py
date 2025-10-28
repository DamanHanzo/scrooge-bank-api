"""
Scrooge Bank API - Application Entry Point

This module serves as the entry point for running the Flask application.
It creates the app instance and runs the development server.

Usage:
    flask run
    python run.py
"""

import os
from app import create_app
from app.config import get_config

# Get environment from environment variable
environment = os.environ.get('FLASK_ENV', 'development')

# Create Flask app with appropriate configuration
app = create_app(get_config(environment))


@app.shell_context_processor
def make_shell_context():
    """
    Create a shell context that adds database instance and models to the shell session.
    This allows you to work with the database and models directly in Flask shell.
    
    Usage:
        flask shell
        >>> Customer.query.all()
    """
    from app.models import db
    from app.models.customer import Customer
    from app.models.account import Account
    from app.models.transaction import Transaction
    from app.models.loan_application import LoanApplication
    from app.models.user import User
    
    return {
        'db': db,
        'Customer': Customer,
        'Account': Account,
        'Transaction': Transaction,
        'LoanApplication': LoanApplication,
        'User': User,
    }


@app.cli.command()
def test():
    """
    Run the unit tests.
    
    Usage:
        flask test
    """
    import pytest
    pytest.main(['-v', 'tests/'])


@app.cli.command()
def init_db():
    """
    Initialize the database.
    
    Usage:
        flask init-db
    """
    from app.models import db
    db.create_all()
    print("Database initialized successfully!")


@app.cli.command()
def seed_db():
    """
    Seed the database with sample data.
    
    Usage:
        flask seed-db
    """
    from scripts.seed_data import seed_database
    seed_database()
    print("Database seeded successfully!")


if __name__ == '__main__':
    # Run the development server
    # Note: In production, use gunicorn or similar WSGI server
    app.run(
        host=os.environ.get('FLASK_RUN_HOST', '0.0.0.0'),
        port=int(os.environ.get('FLASK_RUN_PORT', 5000)),
        debug=app.config['DEBUG']
    )

