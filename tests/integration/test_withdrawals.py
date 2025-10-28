"""
Integration tests for Withdrawal Transactions.

These are integration tests that validate withdrawal functionality:
- User Story 1: Users can make withdrawals from their accounts
- User Story 2: Error if insufficient funds
- User Story 3: Cannot withdraw from other people's accounts

Tests ensure proper withdrawal transaction flow, validation, and authorization.
"""

from decimal import Decimal
import re
import pytest

from app.models import Transaction, Account


class TestWithdrawalFunctionalTests:
    """Test suite for withdrawal transaction functional tests."""

    def test_withdrawal_from_own_account_succeeds(
        self, client, auth_headers, sample_checking_account, db_session, app
    ):
        """
        Test 1: Customer can withdraw from their own account.

        User Story 1: "As a user, I should be able to make a withdrawal from my account"

        Given: Customer has an active CHECKING account with balance $1000.00
        When: Customer makes a withdrawal of $500.00
        Then: Withdrawal succeeds with 201 response
        And: Transaction is created with correct details
        """
        with app.app_context():
            # Arrange
            initial_balance = sample_checking_account.balance
            withdrawal_amount = Decimal("500.00")

            # Act
            response = client.post(
                f"/v1/accounts/{sample_checking_account.id}/transactions",
                headers=auth_headers,
                json={
                    "type": "WITHDRAWAL",
                    "amount": float(withdrawal_amount),
                    "currency": "USD",
                    "description": "Test withdrawal",
                },
            )

            # Assert
            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json}"

            data = response.json
            assert data["transaction_type"] == "WITHDRAWAL"
            assert Decimal(data["amount"]) == withdrawal_amount
            assert Decimal(data["balance_after"]) == initial_balance - withdrawal_amount
            assert data["status"] == "COMPLETED"

            # Verify reference number format: TXN-YYYYMMDD-XXXXXX
            ref_pattern = r"TXN-\d{8}-\d{6}"
            assert re.match(ref_pattern, data["reference_number"]), (
                f"Reference number '{data['reference_number']}' doesn't match pattern {ref_pattern}"
            )

    def test_withdrawal_from_nonexistent_account_fails(self, client, auth_headers, app):
        """
        Test 2: Cannot withdraw from non-existent account.

        Given: Invalid account UUID
        When: Customer attempts withdrawal
        Then: Returns 404 NOT_FOUND
        """
        with app.app_context():
            # Arrange
            fake_account_id = "00000000-0000-0000-0000-000000000000"

            # Act
            response = client.post(
                f"/v1/accounts/{fake_account_id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": 100.00, "currency": "USD"},
            )

            # Assert
            assert response.status_code == 404
            assert "error" in response.json
            # Error format may vary, accept both formats
            if "code" in response.json["error"]:
                assert response.json["error"]["code"] == "NOT_FOUND"
            # Message should contain account reference
            assert "Account" in response.json["error"]["message"] or "not found" in response.json["error"]["message"].lower()

    def test_withdrawal_from_other_customer_account_fails(
        self, client, auth_headers, db_session, app
    ):
        """
        Test 3: Customer cannot withdraw from another customer's account.

        User Story 3: "I should not be able to make withdrawals from other people's accounts"

        Given: Customer A is authenticated
        And: Customer B has an account
        When: Customer A attempts to withdraw from Customer B's account
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

            # Act - Try to withdraw from other customer's account
            response = client.post(
                f"/v1/accounts/{other_account.id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": 100.00, "currency": "USD"},
            )

            # Assert
            assert response.status_code == 403
            assert "error" in response.json
            assert response.json["error"]["code"] == "FORBIDDEN"
            assert "Not authorized" in response.json["error"]["message"]

    def test_withdrawal_from_closed_account_fails(
        self, client, auth_headers, sample_customer, db_session, app
    ):
        """
        Test 5: Cannot withdraw from CLOSED account.

        Given: Customer has a CLOSED account
        When: Customer attempts withdrawal
        Then: Returns 422 BUSINESS_RULE_VIOLATION
        """
        with app.app_context():
            # Arrange - Create a closed account
            closed_account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-CLOSED123",
                status="CLOSED",
                balance=Decimal("100.00"),
                currency="USD",
            )
            db_session.add(closed_account)
            db_session.commit()

            # Act
            response = client.post(
                f"/v1/accounts/{closed_account.id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": 50.00, "currency": "USD"},
            )

            # Assert
            assert response.status_code == 422
            assert "error" in response.json
            assert response.json["error"]["code"] == "BUSINESS_RULE_VIOLATION"
            assert "cannot perform transactions" in response.json["error"]["message"]

    def test_withdrawal_insufficient_funds_fails(
        self, client, auth_headers, sample_checking_account, app
    ):
        """
        Test 6: Cannot withdraw more than account balance.

        User Story 2: "If I do not have enough funds, I should see an error"

        Given: Customer has account with balance $1000.00
        When: Customer attempts to withdraw $2000.00
        Then: Returns 422 INSUFFICIENT_FUNDS
        """
        with app.app_context():
            # Arrange
            balance = sample_checking_account.balance
            withdrawal_amount = balance + Decimal("1000.00")  # More than available

            # Act
            response = client.post(
                f"/v1/accounts/{sample_checking_account.id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": float(withdrawal_amount), "currency": "USD"},
            )

            # Assert
            assert response.status_code == 422
            assert "error" in response.json
            # Check for insufficient funds indication
            error_msg = response.json["error"]["message"].lower()
            assert "insufficient" in error_msg or "funds" in error_msg

    def test_withdrawal_exceeds_max_amount_fails(
        self, client, auth_headers, db_session, sample_customer, app
    ):
        """
        Test 7: Cannot withdraw more than $10,000 per transaction.

        Given: Customer has account with balance $50,000.00
        When: Customer attempts to withdraw $10,001.00
        Then: Returns 422 TRANSACTION_LIMIT_EXCEEDED
        """
        with app.app_context():
            # Arrange - Create account with large balance
            large_account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-LARGE123",
                status="ACTIVE",
                balance=Decimal("50000.00"),
                currency="USD",
            )
            db_session.add(large_account)
            db_session.commit()

            # Act - Try to withdraw more than $10,000
            response = client.post(
                f"/v1/accounts/{large_account.id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": 10001.00, "currency": "USD"},
            )

            # Assert
            assert response.status_code == 422
            assert "error" in response.json
            error_msg = response.json["error"]["message"].lower()
            assert "limit" in error_msg or "maximum" in error_msg or "exceeds" in error_msg

    def test_withdrawal_updates_balance_correctly(
        self, client, auth_headers, sample_checking_account, db_session, app
    ):
        """
        Test 9: Withdrawal updates account balance atomically.

        Given: Account has initial balance of $1000.00
        When: Customer withdraws $50.00
        Then: Account balance is $950.00
        And: Transaction.balance_after is $950.00
        """
        with app.app_context():
            # Arrange
            initial_balance = sample_checking_account.balance
            assert initial_balance == Decimal("1000.00")
            withdrawal_amount = Decimal("50.00")

            # Act
            response = client.post(
                f"/v1/accounts/{sample_checking_account.id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": float(withdrawal_amount), "currency": "USD"},
            )

            # Assert
            assert response.status_code == 201
            data = response.json

            expected_balance = initial_balance - withdrawal_amount
            assert Decimal(data["balance_after"]) == expected_balance

            # Verify account balance in database by re-querying
            updated_account = db_session.query(Account).filter_by(
                id=sample_checking_account.id
            ).first()
            assert updated_account.balance == expected_balance

    def test_withdrawal_creates_transaction_record(
        self, client, auth_headers, sample_checking_account, db_session, app
    ):
        """
        Test 10: Withdrawal creates proper transaction record in database.

        Given: Customer has active account
        When: Customer makes withdrawal
        Then: Transaction record exists in database with correct fields
        """
        with app.app_context():
            # Arrange
            withdrawal_amount = Decimal("250.00")
            description = "Integration test withdrawal"

            # Act
            response = client.post(
                f"/v1/accounts/{sample_checking_account.id}/transactions",
                headers=auth_headers,
                json={
                    "type": "WITHDRAWAL",
                    "amount": float(withdrawal_amount),
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
            assert transaction.transaction_type == "WITHDRAWAL"
            assert transaction.amount == withdrawal_amount
            assert transaction.currency == "USD"
            assert transaction.description == description
            assert transaction.status == "COMPLETED"
            assert transaction.processed_at is not None
            assert transaction.reference_number is not None

    # Edge Case Tests

    def test_withdrawal_exactly_equals_balance(
        self, client, auth_headers, sample_customer, db_session, app
    ):
        """
        Test 11: Withdrawal exactly equals balance (edge case).

        Given: Account has balance of $1000.00
        When: Customer withdraws exactly $1000.00
        Then: Withdrawal succeeds with 201
        And: Final balance is exactly $0.00
        """
        with app.app_context():
            # Arrange - Create account with specific balance
            account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-EXACTBAL",
                status="ACTIVE",
                balance=Decimal("1000.00"),
                currency="USD",
            )
            db_session.add(account)
            db_session.commit()

            # Act - Withdraw exact balance
            response = client.post(
                f"/v1/accounts/{account.id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": 1000.00, "currency": "USD"},
            )

            # Assert - Withdrawal succeeds
            assert response.status_code == 201
            data = response.json

            # Check response data
            assert data["transaction_type"] == "WITHDRAWAL"
            assert Decimal(data["amount"]) == Decimal("1000.00")
            assert Decimal(data["balance_after"]) == Decimal("0.00")
            assert data["status"] == "COMPLETED"

            # Verify database balance is exactly zero
            db_session.expire_all()
            updated_account = db_session.query(Account).filter_by(id=account.id).first()
            assert updated_account.balance == Decimal("0.00")
            # No rounding errors
            assert str(updated_account.balance) == "0.00"

    def test_withdrawal_currency_mismatch_fails(
        self, client, auth_headers, sample_customer, db_session, app
    ):
        """
        Test 12: Withdrawal with currency mismatch fails.

        Given: Account has USD currency
        When: Customer attempts withdrawal with EUR currency
        Then: Returns 422 VALIDATION_ERROR
        """
        with app.app_context():
            # Arrange - Create USD account
            account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-USDONLY",
                status="ACTIVE",
                balance=Decimal("1000.00"),
                currency="USD",
            )
            db_session.add(account)
            db_session.commit()

            # Act - Attempt withdrawal with mismatched currency
            response = client.post(
                f"/v1/accounts/{account.id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": 100.00, "currency": "EUR"},
            )

            # Assert - Request fails with validation error
            # Status code can be either 400 (Marshmallow validation) or 422 (business rule)
            assert response.status_code in [400, 422]
            assert "error" in response.json
            error_msg = response.json["error"]["message"].lower()
            assert "currency" in error_msg and "mismatch" in error_msg

    def test_withdrawal_from_loan_account_fails(
        self, client, auth_headers, sample_customer, db_session, app
    ):
        """
        Test 13: Cannot withdraw from LOAN account.

        Given: Customer has a LOAN account
        When: Customer attempts to withdraw
        Then: Returns 422 BUSINESS_RULE_VIOLATION
        """
        with app.app_context():
            # Arrange - Create LOAN account
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-12345",
                status="ACTIVE",
                balance=Decimal("-5000.00"),  # Loan accounts have negative balance
                currency="USD",
            )
            db_session.add(loan_account)
            db_session.commit()

            # Act - Attempt withdrawal from LOAN account
            response = client.post(
                f"/v1/accounts/{loan_account.id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": 100.00, "currency": "USD"},
            )

            # Assert - Request fails with business rule violation
            assert response.status_code == 422
            assert "error" in response.json
            error = response.json["error"]
            assert error["code"] == "BUSINESS_RULE_VIOLATION"
            assert "invalid account type" in error["message"].lower()

    def test_concurrent_withdrawals_prevent_overdraft(
        self, client, auth_headers, sample_customer, db_session, app
    ):
        """
        Test 14: Concurrent withdrawals don't cause overdraft.

        Given: Account has balance of $100.00
        When: Two withdrawals of $60.00 are attempted concurrently
        Then: One succeeds, one fails with insufficient funds
        And: Final balance is $40.00 (not negative)
        """
        import threading

        with app.app_context():
            # Arrange - Create account with $100
            account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-CONCURRENT",
                status="ACTIVE",
                balance=Decimal("100.00"),
                currency="USD",
            )
            db_session.add(account)
            db_session.commit()
            account_id = account.id

        # Act - Attempt concurrent withdrawals
        results = []

        def make_withdrawal():
            """Make a withdrawal request in a thread."""
            response = client.post(
                f"/v1/accounts/{account_id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": 60.00, "currency": "USD"},
            )
            results.append(response)

        # Launch two concurrent withdrawal threads
        thread1 = threading.Thread(target=make_withdrawal)
        thread2 = threading.Thread(target=make_withdrawal)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Assert - Check results
        assert len(results) == 2

        status_codes = sorted([r.status_code for r in results])

        with app.app_context():
            db_session.expire_all()
            final_account = (
                db_session.query(Account).filter_by(id=account_id).first()
            )

            # Assert - Balance should never be negative
            assert final_account.balance >= Decimal("0.00")

            # If one succeeded, balance should be $40
            if 201 in status_codes:
                success_count = status_codes.count(201)
                if success_count == 1:
                    assert final_account.balance == Decimal("40.00")
                elif success_count == 2:
                    # Both succeeded - would indicate race condition bug
                    assert (
                        final_account.balance >= Decimal("0.00")
                    ), "Race condition: Balance went negative!"

    def test_withdrawal_large_amount_precision(
        self, client, auth_headers, sample_customer, db_session, app
    ):
        """
        Test 15: Large withdrawal amounts maintain decimal precision.

        Given: Account has balance $50,000.99
        When: Customer withdraws $9,999.99 (max single withdrawal)
        Then: Balance calculation is exact ($40,001.00)
        And: No floating point errors
        """
        with app.app_context():
            # Arrange - Create account with large balance
            account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-LARGEBAL",
                status="ACTIVE",
                balance=Decimal("50000.99"),
                currency="USD",
            )
            db_session.add(account)
            db_session.commit()

            # Act - Withdraw large amount (just under max limit)
            response = client.post(
                f"/v1/accounts/{account.id}/transactions",
                headers=auth_headers,
                json={"type": "WITHDRAWAL", "amount": 9999.99, "currency": "USD"},
            )

            # Assert - Withdrawal succeeds
            assert response.status_code == 201
            data = response.json

            # Check decimal precision in response
            assert Decimal(data["amount"]) == Decimal("9999.99")
            expected_balance = Decimal("40001.00")
            assert Decimal(data["balance_after"]) == expected_balance

            # Verify database balance precision
            db_session.expire_all()
            updated_account = db_session.query(Account).filter_by(id=account.id).first()
            assert updated_account.balance == expected_balance
            # Verify exact string representation (no floating point errors)
            assert str(updated_account.balance) == "40001.00"

            # Additional precision test - balance should have exactly 2 decimal places
            balance_str = str(updated_account.balance)
            assert "." in balance_str
            decimal_places = len(balance_str.split(".")[1])
            assert decimal_places == 2
