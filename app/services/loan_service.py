"""
Bank API - Loan Service

Business logic for loan application and management operations.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
import random
import string

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import LoanApplication, Customer, Account, Transaction
from app.schemas.loan import LoanApplicationRequest, LoanReviewRequest, LoanDisbursementRequest
from app.exceptions import NotFoundError, ValidationError, BusinessRuleViolationError
from app.services.bank_service import BankService


class LoanService:
    """Service class for loan-related business logic."""

    def __init__(self, db: Session):
        """
        Initialize LoanService.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def submit_application(self, application_data: LoanApplicationRequest) -> LoanApplication:
        """
        Submit a new loan application.

        Args:
            application_data: Loan application data

        Returns:
            Created loan application instance

        Raises:
            NotFoundError: If customer not found
            ValidationError: If validation fails
        """
        # Verify customer exists and is active
        customer = (
            self.db.query(Customer).filter(Customer.id == application_data.customer_id).first()
        )

        if not customer:
            raise NotFoundError(f"Customer with ID {application_data.customer_id} not found")

        if not customer.is_active:
            raise BusinessRuleViolationError("Cannot submit loan application for inactive customer")

        # Check for existing pending applications
        existing_pending = (
            self.db.query(LoanApplication)
            .filter(
                LoanApplication.customer_id == application_data.customer_id,
                LoanApplication.status == "PENDING",
            )
            .first()
        )

        if existing_pending:
            raise BusinessRuleViolationError("Customer already has a pending loan application")

        # Generate application number
        application_number = self._generate_application_number()

        # Create loan application
        application = LoanApplication(
            customer_id=application_data.customer_id,
            application_number=application_number,
            requested_amount=application_data.requested_amount,
            purpose=application_data.purpose,
            term_months=application_data.term_months,
            employment_status=application_data.employment_status,
            annual_income=application_data.annual_income,
            status="PENDING",
            applied_at=datetime.utcnow(),
            external_account_number=application_data.external_account.account_number,
            external_routing_number=application_data.external_account.routing_number,
        )

        try:
            self.db.add(application)
            self.db.commit()
            self.db.refresh(application)
            return application
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error submitting loan application: {str(e)}")

    def get_application(self, application_id: UUID) -> LoanApplication:
        """
        Get loan application by ID.

        Args:
            application_id: Application UUID

        Returns:
            LoanApplication instance

        Raises:
            NotFoundError: If application not found
        """
        application = (
            self.db.query(LoanApplication).filter(LoanApplication.id == application_id).first()
        )

        if not application:
            raise NotFoundError(f"Loan application with ID {application_id} not found")

        return application

    def get_customer_applications(
        self, customer_id: UUID, status: Optional[str] = None
    ) -> List[LoanApplication]:
        """
        Get all loan applications for a customer.

        Args:
            customer_id: Customer UUID
            status: Optional status filter

        Returns:
            List of loan applications
        """
        query = self.db.query(LoanApplication).filter(LoanApplication.customer_id == customer_id)

        if status:
            query = query.filter(LoanApplication.status == status)

        return query.order_by(LoanApplication.applied_at.desc()).all()

    def list_applications(
        self, status: Optional[str] = None, limit: int = 20, offset: int = 0
    ) -> Tuple[List[LoanApplication], int]:
        """
        List all loan applications (admin operation).

        Args:
            status: Optional status filter
            limit: Number of results
            offset: Pagination offset

        Returns:
            Tuple of (list of applications, total count)
        """
        query = self.db.query(LoanApplication)

        if status:
            query = query.filter(LoanApplication.status == status)

        # Get total count
        total = query.count()

        # Order by applied_at descending
        query = query.order_by(LoanApplication.applied_at.desc())

        # Apply pagination
        applications = query.limit(limit).offset(offset).all()

        return applications, total

    def review_application(
        self, application_id: UUID, review_data: LoanReviewRequest
    ) -> LoanApplication:
        """
        Review a loan application (admin operation).

        Before approving a loan, checks if the bank has sufficient funds.
        Loans cannot put the bank into debt (net cash position must remain >= 0).

        Args:
            application_id: Application UUID
            review_data: Review decision data

        Returns:
            Updated loan application

        Raises:
            NotFoundError: If application not found
            BusinessRuleViolationError: If application cannot be reviewed or
                                       if bank has insufficient funds to approve loan
        """
        application = self.get_application(application_id)

        # Validate application can be reviewed
        if not application.can_be_reviewed:
            raise BusinessRuleViolationError(
                f"Application with status {application.status} cannot be reviewed"
            )

        # Check bank funds if approving the loan
        if review_data.status == "APPROVED":
            # Determine the approved amount
            approved_amount = review_data.approved_amount or application.requested_amount

            # Check if bank has sufficient funds
            bank_service = BankService(self.db)
            can_approve, reason = bank_service.can_approve_loan(approved_amount)

            if not can_approve:
                raise BusinessRuleViolationError(f"Cannot approve loan: {reason}")

        # Update application based on review decision
        application.status = review_data.status
        application.reviewed_at = datetime.utcnow()

        if review_data.status == "APPROVED":
            # Set approval details
            application.approved_amount = (
                review_data.approved_amount or application.requested_amount
            )
            application.interest_rate = review_data.interest_rate
            application.term_months = review_data.term_months or application.term_months

        elif review_data.status == "REJECTED":
            # Set rejection reason
            application.rejection_reason = review_data.rejection_reason

        try:
            self.db.commit()
            self.db.refresh(application)
            return application
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error reviewing application: {str(e)}")

    def disburse_loan(
        self, application_id: UUID, disbursement_data: LoanDisbursementRequest
    ) -> LoanApplication:
        """
        Disburse an approved loan (admin operation).

        Re-checks bank funds before disbursement to handle time-of-check-time-of-use
        race conditions. Bank position may have changed between approval and disbursement.

        Args:
            application_id: Application UUID
            disbursement_data: Disbursement confirmation

        Returns:
            Updated loan application

        Raises:
            NotFoundError: If application not found
            BusinessRuleViolationError: If loan cannot be disbursed or
                                       if bank has insufficient funds at disbursement time
        """
        application = self.get_application(application_id)

        # Validate application can be disbursed
        if not application.can_be_disbursed:
            raise BusinessRuleViolationError(
                f"Application with status {application.status} cannot be disbursed"
            )

        if not disbursement_data.confirm:
            raise ValidationError("Disbursement confirmation required")

        # Re-check bank funds before disbursement (time-of-use check)
        # Bank position may have changed since approval
        bank_service = BankService(self.db)
        can_approve, reason = bank_service.can_approve_loan(application.approved_amount)

        if not can_approve:
            raise BusinessRuleViolationError(
                f"Cannot disburse loan: {reason}. Bank cash position may have changed since approval."
            )

        # Check for existing active accounts (single account rule)
        # Per requirements: Customer must close CHECKING account before getting loan
        existing_account = self.db.query(Account).filter(
            Account.customer_id == application.customer_id,
            Account.status == 'ACTIVE'
        ).first()
        
        if existing_account:
            raise BusinessRuleViolationError(
                f"Customer already has an active {existing_account.account_type.lower()} account "
                f"(Account #: {existing_account.account_number}). "
                f"Only one account per customer is allowed. Please close existing account before loan disbursement."
            )

        # Create loan account
        loan_account = Account(
            customer_id=application.customer_id,
            account_type="LOAN",
            account_number=self._generate_loan_account_number(),
            status="ACTIVE",
            balance=-application.approved_amount,  # Negative balance = debt
            currency="USD",
        )

        # Generate disbursement transaction
        reference_number = self._generate_reference_number()

        disbursement_transaction = Transaction(
            account_id=loan_account.id,  # Will be set after commit
            transaction_type="LOAN_DISBURSEMENT",
            amount=application.approved_amount,
            currency="USD",
            balance_after=-application.approved_amount,
            description=f"Loan disbursement for application {application.application_number}",
            reference_number=reference_number,
            status="COMPLETED",
            processed_at=datetime.utcnow(),
        )

        try:
            # Add loan account
            self.db.add(loan_account)
            self.db.flush()  # Flush to get account ID

            # Link transaction to account
            disbursement_transaction.account_id = loan_account.id
            self.db.add(disbursement_transaction)

            # Update application
            application.loan_account_id = loan_account.id
            application.status = "DISBURSED"
            application.disbursed_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(application)
            return application

        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error disbursing loan: {str(e)}")

    def cancel_application(self, application_id: UUID) -> LoanApplication:
        """
        Cancel a loan application.

        Args:
            application_id: Application UUID

        Returns:
            Updated loan application

        Raises:
            NotFoundError: If application not found
            BusinessRuleViolationError: If application cannot be cancelled
        """
        application = self.get_application(application_id)

        # Can only cancel pending applications
        if application.status != "PENDING":
            raise BusinessRuleViolationError(
                f"Cannot cancel application with status {application.status}"
            )

        application.status = "CANCELLED"

        try:
            self.db.commit()
            self.db.refresh(application)
            return application
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error cancelling application: {str(e)}")

    @staticmethod
    def _generate_application_number() -> str:
        """Generate unique loan application number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        random_suffix = "".join(random.choices(string.digits, k=6))
        return f"LOAN-{timestamp}-{random_suffix}"

    @staticmethod
    def _generate_loan_account_number() -> str:
        """Generate unique loan account number."""
        random_digits = "".join(random.choices(string.digits, k=10))
        return f"LOAN-{random_digits}"

    @staticmethod
    def _generate_reference_number() -> str:
        """Generate unique transaction reference number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        random_suffix = "".join(random.choices(string.digits, k=6))
        return f"TXN-{timestamp}-{random_suffix}"
