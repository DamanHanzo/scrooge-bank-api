"""
Bank API - Transaction Service

Business logic for transaction operations (deposits, withdrawals, transfers).
"""

from typing import List, Optional, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timedelta
import random
import string

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, func

from app.models import Transaction, Account
from app.schemas.transaction import DepositRequest, WithdrawalRequest
from app.exceptions import (
    NotFoundError,
    ValidationError,
    BusinessRuleViolationError,
    InsufficientFundsError,
    TransactionLimitError
)


class TransactionService:
    """Service class for transaction-related business logic."""
    
    # Business rule constants
    MAX_WITHDRAWAL_AMOUNT = Decimal('10000.00')
    DAILY_WITHDRAWAL_LIMIT = Decimal('50000.00')
    
    def __init__(self, db: Session):
        """
        Initialize TransactionService.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def deposit(
        self,
        account_id: UUID,
        deposit_data: DepositRequest
    ) -> Transaction:
        """
        Process a deposit transaction.
        
        Args:
            account_id: Account UUID
            deposit_data: Deposit request data
            
        Returns:
            Created transaction instance
            
        Raises:
            NotFoundError: If account not found
            BusinessRuleViolationError: If account cannot transact
        """
        # Get and validate account
        account = self._get_and_validate_account(account_id, 'CHECKING')
        
        # Validate currency match
        if deposit_data.currency != account.currency:
            raise ValidationError(
                f"Currency mismatch. Account currency is {account.currency}"
            )
        
        # Calculate new balance
        new_balance = account.balance + deposit_data.amount
        
        # Generate reference number
        reference_number = self._generate_reference_number()
        
        # Create transaction
        transaction = Transaction(
            account_id=account_id,
            transaction_type='DEPOSIT',
            amount=deposit_data.amount,
            currency=deposit_data.currency,
            balance_after=new_balance,
            description=deposit_data.description,
            reference_number=reference_number,
            status='PENDING'
        )
        
        try:
            # Add transaction
            self.db.add(transaction)
            
            # Update account balance
            account.balance = new_balance
            
            # Mark transaction as completed
            transaction.status = 'COMPLETED'
            transaction.processed_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(transaction)
            return transaction
            
        except IntegrityError as e:
            self.db.rollback()
            transaction.status = 'FAILED'
            raise ValidationError(f"Error processing deposit: {str(e)}")
    
    def withdraw(
        self,
        account_id: UUID,
        withdrawal_data: WithdrawalRequest
    ) -> Transaction:
        """
        Process a withdrawal transaction.
        
        Args:
            account_id: Account UUID
            withdrawal_data: Withdrawal request data
            
        Returns:
            Created transaction instance
            
        Raises:
            NotFoundError: If account not found
            InsufficientFundsError: If insufficient balance
            TransactionLimitError: If withdrawal limits exceeded
            BusinessRuleViolationError: If account cannot transact
        """
        # Get and validate account
        account = self._get_and_validate_account(account_id, 'CHECKING')
        
        # Validate currency match
        if withdrawal_data.currency != account.currency:
            raise ValidationError(
                f"Currency mismatch. Account currency is {account.currency}"
            )
        
        # Business rule validations
        self._validate_withdrawal_amount(withdrawal_data.amount)
        self._validate_sufficient_funds(account, withdrawal_data.amount)
        self._validate_daily_withdrawal_limit(account_id, withdrawal_data.amount)
        
        # Calculate new balance
        new_balance = account.balance - withdrawal_data.amount
        
        # Generate reference number
        reference_number = self._generate_reference_number()
        
        # Create transaction
        transaction = Transaction(
            account_id=account_id,
            transaction_type='WITHDRAWAL',
            amount=withdrawal_data.amount,
            currency=withdrawal_data.currency,
            balance_after=new_balance,
            description=withdrawal_data.description,
            reference_number=reference_number,
            status='PENDING'
        )
        
        try:
            # Add transaction
            self.db.add(transaction)
            
            # Update account balance
            account.balance = new_balance
            
            # Mark transaction as completed
            transaction.status = 'COMPLETED'
            transaction.processed_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(transaction)
            return transaction
            
        except IntegrityError as e:
            self.db.rollback()
            transaction.status = 'FAILED'
            raise ValidationError(f"Error processing withdrawal: {str(e)}")
    
    def get_transaction(self, transaction_id: UUID) -> Transaction:
        """
        Get transaction by ID.
        
        Args:
            transaction_id: Transaction UUID
            
        Returns:
            Transaction instance
            
        Raises:
            NotFoundError: If transaction not found
        """
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        
        if not transaction:
            raise NotFoundError(f"Transaction with ID {transaction_id} not found")
        
        return transaction
    
    def get_account_transactions(
        self,
        account_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Transaction], int]:
        """
        Get transactions for an account with filtering.
        
        Args:
            account_id: Account UUID
            start_date: Filter from this date
            end_date: Filter until this date
            transaction_type: Filter by type
            status: Filter by status
            limit: Number of results
            offset: Pagination offset
            
        Returns:
            Tuple of (list of transactions, total count)
        """
        query = self.db.query(Transaction).filter(
            Transaction.account_id == account_id
        )
        
        # Apply filters
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        
        if end_date:
            query = query.filter(Transaction.created_at <= end_date)
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        if status:
            query = query.filter(Transaction.status == status)
        
        # Get total count
        total = query.count()
        
        # Order by created_at descending
        query = query.order_by(Transaction.created_at.desc())
        
        # Apply pagination
        transactions = query.limit(limit).offset(offset).all()
        
        return transactions, total
    
    def reverse_transaction(
        self,
        transaction_id: UUID,
        reason: str
    ) -> Transaction:
        """
        Reverse a transaction (admin operation).
        
        Args:
            transaction_id: Transaction UUID
            reason: Reason for reversal
            
        Returns:
            Original transaction (now marked as REVERSED)
            
        Raises:
            NotFoundError: If transaction not found
            BusinessRuleViolationError: If transaction cannot be reversed
        """
        transaction = self.get_transaction(transaction_id)
        
        # Validate transaction can be reversed
        if transaction.status != 'COMPLETED':
            raise BusinessRuleViolationError(
                f"Cannot reverse transaction with status {transaction.status}"
            )
        
        if transaction.is_reversed:
            raise BusinessRuleViolationError("Transaction is already reversed")
        
        # Get account
        account = self.db.query(Account).filter(
            Account.id == transaction.account_id
        ).first()
        
        if not account:
            raise NotFoundError(f"Account {transaction.account_id} not found")
        
        # Reverse the transaction effect on balance
        if transaction.transaction_type == 'DEPOSIT':
            account.balance -= transaction.amount
        elif transaction.transaction_type == 'WITHDRAWAL':
            account.balance += transaction.amount
        
        # Mark transaction as reversed
        transaction.status = 'REVERSED'
        
        try:
            self.db.commit()
            self.db.refresh(transaction)
            return transaction
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error reversing transaction: {str(e)}")
    
    def _get_and_validate_account(
        self,
        account_id: UUID,
        expected_type: str
    ) -> Account:
        """
        Get account and validate it can transact.
        
        Args:
            account_id: Account UUID
            expected_type: Expected account type
            
        Returns:
            Account instance
            
        Raises:
            NotFoundError: If account not found
            BusinessRuleViolationError: If account type mismatch or cannot transact
        """
        account = self.db.query(Account).filter(
            Account.id == account_id
        ).first()
        
        if not account:
            raise NotFoundError(f"Account with ID {account_id} not found")
        
        if account.account_type != expected_type:
            raise BusinessRuleViolationError(
                f"Invalid account type. Expected {expected_type}, got {account.account_type}"
            )
        
        if not account.can_transact():
            raise BusinessRuleViolationError(
                f"Account with status {account.status} cannot perform transactions"
            )
        
        return account
    
    def _validate_withdrawal_amount(self, amount: Decimal) -> None:
        """Validate withdrawal amount against maximum limit."""
        if amount > self.MAX_WITHDRAWAL_AMOUNT:
            raise TransactionLimitError(
                f"Withdrawal amount ${amount} exceeds maximum limit of ${self.MAX_WITHDRAWAL_AMOUNT}"
            )
    
    def _validate_sufficient_funds(self, account: Account, amount: Decimal) -> None:
        """Validate account has sufficient funds."""
        if account.balance < amount:
            raise InsufficientFundsError(
                f"Insufficient funds. Available: ${account.balance}, Requested: ${amount}"
            )
    
    def _validate_daily_withdrawal_limit(
        self,
        account_id: UUID,
        amount: Decimal
    ) -> None:
        """Validate daily withdrawal limit."""
        # Get today's date range
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Sum today's withdrawals
        total_today = self.db.query(
            func.sum(Transaction.amount)
        ).filter(
            and_(
                Transaction.account_id == account_id,
                Transaction.transaction_type == 'WITHDRAWAL',
                Transaction.status == 'COMPLETED',
                Transaction.created_at >= today_start,
                Transaction.created_at < today_end
            )
        ).scalar() or Decimal('0.00')
        
        if total_today + amount > self.DAILY_WITHDRAWAL_LIMIT:
            raise TransactionLimitError(
                f"Daily withdrawal limit exceeded. Limit: ${self.DAILY_WITHDRAWAL_LIMIT}, "
                f"Already withdrawn today: ${total_today}, Requested: ${amount}"
            )
    
    @staticmethod
    def _generate_reference_number() -> str:
        """Generate unique transaction reference number."""
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=6))
        return f"TXN-{timestamp}-{random_suffix}"

