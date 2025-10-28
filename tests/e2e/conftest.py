"""
E2E Test Configuration

Pytest fixtures specifically for E2E tests that ensure proper database cleanup.
"""

import pytest
from app.models import db


@pytest.fixture(autouse=True)
def cleanup_database(app):
    """
    Automatically clean database before and after each E2E test.

    This fixture runs automatically for all tests in this directory.
    It ensures complete isolation between E2E tests by clearing all data.
    """
    with app.app_context():
        # Clean before test
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()

        yield

        # Clean after test
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
