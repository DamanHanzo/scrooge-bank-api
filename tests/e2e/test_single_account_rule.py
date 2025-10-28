"""
E2E Test - Single Account Business Rule

Tests that customers can only have ONE active account at a time.
This applies to ALL account types (checking and loan).

Business Rule: A customer cannot have more than one active account simultaneously.
"""

from datetime import date
from decimal import Decimal


def test_cannot_apply_for_loan_with_active_checking_account(client, db_session):
    """
    Test that customer cannot apply for loan when they have an active checking account.

    Flow:
    1. Customer registers and gets checking account
    2. Customer tries to apply for loan
    3. Loan application is rejected with business rule violation
    """
    from app.models import User, Customer, Account

    # Setup: Create customer with active checking account
    customer = Customer(
        email="singleaccount@example.com",
        first_name="Single",
        last_name="Account",
        date_of_birth=date(1990, 1, 1),
        phone="+1-555-0200",
        address_line_1="456 Test Ave",
        city="Test City",
        state="CA",
        zip_code="12345",
        status="ACTIVE"
    )
    db_session.add(customer)
    db_session.flush()

    # Create user for customer
    customer_user = User(
        email="singleaccount@example.com",
        role="CUSTOMER",
        is_active=True,
        customer_id=customer.id
    )
    customer_user.set_password("Password123!")
    db_session.add(customer_user)

    # Create active checking account for customer
    checking_account = Account(
        customer_id=customer.id,
        account_type="CHECKING",
        account_number="CHK-TEST-001",
        status="ACTIVE",
        balance=Decimal("1000.00"),
        currency="USD"
    )
    db_session.add(checking_account)
    db_session.commit()

    # Step 1: Customer login
    login_data = {
        "email": "singleaccount@example.com",
        "password": "Password123!"
    }

    response = client.post('/v1/auth/login', json=login_data)
    assert response.status_code == 200
    customer_token = response.json['access_token']
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    # Step 2: Customer tries to apply for loan (should fail)
    loan_data = {
        "customer_id": str(customer.id),
        "requested_amount": 15000.00,
        "purpose": "Home improvement",
        "term_months": 24,
        "employment_status": "FULL_TIME",
        "annual_income": 60000.00,
        "external_account": {
            "account_number": "9876543210",
            "routing_number": "121000248"
        }
    }

    response = client.post('/v1/loan-applications', json=loan_data, headers=customer_headers)

    # Assert: Application rejected with 422 business rule violation
    assert response.status_code == 422
    assert 'error' in response.json
    error_message = response.json['error']['message'].lower()
    assert 'active' in error_message
    assert 'account' in error_message or 'checking' in error_message


def test_cannot_open_checking_account_with_active_loan(client, db_session):
    """
    Test that customer cannot open checking account when they have an active loan account.

    Flow:
    1. Setup customer with active loan account (already disbursed)
    2. Customer tries to open checking account
    3. Request is rejected with business rule violation
    """
    from app.models import User, Customer, Account

    # Setup: Create customer with active loan account
    customer = Customer(
        email="loanfirst@example.com",
        first_name="Loan",
        last_name="First",
        date_of_birth=date(1985, 5, 15),
        phone="+1-555-0300",
        address_line_1="789 Test Blvd",
        city="Test City",
        state="CA",
        zip_code="12345",
        status="ACTIVE"
    )
    db_session.add(customer)
    db_session.flush()

    # Create user for customer
    customer_user = User(
        email="loanfirst@example.com",
        role="CUSTOMER",
        is_active=True,
        customer_id=customer.id
    )
    customer_user.set_password("Password123!")
    db_session.add(customer_user)

    # Create active loan account for customer
    loan_account = Account(
        customer_id=customer.id,
        account_type="LOAN",
        account_number="LOAN-TEST-001",
        status="ACTIVE",
        balance=Decimal("-20000.00"),  # Negative = debt
        currency="USD"
    )
    db_session.add(loan_account)
    db_session.commit()

    # Step 1: Customer login
    login_data = {
        "email": "loanfirst@example.com",
        "password": "Password123!"
    }

    response = client.post('/v1/auth/login', json=login_data)
    assert response.status_code == 200
    customer_token = response.json['access_token']
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    # Step 2: Customer tries to open checking account (should fail)
    account_data = {
        "account_type": "CHECKING",
        "initial_deposit": 500.00,
        "currency": "USD"
    }

    response = client.post('/v1/accounts', json=account_data, headers=customer_headers)

    # Assert: Request rejected with 422 business rule violation
    assert response.status_code == 422
    assert 'error' in response.json
    error_message = response.json['error']['message'].lower()
    # Check for keywords indicating the single account rule violation
    assert 'account' in error_message
    assert ('loan' in error_message or 'open' in error_message or 'active' in error_message)


def test_can_apply_for_loan_after_closing_checking_account(client, db_session):
    """
    Test that customer CAN apply for loan after closing their checking account.

    Flow:
    1. Customer has active checking account
    2. Customer closes checking account
    3. Customer successfully applies for loan
    """
    from app.models import User, Customer, Account

    # Setup: Create customer with active checking account
    customer = Customer(
        email="closethenopen@example.com",
        first_name="Close",
        last_name="ThenOpen",
        date_of_birth=date(1992, 8, 20),
        phone="+1-555-0400",
        address_line_1="321 Test Ln",
        city="Test City",
        state="CA",
        zip_code="12345",
        status="ACTIVE"
    )
    db_session.add(customer)
    db_session.flush()

    # Create user for customer
    customer_user = User(
        email="closethenopen@example.com",
        role="CUSTOMER",
        is_active=True,
        customer_id=customer.id
    )
    customer_user.set_password("Password123!")
    db_session.add(customer_user)

    # Create active checking account for customer with ZERO balance (required to close)
    checking_account = Account(
        customer_id=customer.id,
        account_type="CHECKING",
        account_number="CHK-TEST-002",
        status="ACTIVE",
        balance=Decimal("0.00"),  # Zero balance required to close
        currency="USD"
    )
    db_session.add(checking_account)
    db_session.commit()

    # Step 1: Customer login
    login_data = {
        "email": "closethenopen@example.com",
        "password": "Password123!"
    }

    response = client.post('/v1/auth/login', json=login_data)
    assert response.status_code == 200
    customer_token = response.json['access_token']
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    # Step 2: Customer closes checking account (PATCH with status=CLOSED)
    close_data = {
        "status": "CLOSED"
    }

    response = client.patch(
        f'/v1/accounts/{checking_account.id}',
        json=close_data,
        headers=customer_headers
    )
    assert response.status_code == 200
    assert response.json['status'] == 'CLOSED'

    # Step 3: Customer applies for loan (should succeed now)
    loan_data = {
        "customer_id": str(customer.id),
        "requested_amount": 10000.00,
        "purpose": "Debt consolidation",
        "term_months": 36,
        "employment_status": "FULL_TIME",
        "annual_income": 55000.00,
        "external_account": {
            "account_number": "1122334455",
            "routing_number": "121000248"
        }
    }

    response = client.post('/v1/loan-applications', json=loan_data, headers=customer_headers)

    # Assert: Application succeeds
    assert response.status_code == 201
    assert response.json['status'] == 'PENDING'
    assert 'id' in response.json
