"""
Integration tests for Single Account Per Customer Rule.

These are integration tests that validate the business rule:
- A customer can have only ONE open account at a time (any type)
- ACTIVE accounts block new account creation
- CLOSED accounts do NOT block new account creation
- Rule applies to ALL account types (CHECKING and LOAN)

Tests ensure AccountService.create_account() properly enforces the rule.
"""

from decimal import Decimal
from datetime import date
import pytest

from app.services.account_service import AccountService
from app.schemas.account import AccountCreateRequest
from app.models import Account, Customer
from app.exceptions import BusinessRuleViolationError, NotFoundError


class TestSingleAccountRule:
    """Test suite for single account per customer business rule."""

    def test_create_first_account_successfully(self, db_session, sample_customer, app):
        """
        Test: Create first account successfully (happy path).
        
        Scenario: Customer has no existing accounts
        Action: Create a CHECKING account
        Expected: Account created successfully with status ACTIVE
        """
        with app.app_context():
            # Arrange
            service = AccountService(db_session)
            account_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("100.00"),
                currency="USD"
            )
            
            # Act
            account = service.create_account(account_data, sample_customer.id)
            
            # Assert
            assert account is not None
            assert account.customer_id == sample_customer.id
            assert account.account_type == "CHECKING"
            assert account.status == "ACTIVE"
            assert account.balance == Decimal("100.00")
            assert account.account_number.startswith("CHK-")

    def test_cannot_create_second_checking_account_when_active_checking_exists(
        self, db_session, sample_customer, app
    ):
        """
        Test: Attempt to create second CHECKING account when ACTIVE CHECKING exists.
        
        Scenario: Customer has an existing ACTIVE CHECKING account
        Action: Attempt to create another CHECKING account
        Expected: BusinessRuleViolationError with proper message
        """
        with app.app_context():
            # Arrange - Create first account
            service = AccountService(db_session)
            first_account_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("100.00"),
                currency="USD"
            )
            first_account = service.create_account(first_account_data, sample_customer.id)
            
            # Act & Assert - Try to create second account
            second_account_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("50.00"),
                currency="USD"
            )
            
            with pytest.raises(BusinessRuleViolationError) as exc_info:
                service.create_account(second_account_data, sample_customer.id)
            
            # Verify error message contains correct details
            error_message = str(exc_info.value)
            assert "Customer already has an open checking account" in error_message
            assert first_account.account_number in error_message
            assert "Only one account per customer is allowed" in error_message

    def test_cannot_create_checking_account_when_active_loan_exists(
        self, db_session, sample_customer, app
    ):
        """
        Test: Attempt to create CHECKING account when ACTIVE LOAN exists.
        
        Scenario: Customer has an existing ACTIVE LOAN account
        Action: Attempt to create a CHECKING account
        Expected: BusinessRuleViolationError (single account rule applies across types)
        """
        with app.app_context():
            # Arrange - Create a LOAN account directly (simulating loan disbursement)
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-1234567890",
                status="ACTIVE",
                balance=Decimal("-25000.00"),
                currency="USD"
            )
            db_session.add(loan_account)
            db_session.commit()
            
            # Act & Assert - Try to create CHECKING account
            service = AccountService(db_session)
            checking_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("100.00"),
                currency="USD"
            )
            
            with pytest.raises(BusinessRuleViolationError) as exc_info:
                service.create_account(checking_data, sample_customer.id)
            
            # Verify error message
            error_message = str(exc_info.value)
            assert "Customer already has an open loan account" in error_message
            assert "LOAN-1234567890" in error_message

    def test_cannot_create_loan_account_when_active_checking_exists(
        self, db_session, sample_customer, app
    ):
        """
        Test: Attempt to create LOAN account when ACTIVE CHECKING exists.
        
        Scenario: Customer has an existing ACTIVE CHECKING account
        Action: Attempt to create a LOAN account
        Expected: BusinessRuleViolationError (single account rule applies across types)
        """
        with app.app_context():
            # Arrange - Create CHECKING account first
            service = AccountService(db_session)
            checking_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("100.00"),
                currency="USD"
            )
            checking_account = service.create_account(checking_data, sample_customer.id)
            
            # Act & Assert - Try to create LOAN account
            loan_data = AccountCreateRequest(
                account_type="LOAN",
                initial_deposit=None,
                currency="USD"
            )
            
            with pytest.raises(BusinessRuleViolationError) as exc_info:
                service.create_account(loan_data, sample_customer.id)
            
            # Verify error message
            error_message = str(exc_info.value)
            assert "Customer already has an open checking account" in error_message
            assert checking_account.account_number in error_message

    def test_can_create_account_after_closing_previous_account(
        self, db_session, sample_customer, app
    ):
        """
        Test: Create new account after closing previous account (CLOSED status).
        
        Scenario: 
        1. Customer has an account with zero balance
        2. Account is closed (status = CLOSED)
        3. Customer attempts to create a new account
        Expected: New account created successfully (CLOSED accounts don't block)
        """
        with app.app_context():
            # Arrange - Create first account with zero balance
            service = AccountService(db_session)
            first_account_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("0.00"),
                currency="USD"
            )
            first_account = service.create_account(first_account_data, sample_customer.id)
            
            # Close the first account
            closed_account = service.close_account(first_account.id)
            assert closed_account.status == "CLOSED"
            
            # Act - Create new account (should succeed)
            second_account_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("200.00"),
                currency="USD"
            )
            second_account = service.create_account(second_account_data, sample_customer.id)
            
            # Assert
            assert second_account is not None
            assert second_account.status == "ACTIVE"
            assert second_account.id != first_account.id
            assert second_account.account_number != first_account.account_number
            assert second_account.balance == Decimal("200.00")

    def test_error_message_contains_account_type_and_number(
        self, db_session, sample_customer, app
    ):
        """
        Test: Verify error message contains correct account type and number.
        
        Scenario: Customer has existing account, attempts to create another
        Expected: Error message includes:
        - Account type (checking/loan)
        - Account number
        - Clear explanation
        """
        with app.app_context():
            # Arrange - Create first account
            service = AccountService(db_session)
            first_account_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("100.00"),
                currency="USD"
            )
            first_account = service.create_account(first_account_data, sample_customer.id)
            
            # Act & Assert - Try to create second account
            second_account_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("50.00"),
                currency="USD"
            )
            
            with pytest.raises(BusinessRuleViolationError) as exc_info:
                service.create_account(second_account_data, sample_customer.id)
            
            error_message = str(exc_info.value)
            
            # Verify all required components in error message
            assert "checking" in error_message.lower()
            assert first_account.account_number in error_message
            assert "Only one account per customer is allowed" in error_message
            assert "Please close existing account" in error_message

    def test_closed_accounts_do_not_block_new_account_creation(
        self, db_session, sample_customer, app
    ):
        """
        Test: Verify CLOSED accounts don't block new account creation.
        
        Scenario: Customer has a CLOSED account
        Action: Create a new account
        Expected: New account created successfully
        """
        with app.app_context():
            # Arrange - Create a CLOSED account directly
            closed_account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-CLOSED001",
                status="CLOSED",
                balance=Decimal("0.00"),
                currency="USD"
            )
            db_session.add(closed_account)
            db_session.commit()
            
            # Act - Create new account (should succeed)
            service = AccountService(db_session)
            new_account_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("500.00"),
                currency="USD"
            )
            new_account = service.create_account(new_account_data, sample_customer.id)
            
            # Assert
            assert new_account is not None
            assert new_account.status == "ACTIVE"
            assert new_account.balance == Decimal("500.00")
            
            # Verify we now have 2 accounts (1 closed, 1 active)
            all_accounts = service.get_customer_accounts(sample_customer.id)
            assert len(all_accounts) == 2
            active_accounts = [a for a in all_accounts if a.status == "ACTIVE"]
            assert len(active_accounts) == 1

    def test_multiple_customers_can_each_have_one_account(
        self, db_session, app
    ):
        """
        Test: Multiple customers can each have their own account.
        
        Scenario: Two different customers each create one account
        Expected: Both accounts created successfully (rule is per-customer)
        """
        with app.app_context():
            # Arrange - Create two customers
            customer1 = Customer(
                email="customer1@example.com",
                first_name="Customer",
                last_name="One",
                date_of_birth=date(1990, 1, 1),
                phone="+1-555-0001",
                address_line_1="123 First St",
                city="Test City",
                state="CA",
                zip_code="12345",
                status="ACTIVE"
            )
            customer2 = Customer(
                email="customer2@example.com",
                first_name="Customer",
                last_name="Two",
                date_of_birth=date(1991, 2, 2),
                phone="+1-555-0002",
                address_line_1="456 Second St",
                city="Test City",
                state="CA",
                zip_code="12345",
                status="ACTIVE"
            )
            db_session.add(customer1)
            db_session.add(customer2)
            db_session.commit()
            
            # Act - Create account for each customer
            service = AccountService(db_session)
            
            account1_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("100.00"),
                currency="USD"
            )
            account1 = service.create_account(account1_data, customer1.id)
            
            account2_data = AccountCreateRequest(
                account_type="CHECKING",
                initial_deposit=Decimal("200.00"),
                currency="USD"
            )
            account2 = service.create_account(account2_data, customer2.id)
            
            # Assert
            assert account1 is not None
            assert account2 is not None
            assert account1.customer_id != account2.customer_id
            assert account1.status == "ACTIVE"
            assert account2.status == "ACTIVE"

