"""
Integration test for Loan Service and Single Account Rule.

Tests the interaction between loan service and the single account per customer rule.
Per requirements (Option C): Customer must close CHECKING account before getting loan.
"""

from decimal import Decimal
from datetime import date, datetime
import pytest

from app.models import Account, Customer, LoanApplication
from app.services.loan_service import LoanService
from app.schemas.loan import LoanDisbursementRequest
from app.exceptions import BusinessRuleViolationError


class TestLoanAccountSingleRule:
    """Test suite for loan service respecting single account rule."""

    def test_loan_disbursement_fails_when_customer_has_active_checking_account(
        self, db_session, app
    ):
        """
        Test: Attempt to disburse loan when customer has active checking account → should fail.
        
        Scenario: 
        1. Customer has an active CHECKING account
        2. Loan application is approved
        3. Attempt to disburse loan (creates LOAN account)
        Expected: BusinessRuleViolationError - customer already has active account
        """
        with app.app_context():
            # Arrange - Create customer with CHECKING account
            customer = Customer(
                email="loantest@example.com",
                first_name="Loan",
                last_name="Test",
                date_of_birth=date(1988, 8, 8),
                phone="+1-555-8888",
                address_line_1="888 Loan St",
                city="Test City",
                state="CA",
                zip_code="88888",
                status="ACTIVE"
            )
            db_session.add(customer)
            db_session.commit()
            
            # Create active CHECKING account
            checking_account = Account(
                customer_id=customer.id,
                account_type="CHECKING",
                account_number="CHK-LOAN-TEST",
                status="ACTIVE",
                balance=Decimal("1000.00"),
                currency="USD"
            )
            db_session.add(checking_account)
            db_session.commit()
            
            # Create approved loan application
            loan_app = LoanApplication(
                customer_id=customer.id,
                application_number="LOAN-APP-TEST001",
                requested_amount=Decimal("10000.00"),
                approved_amount=Decimal("10000.00"),
                purpose="Test loan",
                term_months=24,
                employment_status="FULL_TIME",
                annual_income=Decimal("60000.00"),
                status="APPROVED",
                applied_at=datetime.utcnow(),
                reviewed_at=datetime.utcnow(),
                external_account_number="9876543210",
                external_routing_number="121000248"
            )
            db_session.add(loan_app)
            db_session.commit()
            
            # Act & Assert - Try to disburse loan
            service = LoanService(db_session)
            disbursement_data = LoanDisbursementRequest(confirm=True)
            
            with pytest.raises(BusinessRuleViolationError) as exc_info:
                service.disburse_loan(loan_app.id, disbursement_data)
            
            # Verify error message
            error_message = str(exc_info.value)
            assert "already has an active" in error_message
            assert "checking account" in error_message.lower()
            assert "CHK-LOAN-TEST" in error_message
            assert "Only one account per customer is allowed" in error_message

    def test_loan_disbursement_succeeds_when_customer_has_no_accounts(
        self, db_session, app
    ):
        """
        Test: Loan disbursement succeeds when customer has no existing accounts.
        
        Scenario: 
        1. Customer has no accounts
        2. Loan application is approved
        3. Disburse loan
        Expected: Success - LOAN account created
        """
        with app.app_context():
            # Arrange - Create customer WITHOUT any accounts
            customer = Customer(
                email="loantest2@example.com",
                first_name="Loan",
                last_name="Test2",
                date_of_birth=date(1989, 9, 9),
                phone="+1-555-9999",
                address_line_1="999 Loan St",
                city="Test City",
                state="CA",
                zip_code="99999",
                status="ACTIVE"
            )
            db_session.add(customer)
            db_session.commit()
            
            # Create approved loan application
            loan_app = LoanApplication(
                customer_id=customer.id,
                application_number="LOAN-APP-TEST002",
                requested_amount=Decimal("15000.00"),
                approved_amount=Decimal("15000.00"),
                purpose="Test loan 2",
                term_months=36,
                employment_status="FULL_TIME",
                annual_income=Decimal("70000.00"),
                status="APPROVED",
                applied_at=datetime.utcnow(),
                reviewed_at=datetime.utcnow(),
                external_account_number="1234567890",
                external_routing_number="121000248"
            )
            db_session.add(loan_app)
            db_session.commit()
            
            # Act - Disburse loan (should succeed)
            service = LoanService(db_session)
            disbursement_data = LoanDisbursementRequest(confirm=True)
            
            result = service.disburse_loan(loan_app.id, disbursement_data)
            
            # Assert - Verify loan was disbursed
            assert result.status == "DISBURSED"
            assert result.disbursed_at is not None
            
            # Verify LOAN account was created
            loan_account = db_session.query(Account).filter(
                Account.customer_id == customer.id,
                Account.account_type == "LOAN"
            ).first()
            
            assert loan_account is not None
            assert loan_account.status == "ACTIVE"
            assert loan_account.balance == -Decimal("15000.00")

    def test_loan_disbursement_succeeds_after_closing_checking_account(
        self, db_session, app
    ):
        """
        Test: Loan disbursement succeeds after customer closes CHECKING account.
        
        Scenario: 
        1. Customer has CHECKING account
        2. Customer closes CHECKING account
        3. Loan application is approved
        4. Disburse loan
        Expected: Success - LOAN account created (CLOSED accounts don't block)
        """
        with app.app_context():
            from app.services.account_service import AccountService
            
            # Arrange - Create customer with CHECKING account
            customer = Customer(
                email="loantest3@example.com",
                first_name="Loan",
                last_name="Test3",
                date_of_birth=date(1990, 10, 10),
                phone="+1-555-1010",
                address_line_1="1010 Loan St",
                city="Test City",
                state="CA",
                zip_code="10101",
                status="ACTIVE"
            )
            db_session.add(customer)
            db_session.commit()
            
            # Create CHECKING account with zero balance
            checking_account = Account(
                customer_id=customer.id,
                account_type="CHECKING",
                account_number="CHK-LOAN-TEST3",
                status="ACTIVE",
                balance=Decimal("0.00"),
                currency="USD"
            )
            db_session.add(checking_account)
            db_session.commit()
            
            # Close the CHECKING account
            account_service = AccountService(db_session)
            account_service.close_account(checking_account.id)
            
            # Verify account is closed
            db_session.refresh(checking_account)
            assert checking_account.status == "CLOSED"
            
            # Create approved loan application
            loan_app = LoanApplication(
                customer_id=customer.id,
                application_number="LOAN-APP-TEST003",
                requested_amount=Decimal("20000.00"),
                approved_amount=Decimal("20000.00"),
                purpose="Test loan 3",
                term_months=48,
                employment_status="FULL_TIME",
                annual_income=Decimal("80000.00"),
                status="APPROVED",
                applied_at=datetime.utcnow(),
                reviewed_at=datetime.utcnow(),
                external_account_number="5555555555",
                external_routing_number="121000248"
            )
            db_session.add(loan_app)
            db_session.commit()
            
            # Act - Disburse loan (should succeed since CHECKING is CLOSED)
            loan_service = LoanService(db_session)
            disbursement_data = LoanDisbursementRequest(confirm=True)
            
            result = loan_service.disburse_loan(loan_app.id, disbursement_data)
            
            # Assert - Verify loan was disbursed
            assert result.status == "DISBURSED"
            
            # Verify LOAN account was created
            loan_account = db_session.query(Account).filter(
                Account.customer_id == customer.id,
                Account.account_type == "LOAN"
            ).first()
            
            assert loan_account is not None
            assert loan_account.status == "ACTIVE"

