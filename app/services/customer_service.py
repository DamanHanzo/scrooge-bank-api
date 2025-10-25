"""
Bank API - Customer Service

Business logic for customer management operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Customer
from app.schemas.customer import CustomerCreateRequest, CustomerUpdateRequest
from app.exceptions import NotFoundError, ValidationError
from datetime import datetime


class CustomerService:
    """Service class for customer-related business logic."""
    
    def __init__(self, db: Session):
        """
        Initialize CustomerService.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create_customer(self, customer_data: CustomerCreateRequest) -> Customer:
        """
        Create a new customer.
        
        Args:
            customer_data: Customer creation data
            
        Returns:
            Created customer instance
            
        Raises:
            ValidationError: If email already exists or validation fails
        """
        # Check if email already exists
        existing = self.db.query(Customer).filter(
            Customer.email == customer_data.email
        ).first()
        
        if existing:
            raise ValidationError(f"Customer with email {customer_data.email} already exists")
        
        # Create customer instance
        customer = Customer(
            email=customer_data.email,
            first_name=customer_data.first_name,
            last_name=customer_data.last_name,
            date_of_birth=customer_data.date_of_birth,
            phone=customer_data.phone,
            status='ACTIVE'
        )
        
        # Add address if provided
        if customer_data.address:
            customer.address_line_1 = customer_data.address.line_1
            customer.address_line_2 = customer_data.address.line_2
            customer.city = customer_data.address.city
            customer.state = customer_data.address.state
            customer.zip_code = customer_data.address.zip_code
        
        try:
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)
            return customer
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error creating customer: {str(e)}")
    
    def get_customer(self, customer_id: UUID) -> Customer:
        """
        Get customer by ID.
        
        Args:
            customer_id: Customer UUID
            
        Returns:
            Customer instance
            
        Raises:
            NotFoundError: If customer not found
        """
        customer = self.db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer:
            raise NotFoundError(f"Customer with ID {customer_id} not found")
        
        return customer
    
    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """
        Get customer by email.
        
        Args:
            email: Customer email
            
        Returns:
            Customer instance or None
        """
        return self.db.query(Customer).filter(
            Customer.email == email
        ).first()
    
    def update_customer(
        self,
        customer_id: UUID,
        update_data: CustomerUpdateRequest
    ) -> Customer:
        """
        Update customer information.
        
        Args:
            customer_id: Customer UUID
            update_data: Update data
            
        Returns:
            Updated customer instance
            
        Raises:
            NotFoundError: If customer not found
        """
        customer = self.get_customer(customer_id)
        
        # Update fields if provided
        if update_data.first_name is not None:
            customer.first_name = update_data.first_name
        
        if update_data.last_name is not None:
            customer.last_name = update_data.last_name
        
        if update_data.phone is not None:
            customer.phone = update_data.phone
        
        if update_data.address is not None:
            customer.address_line_1 = update_data.address.line_1
            customer.address_line_2 = update_data.address.line_2
            customer.city = update_data.address.city
            customer.state = update_data.address.state
            customer.zip_code = update_data.address.zip_code
        
        try:
            self.db.commit()
            self.db.refresh(customer)
            return customer
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error updating customer: {str(e)}")
    
    def list_customers(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[Customer], int]:
        """
        List customers with optional filtering.
        
        Args:
            status: Filter by status
            limit: Number of results to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (list of customers, total count)
        """
        query = self.db.query(Customer)
        
        # Apply filters
        if status:
            query = query.filter(Customer.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        customers = query.limit(limit).offset(offset).all()
        
        return customers, total
    
    def suspend_customer(self, customer_id: UUID, reason: str) -> Customer:
        """
        Suspend a customer account (admin operation).
        
        Args:
            customer_id: Customer UUID
            reason: Reason for suspension
            
        Returns:
            Updated customer instance
            
        Raises:
            NotFoundError: If customer not found
        """
        customer = self.get_customer(customer_id)
        customer.status = 'SUSPENDED'
        customer.suspended_at = datetime.now()
        customer.suspended_by = reason
        customer.suspended_reason = reason
        self.db.commit()
        self.db.refresh(customer)
        return customer
    
    def activate_customer(self, customer_id: UUID) -> Customer:
        """
        Activate a customer account (admin operation).
        
        Args:
            customer_id: Customer UUID
            
        Returns:
            Updated customer instance
            
        Raises:
            NotFoundError: If customer not found
        """
        customer = self.get_customer(customer_id)
        customer.status = 'ACTIVE'
        customer.suspended_at = None
        customer.suspended_by = None
        customer.suspended_reason = None
        self.db.commit()
        self.db.refresh(customer)
        return customer

