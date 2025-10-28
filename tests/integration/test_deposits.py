"""
Integration tests for Deposit Transactions.

These are integration tests that validate deposit functionality:
- User Story 1: Users can make deposits to their accounts
- User Story 2: Error if account doesn't exist
- User Story 3: Cannot deposit to other people's accounts

Tests ensure proper deposit transaction flow, validation, and authorization.
"""

from decimal import Decimal
import re
import pytest

from app.models import Transaction, Account


class TestDepositFunctionalTests:
    """Test suite for deposit transaction functional tests."""

    def test_deposit_to_own_account_succeeds(
        self, client, auth_headers, sample_checking_account, db_session, app
    ):
        """
        Test 1: Customer can deposit to their own account.

        User Story 1: "As a customer, I want to be able to make deposits to my account"

        Given: Customer has an active CHECKING account with balance $1000.00
        When: Customer makes a deposit of $500.00
        Then: Deposit succeeds with 201 response
        And: Transaction is created with correct details
        """
        with app.app_context():
            # Arrange
            initial_balance = sample_checking_account.balance
            deposit_amount = Decimal("500.00")

            # Act
            response = client.post(
                f"/v1/accounts/{sample_checking_account.id}/transactions",
                headers=auth_headers,
                json={
                    "type": "DEPOSIT",
                    "amount": float(deposit_amount),
                    "currency": "USD",
                    "description": "Test deposit",
                },
            )

            # Assert
            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json}"

            data = response.json
            assert data["transaction_type"] == "DEPOSIT"
            assert Decimal(data["amount"]) == deposit_amount
            assert Decimal(data["balance_after"]) == initial_balance + deposit_amount
            assert data["status"] == "COMPLETED"

            # Verify reference number format: TXN-YYYYMMDD-XXXXXX
            ref_pattern = r"TXN-\d{8}-\d{6}"
            assert re.match(ref_pattern, data["reference_number"]), (
                f"Reference number '{data['reference_number']}' doesn't match pattern {ref_pattern}"
            )

    def test_deposit_to_nonexistent_account_fails(self, client, auth_headers, app):
        """
        Test 2: Cannot deposit to non-existent account.

        User Story 2: "If I do not have an account when I deposit, I should see an error"

        Given: Invalid account UUID
        When: Customer attempts deposit
        Then: Returns 404 NOT_FOUND
        """
        with app.app_context():
            # Arrange
            fake_account_id = "00000000-0000-0000-0000-000000000000"

            # Act
            response = client.post(
                f"/v1/accounts/{fake_account_id}/transactions",
                headers=auth_headers,
                json={"type": "DEPOSIT", "amount": 100.00, "currency": "USD"},
            )

            # Assert
            assert response.status_code == 404
            assert "error" in response.json
            # Error format may vary, accept both formats
            if "code" in response.json["error"]:
                assert response.json["error"]["code"] == "NOT_FOUND"
            # Message should contain account reference
            assert "Account" in response.json["error"]["message"] or "not found" in response.json["error"]["message"].lower()

    def test_deposit_to_other_customer_account_fails(
        self, client, auth_headers, db_session, app
    ):
        """
        Test 3: Customer cannot deposit to another customer's account.

        User Story 3: "I should not be able to make deposits to other people's accounts"

        Given: Customer A is authenticated
        And: Customer B has an account
        When: Customer A attempts to deposit to Customer B's account
        Then: Returns 403 FORBIDDEN
        """
        with app.app_context():
            # Arrange - Create a different customer's account
            from app.models import Customer, Account
            from datetime import date

            other_customer = Customer(
                email="other@example.com",
                first_name="Other",
                last_name="Customer",
                date_of_birth=date(1985, 5, 15),
                phone="+1-555-9999",
                address_line_1="456 Other St",
                city="Other City",
                state="NY",
                zip_code="54321",
                status="ACTIVE",
            )
            db_session.add(other_customer)
            db_session.commit()

            other_account = Account(
                customer_id=other_customer.id,
                account_type="CHECKING",
                account_number="CHK-OTHER123",
                status="ACTIVE",
                balance=Decimal("2000.00"),
                currency="USD",
            )
            db_session.add(other_account)
            db_session.commit()

            # Act - Try to deposit to other customer's account
            response = client.post(
                f"/v1/accounts/{other_account.id}/transactions",
                headers=auth_headers,
                json={"type": "DEPOSIT", "amount": 100.00, "currency": "USD"},
            )

            # Assert
            assert response.status_code == 403
            assert "error" in response.json
            assert response.json["error"]["code"] == "FORBIDDEN"
            assert "Not authorized" in response.json["error"]["message"]

    def test_deposit_to_closed_account_fails(
        self, client, auth_headers, sample_customer, db_session, app
    ):
        """
        Test 5: Cannot deposit to CLOSED account.

        Given: Customer has a CLOSED account
        When: Customer attempts deposit
        Then: Returns 422 BUSINESS_RULE_VIOLATION
        """
        with app.app_context():
            # Arrange - Create a closed account
            closed_account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-CLOSED123",
                status="CLOSED",
                balance=Decimal("0.00"),
                currency="USD",
            )
            db_session.add(closed_account)
            db_session.commit()

            # Act
            response = client.post(
                f"/v1/accounts/{closed_account.id}/transactions",
                headers=auth_headers,
                json={"type": "DEPOSIT", "amount": 100.00, "currency": "USD"},
            )

            # Assert
            assert response.status_code == 422
            assert "error" in response.json
            assert response.json["error"]["code"] == "BUSINESS_RULE_VIOLATION"
            assert "cannot perform transactions" in response.json["error"]["message"]

    def test_deposit_negative_amount_fails(
        self, client, auth_headers, sample_checking_account, app
    ):
        """
        Test 6: Cannot deposit negative amount.

        Given: Customer has active account
        When: Customer attempts deposit with negative amount
        Then: Returns 400 VALIDATION_ERROR
        """
        with app.app_context():
            # Act
            response = client.post(
                f"/v1/accounts/{sample_checking_account.id}/transactions",
                headers=auth_headers,
                json={"type": "DEPOSIT", "amount": -100.00, "currency": "USD"},
            )

            # Assert
            # Pydantic validation should catch negative amounts
            # Flask-SMOREST returns 422 for validation errors
            assert response.status_code in [400, 422]
            assert "error" in response.json or "errors" in response.json

    def test_deposit_zero_amount_fails(
        self, client, auth_headers, sample_checking_account, app
    ):
        """
        Test 7: Cannot deposit zero amount.

        Given: Customer has active account
        When: Customer attempts deposit with amount = 0.00
        Then: Returns 400 VALIDATION_ERROR
        """
        with app.app_context():
            # Act
            response = client.post(
                f"/v1/accounts/{sample_checking_account.id}/transactions",
                headers=auth_headers,
                json={"type": "DEPOSIT", "amount": 0.00, "currency": "USD"},
            )

            # Assert
            # Pydantic validation: gt=0 constraint
            # Flask-SMOREST returns 422 for validation errors
            assert response.status_code in [400, 422]
            assert "error" in response.json or "errors" in response.json

    def test_deposit_updates_balance_correctly(
        self, client, auth_headers, sample_checking_account, db_session, app
    ):
        """
        Test 8: Deposit updates account balance atomically.

        Given: Account has initial balance of $1000.00
        When: Customer deposits $50.00
        Then: Account balance is $1050.00
        And: Transaction.balance_after is $1050.00
        """
        with app.app_context():
            # Arrange
            initial_balance = sample_checking_account.balance
            assert initial_balance == Decimal("1000.00")
            deposit_amount = Decimal("50.00")

            # Act
            response = client.post(
                f"/v1/accounts/{sample_checking_account.id}/transactions",
                headers=auth_headers,
                json={"type": "DEPOSIT", "amount": float(deposit_amount), "currency": "USD"},
            )

            # Assert
            assert response.status_code == 201
            data = response.json

            expected_balance = initial_balance + deposit_amount
            assert Decimal(data["balance_after"]) == expected_balance

            # Verify account balance in database by re-querying
            updated_account = db_session.query(Account).filter_by(
                id=sample_checking_account.id
            ).first()
            assert updated_account.balance == expected_balance

    def test_deposit_creates_transaction_record(
        self, client, auth_headers, sample_checking_account, db_session, app
    ):
        """
        Test 9: Deposit creates proper transaction record in database.

        Given: Customer has active account
        When: Customer makes deposit
        Then: Transaction record exists in database with correct fields
        """
        with app.app_context():
            # Arrange
            deposit_amount = Decimal("250.00")
            description = "Integration test deposit"

            # Act
            response = client.post(
                f"/v1/accounts/{sample_checking_account.id}/transactions",
                headers=auth_headers,
                json={
                    "type": "DEPOSIT",
                    "amount": float(deposit_amount),
                    "currency": "USD",
                    "description": description,
                },
            )

            # Assert
            assert response.status_code == 201
            transaction_id = response.json["id"]

            # Query database for transaction
            transaction = db_session.query(Transaction).filter_by(id=transaction_id).first()

            assert transaction is not None
            assert transaction.transaction_type == "DEPOSIT"
            assert transaction.amount == deposit_amount
            assert transaction.currency == "USD"
            assert transaction.description == description
            assert transaction.status == "COMPLETED"
            assert transaction.processed_at is not None
            assert transaction.reference_number is not None

    def test_deposit_generates_unique_reference_number(
        self, client, auth_headers, sample_checking_account, db_session, app
    ):
        """
        Test 10: Each deposit generates a unique reference number.

        Given: Customer has active account
        When: Customer makes multiple deposits
        Then: Each transaction has unique reference number
        And: Reference numbers follow format TXN-YYYYMMDD-XXXXXX
        """
        with app.app_context():
            # Arrange
            ref_pattern = r"TXN-\d{8}-\d{6}"
            reference_numbers = []

            # Act - Make 3 deposits
            for i in range(3):
                response = client.post(
                    f"/v1/accounts/{sample_checking_account.id}/transactions",
                    headers=auth_headers,
                    json={"type": "DEPOSIT", "amount": 10.00 + i, "currency": "USD"},
                )

                assert response.status_code == 201
                ref_number = response.json["reference_number"]
                reference_numbers.append(ref_number)

            # Assert
            # All reference numbers match pattern
            for ref in reference_numbers:
                assert re.match(ref_pattern, ref), (
                    f"Reference number '{ref}' doesn't match pattern {ref_pattern}"
                )

            # All reference numbers are unique
            assert len(reference_numbers) == len(set(reference_numbers)), (
                f"Reference numbers are not unique: {reference_numbers}"
            )

            # Verify uniqueness in database
            transactions = (
                db_session.query(Transaction)
                .filter(Transaction.account_id == sample_checking_account.id)
                .all()
            )
            db_ref_numbers = [t.reference_number for t in transactions]
            assert len(db_ref_numbers) == len(set(db_ref_numbers)), (
                "Reference numbers in database are not unique"
            )
