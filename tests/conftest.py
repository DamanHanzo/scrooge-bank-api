"""
Bank API - Test Configuration

Pytest configuration and fixtures for testing.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from app import create_app
from app.models import db, Customer, Account, Transaction, User, LoanApplication
from app.config import TestingConfig


@pytest.fixture(scope='session')
def app():
    """
    Create application for testing.
    
    Yields:
        Flask application configured for testing
    """
    app = create_app(TestingConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def db_session(app):
    """
    Create a database session for testing.
    
    Args:
        app: Flask application fixture
        
    Yields:
        Database session
    """
    with app.app_context():
        # Begin a nested transaction
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Bind session to connection
        session = db.session
        session.bind = connection
        
        yield session
        
        # Rollback transaction and close connection
        transaction.rollback()
        connection.close()
        session.remove()


@pytest.fixture(scope='function')
def client(app):
    """
    Create a test client.
    
    Args:
        app: Flask application fixture
        
    Returns:
        Flask test client
    """
    return app.test_client()


@pytest.fixture
def sample_customer(db_session):
    """
    Create a sample customer for testing.
    
    Args:
        db_session: Database session fixture
        
    Returns:
        Customer instance
    """
    customer = Customer(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        date_of_birth=date(1990, 1, 1),
        phone='+1-555-0123',
        address_line_1='123 Test St',
        city='Test City',
        state='CA',
        zip_code='12345',
        status='ACTIVE'
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture
def sample_user(db_session, sample_customer):
    """
    Create a sample user for testing.
    
    Args:
        db_session: Database session fixture
        sample_customer: Sample customer fixture
        
    Returns:
        User instance
    """
    user = User(
        email='test@example.com',
        role='CUSTOMER',
        is_active=True,
        customer_id=sample_customer.id
    )
    user.set_password('password123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session):
    """
    Create an admin user for testing.
    
    Args:
        db_session: Database session fixture
        
    Returns:
        Admin user instance
    """
    user = User(
        email='admin@example.com',
        role='ADMIN',
        is_active=True
    )
    user.set_password('admin123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_checking_account(db_session, sample_customer):
    """
    Create a sample checking account for testing.
    
    Args:
        db_session: Database session fixture
        sample_customer: Sample customer fixture
        
    Returns:
        Account instance
    """
    account = Account(
        customer_id=sample_customer.id,
        account_type='CHECKING',
        account_number='CHK-TEST123',
        status='ACTIVE',
        balance=Decimal('1000.00'),
        currency='USD'
    )
    db_session.add(account)
    db_session.commit()
    return account


@pytest.fixture
def sample_loan_account(db_session, sample_customer):
    """
    Create a sample loan account for testing.
    
    Args:
        db_session: Database session fixture
        sample_customer: Sample customer fixture
        
    Returns:
        Loan account instance
    """
    account = Account(
        customer_id=sample_customer.id,
        account_type='LOAN',
        account_number='LOAN-TEST456',
        status='ACTIVE',
        balance=Decimal('-25000.00'),  # Negative balance = debt
        currency='USD'
    )
    db_session.add(account)
    db_session.commit()
    return account


@pytest.fixture
def sample_transaction(db_session, sample_checking_account):
    """
    Create a sample transaction for testing.
    
    Args:
        db_session: Database session fixture
        sample_checking_account: Sample checking account fixture
        
    Returns:
        Transaction instance
    """
    transaction = Transaction(
        account_id=sample_checking_account.id,
        transaction_type='DEPOSIT',
        amount=Decimal('500.00'),
        currency='USD',
        balance_after=Decimal('1500.00'),
        description='Test deposit',
        reference_number='TXN-TEST-001',
        status='COMPLETED',
        processed_at=datetime.utcnow()
    )
    db_session.add(transaction)
    db_session.commit()
    return transaction


@pytest.fixture
def sample_loan_application(db_session, sample_customer):
    """
    Create a sample loan application for testing.
    
    Args:
        db_session: Database session fixture
        sample_customer: Sample customer fixture
        
    Returns:
        LoanApplication instance
    """
    application = LoanApplication(
        customer_id=sample_customer.id,
        application_number='LOAN-APP-TEST',
        requested_amount=Decimal('25000.00'),
        purpose='Test loan',
        term_months=36,
        employment_status='FULL_TIME',
        annual_income=Decimal('75000.00'),
        status='PENDING',
        applied_at=datetime.utcnow(),
        external_account_number='1234567890',
        external_routing_number='121000248'
    )
    db_session.add(application)
    db_session.commit()
    return application


@pytest.fixture
def auth_headers(client, sample_user):
    """
    Create authentication headers for testing.
    
    Args:
        client: Flask test client
        sample_user: Sample user fixture
        
    Returns:
        Dictionary with Authorization header
    """
    # Login to get token
    response = client.post('/v1/auth/login', json={
        'email': sample_user.email,
        'password': 'password123'
    })
    
    if response.status_code == 200:
        token = response.json['access_token']
        return {'Authorization': f'Bearer {token}'}
    
    return {}


@pytest.fixture
def admin_auth_headers(client, admin_user):
    """
    Create admin authentication headers for testing.
    
    Args:
        client: Flask test client
        admin_user: Admin user fixture
        
    Returns:
        Dictionary with Authorization header
    """
    # Login to get token
    response = client.post('/v1/auth/login', json={
        'email': admin_user.email,
        'password': 'admin123'
    })
    
    if response.status_code == 200:
        token = response.json['access_token']
        return {'Authorization': f'Bearer {token}'}
    
    return {}

