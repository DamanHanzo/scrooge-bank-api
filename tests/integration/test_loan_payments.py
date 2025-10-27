"""
Integration tests for loan payment functionality.

Tests User Story 4: "As a user, I can make a payment on my loan"

Test Coverage:
1. Make payment on own loan account succeeds
2. Make payment reduces loan balance correctly
3. Full payment closes loan account
4. Payment exceeding debt fails
5. Negative payment amount fails
6. Zero payment amount fails
7. Payment on non-existent account fails (404)
8. Payment on CHECKING account fails (not a loan)
9. Payment on CLOSED loan fails
10. Payment on another customer's loan fails (403)
11. Payment creates LOAN_PAYMENT transaction
12. Unauthenticated payment fails (401)
"""

import pytest
from decimal import Decimal
from datetime import date

from app.models import Account, Customer, Transaction


class TestLoanPayments:
    """Test suite for loan payment functionality."""

    def test_make_payment_on_own_loan_succeeds(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 1: Customer can make payment on their own loan.

        Given: Customer has LOAN account with -$5000 balance
        When: Customer makes $1000 payment
        Then: Payment succeeds with 201, balance becomes -$4000
        """
        with app.app_context():
            # Arrange - Create loan account with debt
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-TEST-001",
                status="ACTIVE",
                balance=Decimal("-5000.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            # Create authenticated user for the customer
            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            # Login to get auth token
            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act - Make payment
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                headers=auth_headers,
                json={"amount": 1000.00, "description": "Test payment"}
            )

            # Assert
            assert response.status_code == 201
            data = response.json

            assert data["transaction_type"] == "LOAN_PAYMENT"
            assert Decimal(data["amount"]) == Decimal("1000.00")
            assert Decimal(data["balance_after"]) == Decimal("-4000.00")
            assert data["status"] == "COMPLETED"
            assert "reference_number" in data

    def test_payment_reduces_balance_correctly(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 2: Payment correctly reduces loan balance.

        Given: Loan balance is -$10000
        When: Payment of $3000 is made
        Then: New balance is -$7000 (debt reduced by $3000)
        """
        with app.app_context():
            # Arrange
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-TEST-002",
                status="ACTIVE",
                balance=Decimal("-10000.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act - Make payment
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                headers=auth_headers,
                json={"amount": 3000.00}
            )

            # Assert
            assert response.status_code == 201
            assert Decimal(response.json["balance_after"]) == Decimal("-7000.00")

            # Verify in database
            db_session.expire_all()
            updated_account = db_session.query(Account).filter_by(id=loan_account.id).first()
            assert updated_account.balance == Decimal("-7000.00")

    def test_full_payment_closes_loan_account(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 3: Paying off loan completely closes the account.

        Given: Loan balance is -$100
        When: Payment of $100 is made
        Then: Balance becomes $0.00 AND account status is CLOSED
        """
        with app.app_context():
            # Arrange
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-TEST-003",
                status="ACTIVE",
                balance=Decimal("-100.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act - Pay off loan completely
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                headers=auth_headers,
                json={"amount": 100.00}
            )

            # Assert
            assert response.status_code == 201
            assert Decimal(response.json["balance_after"]) == Decimal("0.00")

            # Verify account is closed and description contains "PAID IN FULL"
            db_session.expire_all()
            updated_account = db_session.query(Account).filter_by(id=loan_account.id).first()
            assert updated_account.status == "CLOSED"
            assert updated_account.balance == Decimal("0.00")

            # Check transaction description
            transaction = db_session.query(Transaction).filter_by(
                account_id=loan_account.id,
                transaction_type="LOAN_PAYMENT"
            ).first()
            assert "LOAN PAID IN FULL" in transaction.description

    def test_payment_exceeding_debt_fails(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 4: Payment amount exceeding debt fails.

        Given: Loan balance is -$500 (debt = $500)
        When: Payment of $600 is attempted
        Then: Returns 422 VALIDATION_ERROR
        """
        with app.app_context():
            # Arrange
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-TEST-004",
                status="ACTIVE",
                balance=Decimal("-500.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                headers=auth_headers,
                json={"amount": 600.00}
            )

            # Assert
            assert response.status_code == 422
            assert "error" in response.json
            assert "exceeds outstanding debt" in response.json["error"]["message"]

    def test_negative_payment_amount_fails(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 5: Negative payment amount fails.

        Given: Loan account exists
        When: Payment with negative amount is attempted
        Then: Returns 400 or 422 validation error
        """
        with app.app_context():
            # Arrange
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-TEST-005",
                status="ACTIVE",
                balance=Decimal("-1000.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                headers=auth_headers,
                json={"amount": -100.00}
            )

            # Assert
            assert response.status_code in [400, 422]
            # Flask-SMOREST returns 'errors' not 'error' for validation
            assert "errors" in response.json or "error" in response.json

    def test_zero_payment_amount_fails(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 6: Zero payment amount fails.

        Given: Loan account exists
        When: Payment with zero amount is attempted
        Then: Returns 400 or 422 validation error
        """
        with app.app_context():
            # Arrange
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-TEST-006",
                status="ACTIVE",
                balance=Decimal("-1000.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                headers=auth_headers,
                json={"amount": 0.00}
            )

            # Assert
            assert response.status_code in [400, 422]
            # Flask-SMOREST returns 'errors' not 'error' for validation
            assert "errors" in response.json or "error" in response.json

    def test_payment_on_nonexistent_account_fails(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 7: Payment on non-existent account returns 404.

        Given: Account ID does not exist
        When: Payment is attempted
        Then: Returns 404 NOT_FOUND
        """
        with app.app_context():
            from app.models import User
            from uuid import uuid4

            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act - Use fake UUID
            fake_id = uuid4()
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{fake_id}/payments",
                headers=auth_headers,
                json={"amount": 100.00}
            )

            # Assert
            assert response.status_code == 404
            assert "error" in response.json

    def test_payment_on_checking_account_fails(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 8: Payment on CHECKING account fails.

        Given: Account is CHECKING type (not LOAN)
        When: Payment is attempted
        Then: Returns 422 BUSINESS_RULE_VIOLATION
        """
        with app.app_context():
            # Arrange - Create CHECKING account
            checking_account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-TEST-008",
                status="ACTIVE",
                balance=Decimal("1000.00"),
                currency="USD",
            )
            db_session.add(checking_account)
            db_session.commit()

            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{checking_account.id}/payments",
                headers=auth_headers,
                json={"amount": 100.00}
            )

            # Assert
            assert response.status_code == 422
            assert "error" in response.json
            assert "not a loan account" in response.json["error"]["message"].lower()

    def test_payment_on_closed_loan_fails(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 9: Payment on CLOSED loan account fails.

        Given: Loan account is CLOSED
        When: Payment is attempted
        Then: Returns 422 BUSINESS_RULE_VIOLATION
        """
        with app.app_context():
            # Arrange - Create CLOSED loan account
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-TEST-009",
                status="CLOSED",
                balance=Decimal("0.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                headers=auth_headers,
                json={"amount": 100.00}
            )

            # Assert
            assert response.status_code == 422
            assert "error" in response.json
            assert "closed" in response.json["error"]["message"].lower()

    def test_payment_on_another_customer_loan_fails(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 10: Payment on another customer's loan fails (403).

        Given: Customer A has a loan
        When: Customer B attempts to pay Customer A's loan
        Then: Returns 403 FORBIDDEN
        """
        with app.app_context():
            # Arrange - Create another customer with loan
            other_customer = Customer(
                email="other@example.com",
                first_name="Other",
                last_name="Customer",
                date_of_birth=date(1985, 5, 15),
                phone="+1-555-9999",
                address_line_1="999 Other St",
                city="Test City",
                state="CA",
                zip_code="99999",
                status="ACTIVE"
            )
            db_session.add(other_customer)
            db_session.commit()

            loan_account = Account(
                customer_id=other_customer.id,  # Belongs to other_customer
                account_type="LOAN",
                account_number="LOAN-TEST-010",
                status="ACTIVE",
                balance=Decimal("-5000.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            # Create user for sample_customer (not the loan owner)
            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act - Try to pay another customer's loan
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                headers=auth_headers,
                json={"amount": 100.00}
            )

            # Assert
            assert response.status_code == 403
            assert "error" in response.json

    def test_payment_creates_loan_payment_transaction(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 11: Payment creates LOAN_PAYMENT transaction record.

        Given: Loan account exists
        When: Payment is made
        Then: Transaction record with type LOAN_PAYMENT is created
        """
        with app.app_context():
            # Arrange
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-TEST-011",
                status="ACTIVE",
                balance=Decimal("-2000.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            from app.models import User
            user = User(
                email=sample_customer.email,
                role="CUSTOMER",
                is_active=True,
                customer_id=sample_customer.id
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()

            login_response = client.post(
                "/v1/auth/login",
                json={"email": user.email, "password": "password123"}
            )
            token = login_response.json["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Act
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                headers=auth_headers,
                json={"amount": 500.00, "description": "Test loan payment"}
            )

            # Assert
            assert response.status_code == 201

            # Verify transaction exists in database
            db_session.expire_all()
            transaction = db_session.query(Transaction).filter_by(
                account_id=loan_account.id,
                transaction_type="LOAN_PAYMENT"
            ).first()

            assert transaction is not None
            assert transaction.amount == Decimal("500.00")
            assert transaction.balance_after == Decimal("-1500.00")
            assert transaction.status == "COMPLETED"
            assert "Test loan payment" in transaction.description

    def test_unauthenticated_payment_fails(
        self, client, sample_customer, db_session, app
    ):
        """
        Test 12: Unauthenticated payment fails with 401.

        Given: No authentication token
        When: Payment is attempted
        Then: Returns 401 UNAUTHORIZED
        """
        with app.app_context():
            # Arrange
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-TEST-012",
                status="ACTIVE",
                balance=Decimal("-1000.00"),
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            # Act - No auth headers
            response = client.post(
                f"/v1/loan-applications/loan-accounts/{loan_account.id}/payments",
                json={"amount": 100.00}
            )

            # Assert
            assert response.status_code == 401
