"""
Integration tests for BankService with Bank Capital + Fractional Reserve Model.

These are integration tests (not unit tests) because they:
- Use a real PostgreSQL database (not mocked)
- Execute actual SQL queries via SQLAlchemy
- Test the service layer integrated with the data layer

Tests validate the business logic formula:
Available for Lending = Bank Capital + (0.25 × Deposits) - Loans Outstanding

Where:
- Bank Capital = $250,000 (static)
- Reserve Ratio = 0.25 (can use 25% of deposits)
- Customer Deposits = Sum of ACTIVE checking balances
- Loans Outstanding = |Sum of ACTIVE loan balances|
"""

from decimal import Decimal
from datetime import datetime

from app.services.bank_service import BankService
from app.models import Account, Customer


class TestBankService:
    """Test suite for BankService class with capital model."""

    def test_bank_service_initialization(self, db_session):
        """Test BankService can be instantiated with a database session."""
        service = BankService(db_session)

        assert service is not None
        assert service.db == db_session

    def test_get_bank_capital_returns_250k(self, db_session, app):
        """
        Test get_bank_capital returns $250,000.

        Bank starts with $250k capital (static for MVP).
        """
        with app.app_context():
            service = BankService(db_session)
            capital = service.get_bank_capital()

            assert capital == Decimal("250000.00")
            assert isinstance(capital, Decimal)

    def test_get_available_for_lending_with_no_accounts(self, db_session, app):
        """
        Test get_available_for_lending with no accounts.

        Scenario: Empty bank with no customers
        Formula: $250,000 + (0.25 × $0) - $0 = $250,000
        Expected: Returns Decimal('250000.00')
        """
        with app.app_context():
            service = BankService(db_session)
            available = service.get_available_for_lending()

            assert available == Decimal("250000.00")
            assert isinstance(available, Decimal)

    def test_get_available_for_lending_with_checking_accounts_only(
        self, db_session, sample_customer, app
    ):
        """
        Test get_available_for_lending with only checking accounts.

        Scenario: Bank with 3 checking accounts, no loans
        Setup: Accounts with balances $1000, $2000, $3000 (total $6000)
        Formula: $250,000 + (0.25 × $6,000) - $0 = $251,500
        Expected: Returns Decimal('251500.00')
        """
        with app.app_context():
            # Arrange
            accounts = [
                Account(
                    customer_id=sample_customer.id,
                    account_type="CHECKING",
                    account_number=f"CHK-TEST-{i}",
                    status="ACTIVE",
                    balance=Decimal(str(amount)),
                    currency="USD",
                )
                for i, amount in enumerate([1000, 2000, 3000], 1)
            ]

            for account in accounts:
                db_session.add(account)
            db_session.commit()

            service = BankService(db_session)

            # Act
            available = service.get_available_for_lending()

            # Assert
            # Bank capital: $250k
            # Deposits: $6k, usable: $1.5k (25%)
            # Loans: $0
            # Available: $250k + $1.5k - $0 = $251.5k
            assert available == Decimal("251500.00")
            assert isinstance(available, Decimal)

    def test_get_available_for_lending_with_loan_accounts_only(
        self, db_session, sample_customer, app
    ):
        """
        Test get_available_for_lending with only loan accounts.

        Scenario: Bank with 2 loan accounts, no checking
        Setup: Loans with balances -$10,000, -$15,000 (total -$25,000)
        Formula: $250,000 + (0.25 × $0) - $25,000 = $225,000
        Expected: Returns Decimal('225000.00')
        """
        with app.app_context():
            # Arrange
            accounts = [
                Account(
                    customer_id=sample_customer.id,
                    account_type="LOAN",
                    account_number=f"LOAN-TEST-{i}",
                    status="ACTIVE",
                    balance=Decimal(str(amount)),
                    currency="USD",
                )
                for i, amount in enumerate([-10000, -15000], 1)
            ]

            for account in accounts:
                db_session.add(account)
            db_session.commit()

            service = BankService(db_session)

            # Act
            available = service.get_available_for_lending()

            # Assert
            # Bank capital: $250k
            # Deposits: $0, usable: $0
            # Loans: $25k
            # Available: $250k + $0 - $25k = $225k
            assert available == Decimal("225000.00")
            assert isinstance(available, Decimal)

    def test_get_available_for_lending_with_mixed_accounts(self, db_session, sample_customer, app):
        """
        Test get_available_for_lending with both checking and loan accounts.

        Scenario: Bank with checking and loan accounts
        Setup: Checking = $150k, Loans = -$200k
        Formula: $250,000 + (0.25 × $150,000) - $200,000 = $87,500
        Expected: Returns Decimal('87500.00')
        """
        with app.app_context():
            # Arrange
            checking = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-MIXED",
                status="ACTIVE",
                balance=Decimal("150000.00"),
                currency="USD",
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-MIXED",
                status="ACTIVE",
                balance=Decimal("-200000.00"),
                currency="USD",
            )

            db_session.add(checking)
            db_session.add(loan)
            db_session.commit()

            service = BankService(db_session)

            # Act
            available = service.get_available_for_lending()

            # Assert
            # Bank capital: $250k
            # Deposits: $150k, usable: $37.5k (25%)
            # Loans: $200k
            # Available: $250k + $37.5k - $200k = $87.5k
            assert available == Decimal("87500.00")
            assert isinstance(available, Decimal)

    def test_get_available_for_lending_bank_overextended(self, db_session, sample_customer, app):
        """
        Test get_available_for_lending when bank is overextended.

        Scenario: Loans exceed capital + usable deposits
        Setup: Deposits = $100k, Loans = $300k
        Formula: $250,000 + (0.25 × $100,000) - $300,000 = -$25,000
        Expected: Returns Decimal('-25000.00') (negative = overextended)
        """
        with app.app_context():
            # Arrange
            checking = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-OVER",
                status="ACTIVE",
                balance=Decimal("100000.00"),
                currency="USD",
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-OVER",
                status="ACTIVE",
                balance=Decimal("-300000.00"),
                currency="USD",
            )

            db_session.add(checking)
            db_session.add(loan)
            db_session.commit()

            service = BankService(db_session)

            # Act
            available = service.get_available_for_lending()

            # Assert
            # Bank capital: $250k
            # Deposits: $100k, usable: $25k (25%)
            # Loans: $300k
            # Available: $250k + $25k - $300k = -$25k (overextended!)
            assert available == Decimal("-25000.00")
            assert isinstance(available, Decimal)
            assert available < 0  # Bank is overextended

    def test_get_available_for_lending_decimal_precision(self, db_session, sample_customer, app):
        """
        Test get_available_for_lending maintains decimal precision.

        Scenario: Accounts with fractional cents
        Setup: Checking = $1,234.56, Loan = -$5,678.90
        Formula: $250,000 + (0.25 × $1,234.56) - $5,678.90 = $244,629.74
        Expected: Returns Decimal('244629.74') with exact 2 decimal places
        """
        with app.app_context():
            # Arrange
            checking = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-DECIMAL",
                status="ACTIVE",
                balance=Decimal("1234.56"),
                currency="USD",
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-DECIMAL",
                status="ACTIVE",
                balance=Decimal("-5678.90"),
                currency="USD",
            )

            db_session.add(checking)
            db_session.add(loan)
            db_session.commit()

            service = BankService(db_session)

            # Act
            available = service.get_available_for_lending()

            # Assert
            # Bank capital: $250,000
            # Deposits: $1,234.56, usable: $308.64 (25%)
            # Loans: $5,678.90
            # Available: $250,000 + $308.64 - $5,678.90 = $244,629.74
            assert available == Decimal("244629.74")
            assert isinstance(available, Decimal)

    def test_get_bank_financial_status_returns_complete_dict(
        self, db_session, sample_customer, app
    ):
        """
        Test get_bank_financial_status returns a complete dictionary with new fields.

        Scenario: Bank with mixed accounts
        Setup: 2 checking accounts ($5000 total), 1 loan account (-$10000)
        Expected: Dict with all required keys and correct values
        """
        with app.app_context():
            # Arrange
            checking1 = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-STATUS-1",
                status="ACTIVE",
                balance=Decimal("3000.00"),
                currency="USD",
            )
            checking2 = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-STATUS-2",
                status="ACTIVE",
                balance=Decimal("2000.00"),
                currency="USD",
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-STATUS-1",
                status="ACTIVE",
                balance=Decimal("-10000.00"),
                currency="USD",
            )

            db_session.add_all([checking1, checking2, loan])
            db_session.commit()

            service = BankService(db_session)

            # Act
            status = service.get_bank_financial_status()

            # Assert - Check all required keys exist
            assert "bank_capital" in status
            assert "total_customer_deposits" in status
            assert "usable_customer_deposits" in status
            assert "reserved_deposits" in status
            assert "total_loans_outstanding" in status
            assert "available_for_lending" in status
            assert "is_overextended" in status
            assert "account_breakdown" in status
            assert "as_of" in status

            # Assert - Check values are correct
            # Deposits: $5000
            # Usable: $1250 (25%)
            # Reserved: $3750 (75%)
            # Loans: $10000
            # Available: $250k + $1250 - $10000 = $241,250
            assert status["bank_capital"] == Decimal("250000.00")
            assert status["total_customer_deposits"] == Decimal("5000.00")
            assert status["usable_customer_deposits"] == Decimal("1250.00")
            assert status["reserved_deposits"] == Decimal("3750.00")
            assert status["total_loans_outstanding"] == Decimal("10000.00")
            assert status["available_for_lending"] == Decimal("241250.00")
            assert status["is_overextended"] == False

            # Assert - Check account breakdown structure
            assert "total_checking_accounts" in status["account_breakdown"]
            assert "total_loan_accounts" in status["account_breakdown"]
            assert "active_accounts" in status["account_breakdown"]

            # Assert - as_of is a datetime
            assert isinstance(status["as_of"], datetime)

    def test_get_bank_financial_status_account_breakdown_accuracy(
        self, db_session, sample_customer, app
    ):
        """
        Test get_bank_financial_status returns accurate account counts.

        Scenario: Bank with specific number of accounts
        Setup: 10 ACTIVE checking, 5 ACTIVE loans
        Expected: Counts match exactly
        """
        with app.app_context():
            # Arrange - Create 10 checking accounts
            checking_accounts = [
                Account(
                    customer_id=sample_customer.id,
                    account_type="CHECKING",
                    account_number=f"CHK-COUNT-{i}",
                    status="ACTIVE",
                    balance=Decimal("1000.00"),
                    currency="USD",
                )
                for i in range(10)
            ]

            # Create 5 loan accounts
            loan_accounts = [
                Account(
                    customer_id=sample_customer.id,
                    account_type="LOAN",
                    account_number=f"LOAN-COUNT-{i}",
                    status="ACTIVE",
                    balance=Decimal("-5000.00"),
                    currency="USD",
                )
                for i in range(5)
            ]

            db_session.add_all(checking_accounts + loan_accounts)
            db_session.commit()

            service = BankService(db_session)

            # Act
            status = service.get_bank_financial_status()

            # Assert - Check exact counts
            assert status["account_breakdown"]["total_checking_accounts"] == 10
            assert status["account_breakdown"]["total_loan_accounts"] == 5
            assert status["account_breakdown"]["active_accounts"] == 15

    def test_can_approve_loan_with_sufficient_funds(self, db_session, sample_customer, app):
        """
        Test can_approve_loan returns True when bank has sufficient funds.

        Scenario: Bank has $250k capital, no loans
        Request: $50k loan
        Formula: $250,000 + $0 - $0 = $250,000 available
        Expected: Returns (True, success message)
        """
        with app.app_context():
            # Arrange - Empty bank has $250k capital
            service = BankService(db_session)

            # Act
            can_approve, reason = service.can_approve_loan(Decimal("50000.00"))

            # Assert
            assert can_approve is True
            assert "sufficient" in reason.lower() or "available" in reason.lower()
            assert "250000.00" in reason  # Current available
            assert "200000.00" in reason  # After loan

    def test_can_approve_loan_with_insufficient_funds(self, db_session, sample_customer, app):
        """
        Test can_approve_loan returns False when bank has insufficient funds.

        Scenario: Bank has large loans already
        Setup: Deposits = $100k, Loans = $270k
        Formula: $250k + $25k - $270k = $5k available
        Request: $10k loan (exceeds available)
        Expected: Returns (False, detailed error message)
        """
        with app.app_context():
            # Arrange - Create accounts so available = $5k
            checking = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-INSUFFICIENT",
                status="ACTIVE",
                balance=Decimal("100000.00"),
                currency="USD",
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-INSUFFICIENT",
                status="ACTIVE",
                balance=Decimal("-270000.00"),
                currency="USD",
            )

            db_session.add_all([checking, loan])
            db_session.commit()

            service = BankService(db_session)

            # Act
            can_approve, reason = service.can_approve_loan(Decimal("10000.00"))

            # Assert
            assert can_approve is False
            assert "insufficient" in reason.lower()
            assert "5000.00" in reason  # Available amount
            assert "10000.00" in reason  # Requested amount

    def test_can_approve_loan_exact_amount(self, db_session, sample_customer, app):
        """
        Test can_approve_loan with exact amount (edge case).

        Scenario: Bank has exactly $50k available
        Setup: Deposits = $100k, Loans = $225k
        Formula: $250k + $25k - $225k = $50k available
        Request: $50k loan (exact match)
        Expected: Returns (True, ...) - bank goes to exactly $0
        """
        with app.app_context():
            # Arrange - Create accounts so available = exactly $50k
            checking = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-EXACT",
                status="ACTIVE",
                balance=Decimal("100000.00"),
                currency="USD",
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-EXACT",
                status="ACTIVE",
                balance=Decimal("-225000.00"),
                currency="USD",
            )

            db_session.add_all([checking, loan])
            db_session.commit()

            service = BankService(db_session)

            # Act
            can_approve, reason = service.can_approve_loan(Decimal("50000.00"))

            # Assert - Should approve (bank goes to $0, which is >= 0)
            assert can_approve is True
            assert "0.00" in reason or "0" in reason  # After loan amount should be 0

    def test_can_approve_loan_when_bank_overextended(self, db_session, sample_customer, app):
        """
        Test can_approve_loan when bank is already overextended.

        Scenario: Bank already has more loans than capital + reserves
        Setup: Deposits = $100k, Loans = $280k
        Formula: $250k + $25k - $280k = -$5k (overextended!)
        Request: $5k loan
        Expected: Returns (False, ...) - cannot approve when overextended
        """
        with app.app_context():
            # Arrange - Create accounts so bank is overextended by $5k
            checking = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-OVER",
                status="ACTIVE",
                balance=Decimal("100000.00"),
                currency="USD",
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-OVER",
                status="ACTIVE",
                balance=Decimal("-280000.00"),
                currency="USD",
            )

            db_session.add_all([checking, loan])
            db_session.commit()

            service = BankService(db_session)

            # Verify bank is overextended first
            available = service.get_available_for_lending()
            assert available < 0  # Sanity check: -$5k

            # Act
            can_approve, reason = service.can_approve_loan(Decimal("5000.00"))

            # Assert - Cannot approve when already overextended
            assert can_approve is False
            assert "insufficient" in reason.lower()

    def test_get_available_for_lending_large_numbers(self, db_session, sample_customer, app):
        """
        Test get_available_for_lending with large balances (>$1M).

        Scenario: Large deposits and loans
        Setup: Deposits = $2M, Loans = $400k
        Formula: $250k + (0.25 × $2M) - $400k = $350k
        Expected: Correct calculation with large numbers
        """
        with app.app_context():
            # Arrange
            checking = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-LARGE",
                status="ACTIVE",
                balance=Decimal("2000000.00"),
                currency="USD",
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-LARGE",
                status="ACTIVE",
                balance=Decimal("-400000.00"),
                currency="USD",
            )

            db_session.add_all([checking, loan])
            db_session.commit()

            service = BankService(db_session)

            # Act
            available = service.get_available_for_lending()

            # Assert
            # Bank capital: $250k
            # Deposits: $2M, usable: $500k (25%)
            # Loans: $400k
            # Available: $250k + $500k - $400k = $350k
            assert available == Decimal("350000.00")
            assert isinstance(available, Decimal)

    def test_get_available_for_lending_many_accounts(self, db_session, sample_customer, app):
        """
        Test get_available_for_lending with many accounts (100+).

        Scenario: Bank efficiently aggregates large number of accounts
        Setup: 50 checking accounts ($1k each), 75 loan accounts ($2k each)
        Formula: $250k + (0.25 × $50k) - $150k = $112.5k
        Expected: Correct aggregation across many accounts
        """
        with app.app_context():
            # Arrange - Create 50 checking accounts
            checking_accounts = [
                Account(
                    customer_id=sample_customer.id,
                    account_type="CHECKING",
                    account_number=f"CHK-MANY-{i:04d}",
                    status="ACTIVE",
                    balance=Decimal("1000.00"),
                    currency="USD",
                )
                for i in range(50)
            ]

            # Create 75 loan accounts
            loan_accounts = [
                Account(
                    customer_id=sample_customer.id,
                    account_type="LOAN",
                    account_number=f"LOAN-MANY-{i:04d}",
                    status="ACTIVE",
                    balance=Decimal("-2000.00"),
                    currency="USD",
                )
                for i in range(75)
            ]

            db_session.add_all(checking_accounts + loan_accounts)
            db_session.commit()

            service = BankService(db_session)

            # Act
            available = service.get_available_for_lending()

            # Assert
            # Total checking: 50 * $1000 = $50,000
            # Usable: 25% = $12,500
            # Total loans: 75 * $2000 = $150,000
            # Available: $250k + $12.5k - $150k = $112.5k
            assert available == Decimal("112500.00")
            assert isinstance(available, Decimal)

    def test_can_approve_loan_zero_amount(self, db_session, app):
        """
        Test can_approve_loan with zero amount (edge case).

        Scenario: Request to approve $0 loan
        Expected: Should approve (no impact on reserves)
        """
        with app.app_context():
            service = BankService(db_session)

            # Act
            can_approve, reason = service.can_approve_loan(Decimal("0.00"))

            # Assert - Should approve $0 loan
            assert can_approve is True

    def test_can_approve_loan_exact_bank_cash_match(self, db_session, sample_customer, app):
        """
        Test can_approve_loan when requested amount exactly matches available.

        Scenario: Available = $112.5k exactly
        Setup: Deposits = $50k, Loans = $150k
        Formula: $250k + $12.5k - $150k = $112.5k
        Request: $112,500 (exact match)
        Expected: Approve (results in $0 available, which is valid)
        """
        with app.app_context():
            # Arrange
            checking = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-MATCH",
                status="ACTIVE",
                balance=Decimal("50000.00"),
                currency="USD",
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-MATCH",
                status="ACTIVE",
                balance=Decimal("-150000.00"),
                currency="USD",
            )

            db_session.add_all([checking, loan])
            db_session.commit()

            service = BankService(db_session)

            # Verify available is exactly $112.5k
            available = service.get_available_for_lending()
            assert available == Decimal("112500.00")

            # Act
            can_approve, reason = service.can_approve_loan(Decimal("112500.00"))

            # Assert
            assert can_approve is True
            assert "0.00" in reason  # After loan should be $0

    def test_backwards_compatibility_get_total_cash_on_hand(self, db_session, app):
        """
        Test that deprecated get_total_cash_on_hand() still works.

        It should return the same value as get_available_for_lending().
        """
        with app.app_context():
            service = BankService(db_session)

            # Both methods should return same value
            old_method = service.get_total_cash_on_hand()
            new_method = service.get_available_for_lending()

            assert old_method == new_method
            assert old_method == Decimal("250000.00")  # Empty bank
