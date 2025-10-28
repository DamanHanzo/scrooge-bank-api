"""
E2E Test - Loan Account Happy Path

Tests customer journey with loan account:
Apply for Loan → Admin Approves → Admin Disburses → Make Payment

Note: Customer must NOT have any active accounts to apply for a loan (business rule).
"""

from decimal import Decimal
from datetime import date


def test_loan_account_happy_path(client, db_session):
    """Test complete loan account workflow."""

    # Setup: Create customer and admin WITHOUT going through registration
    # (Registration might create an account, violating business rule)
    from app.models import User, Customer

    # Create customer without any accounts
    customer = Customer(
        email="loan.customer@example.com",
        first_name="Loan",
        last_name="Customer",
        date_of_birth=date(1990, 1, 1),
        phone="+1-555-0100",
        address_line_1="123 Test St",
        city="Test City",
        state="CA",
        zip_code="12345",
        status="ACTIVE"
    )
    db_session.add(customer)
    db_session.flush()  # Flush to get customer.id

    # Create user for customer
    customer_user = User(
        email="loan.customer@example.com",
        role="CUSTOMER",
        is_active=True,
        customer_id=customer.id
    )
    customer_user.set_password("Password123!")
    db_session.add(customer_user)

    # Create admin user
    admin_user = User(email="admin@bank.com", role="ADMIN", is_active=True)
    admin_user.set_password("Admin123!")
    db_session.add(admin_user)

    db_session.commit()

    # Step 1: Customer login
    login_data = {
        "email": "loan.customer@example.com",
        "password": "Password123!"
    }

    response = client.post('/v1/auth/login', json=login_data)
    assert response.status_code == 200
    customer_token = response.json['access_token']
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    # Step 2: Customer applies for loan (has no active account)
    loan_data = {
        "customer_id": str(customer.id),
        "requested_amount": 25000.00,
        "purpose": "Home improvement",
        "term_months": 36,
        "employment_status": "FULL_TIME",
        "annual_income": 85000.00,
        "external_account": {
            "account_number": "1234567890",
            "routing_number": "121000248"
        }
    }

    response = client.post('/v1/loan-applications', json=loan_data, headers=customer_headers)
    assert response.status_code == 201
    assert response.json['status'] == 'PENDING'
    loan_app_id = response.json['id']

    # Step 3: Admin login
    admin_login = {
        "email": "admin@bank.com",
        "password": "Admin123!"
    }

    response = client.post('/v1/auth/login', json=admin_login)
    assert response.status_code == 200
    admin_token = response.json['access_token']
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Step 4: Admin approves loan
    approval_data = {
        "status": "APPROVED",
        "approved_amount": 25000.00
    }

    response = client.patch(
        f'/v1/admin/loan-applications/{loan_app_id}',
        json=approval_data,
        headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json['status'] == 'APPROVED'

    # Step 5: Admin disburses loan (creates loan account)
    disbursement_data = {
        "confirm": True,
        "notes": "Loan disbursed"
    }

    response = client.post(
        f'/v1/admin/loan-applications/{loan_app_id}/disburse',
        json=disbursement_data,
        headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json['status'] == 'DISBURSED'

    # Get loan application details to find loan account ID
    response = client.get(f'/v1/loan-applications/{loan_app_id}', headers=customer_headers)
    assert response.status_code == 200
    loan_account_id = response.json['loan_account_id']
    assert loan_account_id is not None

    # Step 6: Verify loan account was created
    response = client.get(f'/v1/accounts/{loan_account_id}', headers=customer_headers)
    assert response.status_code == 200
    assert response.json['account_type'] == 'LOAN'
    assert Decimal(response.json['balance']) == Decimal('-25000.00')  # Negative = debt
    assert response.json['status'] == 'ACTIVE'

    # Step 7: Customer makes loan payment
    payment_data = {
        "type": "LOAN_PAYMENT",
        "amount": 1000.00,
        "currency": "USD",
        "description": "Monthly payment"
    }

    response = client.post(
        f'/v1/accounts/{loan_account_id}/transactions',
        json=payment_data,
        headers=customer_headers
    )
    assert response.status_code == 201
    assert response.json['transaction_type'] == 'LOAN_PAYMENT'
    assert Decimal(response.json['amount']) == Decimal('1000.00')
    assert Decimal(response.json['balance_after']) == Decimal('-24000.00')

    # Step 8: Verify final loan balance
    response = client.get(f'/v1/accounts/{loan_account_id}/balance', headers=customer_headers)
    assert response.status_code == 200
    assert Decimal(response.json['balance']) == Decimal('-24000.00')
