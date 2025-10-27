"""
Bank API - Bank Service

Business logic for bank-level operations and financial reporting.
Updated to use Bank Capital + Fractional Reserve Banking model.
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func
from flask import current_app

from app.models import Account


class BankService:
    """
    Service class for bank-level operations and reporting.

    Implements fractional reserve banking model:
    - Bank starts with $250,000 capital
    - Can use 25% of customer deposits for lending
    - Must keep 75% of deposits liquid for withdrawals

    Handles bank-wide financial calculations including:
    - Available lending capacity
    - Bank financial status reporting
    - Loan approval validation based on reserves
    - Reserve requirement monitoring
    """

    def __init__(self, db: Session):
        """
        Initialize BankService.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_bank_capital(self) -> Decimal:
        """
        Get bank's own capital (not customer deposits).

        For MVP: Returns static initial capital of $250,000.
        Future: Will track dynamic capital that grows with interest revenue.

        Returns:
            Decimal: Bank capital amount
        """
        return Decimal(str(current_app.config["BANK_INITIAL_CAPITAL"]))

    def get_customer_deposits(self) -> Decimal:
        """
        Get total customer deposits (sum of all ACTIVE checking balances).

        Returns:
            Decimal: Total deposits bank owes to customers
        """
        deposits = self.db.query(func.sum(Account.balance)).filter(
            Account.account_type == "CHECKING", Account.status == "ACTIVE"
        ).scalar() or Decimal("0.00")

        return deposits

    def get_usable_deposits(self) -> Decimal:
        """
        Get portion of customer deposits available for lending (25%).

        Under fractional reserve banking, bank can use 25% of deposits for loans,
        must keep 75% liquid for withdrawals.

        Returns:
            Decimal: Amount of deposits available for lending (25% of total)
        """
        deposits = self.get_customer_deposits()
        reserve_ratio = Decimal(str(current_app.config["RESERVE_RATIO"]))

        return deposits * reserve_ratio

    def get_reserved_deposits(self) -> Decimal:
        """
        Get portion of customer deposits that must remain liquid (75%).

        Returns:
            Decimal: Amount that must be kept for withdrawals (75% of total)
        """
        deposits = self.get_customer_deposits()
        reserve_requirement = Decimal(str(current_app.config["RESERVE_REQUIREMENT"]))

        return deposits * reserve_requirement

    def get_loans_outstanding(self) -> Decimal:
        """
        Get total outstanding loan amounts (absolute value).

        Loan balances are stored as negative values.
        This returns the positive amount customers owe the bank.

        Returns:
            Decimal: Total outstanding loans (positive value)
        """
        loans = self.db.query(func.sum(Account.balance)).filter(
            Account.account_type == "LOAN", Account.status == "ACTIVE"
        ).scalar() or Decimal("0.00")

        return abs(loans)

    def get_available_for_lending(self) -> Decimal:
        """
        Calculate total funds available for new loans.

        Formula:
        Available = Bank Capital + (Reserve Ratio × Customer Deposits) - Loans Outstanding

        Where:
        - Bank Capital = $250,000 (initial capital, static for MVP)
        - Reserve Ratio = 0.25 (can use 25% of deposits)
        - Customer Deposits = Sum of all ACTIVE checking balances
        - Loans Outstanding = |Sum of all ACTIVE loan balances|

        Examples:
        - No customers: $250,000 + (0.25 × $0) - $0 = $250,000
        - With $100k deposits, $200k loans: $250k + $25k - $200k = $75k
        - Overextended: $250k + $25k - $300k = -$25k (cannot lend more)

        Returns:
            Decimal: Amount available for new loans (can be negative if overextended)
        """
        bank_capital = self.get_bank_capital()
        usable_deposits = self.get_usable_deposits()
        loans_outstanding = self.get_loans_outstanding()

        available = bank_capital + usable_deposits - loans_outstanding

        return available

    def get_reserve_requirement_status(self) -> Dict:
        """
        Check reserve requirement status.

        Monitors whether bank is maintaining 75% reserve on customer deposits.
        This is informational only (soft limit) - withdrawals are not blocked.

        Returns:
            dict: Reserve status with compliance information
        """
        deposits = self.get_customer_deposits()
        reserved = self.get_reserved_deposits()
        usable = self.get_usable_deposits()

        return {
            "total_deposits": deposits,
            "reserved_amount": reserved,
            "reserved_percentage": Decimal("0.75"),
            "usable_amount": usable,
            "usable_percentage": Decimal("0.25"),
            "is_compliant": True,  # Always true for MVP (soft limit)
        }

    def get_bank_financial_status(self) -> dict:
        """
        Get comprehensive bank financial status.

        Returns detailed financial metrics including:
        - Bank's own capital
        - Total customer deposits
        - Usable deposits (25% for lending)
        - Reserved deposits (75% for withdrawals)
        - Total loans outstanding
        - Available lending capacity
        - Whether bank is overextended
        - Account breakdown statistics
        - Timestamp of calculation

        Returns:
            dict: Complete financial status with all metrics
        """
        # Get core financial data
        bank_capital = self.get_bank_capital()
        customer_deposits = self.get_customer_deposits()
        usable_deposits = self.get_usable_deposits()
        reserved_deposits = self.get_reserved_deposits()
        loans_outstanding = self.get_loans_outstanding()
        available = self.get_available_for_lending()

        # Get account counts by type
        total_checking = (
            self.db.query(func.count(Account.id))
            .filter(Account.account_type == "CHECKING", Account.status == "ACTIVE")
            .scalar()
            or 0
        )

        total_loans = (
            self.db.query(func.count(Account.id))
            .filter(Account.account_type == "LOAN", Account.status == "ACTIVE")
            .scalar()
            or 0
        )

        total_active = total_checking + total_loans

        return {
            "bank_capital": bank_capital,
            "total_customer_deposits": customer_deposits,
            "usable_customer_deposits": usable_deposits,
            "reserved_deposits": reserved_deposits,
            "total_loans_outstanding": loans_outstanding,
            "available_for_lending": available,
            "is_overextended": available < 0,
            "account_breakdown": {
                "total_checking_accounts": total_checking,
                "total_loan_accounts": total_loans,
                "active_accounts": total_active,
            },
            "as_of": datetime.utcnow(),
        }

    def can_approve_loan(self, requested_amount: Decimal) -> tuple[bool, str]:
        """
        Check if bank has sufficient funds to approve a loan.

        Business Rule: Loans cannot put bank into overextended position.
        Calculates if approving the loan would leave available funds >= $0.

        Args:
            requested_amount: Loan amount requested (as positive Decimal)

        Returns:
            tuple: (can_approve: bool, reason: str)
            - (True, message) if loan can be approved
            - (False, detailed_message) if insufficient funds
        """
        # Get current available lending capacity
        available = self.get_available_for_lending()

        # Calculate what would be available after loan
        available_after_loan = available - requested_amount

        # Can approve if bank would still have >= $0 after loan
        if available_after_loan >= 0:
            return (
                True,
                f"Sufficient funds available. Current: ${available:.2f}, After loan: ${available_after_loan:.2f}",
            )
        else:
            shortfall = abs(available_after_loan)
            return (
                False,
                f"Insufficient bank reserves. Available: ${available:.2f}, Requested: ${requested_amount:.2f}, Shortfall: ${shortfall:.2f}",
            )

    # Backwards compatibility: alias old method name to new one
    def get_total_cash_on_hand(self) -> Decimal:
        """
        DEPRECATED: Use get_available_for_lending() instead.

        This method is kept for backwards compatibility but should not be used
        in new code. It now returns the same value as get_available_for_lending().
        """
        return self.get_available_for_lending()
