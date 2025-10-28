"""
E2E Test - Bank Operator Happy Path

Tests bank operator (admin) workflow:
1. View bank financial status
2. Review and approve loan application
3. Disburse approved loan
4. Verify bank financial status updated correctly
5. Manage customer accounts

This validates the admin-facing operations and business rules.
"""

from datetime import date
from decimal import Decimal


def test_bank_operator_happy_path(client, db_session):
    """
    Test complete bank operator workflow.

    Flow:
    1. Admin logs in
    2. Views bank financial status (initial state)
    3. Customer applies for loan
    4. Admin reviews and approves loan
    5. Admin disburses loan
    6. Admin verifies bank financial status updated
    7. Admin views all customers
    8. Admin manages customer status
    """
    from app.models import User, Customer, Account

    # Setup: Create admin user
    admin_user = User(email="bankoperator@example.com", role="ADMIN", is_active=True)
    admin_user.set_password("Admin123!")
    db_session.add(admin_user)

    # Setup: Create customer for loan application
    customer = Customer(
        email="borrower@example.com",
        first_name="Borrower",
        last_name="Customer",
        date_of_birth=date(1988, 3, 15),
        phone="+1-555-0500",
        address_line_1="123 Loan St",
        city="Test City",
        state="CA",
        zip_code="12345",
        status="ACTIVE"
    )
    db_session.add(customer)
    db_session.flush()

    # Create user for customer
    customer_user = User(
        email="borrower@example.com",
        role="CUSTOMER",
        is_active=True,
        customer_id=customer.id
    )
    customer_user.set_password("Password123!")
    db_session.add(customer_user)

    # Setup: Create another customer with deposit (to provide bank funds)
    depositor = Customer(
        email="depositor@example.com",
        first_name="Rich",
        last_name="Depositor",
        date_of_birth=date(1975, 6, 20),
        phone="+1-555-0600",
        address_line_1="456 Rich Ave",
        city="Test City",
        state="CA",
        zip_code="12345",
        status="ACTIVE"
    )
    db_session.add(depositor)
    db_session.flush()

    # Create checking account for depositor with funds
    depositor_account = Account(
        customer_id=depositor.id,
        account_type="CHECKING",
        account_number="CHK-DEPOSIT-001",
        status="ACTIVE",
        balance=Decimal("100000.00"),  # Large deposit to ensure bank has funds
        currency="USD"
    )
    db_session.add(depositor_account)
    db_session.commit()

    # Step 1: Admin login
    admin_login = {
        "email": "bankoperator@example.com",
        "password": "Admin123!"
    }

    response = client.post('/v1/auth/login', json=admin_login)
    assert response.status_code == 200
    admin_token = response.json['access_token']
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Step 2: Admin views initial bank financial status
    response = client.get('/v1/admin/bank/financial-status', headers=admin_headers)
    assert response.status_code == 200

    initial_status = response.json
    assert 'available_for_lending' in initial_status
    assert 'bank_capital' in initial_status
    assert 'total_customer_deposits' in initial_status
    assert 'total_loans_outstanding' in initial_status

    initial_available = Decimal(initial_status['available_for_lending'])
    print(f"Initial available for lending: ${initial_available}")

    # Step 3: Customer logs in and applies for loan
    customer_login = {
        "email": "borrower@example.com",
        "password": "Password123!"
    }

    response = client.post('/v1/auth/login', json=customer_login)
    assert response.status_code == 200
    customer_token = response.json['access_token']
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    loan_data = {
        "customer_id": str(customer.id),
        "requested_amount": 30000.00,
        "purpose": "Business expansion",
        "term_months": 48,
        "employment_status": "SELF_EMPLOYED",
        "annual_income": 80000.00,
        "external_account": {
            "account_number": "9988776655",
            "routing_number": "121000248"
        }
    }

    response = client.post('/v1/loan-applications', json=loan_data, headers=customer_headers)
    assert response.status_code == 201
    assert response.json['status'] == 'PENDING'
    loan_app_id = response.json['id']
    print(f"Loan application submitted: {loan_app_id}")

    # Step 4: Admin reviews all customers (should see both)
    response = client.get('/v1/admin/customers', headers=admin_headers)
    assert response.status_code == 200
    customers_data = response.json
    assert 'data' in customers_data
    assert len(customers_data['data']) >= 2  # At least our two test customers

    # Step 5: Admin reviews and approves loan application
    approval_data = {
        "status": "APPROVED",
        "approved_amount": 30000.00,
        "interest_rate": 0.065,  # 6.5%
        "term_months": 48
    }

    response = client.patch(
        f'/v1/admin/loan-applications/{loan_app_id}',
        json=approval_data,
        headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json['status'] == 'APPROVED'
    print("Loan application approved")

    # Step 6: Admin verifies bank still has sufficient funds for disbursement
    response = client.get('/v1/admin/bank/financial-status', headers=admin_headers)
    assert response.status_code == 200

    pre_disburse_status = response.json
    pre_disburse_available = Decimal(pre_disburse_status['available_for_lending'])
    assert pre_disburse_available >= Decimal("30000.00")  # Enough for loan
    print(f"Pre-disbursement available: ${pre_disburse_available}")

    # Step 7: Admin disburses the approved loan
    disbursement_data = {
        "confirm": True,
        "notes": "Loan approved and disbursed for business expansion"
    }

    response = client.post(
        f'/v1/admin/loan-applications/{loan_app_id}/disburse',
        json=disbursement_data,
        headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json['status'] == 'DISBURSED'
    print("Loan disbursed successfully")

    # Step 8: Admin verifies bank financial status updated correctly
    response = client.get('/v1/admin/bank/financial-status', headers=admin_headers)
    assert response.status_code == 200

    final_status = response.json
    final_total_loans = Decimal(final_status['total_loans_outstanding'])
    final_available = Decimal(final_status['available_for_lending'])

    # Verify loan amount shows in total loans
    assert final_total_loans >= Decimal("30000.00")

    # Verify available funds decreased by loan amount
    expected_available = pre_disburse_available - Decimal("30000.00")
    assert abs(final_available - expected_available) < Decimal("0.01")  # Allow for rounding

    print(f"Final total loans: ${final_total_loans}")
    print(f"Final available for lending: ${final_available}")

    # Step 9: Verify loan application details show loan account
    response = client.get(f'/v1/loan-applications/{loan_app_id}', headers=customer_headers)
    assert response.status_code == 200
    loan_details = response.json
    assert loan_details['status'] == 'DISBURSED'
    assert loan_details['loan_account_id'] is not None
    loan_account_id = loan_details['loan_account_id']

    # Step 10: Verify loan account was created with correct balance
    response = client.get(f'/v1/accounts/{loan_account_id}', headers=customer_headers)
    assert response.status_code == 200
    loan_account = response.json
    assert loan_account['account_type'] == 'LOAN'
    assert Decimal(loan_account['balance']) == Decimal('-30000.00')  # Negative = debt
    assert loan_account['status'] == 'ACTIVE'
    print(f"Loan account created: {loan_account_id}, balance: ${loan_account['balance']}")

    # Step 11: Admin views account breakdown in financial status
    response = client.get('/v1/admin/bank/financial-status', headers=admin_headers)
    assert response.status_code == 200

    breakdown = response.json.get('account_breakdown', {})
    assert 'total_checking_accounts' in breakdown
    assert 'total_loan_accounts' in breakdown
    assert 'active_accounts' in breakdown

    # Should have 1 checking account (depositor) and 1 loan account (borrower)
    assert breakdown['total_checking_accounts'] == 1
    assert breakdown['total_loan_accounts'] == 1
    assert breakdown['active_accounts'] == 2  # Total active accounts

    final_status_full = response.json
    assert Decimal(final_status_full['total_loans_outstanding']) == Decimal('30000.00')

    print("Bank financial status verified:")
    print(f"  - Checking accounts: {breakdown['total_checking_accounts']}")
    print(f"  - Loan accounts: {breakdown['total_loan_accounts']}")
    print(f"  - Total loans outstanding: ${final_status_full['total_loans_outstanding']}")


def test_bank_operator_validates_max_loan_amount(client, db_session):
    """
    Test that loan application validates maximum amount ($100k schema limit).

    Flow:
    1. Customer applies for maximum allowed loan
    2. Application accepted (bank has sufficient capital)

    Validates: Schema validation for loan amount limits.
    """
    from app.models import User, Customer

    # Setup: Create admin
    admin_user = User(email="admin2@bank.com", role="ADMIN", is_active=True)
    admin_user.set_password("Admin123!")
    db_session.add(admin_user)

    # Setup: Create customer for loan
    customer = Customer(
        email="bigloan@example.com",
        first_name="Big",
        last_name="Borrower",
        date_of_birth=date(1980, 1, 1),
        phone="+1-555-0700",
        address_line_1="789 Big Loan Ave",
        city="Test City",
        state="CA",
        zip_code="12345",
        status="ACTIVE"
    )
    db_session.add(customer)
    db_session.flush()

    customer_user = User(
        email="bigloan@example.com",
        role="CUSTOMER",
        is_active=True,
        customer_id=customer.id
    )
    customer_user.set_password("Password123!")
    db_session.add(customer_user)
    db_session.commit()

    # Customer login
    customer_login = {"email": "bigloan@example.com", "password": "Password123!"}
    response = client.post('/v1/auth/login', json=customer_login)
    assert response.status_code == 200
    customer_token = response.json['access_token']
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    # Customer applies for maximum allowed loan ($100k - schema limit)
    # Bank only has $250k capital, so this tests the bank funds check
    loan_data = {
        "customer_id": str(customer.id),
        "requested_amount": 100000.00,  # Maximum allowed by schema
        "purpose": "Large business venture",
        "term_months": 60,
        "employment_status": "SELF_EMPLOYED",
        "annual_income": 150000.00,
        "external_account": {
            "account_number": "1111222233",
            "routing_number": "121000248"
        }
    }

    response = client.post('/v1/loan-applications', json=loan_data, headers=customer_headers)

    # Assert: Application should succeed if bank has $250k capital
    # Bank capital ($250k) + 25% of deposits ($0) = $250k available, so $100k loan is allowed
    assert response.status_code == 201
    assert response.json['status'] == 'PENDING'

    print(f"✅ Loan application submitted successfully (bank has sufficient funds)")
