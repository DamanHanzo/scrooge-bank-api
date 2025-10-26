"""
Bank API - Account Service

Business logic for account management operations.
"""

from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
import random
import string

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Account, Customer
from app.schemas.account import AccountCreateRequest
from app.exceptions import NotFoundError, ValidationError, BusinessRuleViolationError


class AccountService:
    """Service class for account-related business logic."""
    
    def __init__(self, db: Session):
        """
        Initialize AccountService.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create_account(self, account_data: AccountCreateRequest) -> Account:
        """
        Create a new account.
        
        Args:
            account_data: Account creation data
            
        Returns:
            Created account instance
            
        Raises:
            NotFoundError: If customer not found
            ValidationError: If validation fails
        """
        # Verify customer exists and is active
        customer = self.db.query(Customer).filter(
            Customer.id == account_data.customer_id
        ).first()
        
        if not customer:
            raise NotFoundError(f"Customer with ID {account_data.customer_id} not found")
        
        if not customer.is_active:
            raise BusinessRuleViolationError("Cannot create account for inactive customer")
        
        # Generate unique account number
        account_number = self._generate_account_number(account_data.account_type)
        
        # Determine initial balance
        initial_balance = Decimal('0.00')
        if account_data.account_type == 'CHECKING' and account_data.initial_deposit:
            initial_balance = account_data.initial_deposit
        
        # Create account
        account = Account(
            customer_id=account_data.customer_id,
            account_type=account_data.account_type,
            account_number=account_number,
            status='ACTIVE',
            balance=initial_balance,
            currency=account_data.currency
        )
        
        try:
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            return account
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error creating account: {str(e)}")
    
    def get_account(self, account_id: UUID) -> Account:
        """
        Get account by ID.
        
        Args:
            account_id: Account UUID
            
        Returns:
            Account instance
            
        Raises:
            NotFoundError: If account not found
        """
        account = self.db.query(Account).filter(
            Account.id == account_id
        ).first()
        
        if not account:
            raise NotFoundError(f"Account with ID {account_id} not found")
        
        return account
    
    def get_account_by_number(self, account_number: str) -> Optional[Account]:
        """
        Get account by account number.
        
        Args:
            account_number: Account number
            
        Returns:
            Account instance or None
        """
        return self.db.query(Account).filter(
            Account.account_number == account_number
        ).first()
    
    def get_customer_accounts(
        self,
        customer_id: UUID,
        account_type: Optional[str] = None
    ) -> List[Account]:
        """
        Get all accounts for a customer.
        
        Args:
            customer_id: Customer UUID
            account_type: Optional filter by account type
            
        Returns:
            List of accounts
        """
        query = self.db.query(Account).filter(
            Account.customer_id == customer_id
        )
        
        if account_type:
            query = query.filter(Account.account_type == account_type)
        
        return query.all()
    
    def get_balance(self, account_id: UUID) -> dict:
        """
        Get account balance.
        
        Args:
            account_id: Account UUID
            
        Returns:
            Dictionary with balance information
            
        Raises:
            NotFoundError: If account not found
        """
        account = self.get_account(account_id)
        
        return {
            'account_id': account.id,
            'account_number': account.account_number,
            'balance': account.balance,
            'currency': account.currency,
            'status': account.status,
            'as_of': datetime.utcnow()
        }
    
    def update_account_status(
        self,
        account_id: UUID,
        new_status: str,
        reason: Optional[str] = None
    ) -> Account:
        """
        Update account status (admin operation).
        
        Args:
            account_id: Account UUID
            new_status: New status (ACTIVE, CLOSED)
            reason: Reason for status change
            
        Returns:
            Updated account instance
            
        Raises:
            NotFoundError: If account not found
            ValidationError: If status is invalid
        """
        account = self.get_account(account_id)
        
        valid_statuses = ['ACTIVE', 'CLOSED']
        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        account.status = new_status
        
        try:
            self.db.commit()
            self.db.refresh(account)
            return account
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error updating account status: {str(e)}")
    
    def close_account(self, account_id: UUID) -> Account:
        """
        Close an account.
        
        Args:
            account_id: Account UUID
            
        Returns:
            Updated account instance
            
        Raises:
            BusinessRuleViolationError: If account has non-zero balance
        """
        account = self.get_account(account_id)
        
        # Cannot close account with non-zero balance
        if account.balance != Decimal('0.00'):
            raise BusinessRuleViolationError(
                f"Cannot close account with non-zero balance. Current balance: {account.balance}"
            )
        
        return self.update_account_status(account_id, 'CLOSED')
    
    def _generate_account_number(self, account_type: str) -> str:
        """
        Generate a unique account number.
        
        Args:
            account_type: Type of account (CHECKING, LOAN)
            
        Returns:
            Unique account number
        """
        prefix = 'CHK' if account_type == 'CHECKING' else 'LOAN'
        
        # Generate random 10-digit number
        while True:
            random_digits = ''.join(random.choices(string.digits, k=10))
            account_number = f"{prefix}-{random_digits}"
            
            # Check if account number already exists
            existing = self.get_account_by_number(account_number)
            if not existing:
                return account_number

