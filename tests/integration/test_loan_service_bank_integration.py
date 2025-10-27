"""
Integration tests for Loan Service with Bank Capital Integration.

Tests loan approval and disbursement with bank funds checks.

Updated for Bank Capital + Fractional Reserve Model:
- Bank has $250,000 capital
- Can use 25% of customer deposits for lending
- Formula: Available = $250k + (0.25 × Deposits) - Loans
"""

import pytest
from decimal import Decimal

from app.services.loan_service import LoanService
from app.schemas.loan import (
    LoanApplicationRequest,
    LoanReviewRequest,
    LoanDisbursementRequest,
    ExternalAccountSchema,
)
from app.models import Account, LoanApplication, Customer
from app.exceptions import BusinessRuleViolationError
from datetime import date


class TestLoanServiceBankIntegration:
    """Test suite for loan service integration with bank cash checks."""

    def test_review_application_approve_with_sufficient_bank_funds(
        self, db_session, sample_customer, admin_user
    ):
        """
        Test loan approval succeeds when bank has sufficient funds.

        Scenario:
        - Bank setup: Deposits = $100k, Loans = $200k
        - Formula: $250k + (0.25 × $100k) - $200k = $75k available
        - Customer applies for $50k loan
        - Admin approves loan
        - Expected: Approval succeeds (bank would have $25k remaining)

        Business Rule: Loans cannot overextend bank
        """
        # Arrange - Setup bank with sufficient funds
        # Use sample_customer for existing accounts (to establish bank balance)
        # Create checking account with $100k
        checking = Account(
            customer_id=sample_customer.id,
            account_type="CHECKING",
            account_number="CHK-LOAN-TEST-1",
            status="ACTIVE",
            balance=Decimal("100000.00"),
            currency="USD",
        )

        # Create existing loan with $200k outstanding
        existing_loan_account = Account(
            customer_id=sample_customer.id,
            account_type="LOAN",
            account_number="LOAN-EXISTING-1",
            status="ACTIVE",
            balance=Decimal("-200000.00"),
            currency="USD",
        )

        db_session.add_all([checking, existing_loan_account])
        db_session.commit()

        # Create separate loan applicant customer (must have NO active accounts)
        loan_applicant = Customer(
            email="loanapplicant1@example.com",
            first_name="Loan",
            last_name="Applicant",
            date_of_birth=date(1985, 5, 15),
            phone="+1-555-1111",
            address_line_1="111 Loan St",
            city="Test City",
            state="CA",
            zip_code="11111",
            status="ACTIVE"
        )
        db_session.add(loan_applicant)
        db_session.commit()

        # Bank available: $250k + $25k - $200k = $75k
        # Approving $50k loan would leave $25k (still positive)

        # Create loan application
        loan_service = LoanService(db_session)
        application_data = LoanApplicationRequest(
            customer_id=loan_applicant.id,
            requested_amount=Decimal("50000.00"),
            purpose="Business expansion",
            term_months=24,
            employment_status="FULL_TIME",
            annual_income=Decimal("80000.00"),
            external_account=ExternalAccountSchema(
                account_number="1234567890", routing_number="121000248"
            ),
        )
        application = loan_service.submit_application(application_data)

        # Act - Admin approves loan
        review_data = LoanReviewRequest(
            status="APPROVED",
            approved_amount=Decimal("50000.00"),
            interest_rate=Decimal("0.0525"),
            term_months=24,
        )

        # This should succeed because bank has sufficient funds
        updated_application = loan_service.review_application(application.id, review_data)

        # Assert
        assert updated_application.status == "APPROVED"
        assert updated_application.reviewed_at is not None

    def test_review_application_reject_insufficient_bank_funds(
        self, db_session, sample_customer, admin_user
    ):
        """
        Test loan approval fails when bank has insufficient funds.

        Scenario:
        - Bank setup: Deposits = $100k, Loans = $270k
        - Formula: $250k + (0.25 × $100k) - $270k = $5k available
        - Customer applies for $10k loan
        - Admin attempts to approve loan
        - Expected: BusinessRuleViolationError raised (bank would have -$5k)

        Business Rule: Loans cannot overextend bank
        """
        # Arrange - Setup bank with insufficient funds
        # Use sample_customer for existing accounts (to establish bank balance)
        # Create checking account with $100k
        checking = Account(
            customer_id=sample_customer.id,
            account_type="CHECKING",
            account_number="CHK-LOAN-TEST-2",
            status="ACTIVE",
            balance=Decimal("100000.00"),
            currency="USD",
        )

        # Create existing loan with $270k outstanding
        existing_loan_account = Account(
            customer_id=sample_customer.id,
            account_type="LOAN",
            account_number="LOAN-EXISTING-2",
            status="ACTIVE",
            balance=Decimal("-270000.00"),
            currency="USD",
        )

        db_session.add_all([checking, existing_loan_account])
        db_session.commit()

        # Create separate loan applicant customer (must have NO active accounts)
        loan_applicant = Customer(
            email="loanapplicant2@example.com",
            first_name="Second",
            last_name="Applicant",
            date_of_birth=date(1990, 10, 20),
            phone="+1-555-2222",
            address_line_1="222 Loan Ave",
            city="Test City",
            state="CA",
            zip_code="22222",
            status="ACTIVE"
        )
        db_session.add(loan_applicant)
        db_session.commit()

        # Bank available: $250k + $25k - $270k = $5k
        # Approving $10k loan would result in -$5k (overextended!)

        # Create loan application
        loan_service = LoanService(db_session)
        application_data = LoanApplicationRequest(
            customer_id=loan_applicant.id,
            requested_amount=Decimal("10000.00"),
            purpose="Home renovation",
            term_months=36,
            employment_status="SELF_EMPLOYED",
            annual_income=Decimal("60000.00"),
            external_account=ExternalAccountSchema(
                account_number="9876543210", routing_number="121000248"
            ),
        )
        application = loan_service.submit_application(application_data)

        # Act & Assert - Admin approval should fail
        review_data = LoanReviewRequest(
            status="APPROVED",
            approved_amount=Decimal("10000.00"),
            interest_rate=Decimal("0.0625"),
            term_months=36,
        )

        # This should raise BusinessRuleViolationError
        with pytest.raises(BusinessRuleViolationError) as exc_info:
            loan_service.review_application(application.id, review_data)

        # Assert error message contains relevant information
        error_message = str(exc_info.value)
        assert (
            "Insufficient bank reserves" in error_message or "insufficient" in error_message.lower()
        )

        # Verify application status remains PENDING (not approved)
        db_session.refresh(application)
        assert application.status == "PENDING"
        assert application.reviewed_at is None

    def test_disburse_loan_with_sufficient_funds(self, db_session, sample_customer, admin_user):
        """
        Test loan disbursement succeeds when bank has sufficient funds.

        Scenario:
        - Loan already approved for $50k
        - Bank setup: Deposits = $100k, Loans = $200k
        - Formula: $250k + $25k - $200k = $75k available
        - Admin disburses loan
        - Expected: Disbursement succeeds

        Business Rule: Re-check bank funds at disbursement time
        Note: Uses separate customer for bank setup accounts (single account rule)
        """
        # Arrange - Create separate customers for bank setup
        # (to respect single account rule: one customer per account)
        from app.models import Customer
        from datetime import date
        
        customer_with_checking = Customer(
            email="checking_customer@example.com",
            first_name="Checking",
            last_name="Customer",
            date_of_birth=date(1985, 5, 15),
            phone="+1-555-8888",
            address_line_1="888 Checking St",
            city="City",
            state="CA",
            zip_code="88888",
            status="ACTIVE"
        )
        
        customer_with_loan = Customer(
            email="loan_customer@example.com",
            first_name="Loan",
            last_name="Customer",
            date_of_birth=date(1986, 6, 16),
            phone="+1-555-9999",
            address_line_1="999 Loan St",
            city="City",
            state="CA",
            zip_code="99999",
            status="ACTIVE"
        )
        
        db_session.add_all([customer_with_checking, customer_with_loan])
        db_session.commit()
        
        # Setup bank with sufficient funds using separate customers
        checking = Account(
            customer_id=customer_with_checking.id,  # Customer 1
            account_type="CHECKING",
            account_number="CHK-DISBURSE-1",
            status="ACTIVE",
            balance=Decimal("100000.00"),
            currency="USD",
        )

        existing_loan = Account(
            customer_id=customer_with_loan.id,  # Customer 2
            account_type="LOAN",
            account_number="LOAN-EXISTING-3",
            status="ACTIVE",
            balance=Decimal("-200000.00"),
            currency="USD",
        )

        db_session.add_all([checking, existing_loan])
        db_session.commit()

        # Bank available: $250k + $25k - $200k = $75k

        # Create and approve loan application
        loan_service = LoanService(db_session)
        application_data = LoanApplicationRequest(
            customer_id=sample_customer.id,
            requested_amount=Decimal("50000.00"),
            purpose="Medical expenses",
            term_months=24,
            employment_status="FULL_TIME",
            annual_income=Decimal("90000.00"),
            external_account=ExternalAccountSchema(
                account_number="1111222233", routing_number="121000248"
            ),
        )
        application = loan_service.submit_application(application_data)

        # Approve the loan
        review_data = LoanReviewRequest(
            status="APPROVED",
            approved_amount=Decimal("50000.00"),
            interest_rate=Decimal("0.055"),
            term_months=24,
        )
        loan_service.review_application(application.id, review_data)

        # Act - Disburse the loan
        disbursement_data = LoanDisbursementRequest(confirm=True, notes="Disbursement approved")

        # This should succeed
        disbursed_application = loan_service.disburse_loan(application.id, disbursement_data)

        # Assert
        assert disbursed_application.status == "DISBURSED"
        assert disbursed_application.disbursed_at is not None
        assert disbursed_application.loan_account_id is not None

    def test_disburse_loan_fails_if_bank_position_changed(
        self, db_session, sample_customer, admin_user
    ):
        """
        Test loan disbursement fails when bank position changed after approval.

        Scenario:
        - Loan approved when bank had $75k available
        - Between approval and disbursement, bank position drops to $5k
        - Admin attempts to disburse $50k loan
        - Expected: BusinessRuleViolationError raised

        Business Rule: Re-check bank funds at disbursement (time-of-use check)
        Note: Uses separate customers for bank setup accounts (single account rule)
        """
        # Arrange - Create separate customers for bank setup
        from app.models import Customer
        from datetime import date
        
        customer_with_checking = Customer(
            email="checking_customer2@example.com",
            first_name="Checking2",
            last_name="Customer",
            date_of_birth=date(1987, 7, 17),
            phone="+1-555-7777",
            address_line_1="777 Checking St",
            city="City",
            state="CA",
            zip_code="77777",
            status="ACTIVE"
        )
        
        customer_with_loan = Customer(
            email="loan_customer2@example.com",
            first_name="Loan2",
            last_name="Customer",
            date_of_birth=date(1988, 8, 18),
            phone="+1-555-6666",
            address_line_1="666 Loan St",
            city="City",
            state="CA",
            zip_code="66666",
            status="ACTIVE"
        )
        
        db_session.add_all([customer_with_checking, customer_with_loan])
        db_session.commit()
        
        # Setup bank with sufficient funds initially using separate customers
        checking = Account(
            customer_id=customer_with_checking.id,  # Customer 1
            account_type="CHECKING",
            account_number="CHK-DISBURSE-2",
            status="ACTIVE",
            balance=Decimal("100000.00"),
            currency="USD",
        )

        existing_loan = Account(
            customer_id=customer_with_loan.id,  # Customer 2
            account_type="LOAN",
            account_number="LOAN-EXISTING-4",
            status="ACTIVE",
            balance=Decimal("-200000.00"),
            currency="USD",
        )

        db_session.add_all([checking, existing_loan])
        db_session.commit()

        # Bank available: $250k + $25k - $200k = $75k (sufficient for $50k loan)

        # Create and approve loan application
        loan_service = LoanService(db_session)
        application_data = LoanApplicationRequest(
            customer_id=sample_customer.id,
            requested_amount=Decimal("50000.00"),
            purpose="Emergency funds",
            term_months=36,
            employment_status="SELF_EMPLOYED",
            annual_income=Decimal("70000.00"),
            external_account=ExternalAccountSchema(
                account_number="4444555566", routing_number="121000248"
            ),
        )
        application = loan_service.submit_application(application_data)

        # Approve the loan (bank has sufficient funds at this time)
        review_data = LoanReviewRequest(
            status="APPROVED",
            approved_amount=Decimal("50000.00"),
            interest_rate=Decimal("0.065"),
            term_months=36,
        )
        loan_service.review_application(application.id, review_data)

        # SIMULATE BANK POSITION CHANGE
        # The existing loan balance increased significantly
        # (e.g., another large loan was approved and disbursed)
        existing_loan.balance = Decimal("-270000.00")  # Increase from $200k to $270k
        db_session.commit()

        # New bank available: $250k + $25k - $270k = $5k
        # Now trying to disburse $50k should fail!

        # Act & Assert - Disbursement should fail
        disbursement_data = LoanDisbursementRequest(confirm=True, notes="Attempting disbursement")

        # This should raise BusinessRuleViolationError
        with pytest.raises(BusinessRuleViolationError) as exc_info:
            loan_service.disburse_loan(application.id, disbursement_data)

        # Assert error message is informative
        error_message = str(exc_info.value)
        assert "insufficient" in error_message.lower() or "cash position" in error_message.lower()

        # Verify loan was NOT disbursed
        db_session.refresh(application)
        assert application.status == "APPROVED"  # Still approved, not disbursed
        assert application.disbursed_at is None
        assert application.loan_account_id is None
